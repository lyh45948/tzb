"""
WebSocket 服务 - 供 Web 应用连接，支持多辆小车管理
"""
import asyncio
import websockets
from websockets.protocol import State
import json
import threading
import time
from datetime import datetime
from app.utils.logger import get_logger
from app.utils.protocol import ProtocolParser

logger = get_logger('websocket_service')


class WebSocketService:
    """WebSocket 服务 - 供 Web 应用连接，支持多辆小车"""

    def __init__(self, app, udp_car_service, data_service, config):
        self.app = app
        self.udp_car_service = udp_car_service
        self.data_service = data_service
        self.config = config

        self.host = getattr(config, 'WS_HOST', config.TCP_HOST)
        self.port = getattr(config, 'WS_PORT', 8889)

        self.server = None
        self.running = False
        self.loop = None
        self.thread = None

        # WebSocket 客户端 {websocket: client_info}
        self.clients = {}
        self.clients_lock = threading.Lock()

        # 每个客户端当前关注的小车 device_id
        # {websocket: device_id}
        self.client_active_car = {}

        self.simulation_service = None

        # 启动小车列表广播线程
        self.car_list_thread = None

    def start(self):
        """启动 WebSocket 服务"""
        try:
            self.running = True
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()

            from app.services.simulation_service import SimulationService
            self.simulation_service = SimulationService(
                self.data_service,
                self,
                self.udp_car_service
            )

            self.udp_car_service.on_data_received = self._on_car_data

            # 启动小车列表广播线程
            self.car_list_thread = threading.Thread(target=self._car_list_broadcast_loop, daemon=True)
            self.car_list_thread.start()

            logger.info(f"WebSocket 服务已启动在 ws://{self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"WebSocket 服务启动失败: {e}")
            return False

    def _run_server(self):
        """运行 WebSocket 服务器"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def serve():
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10,
            )
            logger.info(f"WebSocket 服务器正在监听 {self.host}:{self.port}")
            await self.server.wait_closed()

        try:
            self.loop.run_until_complete(serve())
        except Exception as e:
            if self.running:
                logger.error(f"WebSocket 服务器异常: {e}")

    def _car_list_broadcast_loop(self):
        """定期广播已连接小车列表给所有客户端"""
        while self.running:
            try:
                time.sleep(2)
                if not self.running:
                    break

                cars = self.udp_car_service.get_connected_cars()
                msg = {
                    'type': 'car_list',
                    'cars': cars,
                    'timestamp': int(time.time() * 1000)
                }

                if self.loop and self.loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast_message(msg),
                        self.loop
                    )
            except Exception as e:
                logger.error(f"小车列表广播异常: {e}")

    async def _handle_client(self, websocket):
        """处理客户端连接"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"WebSocket 客户端连接: {client_addr}")

        with self.clients_lock:
            self.clients[websocket] = {
                'device_id': None,
                'connected_car': False,
                'demo_mode': False,
                'addr': client_addr,
            }
            self.client_active_car[websocket] = None

        # 立即发送当前小车列表
        cars = self.udp_car_service.get_connected_cars()
        await self._send_message(websocket, {
            'type': 'car_list',
            'cars': cars,
        })

        try:
            async for message in websocket:
                try:
                    for line in message.strip().split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                            await self._handle_message(msg, websocket)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON 解析失败: {e}")
                except Exception as e:
                    logger.error(f"处理消息异常: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket 客户端断开: {client_addr}")
        finally:
            with self.clients_lock:
                if websocket in self.clients:
                    del self.clients[websocket]
                if websocket in self.client_active_car:
                    del self.client_active_car[websocket]
            logger.info(f"WebSocket 客户端已移除: {client_addr}")

    async def _handle_message(self, message, websocket):
        """处理接收到的消息"""
        msg_type = message.get('type')
        logger.info(f"收到 WebSocket 消息: type={msg_type}")

        if msg_type == 'ping':
            await self._send_message(websocket, {'type': 'pong', 'timestamp': time.time()})
            return

        if msg_type == 'connect':
            await self._handle_connect(message, websocket)
        elif msg_type == 'disconnect':
            await self._handle_disconnect(message, websocket)
        elif msg_type == 'control':
            await self._handle_control(message, websocket)
        elif msg_type == 'switch_car':
            await self._handle_switch_car(message, websocket)
        elif msg_type == 'query':
            await self._handle_query(message, websocket)
        elif msg_type == 'demo_mode':
            await self._handle_demo_mode(message, websocket)
        elif msg_type == 'car_list':
            await self._handle_car_list_request(websocket)
        elif msg_type == 'heartbeat':
            pass
        else:
            logger.warning(f"未知消息类型: {msg_type}")

    async def _handle_connect(self, message, websocket):
        """处理连接小车请求 - 在线程池中执行避免阻塞事件循环"""
        car_ip = message.get('carIp')
        car_port = message.get('carPort', 7788)
        device_id = message.get('deviceId')

        if not car_ip:
            await self._send_message(websocket, ProtocolParser.create_error_message("缺少 carIp 参数"))
            return

        if not device_id:
            device_id = f"car_{car_ip.replace('.', '_')}"

        logger.info(f"[_handle_connect] 开始连接小车: {car_ip}:{car_port}, device_id={device_id}")
        await self._send_message(websocket, {
            'type': 'status',
            'message': f'正在连接小车 {device_id}...'
        })

        # 在线程池中执行同步阻塞的 connect_to_car，避免阻塞 asyncio 事件循环
        loop = asyncio.get_event_loop()
        try:
            success, msg = await asyncio.wait_for(
                loop.run_in_executor(None, self.udp_car_service.connect_to_car, car_ip, car_port, device_id),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            success, msg = False, "连接超时（5秒）"
        except Exception as e:
            success, msg = False, f"连接异常: {str(e)}"

        logger.info(f"[_handle_connect] 连接结果: success={success}, msg={msg}")

        if success:
            with self.clients_lock:
                if websocket in self.clients:
                    self.clients[websocket]['device_id'] = device_id
                    self.clients[websocket]['connected_car'] = True
                self.client_active_car[websocket] = device_id

            await self._send_message(websocket, ProtocolParser.create_connect_result(True, msg, device_id))

            # 广播更新后的小车列表
            await self._broadcast_car_list()
        else:
            await self._send_message(websocket, ProtocolParser.create_connect_result(False, msg, device_id))

    async def _handle_disconnect(self, message, websocket):
        """处理断开小车请求"""
        device_id = message.get('deviceId')

        with self.clients_lock:
            if websocket in self.client_active_car:
                active_id = self.client_active_car[websocket]
                if not device_id:
                    device_id = active_id

        if device_id:
            success, msg = self.udp_car_service.disconnect_car(device_id)
        else:
            success, msg = self.udp_car_service.disconnect_car()
            # 也断开演示模式
            if self.simulation_service and self.simulation_service.demo_mode:
                self.simulation_service.set_demo_mode(False)

        with self.clients_lock:
            if websocket in self.clients:
                self.clients[websocket]['connected_car'] = False
                self.clients[websocket]['demo_mode'] = False
            self.client_active_car[websocket] = None

        await self._send_message(websocket, {
            "type": "disconnect_result",
            "success": success,
            "message": msg
        })

        await self._broadcast_car_list()

    async def _handle_control(self, message, websocket):
        """处理控制命令"""
        with self.clients_lock:
            client = self.clients.get(websocket, {})

        if not client.get('connected_car'):
            await self._send_message(websocket, ProtocolParser.create_error_message("未连接小车"))
            return

        command = message.get('command', {})
        device_id = message.get('deviceId')

        # 如果没有指定device_id，使用客户端当前活跃的小车
        if not device_id:
            with self.clients_lock:
                device_id = self.client_active_car.get(websocket)

        if self.udp_car_service.send_command(command, device_id):
            if self.data_service:
                is_simulated = client.get('demo_mode', False)
                command_type = 'car_control'
                if 'carStatus' in command:
                    command_type = command.get('carStatus')
                elif 'fan' in command:
                    command_type = 'fan'
                elif 'led' in command:
                    command_type = 'led'

                self.data_service.save_control_command(
                    device_id or client.get('device_id'),
                    command_type,
                    command,
                    source='webapp',
                    is_simulated=is_simulated
                )
            await self._send_message(websocket, {
                "type": "control_result",
                "success": True,
                "message": "命令已发送"
            })
        else:
            await self._send_message(websocket, ProtocolParser.create_error_message("命令发送失败"))

    async def _handle_switch_car(self, message, websocket):
        """处理切换当前小车"""
        device_id = message.get('deviceId')

        if not device_id:
            await self._send_message(websocket, ProtocolParser.create_error_message("缺少 deviceId 参数"))
            return

        with self.clients_lock:
            self.client_active_car[websocket] = device_id
            if websocket in self.clients:
                self.clients[websocket]['device_id'] = device_id
                self.clients[websocket]['connected_car'] = True

        await self._send_message(websocket, {
            'type': 'switch_car_result',
            'success': True,
            'deviceId': device_id,
            'message': f'已切换到小车 {device_id}'
        })

    async def _handle_car_list_request(self, websocket):
        """处理获取小车列表请求"""
        cars = self.udp_car_service.get_connected_cars()
        await self._send_message(websocket, {
            'type': 'car_list',
            'cars': cars,
        })

    async def _handle_query(self, message, websocket):
        """处理查询请求"""
        action = message.get('action')
        params = message.get('params', {})

        if not self.data_service:
            await self._send_message(websocket, ProtocolParser.create_error_message("数据服务不可用"))
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

            await self._send_message(websocket, ProtocolParser.create_query_result(action, data))

        except Exception as e:
            logger.error(f"查询失败: {e}")
            await self._send_message(websocket, ProtocolParser.create_error_message(f"查询失败: {str(e)}"))

    async def _handle_demo_mode(self, message, websocket):
        """处理演示模式切换"""
        enabled = message.get('enabled', False)
        device_id = message.get('deviceId', 'demo_car')

        logger.info(f"收到演示模式切换请求: enabled={enabled}, deviceId={device_id}")

        with self.clients_lock:
            if websocket in self.clients:
                self.clients[websocket]['demo_mode'] = enabled
                if enabled:
                    self.clients[websocket]['device_id'] = device_id
                    self.clients[websocket]['connected_car'] = True
                else:
                    self.clients[websocket]['connected_car'] = False
            self.client_active_car[websocket] = device_id if enabled else None

        if self.simulation_service:
            success, msg = self.simulation_service.set_demo_mode(enabled, device_id)
            await self._send_message(websocket, {
                "type": "demo_mode_result",
                "success": success,
                "enabled": enabled,
                "message": msg
            })
        else:
            await self._send_message(websocket, {
                "type": "demo_mode_result",
                "success": False,
                "enabled": enabled,
                "message": "模拟服务未初始化"
            })

    def _on_car_data(self, device_id, data):
        """小车数据回调"""
        if self.simulation_service and not self.simulation_service.demo_mode:
            data = self.simulation_service.enrich_real_data(data)

        realtime_msg = ProtocolParser.create_realtime_message(data)
        realtime_msg['deviceId'] = device_id

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_to_clients(realtime_msg, device_id),
                self.loop
            )

    async def _broadcast_to_clients(self, message, device_id):
        """广播数据给关注该小车的客户端"""
        with self.clients_lock:
            clients_copy = list(self.clients.items())
            active_car_copy = dict(self.client_active_car)

        disconnected = []
        for websocket, client in clients_copy:
            # 发送给所有已连接且未在演示模式的客户端
            # 或者只发送给关注该小车的客户端
            active_car = active_car_copy.get(websocket)
            if client.get('connected_car') and not client.get('demo_mode'):
                try:
                    if websocket.state == State.OPEN:
                        await websocket.send(json.dumps(message, ensure_ascii=False) + '\n')
                except Exception as e:
                    logger.error(f"广播消息失败: {e}")
                    disconnected.append(websocket)

        with self.clients_lock:
            for ws in disconnected:
                if ws in self.clients:
                    del self.clients[ws]
                if ws in self.client_active_car:
                    del self.client_active_car[ws]

    async def _broadcast_car_list(self):
        """广播小车列表给所有客户端"""
        cars = self.udp_car_service.get_connected_cars()
        msg = {
            'type': 'car_list',
            'cars': cars,
            'timestamp': int(time.time() * 1000)
        }
        await self._broadcast_message(msg)

    async def _broadcast_message(self, message):
        """广播消息给所有客户端"""
        with self.clients_lock:
            clients_copy = list(self.clients.keys())

        disconnected = []
        for websocket in clients_copy:
            try:
                if websocket.state == State.OPEN:
                    await websocket.send(json.dumps(message, ensure_ascii=False) + '\n')
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(websocket)

        with self.clients_lock:
            for ws in disconnected:
                if ws in self.clients:
                    del self.clients[ws]
                if ws in self.client_active_car:
                    del self.client_active_car[ws]

    def broadcast_simulated_data(self, data):
        """广播模拟数据"""
        realtime_msg = ProtocolParser.create_realtime_message(data)

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_message(realtime_msg),
                self.loop
            )

    def broadcast_vision_data(self, vision_type, data):
        """广播视觉数据给所有客户端

        Args:
            vision_type: 'obstacles' 或 'counter'
            data: 视觉数据字典
        """
        msg = {
            'type': 'vision',
            'visionType': vision_type,
            'data': data,
            'timestamp': int(time.time() * 1000)
        }

        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._broadcast_message(msg),
                self.loop
            )

    async def _send_message(self, websocket, message):
        """发送消息到指定客户端"""
        try:
            if websocket.state == State.OPEN:
                await websocket.send(json.dumps(message, ensure_ascii=False) + '\n')
                return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
        return False

    def stop(self):
        """停止服务 - 强制断开所有客户端后关闭服务器"""
        logger.info("停止 WebSocket 服务...")
        self.running = False

        # 强制关闭所有客户端连接
        with self.clients_lock:
            clients_copy = list(self.clients.keys())

        for ws in clients_copy:
            try:
                if hasattr(ws, 'close'):
                    asyncio.run_coroutine_threadsafe(ws.close(), self.loop)
            except Exception as e:
                logger.debug(f"关闭客户端连接时出错: {e}")

        # 关闭服务器（停止接受新连接）
        if self.server:
            try:
                self.server.close()
            except:
                pass

        # 等待服务器关闭（最多2秒）
        if self.loop and self.loop.is_running():
            async def _shutdown():
                if self.server:
                    await asyncio.wait_for(self.server.wait_closed(), timeout=1.0)
            try:
                future = asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)
                future.result(timeout=2.0)
            except Exception:
                pass

        # 停止事件循环
        if self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except:
                pass
            self.loop = None

        self.server = None
        self.clients.clear()
        self.client_active_car.clear()
        logger.info("WebSocket 服务已停止")
