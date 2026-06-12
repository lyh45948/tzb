"""
数字孪生大屏数据聚合服务
"""
from datetime import datetime

from app.services.registry import get_latest_sensor_data, get_default_sensor_data
from app.utils.logger import get_logger

logger = get_logger('dashboard_service')


class DashboardService:
    """数字孪生大屏快照服务"""

    def __init__(self, app, data_service=None, udp_car_service=None, agv_task_service=None):
        self.app = app
        self.data_service = data_service
        self.udp_car_service = udp_car_service
        self.agv_task_service = agv_task_service

    def get_snapshot(self):
        """获取数字孪生大屏当前快照"""
        timestamp = int(datetime.now().timestamp() * 1000)
        car_data = self._get_current_car_data()
        env = car_data.get('env', {}) if isinstance(car_data, dict) else {}
        distance_cm, distance_mm = self._distance_values(car_data.get('distance') if isinstance(car_data, dict) else None)
        smart_light = self._smart_light(env)
        # 视觉数据可能补充障碍物最近距离与计数器读数
        vision_obstacles, vision_counter = self._get_vision_caches()
        distance_cm, distance_mm = self._merge_vision_distance(distance_cm, distance_mm, vision_obstacles)
        alert_level, linked_reason, alarm_events = self._build_alerts(env, distance_cm, timestamp)
        fleet = self._get_fleet()
        command_logs = self._get_command_logs()

        data = {
            'timestamp': timestamp,
            'online': bool(self.udp_car_service and getattr(self.udp_car_service, 'connected', False)),
            'demoMode': False,

            'temperature': self._num(env.get('temp'), 24.5),
            'humidity': self._num(env.get('humi'), 58.0),
            'lux': self._int(env.get('lux'), 650),
            'ps': self._int(env.get('ps'), 0),
            'ir': self._int(env.get('ir'), 0),
            'humanDetected': 1 if self._int(env.get('ir'), 0) else 0,
            'pirStatus': 'detected' if self._int(env.get('ir'), 0) else 'clear',

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
            'smartLight': smart_light,
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
                'smartLightBrightness': snapshot['smartLight']['brightness'],
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
            return [{
                'id': item.get('id'),
                'timestamp': item.get('timestamp'),
                'device_id': item.get('device_id'),
                'command_type': item.get('command_type'),
                'command_data': item.get('command_data'),
                'source': item.get('source'),
            } for item in logs]
        except Exception as e:
            logger.warning(f'获取控制日志失败: {e}')
            return []

    def _build_alerts(self, env, distance_cm, timestamp):
        alerts = []
        level = 'normal'
        reason = '系统运行正常，无联动动作'

        co2 = self._int(env.get('co2'), 520)
        tvoc = self._int(env.get('tvoc'), 180)
        gas_mic = self._int(env.get('gasMic'), 120)
        gas_status = self._int(env.get('gasStatus'), 0)
        flame_status = self._int(env.get('flameStatus'), 0)

        def push(alert_level, alert_type, message, metric, value, threshold, suggestion):
            alerts.append({
                'id': timestamp + len(alerts),
                'timestamp': timestamp,
                'level': alert_level,
                'type': alert_type,
                'asset': '智慧工厂',
                'device_id': getattr(self.udp_car_service, 'device_id', None) or 'factory_001',
                'title': message,
                'message': message,
                'metric': metric,
                'value': value,
                'threshold': threshold,
                'source': 'backend',
                'handled': False,
                'suggestion': suggestion,
                'status': 'active',
            })

        if flame_status:
            level = 'critical'
            reason = '检测到火焰风险，已建议蜂鸣器报警并联动停车'
            push('critical', 'flame', '检测到火焰风险', '火焰状态', flame_status, '0', '立即停机并检查现场')
        elif gas_status or gas_mic >= 500 or co2 >= 1000 or tvoc >= 900:
            level = 'danger'
            reason = '危气指标达到危险阈值，建议开启通风并暂停AGV任务'
            push('danger', 'gas', '危气指标达到危险阈值', '危气/CO2/TVOC', max(gas_mic, co2, tvoc), 'danger', '开启通风并检查危气源')
        elif gas_mic >= 300 or co2 >= 800 or tvoc >= 600:
            level = 'warning'
            reason = '危气指标偏高，建议关注通风状态'
            push('warning', 'gas', '危气指标偏高', '危气/CO2/TVOC', max(gas_mic, co2, tvoc), 'warning', '加强通风并持续观察')
        elif distance_cm is not None and distance_cm <= 15:
            level = 'danger'
            reason = 'AGV距离障碍物过近，建议立即停车'
            push('danger', 'obstacle', f'AGV距离障碍物过近 {distance_cm}cm', '安全距离', distance_cm, '15cm', 'AGV停车，清理通道障碍')
        elif distance_cm is not None and distance_cm <= 30:
            level = 'warning'
            reason = 'AGV接近障碍物，建议减速避障'
            push('warning', 'obstacle', f'AGV接近障碍物 {distance_cm}cm', '安全距离', distance_cm, '30cm', 'AGV减速，检查通道')

        return level, reason, alerts

    def _smart_light(self, env):
        data = env.get('smartLight') or {}
        mode = self._int(data.get('mode'), 1)
        time_period = self._int(data.get('timePeriod'), 1)
        light_level = self._int(data.get('lightLevel'), 3)
        return {
            'mode': mode,
            'modeName': '自动' if mode == 1 else '手动',
            'brightness': self._int(data.get('brightness'), 50),
            'targetBrightness': self._int(data.get('targetBrightness'), 70),
            'timePeriod': time_period,
            'timePeriodName': self._time_period_name(time_period),
            'lightLevel': light_level,
            'lightLevelName': self._light_level_name(light_level),
        }

    def _distance_values(self, raw):
        if raw is None:
            return 60, 600
        raw_int = self._int(raw, 60)
        if raw_int > 200:
            return int(round(raw_int / 10)), raw_int
        return raw_int, raw_int * 10

    def _time_period_name(self, value):
        return {
            0: '夜间节能',
            1: '上午生产',
            2: '午间巡检',
            3: '下午生产',
            4: '晚间巡检',
            5: '深夜待机',
        }.get(value, '自动')

    def _light_level_name(self, value):
        return {
            0: '极暗',
            1: '偏暗',
            2: '较暗',
            3: '正常',
            4: '明亮',
            5: '强光',
        }.get(value, '正常')

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
