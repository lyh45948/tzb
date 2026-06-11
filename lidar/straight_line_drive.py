#!/usr/bin/env python3
"""
直线行驶控制脚本 - 用于 SLAM 轮速标定测试

核心优化：
  1. 使用纯 JOY 协议（只发 joyX/joyY，不带 carStatus）
     - 避免 Hi3861 向 STM32 连发两条 UART 命令
     - 避免 STM32 在 RUN ↔ JOYSTICK 状态间切换导致的断续
     - joyY = 100（前进），joyY = -100（后退）
  2. 心跳间隔 100ms，保证控制连续
  3. 里程累计：通过 /odom 坐标增量累加
"""

import argparse
import json
import math
import os
import shlex
import socket
import subprocess
import sys
import time


class Driver:
    DEFAULT_CAR_IP = "192.168.1.8"
    DEFAULT_CAR_PORT = 7788
    SPEED = {"low": 0.5, "middle": 0.8, "high": 1.1}
    CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".wheel_calibration")

    def __init__(self, car_ip, car_port, target_distance, speed_gear="low", manual=False, joy_correction=0):
        self.car_ip = car_ip
        self.car_port = car_port
        self.target_distance = target_distance
        self.speed_gear = speed_gear
        self.manual = manual
        self.joy_correction = joy_correction  # joyX 修正值（-30 ~ 30）
        self.running = False
        self.start_time = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        # odom 读数状态
        self.last_odom_pos = None   # 上一次 (x, y)
        self.odom_accum_dist = 0.0  # 累积行驶距离
        self.udp_fail_count = 0     # UDP 发送失败计数

    def _send(self, d, debug_print=True):
        """发送 UDP 命令，返回是否成功"""
        try:
            payload = json.dumps(d, ensure_ascii=False).encode()
            self.sock.sendto(payload, (self.car_ip, self.car_port))
            if debug_print:
                print(f"  [UDP] {payload.decode()}")
            self.udp_fail_count = 0
            return True
        except Exception as e:
            self.udp_fail_count += 1
            print(f"  [错误] UDP 发送失败 ({self.udp_fail_count}): {e}")
            if self.udp_fail_count >= 5:
                print("  [严重] 连续5次发送失败，强制停车")
                self.running = False
            return False

    def _read_odom(self):
        """读取 /odom 当前坐标和速度，返回 (x, y, v, w) 或 None"""
        py_code = (
            "import rospy\n"
            "from nav_msgs.msg import Odometry\n"
            "import sys\n"
            "rospy.init_node('odom_reader', anonymous=True)\n"
            "pos = None\n"
            "twist = None\n"
            "def cb(msg):\n"
            "    global pos, twist\n"
            "    p = msg.pose.pose.position\n"
            "    t = msg.twist.twist\n"
            "    pos = (p.x, p.y)\n"
            "    twist = (t.linear.x, t.angular.z)\n"
            "sub = rospy.Subscriber('/odom', Odometry, cb)\n"
            "rospy.sleep(0.8)\n"
            "if pos and twist:\n"
            "    print(f'ODOM:{pos[0]:.6f},{pos[1]:.6f},{twist[0]:.4f},{twist[1]:.4f}')\n"
            "sys.stdout.flush()\n"
        )
        try:
            result = subprocess.run(
                ["docker", "exec", "ros_container", "bash", "-c",
                 "source /opt/ros/noetic/setup.bash && source /catkin_ws/devel/setup.bash && "
                 f"python3 -u -c {shlex.quote(py_code)}"],
                capture_output=True, text=True, timeout=10
            )
            for line in reversed(result.stdout.strip().split('\n')):
                if line.startswith("ODOM:"):
                    parts = line.split(":", 1)[1].split(",")
                    return (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        except Exception as e:
            print(f"  [警告] 读取 /odom 失败: {e}")
        return None

    def start_car(self):
        print(f"\n{'='*60}")
        print(f"启动直线行驶")
        print(f"  目标距离: {self.target_distance:.2f} m")
        print(f"  速度档位: {self.speed_gear}")
        print(f"  目标IP  : {self.car_ip}:{self.car_port}")
        print(f"  方向修正: joyX = {self.joy_correction}")
        print(f"{'='*60}\n")
        print("  [提示] 如需准确 /odom 读数，请确保 fwwb 后端已运行")
        print("         cd /home/tzb/tzb/fwwb/backend && python main.py\n")

        # 初始化序列（只发一次）
        self._send({"carStatus": "on"})
        time.sleep(0.3)
        self._send({"carMode": "manual"})
        time.sleep(0.2)
        self._send({"carSpeed": self.speed_gear})
        time.sleep(0.2)

        # 启动后，只发送 JOY 命令（避免状态切换导致的断续）
        # joyY = 100: 前进（正值=前进）
        # joyX: 修正量（正值向右，负值向左）
        self._send({"joyX": self.joy_correction, "joyY": 100})
        self.running = True
        self.start_time = time.time()

        # 初始化 odom 位置
        print("  [初始化] 读取 odom 起点...")
        for _ in range(5):
            odom = self._read_odom()
            if odom is not None:
                self.last_odom_pos = (odom[0], odom[1])
                print(f"  [初始化] odom 起点: ({odom[0]:.4f}, {odom[1]:.4f})")
                break
            time.sleep(0.5)
        if self.last_odom_pos is None:
            print("  [警告] 无法读取 /odom，里程计将不可用")

    def stop_car(self):
        self._send({"joyX": 0, "joyY": 0})
        time.sleep(0.1)
        self._send({"carStatus": "stop"})
        time.sleep(0.1)
        self._send({"joyX": 0, "joyY": 0})
        self.running = False

        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"\n{'='*60}")
        print(f"行驶结束")
        print(f"  目标距离: {self.target_distance:.2f} m")
        print(f"  /odom 累积: {self.odom_accum_dist:.4f} m")
        print(f"  用时: {elapsed:.2f} s")
        if elapsed > 0:
            print(f"  平均速度: {self.odom_accum_dist/elapsed:.3f} m/s")
        print(f"{'='*60}\n")
        print("  [提示] 请用卷尺测量实际距离，对比 odom 误差")

    def run(self):
        if not self.manual:
            self.start_car()
        else:
            print(f"\n手动模式 - 按 Ctrl+C 结束")
            self.start_time = time.time()
            self.running = True

        last_joy_time = 0
        last_print_time = 0
        odom_fail_count = 0

        try:
            while self.running:
                now = time.time()

                # 每 100ms 发送一次 JOY 心跳（更频繁，保证控制连续）
                if now - last_joy_time >= 0.1:
                    self._send({"joyX": self.joy_correction, "joyY": 100}, debug_print=False)
                    last_joy_time = now

                # 每 1.0s 读取一次 /odom 并更新里程
                if now - last_print_time >= 1.0:
                    odom = self._read_odom()
                    if odom is not None and self.last_odom_pos is not None:
                        dx = odom[0] - self.last_odom_pos[0]
                        dy = odom[1] - self.last_odom_pos[1]
                        step_dist = math.sqrt(dx * dx + dy * dy)
                        self.odom_accum_dist += step_dist
                        self.last_odom_pos = (odom[0], odom[1])
                        odom_fail_count = 0
                        # 显示：累积距离、当前线速度、角速度（偏航）
                        print(f"  里程: {self.odom_accum_dist:6.3f}m / {self.target_distance:.1f}m  "
                              f"| v={odom[2]:.3f}m/s  w={math.degrees(odom[3]):.1f}°/s")
                        # 到达目标距离自动停止
                        if self.odom_accum_dist >= self.target_distance:
                            print(f"\n  [完成] 到达目标距离!")
                            self.stop_car()
                            break
                    elif odom is not None and self.last_odom_pos is None:
                        self.last_odom_pos = (odom[0], odom[1])
                    else:
                        odom_fail_count += 1
                        if odom_fail_count >= 3:
                            print(f"  [警告] 连续 {odom_fail_count} 次无法读取 /odom")
                    last_print_time = now

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n  [中断] 用户停止")
            self.stop_car()


