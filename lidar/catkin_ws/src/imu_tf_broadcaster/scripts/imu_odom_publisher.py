#!/usr/bin/env python3
"""
imu_odom_publisher.py v2

用 IMU AHRS orientation + 加速度积分发布 Odometry 和 odom→base_link TF。
作为 Cartographer 的外部里程计使用。

改进：
  - stamp 用 rospy.Time.now()，避免 IMU 时间戳与 ROS 时间不同步
  - 始终发布 TF，不 early return
  - ZUPT 只减速不停止
  - covariance 合理设置，让 Cartographer 知道里程计质量
"""

import rospy
import numpy as np
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry
import tf2_ros
from geometry_msgs.msg import TransformStamped
import tf.transformations as tft

GRAVITY = 9.80665


class ImuOdomPublisher:
    def __init__(self):
        rospy.init_node('imu_odom_publisher')

        # 位姿状态
        self.position = np.array([0., 0., 0.])
        self.velocity = np.array([0., 0., 0.])
        self.orientation = np.array([0., 0., 0., 1.])
        self.last_imu_time = None

        # 参数
        self.zupt_acc_thresh = rospy.get_param('~zupt_acc_thresh', 0.3)
        self.zupt_gyro_thresh = rospy.get_param('~zupt_gyro_thresh', 0.05)
        self.z_damping = rospy.get_param('~z_damping', 0.95)
        self.imu_topic = rospy.get_param('~imu_topic', '/imu')
        self.odom_topic = rospy.get_param('~odom_topic', '/odom')

        # 发布
        self.odom_pub = rospy.Publisher(self.odom_topic, Odometry, queue_size=10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()

        rospy.Subscriber(self.imu_topic, Imu, self.imu_callback)

        rospy.loginfo(
            "imu_odom_publisher v2 started: zupt_acc=%.2f, zupt_gyro=%.2f, damping=%.2f",
            self.zupt_acc_thresh, self.zupt_gyro_thresh, self.z_damping
        )

    def imu_callback(self, msg):
        q = msg.orientation
        q_arr = np.array([q.x, q.y, q.z, q.w])
        norm = np.linalg.norm(q_arr)
        if norm > 0:
            q_arr /= norm
        self.orientation = q_arr

        # 用 ROS 当前时间，避免 IMU 时间戳不同步
        now = rospy.Time.now()

        if self.last_imu_time is None:
            self.last_imu_time = now
            self.publish(now)
            return

        dt = (now - self.last_imu_time).to_sec()
        if dt <= 0 or dt > 0.1:
            self.last_imu_time = now
            self.publish(now)
            return

        # 加速度转到世界坐标系
        R = tft.quaternion_matrix(self.orientation)[:3, :3]
        acc = np.array([
            msg.linear_acceleration.x,
            msg.linear_acceleration.y,
            msg.linear_acceleration.z
        ])
        acc_world = R @ acc
        acc_world[2] -= GRAVITY

        # ZUPT：加速度 + 角速度都很小 → 认为静止，速度衰减
        gyro = np.array([
            msg.angular_velocity.x,
            msg.angular_velocity.y,
            msg.angular_velocity.z
        ])
        is_stationary = (
            np.linalg.norm(acc_world) < self.zupt_acc_thresh and
            np.linalg.norm(gyro) < self.zupt_gyro_thresh
        )

        if is_stationary:
            self.velocity *= self.z_damping
        else:
            self.velocity += acc_world * dt

        self.position += self.velocity * dt
        self.last_imu_time = now
        self.publish(now)

    def publish(self, stamp):
        # Odometry 消息
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.position[0]
        odom.pose.pose.position.y = self.position[1]
        odom.pose.pose.position.z = self.position[2]
        odom.pose.pose.orientation.x = self.orientation[0]
        odom.pose.pose.orientation.y = self.orientation[1]
        odom.pose.pose.orientation.z = self.orientation[2]
        odom.pose.pose.orientation.w = self.orientation[3]

        # Covariance：位置不确定性较大（IMU 积分漂移），姿态较准（AHRS）
        odom.pose.covariance = [
            0.5, 0, 0, 0, 0, 0,
            0, 0.5, 0, 0, 0, 0,
            0, 0, 0.5, 0, 0, 0,
            0, 0, 0, 0.01, 0, 0,
            0, 0, 0, 0, 0.01, 0,
            0, 0, 0, 0, 0, 0.05
        ]
        odom.twist.covariance = [0.1] + [0] * 34 + [0.1]

        self.odom_pub.publish(odom)

        # TF: odom → base_link
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.position[0]
        t.transform.translation.y = self.position[1]
        t.transform.translation.z = self.position[2]
        t.transform.rotation.x = self.orientation[0]
        t.transform.rotation.y = self.orientation[1]
        t.transform.rotation.z = self.orientation[2]
        t.transform.rotation.w = self.orientation[3]
        self.tf_broadcaster.sendTransform(t)


if __name__ == '__main__':
    node = ImuOdomPublisher()
    rospy.spin()
