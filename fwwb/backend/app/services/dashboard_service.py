"""
数字孪生大屏数据聚合服务
"""
from datetime import datetime

from app.services.registry import get_latest_sensor_data, get_default_sensor_data
from app.utils.alert_rules import evaluate_gas_alert_level
from app.utils.logger import get_logger

logger = get_logger('dashboard_service')


class DashboardService:
    """数字孪生大屏快照服务"""

    def __init__(self, app, data_service=None, udp_car_service=None, agv_task_service=None, linkage_controller=None):
        self.app = app
        self.data_service = data_service
        self.udp_car_service = udp_car_service
        self.agv_task_service = agv_task_service
        self.linkage_controller = linkage_controller

    def get_snapshot(self):
        """获取数字孪生大屏当前快照"""
        timestamp = int(datetime.now().timestamp() * 1000)
        car_data = self._get_current_car_data()
        env = car_data.get('env', {}) if isinstance(car_data, dict) else {}
        distance_cm, distance_mm = self._distance_values(car_data.get('distance') if isinstance(car_data, dict) else None)
        # 视觉数据可能补充障碍物最近距离与计数器读数
        vision_obstacles, vision_counter = self._get_vision_caches()
        vision_obstacles, vision_counter = self._merge_car_vision_fallback(
            vision_obstacles, vision_counter, car_data)
        distance_cm, distance_mm = self._merge_vision_distance(distance_cm, distance_mm, vision_obstacles)
        alert_level, linked_reason, alarm_events = self._build_alerts(env, distance_cm, timestamp)
        fleet = self._get_fleet()
        command_logs = self._get_command_logs()
        linkage = self._linkage_snapshot()
        human_detected = self._human_detected(env, linkage)

        data = {
            'timestamp': timestamp,
            'online': bool(self.udp_car_service and getattr(self.udp_car_service, 'connected', False)),
            'demoMode': False,

            'temperature': self._num(env.get('temp'), 24.5),
            'humidity': self._num(env.get('humi'), 58.0),
            'lux': self._int(env.get('lux'), 650),
            'ps': self._int(env.get('ps'), 0),
            'ir': self._int(env.get('ir'), 0),
            'humanDetected': 1 if human_detected else 0,
            'pirStatus': 'detected' if human_detected else 'clear',

            'co2': self._int(env.get('co2'), 520),
            'tvoc': self._int(env.get('tvoc'), 180),
            'gasMic': self._int(env.get('gasMic'), 120),
            'gasStatus': self._int(env.get('gasStatus'), 0),
            'flameStatus': self._int(env.get('flameStatus'), 0),

            'minDistance': distance_cm,
            'minDistanceCm': distance_cm,
            'minDistanceMm': distance_mm,

            'goodsCount': self._counter_to_count(vision_counter),
            'goodsPulse': 0,
            'counterDigits': self._counter_digits(vision_counter),

            'fan': self._int(env.get('fan'), 0),
            'led': self._int(env.get('led'), 0),
            'buzzer': self._int(env.get('buzzer'), 0),

            'alertLevel': alert_level,
            'linkedActionReason': linked_reason,
            'linkage': linkage,
            'fleet': fleet,
            'alarmEvents': alarm_events,
            'commandLogs': command_logs,
        }

        data['sensors'] = {
            'temperature': data['temperature'],
            'humidity': data['humidity'],
            'lux': data['lux'],
            'co2': data['co2'],
            'tvoc': data['tvoc'],
            'gasMic': data['gasMic'],
            'gasStatus': data['gasStatus'],
            'flameStatus': data['flameStatus'],
            'humanDetected': data['humanDetected'],
            'ps': data['ps'],
            'ir': data['ir'],
        }
        data['peripherals'] = {
            'fan': data['fan'],
            'led': data['led'],
            'buzzer': data['buzzer'],
        }
        data['goods'] = {
            'goodsCount': data['goodsCount'],
            'goodsPulse': data['goodsPulse'],
            'counterDigits': data['counterDigits'],
        }

        # 车辆环境智能体快照（无服务时省略字段）
        agent_snapshot = self._agent_snapshot()
        if agent_snapshot is not None:
            data['aiAgent'] = agent_snapshot
        return data

    def get_history(self, limit=60):
        """获取大屏历史数据占位。前端也可以继续本地累积。"""
        limit = self._safe_limit(limit, default=60, maximum=200)
        labels = []
        items = []
        now = datetime.now()
        snapshot = self.get_snapshot()
        for index in range(limit):
            ts = now.replace(microsecond=0)
            label = ts.strftime('%H:%M:%S')
            labels.append(label)
            items.append({
                'timestamp': int(ts.timestamp() * 1000),
                'label': label,
                'temperature': snapshot['temperature'],
                'humidity': snapshot['humidity'],
                'lux': snapshot['lux'],
                'co2': snapshot['co2'],
                'tvoc': snapshot['tvoc'],
                'gasMic': snapshot['gasMic'],
                'goodsCount': snapshot['goodsCount'],
            })
        return {
            'labels': labels,
            'items': items,
        }

    def _get_current_car_data(self):
        try:
            data = get_latest_sensor_data()
            return data if data else get_default_sensor_data()
        except Exception as e:
            logger.warning(f'获取当前传感器数据失败: {e}')
            return get_default_sensor_data()

    def _get_vision_caches(self):
        """从 VisionService 拉取最新缓存（无服务时返回 (None, None)）"""
        try:
            from app.services.registry import get_service
            vs = get_service('vision_service')
            if vs is None:
                return None, None
            return vs.get_latest_obstacles(), vs.get_latest_counter()
        except Exception as e:
            logger.debug(f'获取视觉缓存失败: {e}')
            return None, None

    def _merge_car_vision_fallback(self, vision_obstacles, vision_counter, car_data):
        """VisionService 缓存为空时，直接使用小车 UDP 中携带的 OpenMV 结果"""
        if not isinstance(car_data, dict):
            return vision_obstacles, vision_counter
        vision = car_data.get('vision')
        if not isinstance(vision, dict) or not vision.get('valid'):
            return vision_obstacles, vision_counter
        timestamp = vision.get('timestamp') or car_data.get('timestamp')
        if vision_obstacles is None and isinstance(vision.get('obstacles'), list):
            obstacles = vision.get('obstacles')
            fallback_obstacles = {
                'device_id': car_data.get('device_id') or 'car_openmv',
                'obstacles': obstacles,
                'count': vision.get('obstacleCount', len(obstacles)),
                'timestamp': timestamp,
                'source': vision.get('source', 'openmv_spi'),
                'frame': vision.get('frame'),
            }
            apf = self._build_vision_apf(obstacles)
            if apf:
                fallback_obstacles['apf'] = apf
            vision_obstacles = fallback_obstacles
        if vision_counter is None and vision.get('counter'):
            vision_counter = {
                'device_id': car_data.get('device_id') or 'car_openmv',
                'digits': str(vision.get('counter')),
                'timestamp': timestamp,
                'source': vision.get('source', 'openmv_spi'),
                'frame': vision.get('frame'),
            }
        return vision_obstacles, vision_counter

    @staticmethod
    def _build_vision_apf(obstacles):
        nearest_mm = None
        for obstacle in obstacles:
            if not isinstance(obstacle, dict):
                continue
            try:
                distance_mm = int(obstacle.get('distance'))
            except (TypeError, ValueError):
                continue
            if distance_mm <= 0:
                continue
            if nearest_mm is None or distance_mm < nearest_mm:
                nearest_mm = distance_mm
        if nearest_mm is None:
            return None
        return {
            'nearest_distance': nearest_mm / 1000.0,
            'nearest_distance_mm': nearest_mm,
        }

    def _merge_vision_distance(self, distance_cm, distance_mm, vision_obstacles):
        """如果视觉障碍物最近距离更小（更危险），用它替换超声距离"""
        if not vision_obstacles:
            return distance_cm, distance_mm
        apf = vision_obstacles.get('apf') if isinstance(vision_obstacles, dict) else None
        nearest = apf.get('nearest_distance') if isinstance(apf, dict) else None
        if nearest is None:
            return distance_cm, distance_mm
        try:
            visual_cm = int(round(float(nearest) * 100))
        except (ValueError, TypeError):
            return distance_cm, distance_mm
        if distance_cm is None or visual_cm < distance_cm:
            return visual_cm, visual_cm * 10
        return distance_cm, distance_mm

    @staticmethod
    def _counter_digits(vision_counter):
        if not isinstance(vision_counter, dict):
            return '000000'
        digits = vision_counter.get('digits')
        if not digits:
            return '000000'
        # 仅保留数字字符并左侧补 0 至 6 位
        only_digits = ''.join(ch for ch in str(digits) if ch.isdigit())
        if not only_digits:
            return '000000'
        return only_digits.rjust(6, '0')[-6:]

    @staticmethod
    def _counter_to_count(vision_counter):
        digits = DashboardService._counter_digits(vision_counter) if vision_counter else None
        if not digits:
            return 0
        try:
            return int(digits)
        except ValueError:
            return 0

    def _get_fleet(self):
        if not self.agv_task_service:
            return []
        try:
            return self.agv_task_service.get_dashboard_fleet().get('fleet', [])
        except Exception as e:
            logger.warning(f'获取AGV车队快照失败: {e}')
            return []

    def _get_command_logs(self):
        if not self.data_service:
            return []
        try:
            device_id = getattr(self.udp_car_service, 'device_id', None) or 'car_001'
            logs = self.data_service.query_command_history(device_id, limit=10)
            return [self._normalize_command_log(item) for item in logs]
        except Exception as e:
            logger.warning(f'获取控制日志失败: {e}')
            return []

    @staticmethod
    def _normalize_command_log(item):
        """把后端 command_data 同时映射为前端期望的 command 字符串，并补齐缺失字段"""
        cmd_data = item.get('command_data')
        if isinstance(cmd_data, str):
            cmd_str = cmd_data
        elif cmd_data is None:
            cmd_str = ''
        else:
            try:
                import json as _json
                cmd_str = _json.dumps(cmd_data, ensure_ascii=False)
            except Exception:
                cmd_str = str(cmd_data)
        return {
            'id': item.get('id'),
            'timestamp': item.get('timestamp'),
            'device_id': item.get('device_id'),
            'command_type': item.get('command_type'),
            'command_data': cmd_data,
            'command': cmd_str,
            'source': item.get('source'),
            'is_simulated': bool(item.get('is_simulated', False)),
            'result': item.get('result', ''),
            'reason': item.get('reason', ''),
        }

    def _build_alerts(self, env, distance_cm, timestamp):
        device_id = getattr(self.udp_car_service, 'device_id', None) or 'factory_001'
        thresholds = None
        controller = self._get_linkage_controller()
        if controller is not None:
            try:
                thresholds = controller.get_alert_thresholds()
            except Exception as e:
                logger.debug(f'读取告警阈值失败: {e}')
        return evaluate_gas_alert_level(env, distance_cm, device_id=device_id,
                                        timestamp=timestamp, thresholds=thresholds)

    def _get_linkage_controller(self):
        if self.linkage_controller is not None:
            return self.linkage_controller
        try:
            from app.services.registry import get_service
            return get_service('linkage_controller')
        except Exception:
            return None

    def _linkage_snapshot(self):
        """读取 LinkageController 的当前状态（无控制器时返回禁用占位）"""
        controller = self._get_linkage_controller()
        if controller is None:
            return {
                'enabled': False,
                'fan': None,
                'led': None,
                'rgb': {'r': 0, 'g': 0, 'b': 0},
                'alertLevel': 'normal',
                'reasons': {},
                'manualOverrideRemaining': {},
            }
        try:
            return controller.get_status_snapshot()
        except Exception as e:
            logger.warning(f'获取联动状态失败: {e}')
            return {'enabled': False}

    def _agent_snapshot(self):
        """读取 AgentService 的当前快照（无服务时返回 None）"""
        try:
            from app.services.registry import get_service
            agent = get_service('agent_service')
            if agent is None:
                return None
            return agent.get_snapshot()
        except Exception as e:
            logger.debug(f'获取智能体快照失败: {e}')
            return None

    def _human_detected(self, env, linkage):
        """与 LinkageController 一致的判定：ps>PS_TH 或 ir>IR_TH"""
        thresholds = (linkage or {}).get('thresholds') or {}
        ps_th = self._int(thresholds.get('irPs'), 200)
        ir_th = self._int(thresholds.get('irIr'), 100)
        ps = self._int(env.get('ps'), 0)
        ir = self._int(env.get('ir'), 0)
        return ps > ps_th or ir > ir_th

    def _distance_values(self, raw):
        if raw is None:
            return 60, 600
        raw_int = self._int(raw, 60)
        if raw_int > 200:
            return int(round(raw_int / 10)), raw_int
        return raw_int, raw_int * 10

    def _safe_limit(self, value, default=60, maximum=200):
        try:
            limit = int(value)
        except Exception:
            limit = default
        return max(1, min(maximum, limit))

    def _num(self, value, default=None):
        try:
            return round(float(value), 2)
        except Exception:
            return default

    def _int(self, value, default=0):
        try:
            return int(float(value))
        except Exception:
            return default
