#!/usr/bin/env python3
"""
IMU 里程计节点

订阅 /imu (sensor_msgs/Imu)，利用 AHRS 姿态 + 加速度积分得到位置，
发布 odom -> base_link 的 TF 变换和 /imu_odom 话题。

包含简单的零速检测（ZUPT）：当加速度模接近重力且角速度接近零时，
判定为静止，将速度清零以抑制漂移。
"""

import rospy
import tf2_ros
import numpy as np
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Quaternion
import tf.transformations as tft


class ImuOdom:
    def __init__(self):
        rospy.init_node('imu_odom')

        # 参数
        self.imu_topic = rospy.get_param('~imu_topic', '/imu')
        self.odom_topic = rospy.get_param('~odom_topic', '/imu_odom')
        self.odom_frame = rospy.get_param('~odom_frame', 'odom')
        self.base_frame = rospy.get_param('~base_frame', 'base_link')
        self.pub_tf = rospy.get_param('~pub_tf', True)

        # 零速检测阈值
        self.zupt_acc_thresh = rospy.get_param('~zupt_acc_thresh', 0.15)   # m/s^2
        self.zupt_gyro_thresh = rospy.get_param('~zupt_gyro_thresh', 0.05) # rad/s
        self.gravity = rospy.get_param('~gravity', 9.80665)

        # 状态变量
        self.prev_time = None
        self.position = np.array([0.0, 0.0, 0.0])
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.orientation = np.array([0.0, 0.0, 0.0, 1.0])  # x,y,z,w

        # 发布器
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()
        self.odom_pub = rospy.Publisher(self.odom_topic, Odometry, queue_size=10)

        # 订阅器
        rospy.Subscriber(self.imu_topic, Imu, self.imu_callback)

        rospy.loginfo(
            "IMU Odom started: imu_topic=%s, odom_frame=%s, base_frame=%s",
            self.imu_topic, self.odom_frame, self.base_frame
        )

    def imu_callback(self, msg):
        # 使用系统当前时间作为所有输出时间戳，避免与激光雷达/RViz 时间不同步
        curr_time = rospy.Time.now()
        if self.prev_time is None:
            self.prev_time = curr_time
            # 初始化姿态
            q = msg.orientation
            self.orientation = np.array([q.x, q.y, q.z, q.w])
            return

        dt = (curr_time - self.prev_time).to_sec()
        if dt <= 0 or dt > 0.5:
            self.prev_time = curr_time
            return
        self.prev_time = curr_time

        # --- 1. 更新姿态：直接使用 IMU 的 orientation（AHRS 已融合） ---
        q = msg.orientation
        q_new = np.array([q.x, q.y, q.z, q.w])
        q_new = q_new / np.linalg.norm(q_new)
        self.orientation = q_new

        # --- 2. 零速检测（ZUPT）---
        acc_body = np.array([
            msg.linear_acceleration.x,
            msg.linear_acceleration.y,
            msg.linear_acceleration.z
        ])
        gyro_body = np.array([
            msg.angular_velocity.x,
            msg.angular_velocity.y,
            msg.angular_velocity.z
        ])

        acc_norm = np.linalg.norm(acc_body)
        gyro_norm = np.linalg.norm(gyro_body)

        is_stationary = (
            abs(acc_norm - self.gravity) < self.zupt_acc_thresh
            and gyro_norm < self.zupt_gyro_thresh
        )

        if is_stationary:
            # 静止时速度清零，抑制漂移
            self.velocity[:] = 0.0
            # 注意：不能 return，必须继续发布 TF，否则 TF 链会断裂

        # --- 3. 加速度转到世界坐标系并减去重力 ---
        # 净加速度在机体坐标系下 = 测量加速度 - R^T * gravity_world
        # gravity_world = [0, 0, gravity]
        R = tft.quaternion_matrix(self.orientation)[:3, :3]  # 世界->机体
        gravity_body = R.T @ np.array([0.0, 0.0, self.gravity])
        net_acc_body = acc_body - gravity_body

        # 转到世界坐标系
        net_acc_world = R @ net_acc_body

        # --- 4. 积分更新速度和位置 ---
        self.velocity += net_acc_world * dt
        self.position += self.velocity * dt + 0.5 * net_acc_world * dt * dt

        # --- 5. 发布 odom -> base_link TF ---
        if self.pub_tf:
            t = TransformStamped()
            # TF 时间戳也用系统当前时间，确保与 static_transform_publisher / cartographer 同步
            t.header.stamp = rospy.Time.now()
            t.header.frame_id = self.odom_frame
            t.child_frame_id = self.base_frame
            t.transform.translation.x = self.position[0]
            t.transform.translation.y = self.position[1]
            t.transform.translation.z = self.position[2]
            t.transform.rotation.x = self.orientation[0]
            t.transform.rotation.y = self.orientation[1]
            t.transform.rotation.z = self.orientation[2]
            t.transform.rotation.w = self.orientation[3]
            self.tf_broadcaster.sendTransform(t)

        # --- 6. 发布 Odometry 消息 ---
        odom = Odometry()
        odom.header.stamp = rospy.Time.now()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.position[0]
        odom.pose.pose.position.y = self.position[1]
        odom.pose.pose.position.z = self.position[2]
        odom.pose.pose.orientation.x = self.orientation[0]
        odom.pose.pose.orientation.y = self.orientation[1]
        odom.pose.pose.orientation.z = self.orientation[2]
        odom.pose.pose.orientation.w = self.orientation[3]
        odom.twist.twist.linear.x = self.velocity[0]
        odom.twist.twist.linear.y = self.velocity[1]
        odom.twist.twist.linear.z = self.velocity[2]
        odom.twist.twist.angular.x = gyro_body[0]
        odom.twist.twist.angular.y = gyro_body[1]
        odom.twist.twist.angular.z = gyro_body[2]
        self.odom_pub.publish(odom)


if __name__ == '__main__':
    node = ImuOdom()
    rospy.spin()
