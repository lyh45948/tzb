#!/usr/bin/env python3
"""
wheel_odom_publisher.py (v3.5 - Phase 3 优化版)

接收来自 fwwb 后端的 UDP 轮速数据（L_spd / R_spd），
使用差速模型积分计算位置，结合 IMU 自适应修正角度和角速度。

改进 (v3)：
  - 自适应互补滤波 alpha：静止时信任 IMU，运动时信任轮速
  - IMU 角速度融合：用 IMU angular_velocity.z 修正角速度
  - 所有滤波参数可通过 ROS param 调整
  - 改进协方差估计

Phase 3 优化 (v3.5)：
  - 静止状态零漂抑制：当原始轮速接近0时强制清零，避免积分漂移
  - 运动状态协方差动态调整：低速时增大协方差，反映不确定性
  - 静止时完全信任 IMU 角度，不做轮速预测

参数：
  ~udp_port          : 监听端口 (default: 7799)
  ~udp_timeout       : socket 超时秒数 (default: 1.0)
  ~scale_factor      : L_spd → m/s 的系数 (default: 0.0004825)
  ~wheel_base        : 轮距，单位 m (default: 0.286)
  ~odom_topic        : 发布的话题名 (default: /odom)
  ~odom_frame_id     : odom frame (default: odom)
  ~child_frame_id    : base frame (default: base_link)
  ~publish_rate      : 最大发布频率 Hz (default: 20)
  ~imu_topic         : IMU 话题 (default: /imu)
  ~use_imu_angle     : 是否用 IMU 修正角度 (default: true)
  ~alpha_static      : 静止时轮速权重 (default: 0.3, 越小越信任 IMU)
  ~alpha_moving      : 运动时轮速权重 (default: 0.7, 越大越信任轮速)
  ~speed_threshold   : 静止判定阈值 m/s (default: 0.05)
"""

import rospy
import socket
import json
import math
import numpy as np
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from geometry_msgs.msg import TransformStamped
import tf2_ros
import tf.transformations as tft