def load_car_ip():
    """从 fwwb 后端 .env 读取小车 IP"""
    try:
        with open("/home/tzb/tzb/fwwb/backend/.env") as f:
            for line in f:
                if line.startswith("HI3861_IP="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return Driver.DEFAULT_CAR_IP


def load_calibration():
    """从校准文件读取 joyX 修正值"""
    try:
        with open(Driver.CALIBRATION_FILE) as f:
            for line in f:
                if line.startswith("joy_correction="):
                    return int(line.strip().split("=", 1)[1])
    except Exception:
        pass
    return 0


def save_calibration(joy_correction):
    """保存 joyX 修正值到文件"""
    try:
        with open(Driver.CALIBRATION_FILE, "w") as f:
            f.write(f"# 轮速校准: joyX 修正值\n")
            f.write(f"# 正值 = 向右修正，负值 = 向左修正\n")
            f.write(f"joy_correction={joy_correction}\n")
        print(f"  [保存] 校准值已写入: {Driver.CALIBRATION_FILE}")
        return True
    except Exception as e:
        print(f"  [错误] 无法写入校准文件: {e}")
        return False


def test_basic_control(car_ip, car_port):
    """测试基础 UDP 控制：前进 3 秒、停止"""
    print(f"\n{'='*60}")
    print("UDP 控制测试模式")
    print(f"  目标: {car_ip}:{car_port}")
    print(f"{'='*60}\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)

    def send(d):
        payload = json.dumps(d, ensure_ascii=False).encode()
        sock.sendto(payload, (car_ip, car_port))
        print(f"  [发送] {payload.decode()}")

    print("[步骤1] 开机 + 手动模式 + 低速档")
    send({"carStatus": "on"})
    time.sleep(0.3)
    send({"carMode": "manual"})
    time.sleep(0.2)
    send({"carSpeed": "low"})
    time.sleep(0.2)

    print("[步骤2] 纯 JOY 前进 (持续 3 秒，100ms 心跳)")
    for i in range(30):
        send({"joyX": 0, "joyY": 100})
        time.sleep(0.1)

    print("[步骤3] 停止")
    send({"joyX": 0, "joyY": 0})
    time.sleep(0.1)
    send({"carStatus": "stop"})

    print("\n测试完成。观察小车是否丝滑移动。\n")
    sock.close()


def main():
    parser = argparse.ArgumentParser(description="SLAM 轮速标定脚本")
    parser.add_argument("--distance", "-d", type=float, default=5.0,
                        help="目标行驶距离 (米)，默认 5.0m")
    parser.add_argument("--ip", type=str, default=None,
                        help="小车 IP (默认从 fwwb backend .env 读取)")
    parser.add_argument("--port", type=int, default=7788,
                        help="小车 UDP 端口，默认 7788")
    parser.add_argument("--speed", "-s", type=str, default="low",
                        choices=["low", "middle", "high"],
                        help="速度档位，默认 low")
    parser.add_argument("--manual", "-m", action="store_true",
                        help="手动模式：不自动启动，按 Ctrl+C 结束")
    parser.add_argument("--test", "-t", action="store_true",
                        help="仅测试 UDP 控制，不跑里程计")
    parser.add_argument("--joy-correction", "-j", type=int, default=None,
                        help="joyX 修正值（-30~30，正值向右，负值向左），默认从校准文件读取")
    parser.add_argument("--save-calibration", type=int, metavar="VALUE",
                        help="只保存 joyX 修正值到校准文件，不启动小车")

    args = parser.parse_args()

    ip = args.ip or load_car_ip()

    # 只保存校准值，不运行
    if args.save_calibration is not None:
        val = max(-30, min(30, args.save_calibration))
        print(f"保存 joyX 校准值: {val}")
        save_calibration(val)
        return

    # 测试模式
    if args.test:
        test_basic_control(ip, args.port)
        return

    # 读取校准值
    joy_correction = args.joy_correction
    if joy_correction is None:
        joy_correction = load_calibration()
        if joy_correction != 0:
            print(f"  [读取] 从校准文件读取 joy_correction = {joy_correction}")
    joy_correction = max(-30, min(30, joy_correction))  # 限制范围

    driver = Driver(ip, args.port, args.distance, args.speed, args.manual, joy_correction)
    driver.run()


if __name__ == "__main__":
    main()
