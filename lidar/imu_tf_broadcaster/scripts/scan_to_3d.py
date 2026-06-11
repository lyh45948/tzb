#!/usr/bin/env python3
"""
scan_to_3d 节点

订阅 /scan (LaserScan) 和 /imu (sensor_msgs/Imu)，
利用 Cartographer 的 map->base_link 位姿（x, y, yaw）+ IMU AHRS 的 roll/pitch，
将 2D 激光点投影到 3D 世界坐标系，发布 PointCloud2。

手持时通过上下/倾斜改变俯仰角，不同 scan 落在不同 3D 平面上，
累积后由 octomap_server 生成 3D 体素地图。
"""

import rospy
import tf2_ros
import numpy as np
from sensor_msgs.msg import LaserScan, PointCloud2, PointField, Imu
from sensor_msgs import point_cloud2
import tf.transformations as tft


class ScanTo3D:
    def __init__(self):
        rospy.init_node('scan_to_3d')

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # 参数
        self.scan_topic = rospy.get_param('~scan_topic', '/scan')
        self.imu_topic = rospy.get_param('~imu_topic', '/imu')
        self.cloud_topic = rospy.get_param('~cloud_topic', '/cloud')
        self.fixed_z = rospy.get_param('~fixed_z', 1.0)   # 手持高度（米）
        self.min_range = rospy.get_param('~min_range', 0.3)
        self.max_range = rospy.get_param('~max_range', 20.0)

        # 发布 / 订阅
        self.cloud_pub = rospy.Publisher(self.cloud_topic, PointCloud2, queue_size=10)
        rospy.Subscriber(self.scan_topic, LaserScan, self.scan_callback)
        rospy.Subscriber(self.imu_topic, Imu, self.imu_callback)

        # 缓存最新 IMU 姿态
        self.latest_imu_orientation = np.array([0.0, 0.0, 0.0, 1.0])

        rospy.loginfo(
            "scan_to_3d started: fixed_z=%.2f, cloud_topic=%s",
            self.fixed_z, self.cloud_topic
        )

    def imu_callback(self, msg):
        q = msg.orientation
        q_arr = np.array([q.x, q.y, q.z, q.w])
        self.latest_imu_orientation = q_arr / np.linalg.norm(q_arr)

    def scan_callback(self, scan_msg):
        # --- 1. 获取 Cartographer 的 map -> base_link（x, y, yaw）---
        try:
            trans_map_to_base = self.tf_buffer.lookup_transform(
                'map', 'base_link', scan_msg.header.stamp, rospy.Duration(0.1)
            )
        except (tf2_ros.LookupException,
                tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException) as e:
            rospy.logwarn_throttle(5.0, "TF map->base_link failed: %s", e)
            return

        x = trans_map_to_base.transform.translation.x
        y = trans_map_to_base.transform.translation.y
        q = trans_map_to_base.transform.rotation
        _, _, yaw_slam = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])

        # --- 2. 提取 IMU roll/pitch，与 SLAM yaw 合成 ---
        roll_imu, pitch_imu, _ = tft.euler_from_quaternion(
            self.latest_imu_orientation
        )
        q_synthetic = tft.quaternion_from_euler(roll_imu, pitch_imu, yaw_slam)
        R = tft.quaternion_matrix(q_synthetic)[:3, :3]

        # --- 3. 获取 base_link -> laser 静态变换 ---
        try:
            trans_base_to_laser = self.tf_buffer.lookup_transform(
                'base_link', 'laser', scan_msg.header.stamp, rospy.Duration(0.1)
            )
            t_bl = np.array([
                trans_base_to_laser.transform.translation.x,
                trans_base_to_laser.transform.translation.y,
                trans_base_to_laser.transform.translation.z
            ])
            R_bl = tft.quaternion_matrix([
                trans_base_to_laser.transform.rotation.x,
                trans_base_to_laser.transform.rotation.y,
                trans_base_to_laser.transform.rotation.z,
                trans_base_to_laser.transform.rotation.w
            ])[:3, :3]
        except Exception:
            # 默认值与 AGENTS.md 一致：base_link -> laser = 0 0 0.18
            t_bl = np.array([0.0, 0.0, 0.18])
            R_bl = np.eye(3)

        # --- 4. 投影 scan 点到 3D 世界坐标系 ---
        points = []
        angle = scan_msg.angle_min
        for r in scan_msg.ranges:
            if self.min_range < r < self.max_range and not np.isinf(r) and not np.isnan(r):
                # laser 坐标系
                p_laser = np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
                # base_link 坐标系
                p_base = R_bl @ p_laser + t_bl
                # map 坐标系
                p_world = R @ p_base + np.array([x, y, self.fixed_z])
                points.append([p_world[0], p_world[1], p_world[2]])
            angle += scan_msg.angle_increment

        if not points:
            return

        # --- 5. 发布 PointCloud2 ---
        header = rospy.Header()
        header.stamp = rospy.Time.now()
        header.frame_id = 'map'
        fields = [
            PointField('x', 0, PointField.FLOAT32, 1),
            PointField('y', 4, PointField.FLOAT32, 1),
            PointField('z', 8, PointField.FLOAT32, 1),
        ]
        cloud_msg = point_cloud2.create_cloud(header, fields, points)
        self.cloud_pub.publish(cloud_msg)


if __name__ == '__main__':
    node = ScanTo3D()
    rospy.spin()
