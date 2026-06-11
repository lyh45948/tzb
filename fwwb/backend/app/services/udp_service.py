"""
UDP通信服务 - 支持多辆小车同时连接
每辆小车有独立的socket、接收线程和心跳线程
"""
import socket
import threading
import json
import time
from datetime import datetime
from app.utils.logger import get_logger
from app.utils.protocol import ProtocolParser

logger = get_logger('udp_service')


class CarConnection:
    """单个小车的连接封装"""

    def __init__(self, device_id, car_ip, car_port, data_service):
        self.device_id = device_id
        self.car_ip = car_ip
        self.car_port = car_port
        self.data_service = data_service

        self.connected = False
        self.running = False
        self.connection_acknowledged = False

        self.udp_socket = None
        self.receive_thread = None
        self.heartbeat_thread = None

        self.latest_data = None
        self.last_receive_time = None
        self.last_save_time = 0

        self.on_data_received = None
        self.on_connection_change = None

        self.forward_socket = None
        self.forward_addr = ('127.0.0.1', 7799)

    def start(self):
        """启动连接"""
        try:
            logger.info(f"[{self.device_id}] 正在连接小车: {self.car_ip}:{self.car_port}")

            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.settimeout(1.0)
            self.udp_socket.bind(('0.0.0.0', 0))

            try:
                self.forward_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.forward_socket.setblocking(False)
            except Exception as e:
                logger.warning(f"[{self.device_id}] ROS转发Socket初始化失败: {e}")
                self.forward_socket = None

            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

            self._send_init_command()

            start_time = time.time()
            while not self.connection_acknowledged:
                if time.time() - start_time > 3.0:
                    self._cleanup()
                    return False, f"连接超时: 小车 {self.car_ip}:{self.car_port} 无响应"
                time.sleep(0.1)

            self.connected = True
            logger.info(f"[{self.device_id}] 已连接到小车 {self.car_ip}:{self.car_port}")

            if self.on_connection_change:
                self.on_connection_change(self.device_id, True)

            return True, f"已连接到小车 {self.car_ip}:{self.car_port}"

        except Exception as e:
            self._cleanup()
            return False, f"连接失败: {str(e)}"

    def stop(self):
        """停止连接"""
        self._cleanup()
        if self.on_connection_change:
            self.on_connection_change(self.device_id, False)
        return True, "已断开连接"

    def _cleanup(self):
        self.running = False
        self.connected = False
        self.connection_acknowledged = False

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
            self.udp_socket = None

        if self.forward_socket:
            try:
                self.forward_socket.close()
            except:
                pass
            self.forward_socket = None

        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)

    def _receive_loop(self):
        logger.info(f"[{self.device_id}] UDP接收线程启动")
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                try:
                    json_str = data.decode('utf-8')
                    json_data = json.loads(json_str)
                    self._handle_received_data(json_data, addr)
                except json.JSONDecodeError as e:
                    logger.error(f"[{self.device_id}] JSON解析失败: {e}")
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                logger.error(f"[{self.device_id}] UDP处理异常: {e}")
        logger.info(f"[{self.device_id}] UDP接收线程退出")

    def _heartbeat_loop(self):
        logger.info(f"[{self.device_id}] UDP心跳线程启动")
        while self.running:
            try:
                time.sleep(3)
                if self.connected and self.running:
                    self._send_heartbeat()
            except Exception as e:
                logger.error(f"[{self.device_id}] 心跳发送异常: {e}")
        logger.info(f"[{self.device_id}] UDP心跳线程退出")

    def _send_init_command(self):
        try:
            command = {"carStatus": "on"}
            self.send_command(command)
            logger.info(f"[{self.device_id}] 发送初始化命令: {command}")
        except Exception as e:
            logger.error(f"[{self.device_id}] 发送初始化命令失败: {e}")

    def _send_heartbeat(self):
        try:
            command = {"heartbeat": int(time.time() * 1000)}
            self.send_command(command)
            logger.debug(f"[{self.device_id}] 发送心跳命令")
        except Exception as e:
            logger.error(f"[{self.device_id}] 发送心跳失败: {e}")

    def _handle_received_data(self, data, addr):
        try:
            if not self.connection_acknowledged:
                self.connection_acknowledged = True
                logger.info(f"[{self.device_id}] 收到小车首次响应，连接确认成功")

            self.last_receive_time = datetime.now()
            self.latest_data = data

            logger.info(f"[{self.device_id}] 收到数据: carStatus={data.get('carStatus')}")

            if self.on_data_received:
                self.on_data_received(self.device_id, data)

            current_time = time.time()
            if current_time - self.last_save_time >= 1.0:
                self.last_save_time = current_time
                if self.data_service:
                    self.data_service.save_car_data(self.device_id, data)

            self._forward_wheel_speed(data)

        except Exception as e:
            logger.error(f"[{self.device_id}] 数据处理错误: {e}")

    def _forward_wheel_speed(self, data):
        if not self.forward_socket:
            return
        try:
            l_spd = data.get('L_spd')
            r_spd = data.get('R_spd')
            if l_spd is None or r_spd is None:
                return
            payload = json.dumps({
                'L_spd': int(l_spd),
                'R_spd': int(r_spd),
                'ts': int(time.time() * 1000)
            }, ensure_ascii=False).encode('utf-8')
            self.forward_socket.sendto(payload, self.forward_addr)
        except (BlockingIOError, OSError):
            pass
        except Exception as e:
            logger.debug(f"[{self.device_id}] 轮速转发异常: {e}")

    def send_command(self, command):
        if not self.udp_socket:
            return False
        try:
            message = json.dumps(command, ensure_ascii=False).encode('utf-8')
            self.udp_socket.sendto(message, (self.car_ip, self.car_port))
            logger.debug(f"[{self.device_id}] 发送命令: {command}")
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] 发送命令失败: {e}")
            return False

    def get_status(self):
        return {
            'device_id': self.device_id,
            'car_ip': self.car_ip,
            'car_port': self.car_port,
            'connected': self.connected,
            'last_receive_time': self.last_receive_time.isoformat() if self.last_receive_time else None,
        }


