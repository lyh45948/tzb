"""
智能光照服务（内存版）
实现光照强度数据采集、LED补光亮度调节逻辑
本项目已移除智慧光照数据库表，状态仅保存在内存中
"""
from datetime import datetime, time
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SmartLightService:
    """智能光照服务"""

    # 光照等级阈值 (lux)
    LUX_DARK = 50       # 黑暗
    LUX_DIM = 200       # 昏暗
    LUX_LOW = 500       # 偏暗
    LUX_NORMAL = 1000   # 正常
    LUX_BRIGHT = 2000   # 明亮

    # 时间段定义（基准值，会根据季节调整）
    TIME_PERIODS_BASE = {
        0: ('黎明', 5, 8),
        1: ('上午', 8, 12),
        2: ('中午', 12, 14),
        3: ('下午', 14, 17),
        4: ('黄昏', 17, 19),
        5: ('晚间', 19, 23),
        6: ('深夜', 23, 5),
    }

    # 季节配置
    SEASON_CONFIG = {
        'spring': {
            'name': '春季',
            'time_adjust': 0,          # 无时间调整
            'brightness_adjust': 0     # 无亮度调整
        },
        'summer': {
            'name': '夏季',
            'time_adjust': -1,         # 时间段提前1小时（日照更长）
            'brightness_adjust': -10   # 减少补光10%（自然光充足）
        },
        'autumn': {
            'name': '秋季',
            'time_adjust': 0,
            'brightness_adjust': 0
        },
        'winter': {
            'name': '冬季',
            'time_adjust': 1,          # 时间段推迟1小时（日照更短）
            'brightness_adjust': 15    # 增加补光15%（自然光不足）
        }
    }

    def __init__(self):
        self.current_status = {}  # 设备当前状态缓存
        # 亮度平滑器
        self.brightness_smoother = {}  # {device_id: [brightness1, brightness2, ...]}
        self.brightness_window_size = 5  # 平滑窗口大小
        self.min_brightness_change = 5   # 最小变化阈值(%)

    def _get_season(self, month: int) -> str:
        """
        根据月份获取季节
        """
        if month in [3, 4, 5]:
            return 'spring'   # 春季
        elif month in [6, 7, 8]:
            return 'summer'   # 夏季
        elif month in [9, 10, 11]:
            return 'autumn'   # 秋季
        else:
            return 'winter'   # 冬季

    def get_season_config(self) -> dict:
        """
        获取当前季节配置
        """
        month = datetime.now().month
        season = self._get_season(month)
        return self.SEASON_CONFIG.get(season, self.SEASON_CONFIG['spring'])

    def get_adjusted_time_periods(self) -> dict:
        """
        根据季节获取调整后的时间段
        """
        season_config = self.get_season_config()
        time_adjust = season_config['time_adjust']

        adjusted = {}
        for period_id, (name, start_hour, end_hour) in self.TIME_PERIODS_BASE.items():
            # 调整时间（小时），处理跨午夜情况
            adjusted_start = (start_hour + time_adjust) % 24
            adjusted_end = (end_hour + time_adjust) % 24
            adjusted[period_id] = (name, time(adjusted_start, 0), time(adjusted_end, 0))

        return adjusted

    def get_time_period(self, current_time=None):
        """
        获取当前时间段（考虑季节调整）
        """
        if current_time is None:
            current_time = datetime.now().time()

        # 获取季节调整后的时间段
        time_periods = self.get_adjusted_time_periods()

        for period_id, (name, start, end) in time_periods.items():
            if start <= end:
                if start <= current_time < end:
                    return period_id
            else:  # 跨午夜的情况（深夜）
                if current_time >= start or current_time < end:
                    return period_id

        return 6  # 默认深夜

    def _smooth_brightness(self, device_id, new_brightness):
        """
        平滑亮度变化，防止频繁波动
        """
        if device_id not in self.brightness_smoother:
            self.brightness_smoother[device_id] = []

        smoother = self.brightness_smoother[device_id]
        smoother.append(new_brightness)

        # 保持窗口大小
        if len(smoother) > self.brightness_window_size:
            smoother.pop(0)

        # 计算平均值
        if len(smoother) > 0:
            return sum(smoother) // len(smoother)
        return new_brightness

    def get_light_level(self, lux):
        """
        获取光照等级
        """
        if lux < self.LUX_DARK:
            return 0  # 黑暗
        elif lux < self.LUX_DIM:
            return 1  # 昏暗
        elif lux < self.LUX_LOW:
            return 2  # 偏暗
        elif lux < self.LUX_NORMAL:
            return 3  # 正常
        elif lux < self.LUX_BRIGHT:
            return 4  # 明亮
        else:
            return 5  # 非常明亮

    def calculate_brightness(self, device_id, lux, auto_mode=True, manual_brightness=None):
        """
        计算LED补光亮度（包含季节调整）
        """
        current_time = datetime.now()
        time_period = self.get_time_period(current_time.time())
        light_level = self.get_light_level(lux)

        # 获取季节配置
        season_config = self.get_season_config()
        season_name = season_config['name']
        brightness_adjust = season_config['brightness_adjust']

        # 获取调整后的时间段名称
        adjusted_periods = self.get_adjusted_time_periods()
        time_period_name = adjusted_periods[time_period][0]

        result = {
            'time_period': time_period,
            'time_period_name': time_period_name,
            'light_level': light_level,
            'lux': lux,
            'mode': 'auto' if auto_mode else 'manual',
            'season': season_name,
            'brightness': 0,
            'target_brightness': 0
        }

        if auto_mode:
            # 自动模式：根据时间、光照强度和季节计算亮度
            raw_brightness = self._calc_auto_brightness(lux, time_period, brightness_adjust)

            # 获取上一次的亮度
            last_brightness = self.current_status.get(device_id, {}).get('brightness', 0)

            # 只有变化超过阈值才平滑更新
            if abs(raw_brightness - last_brightness) >= self.min_brightness_change:
                brightness = self._smooth_brightness(device_id, raw_brightness)
            else:
                brightness = last_brightness

            result['brightness'] = brightness
            result['target_brightness'] = brightness
        else:
            # 手动模式：使用用户设定的亮度（不平滑）
            brightness = manual_brightness if manual_brightness is not None else 0
            result['brightness'] = brightness
            result['target_brightness'] = brightness
            # 清空平滑器，避免下次切换到自动模式时受旧数据影响
            if device_id in self.brightness_smoother:
                self.brightness_smoother[device_id] = []

        # 更新缓存
        self.current_status[device_id] = result

        logger.info(f"智能光照计算: 设备={device_id}, 季节={season_name}, 亮度={brightness}%, 模式={'自动' if auto_mode else '手动'}")

        return result

    def _calc_auto_brightness(self, lux, time_period, brightness_adjust=0):
        """
        自动模式下的亮度计算（包含季节调整）
        """
        # 深夜时段 (23:00-5:00) 不补光
        if time_period == 6:
            return 0

        # 黎明和黄昏时段适度补光
        if time_period in [0, 4]:
            if lux < self.LUX_LOW:
                base_brightness = min(60, int((self.LUX_LOW - lux) / 10))
            else:
                base_brightness = 0
        else:
            # 白天时段 (上午、中午、下午、晚间)
            # 根据光照强度计算补光需求
            if lux >= self.LUX_NORMAL:
                # 光照充足，不补光
                base_brightness = 0
            elif lux >= self.LUX_LOW:
                # 光照偏暗，轻度补光
                base_brightness = min(30, int((self.LUX_NORMAL - lux) / 20))
            elif lux >= self.LUX_DIM:
                # 光照较暗，中度补光
                base_brightness = min(60, int((self.LUX_LOW - lux) / 5 + 30))
            else:
                # 光照很暗，重度补光
                base_brightness = min(100, int((self.LUX_DIM - lux) / 2 + 60))

        # 应用季节亮度调整
        adjusted_brightness = base_brightness + brightness_adjust

        # 限制范围
        adjusted_brightness = max(0, min(100, adjusted_brightness))

        return adjusted_brightness

    def set_mode(self, device_id, auto_mode, manual_brightness=None):
        """
        设置光照模式
        """
        # 获取当前光照（从缓存或默认）
        current = self.current_status.get(device_id, {})
        lux = current.get('lux', 0)

        result = self.calculate_brightness(device_id, lux, auto_mode, manual_brightness)

        return result

    def set_brightness(self, device_id, brightness):
        """
        设置亮度（手动模式）
        """
        # 限制范围
        brightness = max(0, min(100, int(brightness)))

        # 关键修复：先强制更新缓存中的模式为手动模式
        # 这确保后续 update_lux 调用时能正确读取到手动模式
        if device_id not in self.current_status:
            self.current_status[device_id] = {}
        self.current_status[device_id]['mode'] = 'manual'

        result = self.calculate_brightness(device_id, 0, auto_mode=False, manual_brightness=brightness)

        return result

    def update_lux(self, device_id, lux):
        """
        更新环境光照强度（自动模式下自动调节亮度）
        """
        current = self.current_status.get(device_id, {})
        auto_mode = current.get('mode', 'auto') == 'auto'
        manual_brightness = current.get('target_brightness', 0) if not auto_mode else None

        result = self.calculate_brightness(device_id, lux, auto_mode, manual_brightness)

        return result

    def get_current_status(self, device_id):
        """获取当前状态"""
        return self.current_status.get(device_id, {
            'mode': 'auto',
            'brightness': 0,
            'target_brightness': 0,
            'time_period': self.get_time_period(),
            'lux': 0
        })

    def get_status_history(self, device_id, limit=100):
        """
        获取状态历史
        由于已移除智慧光照数据库表，仅返回空列表
        """
        return []


# 单例
smart_light_service = SmartLightService()
