"""
UDP服务 - 微信小程序连接
用于接收微信小程序的UDP消息并处理
"""
import socket
import threading
import json
import time
from datetime import datetime
from app.utils.logger import get_logger
from app.utils.protocol import ProtocolParser
from app.services.registry import get_service

logger = get_logger('udp_miniapp_service')


class UDPMiniAppService:
    """UDP服务 - 供微信小程序连接"""

    def __init__(self, app, udp_car_service, data_service, config):
        self.app = app
        self.udp_car_service = udp_car_service  # 连接小车的UDP服务
        self.data_service = data_service
        self.config = config

        # 服务器配置
        self.host = config.TCP_HOST  # 复用TCP配置的IP
        self.port = config.TCP_PORT  # 使用8888端口

        # UDP Socket
        self.udp_socket = None
        self.receive_thread = None
        self.running = False

        # 客户端列表 {address: {'device_id': xxx, 'connected_car': bool, 'demo_mode': bool}}
        self.clients = {}
        self.clients_lock = threading.Lock()

        # 模拟服务（延迟初始化）
        self.simulation_service = None

    def start(self):
        """启动UDP服务"""
        try:
            # 先检查端口是否已被占用
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                test_sock.bind((self.host, self.port))
                test_sock.close()
            except OSError as e:
                logger.error(f"端口 {self.port} 已被占用: {e}")
                return False

            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 不使用 SO_REUSEADDR，避免多个进程绑定同一端口
            self.udp_socket.bind((self.host, self.port))
            self.udp_socket.settimeout(1.0)

            self.running = True

            # 启动接收线程
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            # 初始化模拟服务
            from app.services.simulation_service import SimulationService
            print(f"[UDPMiniAppService] 创建SimulationService: data_service={self.data_service is not None}")
            self.simulation_service = SimulationService(
                self.data_service,
                self,
                self.udp_car_service
            )
            print(f"[UDPMiniAppService] SimulationService创建完成")

            # 注册小车数据回调
            self.udp_car_service.on_data_received = self._on_car_data

            logger.info(f"UDP小程序服务已启动在 {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"UDP小程序服务启动失败: {e}")
            return False

    def _receive_loop(self):
        """UDP数据接收循环"""
        print("[UDPMiniAppService] UDP接收线程启动")
        logger.info("UDP接收线程启动")

        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                print(f"[UDPMiniAppService] 收到UDP数据: addr={addr}, len={len(data)}")

                # 解析消息
                try:
                    message_str = data.decode('utf-8').strip()
                    if not message_str:
                        continue

                    # 处理可能的多条消息（用换行符分隔）
                    for line in message_str.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            message = json.loads(line)
                            self._handle_message(message, addr)
                        except json.JSONDecodeError as e:
                            print(f"[UDPMiniAppService] JSON解析失败: {e}")
                            logger.error(f"JSON解析失败: {e}, 数据: {line[:100]}")

                except UnicodeDecodeError as e:
                    print(f"[UDPMiniAppService] 解码失败: {e}")
                    logger.error(f"解码失败: {e}")

            except socket.timeout:
                continue
            except OSError as e:
                if self.running:
                    print(f"[UDPMiniAppService] UDP接收错误: {e}")
                    logger.error(f"UDP接收错误: {e}")
                break
            except Exception as e:
                print(f"[UDPMiniAppService] UDP处理异常: {e}")
                logger.error(f"UDP处理异常: {e}")

        print("[UDPMiniAppService] UDP接收线程退出")
        logger.info("UDP接收线程退出")

    def _handle_message(self, message, addr):
        """处理接收到的消息"""
        msg_type = message.get('type')
        logger.info(f"收到消息: type={msg_type}, from={addr}, message={message}")

        # 记录客户端
        with self.clients_lock:
            if addr not in self.clients:
                self.clients[addr] = {'device_id': None, 'connected_car': False}
                logger.info(f"新客户端: {addr}")

        # Ping/Pong - 连接验证（最高优先级）
        if msg_type == 'ping':
            self._send_message(addr, {'type': 'pong', 'timestamp': time.time()})
            logger.info(f"响应 ping -> pong to {addr}")
            return

        if msg_type == 'connect':
            self._handle_connect(message, addr)
        elif msg_type == 'disconnect':
            self._handle_disconnect(addr)
        elif msg_type == 'control':
            self._handle_control(message, addr)
        elif msg_type == 'query':
            self._handle_query(message, addr)
        elif msg_type == 'demo_mode':
            self._handle_demo_mode(message, addr)
        elif msg_type == 'smart_light_get':
            self._handle_smart_light_get(message, addr)
        elif msg_type == 'smart_light_set_mode':
            self._handle_smart_light_set_mode(message, addr)
        elif msg_type == 'smart_light_set_brightness':
            self._handle_smart_light_set_brightness(message, addr)
        elif msg_type == 'heartbeat':
            # 心跳，不做处理
            pass
        else:
            logger.warning(f"未知消息类型: {msg_type}")

    def _handle_connect(self, message, addr):
        """处理连接小车请求"""
        car_ip = message.get('carIp')
        car_port = message.get('carPort', 7788)
        device_id = message.get('deviceId')

        if not car_ip:
            self._send_message(addr, ProtocolParser.create_error_message("缺少carIp参数"))
            return

        # 连接到小车
        success, msg = self.udp_car_service.connect_to_car(car_ip, car_port, device_id)

        if success:
            with self.clients_lock:
                self.clients[addr] = {
                    'device_id': device_id,
                    'connected_car': True
                }
            self._send_message(addr, ProtocolParser.create_connect_result(True, msg, device_id))
            logger.info(f"客户端 {addr} 已连接小车: {car_ip}:{car_port}")
        else:
            self._send_message(addr, ProtocolParser.create_connect_result(False, msg))

    def _handle_disconnect(self, addr):
        """处理断开连接请求"""
        # 停止演示模式
        if self.simulation_service and self.simulation_service.demo_mode:
            self.simulation_service.set_demo_mode(False)

        if self.udp_car_service.connected:
            self.udp_car_service.disconnect()

        with self.clients_lock:
            if addr in self.clients:
                self.clients[addr]['connected_car'] = False
                self.clients[addr]['demo_mode'] = False

        self._send_message(addr, {
            "type": "disconnect_result",
            "success": True,
            "message": "已断开与小车的连接"
        })

    def _handle_demo_mode(self, message, addr):
        """处理演示模式切换"""
        enabled = message.get('enabled', False)
        device_id = message.get('deviceId', 'demo_car')

        print(f"[UDPMiniAppService] 收到演示模式切换请求: enabled={enabled}, deviceId={device_id}")
        logger.info(f"收到演示模式切换请求: enabled={enabled}, deviceId={device_id}")

        with self.clients_lock:
            if addr in self.clients:
                self.clients[addr]['demo_mode'] = enabled
                if enabled:
                    self.clients[addr]['device_id'] = device_id
                    # 关键修复：演示模式下也需要设置 connected_car，否则控制命令会被拒绝
                    self.clients[addr]['connected_car'] = True
                else:
                    # 关闭演示模式时清除连接状态
                    self.clients[addr]['connected_car'] = False

        # 切换模拟服务
        if self.simulation_service:
            print(f"[UDPMiniAppService] simulation_service 存在，调用 set_demo_mode")
            logger.info(f"simulation_service 存在，调用 set_demo_mode")
            success, msg = self.simulation_service.set_demo_mode(enabled, device_id)

            self._send_message(addr, {
                "type": "demo_mode_result",
                "success": success,
                "enabled": enabled,
                "message": msg
            })

            print(f"[UDPMiniAppService] 客户端 {addr} 演示模式: {'开启' if enabled else '关闭'}")
            logger.info(f"客户端 {addr} 演示模式: {'开启' if enabled else '关闭'}")
        else:
            print("[UDPMiniAppService] simulation_service 为 None，无法切换演示模式")
            logger.error("simulation_service 为 None，无法切换演示模式")
            self._send_message(addr, {
                "type": "demo_mode_result",
                "success": False,
                "enabled": enabled,
                "message": "模拟服务未初始化"
            })

    def _handle_control(self, message, addr):
        """处理控制命令"""
        with self.clients_lock:
            client = self.clients.get(addr, {})

        if not client.get('connected_car'):
            self._send_message(addr, ProtocolParser.create_error_message("未连接小车"))
            return

        command = message.get('command', {})

        # 手动控制时通知 LinkageController 让出该路 30s 自动联动
        try:
            linkage = get_service('linkage_controller')
            if linkage is not None and isinstance(command, dict):
                if 'fan' in command:
                    linkage.notify_manual('fan')
                if 'led' in command:
                    linkage.notify_manual('led')
                if 'rgb' in command:
                    linkage.notify_manual('rgb')
        except Exception as e:
            logger.debug(f"notify_manual 异常: {e}")

        if self.udp_car_service.send_command(command):
            # 记录控制日志
            if self.data_service:
                # 判断是否在演示模式下发送
                is_simulated = client.get('demo_mode', False)
                command_type = 'car_control'
                if 'carStatus' in command:
                    command_type = command.get('carStatus')
                elif 'fan' in command:
                    command_type = 'fan'
                elif 'led' in command:
                    command_type = 'led'

                self.data_service.save_control_command(
                    client.get('device_id'),
                    command_type,
                    command,
                    source='miniapp',
                    is_simulated=is_simulated
                )
            self._send_message(addr, {
                "type": "control_result",
                "success": True,
                "message": "命令已发送"
            })
        else:
            self._send_message(addr, ProtocolParser.create_error_message("命令发送失败"))

    def _handle_query(self, message, addr):
        """处理查询请求"""
        action = message.get('action')
        params = message.get('params', {})

        if not self.data_service:
            self._send_message(addr, ProtocolParser.create_error_message("数据服务不可用"))
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

            self._send_message(addr, ProtocolParser.create_query_result(action, data))

        except Exception as e:
            logger.error(f"查询失败: {e}")
            self._send_message(addr, ProtocolParser.create_error_message(f"查询失败: {str(e)}"))

    def _handle_smart_light_get(self, message, addr):
        """[已废弃] 智能光照功能已被联动控制器替代，仅返回兼容性占位响应。"""
        self._send_smart_light_deprecated(addr)

    def _handle_smart_light_set_mode(self, message, addr):
        """[已废弃] 同上"""
        self._send_smart_light_deprecated(addr)

    def _handle_smart_light_set_brightness(self, message, addr):
        """[已废弃] 同上"""
        self._send_smart_light_deprecated(addr)

    def _send_smart_light_deprecated(self, addr):
        """对旧版小程序保持响应结构稳定（避免崩溃），但不再做实际控制。"""
        self._send_message(addr, {
            'type': 'smart_light_status',
            'data': {
                'mode': 'manual',
                'brightness': 0,
                'targetBrightness': 0,
                'timePeriod': 0,
                'timePeriodName': '已废弃',
                'lightLevel': 0,
                'lux': 0,
            },
            'deprecated': True,
            'message': '智能光照已被联动控制器替代',
        })

    def _on_car_data(self, device_id=None, data=None):
        """小车数据回调，推送给所有已连接的客户端"""
        # 兼容新旧回调签名：可能只传data，也可能传(device_id, data)
        if data is None:
            data = device_id
            device_id = None
        logger.info(f"[DEBUG] _on_car_data收到数据: device_id={device_id}, data={data}")

        # 为实际数据添加CO2和土壤湿度
        if self.simulation_service and not self.simulation_service.demo_mode:
            data = self.simulation_service.enrich_real_data(data)

        realtime_msg = ProtocolParser.create_realtime_message(data)

        with self.clients_lock:
            for addr, client in self.clients.items():
                if client.get('connected_car') and not client.get('demo_mode'):
                    self._send_message(addr, realtime_msg)

    def broadcast_simulated_data(self, data):
        """广播模拟数据给所有演示模式的客户端"""
        realtime_msg = ProtocolParser.create_realtime_message(data)

        with self.clients_lock:
            client_count = len(self.clients)
            if client_count == 0:
                logger.warning("没有已连接的客户端，无法广播模拟数据")
                return

            logger.debug(f"广播模拟数据给 {client_count} 个客户端")
            for addr, client in self.clients.items():
                # 广播给所有已连接的客户端（移除demo_mode条件）
                success = self._send_message(addr, realtime_msg)
                if success:
                    logger.debug(f"模拟数据已发送到 {addr}")
                else:
                    logger.error(f"模拟数据发送失败: {addr}")

    def _send_message(self, addr, message):
        """发送消息到指定地址"""
        if not self.udp_socket:
            return False

        try:
            message_str = json.dumps(message, ensure_ascii=False) + '\n'
            data = message_str.encode('utf-8')
            self.udp_socket.sendto(data, addr)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def stop(self):
        """停止服务"""
        logger.info("停止UDP小程序服务...")
        self.running = False

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
            self.udp_socket = None

        logger.info("UDP小程序服务已停止")