class UDPService:
    """UDP通信服务 - 管理多辆小车连接"""

    def __init__(self, app, data_service, config):
        self.app = app
        self.data_service = data_service
        self.config = config

        # 多车连接注册表 {device_id: CarConnection}
        self.cars = {}
        self.cars_lock = threading.Lock()

        # 全局回调
        self.on_data_received = None

        # 向后兼容：默认单辆车的属性
        self.connected = False
        self.device_id = None
        self.latest_data = None

    def connect_to_car(self, car_ip, car_port=None, device_id=None):
        """连接新的小车，如果同device_id已存在且IP/端口不同则自动断开旧连接"""
        car_port = car_port or 7788
        device_id = device_id or f"car_{car_ip.replace('.', '_')}"

        with self.cars_lock:
            if device_id in self.cars:
                old_car = self.cars[device_id]
                if old_car.car_ip == car_ip and old_car.car_port == car_port:
                    # 同IP同端口，确实已连接
                    return False, f"小车 {device_id} 已连接"
                else:
                    # IP或端口变化，断开旧连接
                    logger.info(f"[{device_id}] IP/端口变更 ({old_car.car_ip}:{old_car.car_port} -> {car_ip}:{car_port})，断开旧连接")
                    old_car = self.cars.pop(device_id)
                    old_car.stop()

            # 清理指向同一IP:端口的其他僵尸连接（如IP变化导致device_id不同的情况）
            zombie_ids = [did for did, car in self.cars.items()
                          if car.car_ip == car_ip and car.car_port == car_port]
            for zombie_id in zombie_ids:
                logger.info(f"[{zombie_id}] 清理指向相同IP:端口 ({car_ip}:{car_port}) 的旧连接")
                zombie = self.cars.pop(zombie_id)
                zombie.stop()

        car_conn = CarConnection(device_id, car_ip, car_port, self.data_service)

        def on_data(device_id, data):
            self.latest_data = data
            if self.on_data_received:
                self.on_data_received(device_id, data)

        def on_conn_change(device_id, connected):
            self._update_legacy_status()

        car_conn.on_data_received = on_data
        car_conn.on_connection_change = on_conn_change

        success, msg = car_conn.start()

        if success:
            with self.cars_lock:
                self.cars[device_id] = car_conn
            self._update_legacy_status()
            return True, msg
        else:
            return False, msg

    def disconnect_car(self, device_id=None):
        """断开指定小车，或断开所有小车"""
        with self.cars_lock:
            if device_id:
                if device_id in self.cars:
                    car = self.cars.pop(device_id)
                    car.stop()
                    result = True, f"已断开小车 {device_id}"
                else:
                    result = False, f"小车 {device_id} 未连接"
            else:
                for car in self.cars.values():
                    car.stop()
                self.cars.clear()
                result = True, "已断开所有小车"

        # 必须在锁外调用，避免死锁（_update_legacy_status 也获取 cars_lock）
        self._update_legacy_status()
        return result

    def send_command(self, command, device_id=None):
        """发送命令到指定小车，或发送到第一辆连接的小车"""
        with self.cars_lock:
            if not self.cars:
                return False

            if device_id and device_id in self.cars:
                return self.cars[device_id].send_command(command)

            # 发送到第一辆小车（向后兼容）
            first_car = next(iter(self.cars.values()))
            return first_car.send_command(command)

    def get_car_status(self, device_id=None):
        """获取指定小车或所有小车的状态"""
        with self.cars_lock:
            if device_id:
                if device_id in self.cars:
                    return self.cars[device_id].get_status()
                return None
            return [car.get_status() for car in self.cars.values()]

    def get_connected_cars(self):
        """获取所有已连接的小车列表"""
        with self.cars_lock:
            return [{
                'device_id': car.device_id,
                'car_ip': car.car_ip,
                'car_port': car.car_port,
                'connected': car.connected,
                'last_receive_time': car.last_receive_time.isoformat() if car.last_receive_time else None,
            } for car in self.cars.values() if car.connected]

    def _update_legacy_status(self):
        """更新向后兼容的单辆车状态属性"""
        with self.cars_lock:
            self.connected = any(car.connected for car in self.cars.values())
            if self.cars:
                first = next(iter(self.cars.values()))
                self.device_id = first.device_id
                self.latest_data = first.latest_data
            else:
                self.device_id = None
                self.latest_data = None

    def get_status(self):
        """获取服务整体状态"""
        return {
            'connected': self.connected,
            'device_id': self.device_id,
            'car_count': len(self.cars),
        }

    def disconnect(self):
        """向后兼容：断开所有小车"""
        return self.disconnect_car()

    def stop(self):
        """停止服务"""
        logger.info("停止UDP服务...")
        self.disconnect_car()