class WheelOdomPublisher:
    def __init__(self):
        rospy.init_node('wheel_odom_publisher')

        # 参数
        self.udp_port = rospy.get_param('~udp_port', 7799)
        self.udp_timeout = rospy.get_param('~udp_timeout', 1.0)
        self.scale_factor = rospy.get_param('~scale_factor', 0.0004825)
        self.wheel_base = rospy.get_param('~wheel_base', 0.286)
        self.odom_topic = rospy.get_param('~odom_topic', '/odom')
        self.odom_frame_id = rospy.get_param('~odom_frame_id', 'odom')
        self.child_frame_id = rospy.get_param('~child_frame_id', 'base_link')
        self.publish_rate = rospy.get_param('~publish_rate', 20.0)
        self.imu_topic = rospy.get_param('~imu_topic', '/imu')
        self.use_imu_angle = rospy.get_param('~use_imu_angle', True)

        # 自适应互补滤波参数
        self.alpha_static = rospy.get_param('~alpha_static', 0.3)    # 静止时：30%轮速+70%IMU
        self.alpha_moving = rospy.get_param('~alpha_moving', 0.7)    # 运动时：70%轮速+30%IMU
        self.speed_threshold = rospy.get_param('~speed_threshold', 0.05)  # 静止判定 m/s

        # Phase 3 新增：零漂抑制与协方差动态调整参数
        self.zero_drift_threshold = rospy.get_param('~zero_drift_threshold', 3.0)  # 原始值阈值，|L_spd|,|R_spd| < 此值视为静止
        self.low_speed_threshold = rospy.get_param('~low_speed_threshold', 0.1)    # 低速阈值 m/s
        self.max_speed_jump = rospy.get_param('~max_speed_jump', 0.5)              # 最大允许速度跳变 m/s

        # 里程计状态
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0          # 当前使用的角度（可能是 IMU 修正后的）
        self.theta_wheel = 0.0    # 纯轮速积分角度
        self.last_time = None
        self.last_l_spd = 0.0
        self.last_r_spd = 0.0
        self.data_timeout = rospy.Duration(0.5)
        self.last_data_time = rospy.Time(0)
        self.got_first_data = False

        # IMU 状态
        self.imu_yaw = None           # IMU 当前 yaw
        self.imu_available = False
        self.imu_last_time = None
        self.imu_wz = 0.0             # IMU 角速度 (yaw rate)

        # 发布器
        self.odom_pub = rospy.Publisher(self.odom_topic, Odometry, queue_size=10)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster()

        # 订阅 IMU
        if self.use_imu_angle:
            rospy.Subscriber(self.imu_topic, Imu, self._imu_callback)
            rospy.loginfo("等待 IMU 数据用于角度修正...")

        # UDP Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(self.udp_timeout)
        self.sock.bind(('0.0.0.0', self.udp_port))

        rospy.loginfo(
            "wheel_odom_publisher v3 started: port=%d, scale=%.6f, wheel_base=%.3f, imu_angle=%s, alpha=[%.1f/%.1f]",
            self.udp_port, self.scale_factor, self.wheel_base, self.use_imu_angle,
            self.alpha_static, self.alpha_moving
        )

        # 主循环
        self._run()

    def _imu_callback(self, msg):
        """IMU 回调：提取 yaw 角和角速度"""
        q = msg.orientation
        _, _, yaw = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])
        self.imu_yaw = yaw
        self.imu_wz = msg.angular_velocity.z
        self.imu_last_time = msg.header.stamp

        if not self.imu_available:
            self.imu_available = True
            rospy.loginfo("✓ IMU 已连接，使用 IMU 修正角度 (yaw=%.1f°)", math.degrees(yaw))

    def _get_imu_yaw(self):
        """获取 IMU yaw，如果可用的话"""
        if self.imu_available and self.imu_yaw is not None:
            return self.imu_yaw
        return None

    def _run(self):
        rate = rospy.Rate(self.publish_rate)
        while not rospy.is_shutdown():
            # 非阻塞尝试收包
            for _ in range(10):
                try:
                    data, addr = self.sock.recvfrom(1024)
                    self._handle_packet(data)
                except socket.timeout:
                    break
                except OSError:
                    break

            now = rospy.Time.now()

            dt = (now - self.last_time).to_sec() if self.last_time else 0.0
            if dt <= 0 or dt > 0.1:
                dt = 1.0 / self.publish_rate

            if (now - self.last_data_time) > self.data_timeout:
                self.last_l_spd = 0.0
                self.last_r_spd = 0.0

            self._update_odometry(self.last_l_spd, self.last_r_spd, dt, now)
            self.last_time = now
            rate.sleep()

    def _handle_packet(self, data):
        try:
            json_data = json.loads(data.decode('utf-8'))
            l_spd = json_data.get('L_spd')
            r_spd = json_data.get('R_spd')
            if l_spd is None or r_spd is None:
                return
            self.last_l_spd = float(l_spd)
            self.last_r_spd = float(r_spd)
            self.last_data_time = rospy.Time.now()
            if not self.got_first_data:
                self.got_first_data = True
                rospy.loginfo("✓ 首次收到轮速数据: L_spd=%.1f, R_spd=%.1f", self.last_l_spd, self.last_r_spd)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            rospy.logdebug("UDP JSON 解析失败: %s", e)

    def _update_odometry(self, l_spd, r_spd, dt, stamp):
        # ==================== Phase 3: 零漂抑制 ====================
        # 当原始轮速接近0时，视为静止状态，强制清零速度
        is_stationary = abs(l_spd) < self.zero_drift_threshold and abs(r_spd) < self.zero_drift_threshold
        if is_stationary:
            l_spd = 0.0
            r_spd = 0.0

        # 原始单位 → m/s
        vL = l_spd * self.scale_factor
        vR = r_spd * self.scale_factor

        # 差速模型
        v = (vL + vR) / 2.0
        w_wheel = (vR - vL) / self.wheel_base

        # ==================== 自适应互补滤波 alpha ====================
        # 静止时信任 IMU（alpha 小），运动时信任轮速（alpha 大）
        speed = abs(v)
        if speed < self.speed_threshold or is_stationary:
            alpha = self.alpha_static   # 默认 0.3: 30%轮速 + 70%IMU
        else:
            alpha = self.alpha_moving   # 默认 0.7: 70%轮速 + 30%IMU

        # ==================== 角度计算 ====================
        # 纯轮速积分角度（用于无 IMU 时）
        self.theta_wheel += w_wheel * dt

        # 获取 IMU yaw
        imu_yaw = self._get_imu_yaw()

        if imu_yaw is not None:
            # ---- 角度融合：轮速预测 + IMU yaw 互补 ----
            theta_pred = self.theta + w_wheel * dt

            # IMU 角度差（处理 ±π 跳变）
            d_theta = imu_yaw - self.theta
            if d_theta > math.pi:
                d_theta -= 2 * math.pi
            elif d_theta < -math.pi:
                d_theta += 2 * math.pi

            # 自适应互补滤波
            self.theta = theta_pred * alpha + (self.theta + d_theta) * (1 - alpha)

            # 规范化到 [-π, π]
            self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

            # ---- 角速度融合：轮速差 + IMU 角速度 ----
            w_fused = alpha * w_wheel + (1 - alpha) * self.imu_wz
        else:
            # 无 IMU：纯轮速积分
            self.theta = self.theta_wheel
            w_fused = w_wheel

        # 位置积分（用当前角度）
        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt

        # ==================== 构造消息 ====================
        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.odom_frame_id
        odom.child_frame_id = self.child_frame_id

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0

        odom.pose.pose.orientation.x = 0.0
        odom.pose.pose.orientation.y = 0.0
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)

        # ==================== Phase 3: 协方差动态调整 ====================
        # 根据运动状态和 IMU 可用性动态调整协方差
        if is_stationary:
            # 静止：高置信度（零漂已抑制）
            pos_cov = 0.005
            yaw_cov = 0.005
        elif speed < self.low_speed_threshold:
            # 低速运动：不确定性较高（轮速信噪比差）
            if imu_yaw is not None:
                pos_cov = 1.0
                yaw_cov = 0.1
            else:
                pos_cov = 2.0
                yaw_cov = 0.5
        elif imu_yaw is not None:
            # 中高速 + 有 IMU：标准置信度
            pos_cov = 0.5
            yaw_cov = 0.05
        else:
            # 中高速 + 无 IMU：较低置信度
            pos_cov = 1.0
            yaw_cov = 0.2

        odom.pose.covariance = [
            pos_cov, 0, 0, 0, 0, 0,
            0, pos_cov, 0, 0, 0, 0,
            0, 0, 0.01, 0, 0, 0,
            0, 0, 0, 0.01, 0, 0,
            0, 0, 0, 0, 0.01, 0,
            0, 0, 0, 0, 0, yaw_cov
        ]

        odom.twist.twist.linear.x = v
        odom.twist.twist.linear.y = 0.0
        odom.twist.twist.linear.z = 0.0
        odom.twist.twist.angular.x = 0.0
        odom.twist.twist.angular.y = 0.0
        odom.twist.twist.angular.z = w_fused

        self.odom_pub.publish(odom)

        # TF: odom → base_link
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = self.odom_frame_id
        t.child_frame_id = self.child_frame_id
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = math.sin(self.theta / 2.0)
        t.transform.rotation.w = math.cos(self.theta / 2.0)
        self.tf_broadcaster.sendTransform(t)

    def __del__(self):
        if hasattr(self, 'sock') and self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


if __name__ == '__main__':
    try:
        node = WheelOdomPublisher()
    except rospy.ROSInterruptException:
        pass
