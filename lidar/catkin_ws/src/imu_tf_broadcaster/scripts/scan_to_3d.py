#!/usr/bin/env python3
"""
scan_to_3d 节点 v3

订阅 /scan (LaserScan) 和 /imu (sensor_msgs/Imu)，
利用 Cartographer 的 map->base_link 位姿（x, y, yaw）+ IMU AHRS 的 roll/pitch，
将 2D 激光点投影到 3D 世界坐标系，发布 PointCloud2。

v3 改进：
  - IMU 环形缓冲区，按 scan 时间戳插值对齐
  - TF 缓存 + Time(0) 查询，避免时间戳不匹配丢帧
  - base_link->laser 缓存
  - IMU 加速度积分估算 z 高度变化（带 ZUPT 零速修正）
"""

import rospy
import tf2_ros
import numpy as np
from collections import deque
from sensor_msgs.msg import LaserScan, PointCloud2, PointField, Imu
from sensor_msgs import point_cloud2
import tf.transformations as tft


GRAVITY = 9.80665


class ScanTo3D:
    def __init__(self):
        rospy.init_node('scan_to_3d')

        self.tf_buffer = tf2_ros.Buffer(cache_time=rospy.Duration(10.0))
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)

        # 参数
        self.scan_topic = rospy.get_param('~scan_topic', '/scan')
        self.imu_topic = rospy.get_param('~imu_topic', '/imu')
        self.cloud_topic = rospy.get_param('~cloud_topic', '/cloud')
        self.fixed_z = rospy.get_param('~fixed_z', 1.0)
        self.min_range = rospy.get_param('~min_range', 0.3)
        self.max_range = rospy.get_param('~max_range', 20.0)
        self.tf_timeout = rospy.get_param('~tf_timeout', 0.15)
        self.imu_queue_size = rospy.get_param('~imu_queue_size', 400)
        self.enable_z_integration = rospy.get_param('~enable_z_integration', True)
        self.zupt_acc_thresh = rospy.get_param('~zupt_acc_thresh', 0.3)
        self.zupt_gyro_thresh = rospy.get_param('~zupt_gyro_thresh', 0.05)
        self.z_damping = rospy.get_param('~z_damping', 0.95)
        self.z_min = rospy.get_param('~z_min', 0.1)
        self.z_max = rospy.get_param('~z_max', 3.0)

        # 发布 / 订阅
        self.cloud_pub = rospy.Publisher(self.cloud_topic, PointCloud2, queue_size=10)
        rospy.Subscriber(self.scan_topic, LaserScan, self.scan_callback)
        rospy.Subscriber(self.imu_topic, Imu, self.imu_callback)

        # IMU 环形缓冲区: [(stamp, [qx, qy, qz, qw]), ...]
        self.imu_buffer = deque(maxlen=self.imu_queue_size)
        self.imu_buffer.append((rospy.Time(0), np.array([0.0, 0.0, 0.0, 1.0])))

        # 缓存最新成功的 TF
        self.cached_map_to_base = None
        self.cached_base_to_laser = None

        # Z 积分状态
        self.z_offset = self.fixed_z
        self.vz = 0.0
        self.last_imu_time = None
        self.stationary_time = 0.0  # 累积静止时间（秒）
        self.z_return_alpha = rospy.get_param('~z_return_alpha', 0.02)  # 静止时每帧拉回比例

        # 统计
        self.scan_count = 0
        self.drop_count = 0

        rospy.loginfo(
            "scan_to_3d v3 started: fixed_z=%.2f, z_integration=%s, z=%.2f",
            self.fixed_z, self.enable_z_integration, self.z_offset
        )

    # ------------------------------------------------------------------
    # IMU 回调：存入缓冲区 + Z 加速度积分
    # ------------------------------------------------------------------
    def imu_callback(self, msg):
        q = msg.orientation
        q_arr = np.array([q.x, q.y, q.z, q.w])
        norm = np.linalg.norm(q_arr)
        if norm > 0:
            q_arr /= norm
        self.imu_buffer.append((msg.header.stamp, q_arr))

        if not self.enable_z_integration:
            return

        # --- Z 加速度积分 ---
        if self.last_imu_time is not None:
            dt = (msg.header.stamp - self.last_imu_time).to_sec()
            if 0.001 < dt < 0.1:
                # 用 orientation 把加速度旋转到世界坐标系
                R = tft.quaternion_matrix(q_arr)[:3, :3]
                acc_imu = np.array([
                    msg.linear_acceleration.x,
                    msg.linear_acceleration.y,
                    msg.linear_acceleration.z
                ])
                acc_world = R @ acc_imu
                acc_world[2] -= GRAVITY  # 减去重力

                gyro = np.array([
                    msg.angular_velocity.x,
                    msg.angular_velocity.y,
                    msg.angular_velocity.z
                ])

                # ZUPT：加速度 + 角速度都很小 → 认为静止，减速
                is_stationary = (
                    abs(acc_world[2]) < self.zupt_acc_thresh and
                    np.linalg.norm(gyro) < self.zupt_gyro_thresh
                )

                if is_stationary:
                    self.vz *= self.z_damping
                    self.stationary_time += dt
                    # 静止超过 1.5 秒，缓慢把 z 拉回 fixed_z
                    if self.stationary_time > 1.5:
                        self.z_offset = (
                            self.z_offset * (1 - self.z_return_alpha)
                            + self.fixed_z * self.z_return_alpha
                        )
                        # z 接近 fixed_z 时，直接归零
                        if abs(self.z_offset - self.fixed_z) < 0.02:
                            self.z_offset = self.fixed_z
                            self.vz = 0.0
                            self.stationary_time = 0.0
                else:
                    self.vz += acc_world[2] * dt
                    self.stationary_time = 0.0

                self.z_offset += self.vz * dt
                self.z_offset = np.clip(self.z_offset, self.z_min, self.z_max)

        self.last_imu_time = msg.header.stamp

    # ------------------------------------------------------------------
    # 在 IMU 缓冲区中查找最接近 target_stamp 的姿态
    # ------------------------------------------------------------------
    def get_imu_at_time(self, target_stamp):
        n = len(self.imu_buffer)
        if n == 0:
            return np.array([0.0, 0.0, 0.0, 1.0])

        best_idx = 0
        best_diff = abs((self.imu_buffer[0][0] - target_stamp).to_sec())
        for i in range(1, n):
            diff = abs((self.imu_buffer[i][0] - target_stamp).to_sec())
            if diff < best_diff:
                best_diff = diff
                best_idx = i

        if best_diff > 0.05:
            return self.imu_buffer[-1][1]
        return self.imu_buffer[best_idx][1]

    # ------------------------------------------------------------------
    # Scan 回调：投影到 3D
    # ------------------------------------------------------------------
    def scan_callback(self, scan_msg):
        self.scan_count += 1
        scan_stamp = scan_msg.header.stamp

        # 1. 获取 IMU 姿态（时间同步）
        imu_q = self.get_imu_at_time(scan_stamp)
        roll_imu, pitch_imu, _ = tft.euler_from_quaternion(imu_q)

        # 2. 获取 SLAM 的 map -> base_link
        try:
            trans_mb = self.tf_buffer.lookup_transform(
                'map', 'base_link', rospy.Time(0), rospy.Duration(self.tf_timeout)
            )
        except Exception as e:
            if self.cached_map_to_base is None:
                self.drop_count += 1
                rospy.logwarn_throttle(
                    5.0,
                    "TF map->base_link 失败且无缓存: %s (drop=%d/%d)",
                    e, self.drop_count, self.scan_count
                )
                return
            x, y, z, yaw_slam = self.cached_map_to_base
        else:
            x = trans_mb.transform.translation.x
            y = trans_mb.transform.translation.y
            z = trans_mb.transform.translation.z
            q = trans_mb.transform.rotation
            _, _, yaw_slam = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])
            self.cached_map_to_base = (x, y, z, yaw_slam)

        # 3. 合成旋转: roll/pitch from IMU, yaw from SLAM
        q_synthetic = tft.quaternion_from_euler(roll_imu, pitch_imu, yaw_slam)
        R_map_base = tft.quaternion_matrix(q_synthetic)[:3, :3]
        t_map_base = np.array([x, y, self.z_offset])

        # 4. 获取 base_link -> laser（带缓存）
        if self.cached_base_to_laser is None:
            try:
                trans_bl = self.tf_buffer.lookup_transform(
                    'base_link', 'laser', rospy.Time(0), rospy.Duration(self.tf_timeout)
                )
                t_bl = np.array([
                    trans_bl.transform.translation.x,
                    trans_bl.transform.translation.y,
                    trans_bl.transform.translation.z
                ])
                R_bl = tft.quaternion_matrix([
                    trans_bl.transform.rotation.x,
                    trans_bl.transform.rotation.y,
                    trans_bl.transform.rotation.z,
                    trans_bl.transform.rotation.w
                ])[:3, :3]
                self.cached_base_to_laser = (t_bl, R_bl)
            except Exception:
                t_bl = np.array([0.0, 0.0, 0.18])
                R_bl = np.eye(3)
                self.cached_base_to_laser = (t_bl, R_bl)
        else:
            t_bl, R_bl = self.cached_base_to_laser

        # 5. 投影 scan 点到 map 坐标系
        points = []
        angle = scan_msg.angle_min
        for r in scan_msg.ranges:
            if self.min_range < r < self.max_range and not np.isinf(r) and not np.isnan(r):
                p_laser = np.array([r * np.cos(angle), r * np.sin(angle), 0.0])
                p_base = R_bl @ p_laser + t_bl
                p_map = R_map_base @ p_base + t_map_base
                points.append([p_map[0], p_map[1], p_map[2]])
            angle += scan_msg.angle_increment

        if not points:
            return

        # 6. 发布 PointCloud2
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
