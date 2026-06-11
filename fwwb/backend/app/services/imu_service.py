"""
IMU 数据服务
支持多种接入方式：
  1. TCP 客户端模式（连接网口版 H30 模块，接收透传 YIS 帧）
  2. 串口模式（直接读取 USB-串口版 H30）
  3. UDP JSON 透传模式（接收 Hi3861 通过 UDP 转发的 JSON 数据）
"""
import os
import time
import threading
import socket
from datetime import datetime
from typing import Optional, Dict

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from app.utils.logger import get_logger
from app.utils.imu_protocol import YISProtocolParser, IMUData, IMUJSONParser

logger = get_logger('imu_service')


class IMUService:
    """IMU 数据服务"""

    # 支持的模式
    MODE_TCP = 'tcp'
    MODE_SERIAL = 'serial'
    MODE_UDP_PASSIVE = 'udp_passive'  # 仅接收 Hi3861 UDP JSON 透传

    def __init__(self, app, config):
        self.app = app
        self.config = config

        # 通用配置
        self.enabled = getattr(config, 'IMU_ENABLED', False)
        self.mode = getattr(config, 'IMU_MODE', self.MODE_TCP).lower()

        # TCP 配置（网口版 H30）
        self.tcp_host = getattr(config, 'IMU_TCP_HOST', '192.168.1.200')
        self.tcp_port = getattr(config, 'IMU_TCP_PORT', 8899)
        self.tcp_timeout = getattr(config, 'IMU_TCP_TIMEOUT', 5.0)

        # 串口配置（USB 串口版 H30）
        self.serial_port = getattr(config, 'IMU_SERIAL_PORT', '/dev/ttyUSB0')
        self.serial_baudrate = getattr(config, 'IMU_SERIAL_BAUDRATE', 460800)
        self.serial_timeout = getattr(config, 'IMU_SERIAL_TIMEOUT', 0.1)

        # 运行时状态
        self.serial_conn: Optional['serial.Serial'] = None
        self.tcp_socket: Optional[socket.socket] = None
        self.read_thread: Optional[threading.Thread] = None
        self.running = False

        # 协议解析器（用于 TCP/串口模式的原始 YIS 帧解析）
        self.yis_parser = YISProtocolParser()
        self.yis_parser.on_frame_parsed = self._on_frame_parsed

        # 最新数据缓存
        self.latest_data: Optional[IMUData] = None
        self.last_receive_time: Optional[datetime] = None
        self.frame_count = 0
        self.error_count = 0

        # 数据接收回调（供外部实时推送使用）
        self.on_data_received: Optional[callable] = None

    def start(self) -> bool:
        """启动 IMU 服务"""
        if not self.enabled:
            logger.info("IMU 服务已禁用（IMU_ENABLED=false）")
            return False

        self.running = True

        if self.mode == self.MODE_TCP:
            return self._start_tcp()
        elif self.mode == self.MODE_SERIAL:
            return self._start_serial()
        elif self.mode == self.MODE_UDP_PASSIVE:
            logger.info("IMU 服务以 UDP 被动模式运行（等待 Hi3861 JSON 透传）")
            return True
        else:
            logger.error(f"未知的 IMU 模式: {self.mode}")
            return False

    def _start_tcp(self) -> bool:
        """启动 TCP 客户端模式（连接网口模块）"""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(self.tcp_timeout)
            logger.info(f"正在连接 IMU 网口模块 {self.tcp_host}:{self.tcp_port}...")
            self.tcp_socket.connect((self.tcp_host, self.tcp_port))
            self.tcp_socket.settimeout(1.0)  # 连接后改为非阻塞式超时
            logger.info(f"IMU TCP 连接成功: {self.tcp_host}:{self.tcp_port}")

            self.read_thread = threading.Thread(target=self._tcp_read_loop, daemon=True)
            self.read_thread.start()
            return True
        except socket.timeout:
            logger.error(f"IMU TCP 连接超时: {self.tcp_host}:{self.tcp_port}")
            self._cleanup_tcp()
            return False
        except ConnectionRefusedError:
            logger.error(f"IMU TCP 连接被拒绝: {self.tcp_host}:{self.tcp_port}")
            self._cleanup_tcp()
            return False
        except Exception as e:
            logger.error(f"IMU TCP 启动异常: {e}")
            self._cleanup_tcp()
            return False

    def _start_serial(self) -> bool:
        """启动串口模式"""
        if not SERIAL_AVAILABLE:
            logger.error("IMU 串口模式启动失败: 未安装 pyserial")
            return False

        try:
            port = self._resolve_serial_port()
            if port is None:
                logger.warning(f"IMU 串口设备未找到: {self.serial_port}")
                return False

            self.serial_conn = serial.Serial(
                port=port,
                baudrate=self.serial_baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.serial_timeout
            )
            self.read_thread = threading.Thread(target=self._serial_read_loop, daemon=True)
            self.read_thread.start()
            logger.info(f"IMU 串口服务已启动: {port} @ {self.serial_baudrate}bps")
            return True
        except serial.SerialException as e:
            logger.error(f"IMU 串口打开失败: {e}")
            return False
        except Exception as e:
            logger.error(f"IMU 串口启动异常: {e}")
            return False

    def stop(self):
        """停止 IMU 服务"""
        self.running = False
        self._cleanup_tcp()
        self._cleanup_serial()
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
        logger.info("IMU 服务已停止")

    def _cleanup_tcp(self):
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass
            self.tcp_socket = None

    def _cleanup_serial(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None

    def _resolve_serial_port(self) -> Optional[str]:
        """解析串口设备路径"""
        if os.path.exists(self.serial_port):
            return self.serial_port
        fallback_ports = ['/dev/yesense_imu', '/dev/ttyUSB0', '/dev/ttyUSB1',
                          '/dev/ttyACM0', '/dev/ttyACM1']
        for p in fallback_ports:
            if os.path.exists(p):
                logger.info(f"自动检测到 IMU 串口设备: {p}")
                return p
        return None

    def _tcp_read_loop(self):
        """TCP 读取循环（网口模块透传）"""
        logger.info("IMU TCP 读取线程启动")
        while self.running:
            try:
                if self.tcp_socket:
                    data = self.tcp_socket.recv(4096)
                    if data:
                        frames = self.yis_parser.feed(data)
                        if frames:
                            logger.debug(f"IMU TCP 解析到 {len(frames)} 帧")
                    else:
                        # 对端关闭连接
                        logger.warning("IMU TCP 连接被对端关闭，尝试重连...")
                        self._cleanup_tcp()
                        time.sleep(2)
                        self._start_tcp()
                else:
                    time.sleep(0.5)
            except socket.timeout:
                continue
            except OSError as e:
                if self.running:
                    logger.error(f"IMU TCP 读取错误: {e}")
                    self.error_count += 1
                    self._cleanup_tcp()
                    time.sleep(2)
                    self._start_tcp()
            except Exception as e:
                logger.error(f"IMU TCP 读取线程异常: {e}")
                time.sleep(1)
        logger.info("IMU TCP 读取线程退出")

    def _serial_read_loop(self):
        """串口读取循环"""
        logger.info("IMU 串口读取线程启动")
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    raw = self.serial_conn.read(self.serial_conn.in_waiting or 1)
                    if raw:
                        frames = self.yis_parser.feed(raw)
                        if frames:
                            logger.debug(f"IMU 串口解析到 {len(frames)} 帧")
                else:
                    time.sleep(0.5)
            except serial.SerialException as e:
                logger.error(f"IMU 串口读取错误: {e}")
                self.error_count += 1
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"IMU 串口读取线程异常: {e}")
                time.sleep(0.5)
        logger.info("IMU 串口读取线程退出")

    def _on_frame_parsed(self, imu_data: IMUData):
        """YIS 帧解析完成回调"""
        self.latest_data = imu_data
        self.last_receive_time = datetime.now()
        self.frame_count += 1
        if self.on_data_received:
            try:
                self.on_data_received(imu_data)
            except Exception as e:
                logger.error(f"IMU 数据回调异常: {e}")

    def feed_json(self, json_data: dict):
        """
        接收通过 UDP/JSON 传来的 IMU 数据（Hi3861 透传模式）
        适用于 mode=udp_passive 或作为 tcp/serial 模式的补充
        """
        imu = IMUJSONParser.parse(json_data)
        if imu:
            self.latest_data = imu
            self.last_receive_time = datetime.now()
            self.frame_count += 1
            if self.on_data_received:
                try:
                    self.on_data_received(imu)
                except Exception as e:
                    logger.error(f"IMU JSON 回调异常: {e}")

    def get_latest_data(self) -> Optional[Dict]:
        """获取最新 IMU 数据（字典格式）"""
        if self.latest_data is None:
            return None
        return self.latest_data.to_dict()

    def get_status(self) -> Dict:
        """获取 IMU 服务状态"""
        return {
            'enabled': self.enabled,
            'mode': self.mode,
            'tcp_connected': self.tcp_socket is not None,
            'tcp_host': self.tcp_host,
            'tcp_port': self.tcp_port,
            'serial_connected': self.serial_conn is not None and self.serial_conn.is_open,
            'serial_port': self.serial_port,
            'serial_baudrate': self.serial_baudrate,
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'last_receive_time': self.last_receive_time.isoformat() if self.last_receive_time else None,
            'has_data': self.latest_data is not None
        }
