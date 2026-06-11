"""
TCP服务器
供微信小程序连接，提供实时数据推送和历史数据查询
"""
import socket
import threading
import select
import time
from datetime import datetime
from app.utils.logger import get_logger
from app.utils.protocol import ProtocolParser

logger = get_logger('tcp_service')


class TCPClient:
    """TCP客户端连接"""

    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self.connected_car = False
        self.device_id = None
        self.connect_time = datetime.now()
        self.buffer = b''

    def send(self, data):
        """发送数据"""
        try:
            message = ProtocolParser.encode_message(data)
            self.socket.sendall(message)
            return True
        except Exception as e:
            logger.error(f"发送数据到 {self.address} 失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        try:
            self.socket.close()
        except:
            pass


class TCPServer:
    """TCP服务器"""

    def __init__(self, app, udp_service, data_service, config):
        self.app = app
        self.udp_service = udp_service
        self.data_service = data_service
        self.config = config

        # 服务器配置
        self.host = config.TCP_HOST
        self.port = config.TCP_PORT
        self.max_clients = getattr(config, 'MAX_TCP_CLIENTS', 10)

        # 服务器状态
        self.server_socket = None
        self.running = False
        self.accept_thread = None
        self.receive_thread = None

        # 客户端列表
        self.clients = []
        self.clients_lock = threading.Lock()

        # 数据推送定时器
        self.push_thread = None
        self.push_interval = 0.05  # 50ms

        # 注册UDP数据回调
        self.udp_service.on_data_received = self._on_udp_data

    def start(self):
        """启动TCP服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)
            self.server_socket.settimeout(1)

            self.running = True

            # 启动接受连接线程
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()

            # 启动接收数据线程
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            # 启动数据推送线程
            self.push_thread = threading.Thread(target=self._push_loop, daemon=True)
            self.push_thread.start()

            logger.info(f"TCP服务器已启动在 {self.host}:{self.port}")

            # 主线程保持运行
            while self.running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"TCP服务器启动失败: {e}")
            raise

    def _accept_loop(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()

                # 检查客户端数量限制
                with self.clients_lock:
                    if len(self.clients) >= self.max_clients:
                        logger.warning(f"客户端数量已达上限 {self.max_clients}")
                        try:
                            client_socket.close()
                        except:
                            pass
                        continue

                client = TCPClient(client_socket, address)
                logger.info(f"新客户端连接: {address}")

                with self.clients_lock:
                    self.clients.append(client)

                # 设置非阻塞
                client_socket.settimeout(0.1)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接异常: {e}")

    def _receive_loop(self):
        """接收客户端数据"""
        while self.running:
            clients_to_check = []

            with self.clients_lock:
                clients_to_check = self.clients.copy()

            if not clients_to_check:
                time.sleep(0.01)
                continue

            # 使用select检查可读socket
            try:
                readable, _, _ = select.select(
                    [c.socket for c in clients_to_check],
                    [],
                    [],
                    0.01
                )
            except:
                continue

            for client in readable:
                try:
                    data = client.socket.recv(4096)
                    if data:
                        client.buffer += data
                        self._process_client_buffer(client)
                    else:
                        # 连接关闭
                        self._remove_client(client)
                except:
                    self._remove_client(client)

    def _process_client_buffer(self, client):
        """处理客户端缓冲区数据"""
        while b'\n' in client.buffer:
            line, client.buffer = client.buffer.split(b'\n', 1)
            line = line.strip()
            if not line:
                continue

            message = ProtocolParser.parse_message(line)
            if message:
                self._handle_client_message(client, message)

    def _handle_client_message(self, client, message):
        """处理客户端消息"""
        msg_type = message.get('type')

        if msg_type == 'connect':
            self._handle_connect(client, message)
        elif msg_type == 'disconnect':
            self._handle_disconnect(client)
        elif msg_type == 'control':
            self._handle_control(client, message)
        elif msg_type == 'query':
            self._handle_query(client, message)
        else:
            logger.warning(f"未知消息类型: {msg_type}")

    def _handle_connect(self, client, message):
        """处理连接小车请求"""
        car_ip = message.get('carIp')
        car_port = message.get('carPort', 7788)
        device_id = message.get('deviceId')

        if not car_ip:
            client.send(ProtocolParser.create_error_message("缺少carIp参数"))
            return

        # 断开之前的连接
        if self.udp_service.connected:
            self.udp_service.disconnect()

        # 连接到小车
        success, msg = self.udp_service.connect_to_car(car_ip, car_port, device_id)

        if success:
            client.connected_car = True
            client.device_id = device_id
            client.send(ProtocolParser.create_connect_result(True, msg, device_id))
            logger.info(f"客户端 {client.address} 已连接小车: {car_ip}:{car_port}")
        else:
            client.send(ProtocolParser.create_connect_result(False, msg))

    def _handle_disconnect(self, client):
        """处理断开连接请求"""
        if self.udp_service.connected:
            self.udp_service.disconnect()

        client.connected_car = False
        client.device_id = None
        client.send({
            "type": "disconnect_result",
            "success": True,
            "message": "已断开与小车的连接"
        })

    def _handle_control(self, client, message):
        """处理控制命令"""
        if not client.connected_car:
            client.send(ProtocolParser.create_error_message("未连接小车"))
            return

        command = message.get('command', {})
        if self.udp_service.send_command(command):
            # 记录控制日志
            if self.data_service:
                self.data_service.save_control_log(
                    client.device_id,
                    command.get('type', 'unknown'),
                    command
                )
            client.send({
                "type": "control_result",
                "success": True,
                "message": "命令已发送"
            })
        else:
            client.send(ProtocolParser.create_error_message("命令发送失败"))

    def _handle_query(self, client, message):
        """处理查询请求"""
        action = message.get('action')
        params = message.get('params', {})

        if not self.data_service:
            client.send(ProtocolParser.create_error_message("数据服务不可用"))
            return

        try:
            if action == 'sensor_history':
                data = self.data_service.query_sensor_history(
                    params.get('deviceId'),
                    params.get('startTime'),
                    params.get('endTime'),
                    params.get('interval')
                )
            elif action == 'car_status_history':
                data = self.data_service.query_car_status_history(
                    params.get('deviceId'),
                    params.get('startTime'),
                    params.get('endTime')
                )
            else:
                data = []

            client.send(ProtocolParser.create_query_result(action, data))

        except Exception as e:
            logger.error(f"查询失败: {e}")
            client.send(ProtocolParser.create_error_message(f"查询失败: {str(e)}"))

    def _on_udp_data(self, data):
        """UDP数据回调，推送给所有已连接小车的客户端"""
        realtime_msg = ProtocolParser.create_realtime_message(data)

        with self.clients_lock:
            for client in self.clients:
                if client.connected_car:
                    client.send(realtime_msg)

    def _push_loop(self):
        """数据推送循环"""
        while self.running:
            time.sleep(self.push_interval)

    def _remove_client(self, client):
        """移除客户端"""
        client.close()

        with self.clients_lock:
            if client in self.clients:
                self.clients.remove(client)

        logger.info(f"客户端 {client.address} 已移除")

    def stop(self):
        """停止服务器"""
        logger.info("停止TCP服务器...")
        self.running = False

        # 关闭所有客户端
        with self.clients_lock:
            for client in self.clients:
                client.close()
            self.clients.clear()

        # 关闭服务器socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        logger.info("TCP服务器已停止")
