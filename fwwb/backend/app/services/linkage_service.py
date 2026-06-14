"""
LinkageController — 后端集中决策三条传感器联动规则

1. PIR(AP3216C ps/ir) → LED 自动照明（连续 N 次有人才点亮，连续 M 次无人才熄灭）
2. 温湿度 → 风扇自动启停（双门限回滞）
3. 危气 alertLevel → AW2013 RGB（warning=黄，danger=红，critical=红 1Hz 闪烁，normal=灭）

设计要点：
- 仅在 desired ≠ _state[ch] 时下发命令；首 tick 强制下发安全默认 (fan=0/led=0/rgb=(0,0,0))
- 小程序手动控制时调用 notify_manual(channel, ttl)，期间该路自动联动静默
- 通过 registry.get_latest_sensor_data() 读取传感器，避免与 dashboard_service 循环依赖
- 通过 alert_rules.evaluate_gas_alert_level() 复用告警分级逻辑
"""
import threading
import time

from app.services.registry import get_latest_sensor_data
from app.utils.alert_rules import evaluate_gas_alert_level
from app.utils.logger import get_logger

logger = get_logger('linkage_service')


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class LinkageController:
    """周期性读取传感器并根据规则下发执行器命令"""

    CHANNELS = ('fan', 'led', 'rgb')

    def __init__(self, app, udp_car_service, config):
        self.app = app
        self.udp_car_service = udp_car_service
        self.config = config

        self._tick_seconds = float(getattr(config, 'LINKAGE_TICK_SECONDS', 1.0))
        self._enabled = bool(getattr(config, 'LINKAGE_ENABLED', True))
        self._manual_ttl = int(getattr(config, 'MANUAL_OVERRIDE_TTL', 30))

        self._fan_temp_on = float(getattr(config, 'FAN_TEMP_ON', 32.0))
        self._fan_temp_off = float(getattr(config, 'FAN_TEMP_OFF', 30.0))
        self._fan_humi_on = float(getattr(config, 'FAN_HUMI_ON', 80.0))
        self._fan_humi_off = float(getattr(config, 'FAN_HUMI_OFF', 75.0))

        self._ir_ps_threshold = int(getattr(config, 'IR_PS_THRESHOLD', 200))
        self._ir_ir_threshold = int(getattr(config, 'IR_IR_THRESHOLD', 100))
        self._ir_debounce_on = int(getattr(config, 'IR_DEBOUNCE_ON', 2))
        self._ir_debounce_off = int(getattr(config, 'IR_DEBOUNCE_OFF', 5))

        # critical 闪烁：1Hz → 每 tick 翻转一次（tick=1s 时正好 1Hz）
        self._blink_hz = float(getattr(config, 'RGB_BLINK_HZ', 1.0))

        # 危气分级阈值（webapp 设置页可在线修改）
        self._alert_thresholds = {
            'co2_warning': int(getattr(config, 'CO2_WARNING', 800)),
            'co2_danger': int(getattr(config, 'CO2_DANGER', 1000)),
            'tvoc_warning': int(getattr(config, 'TVOC_WARNING', 600)),
            'tvoc_danger': int(getattr(config, 'TVOC_DANGER', 900)),
            'gasmic_warning': int(getattr(config, 'GASMIC_WARNING', 300)),
            'gasmic_danger': int(getattr(config, 'GASMIC_DANGER', 500)),
            'distance_warning': int(getattr(config, 'DISTANCE_WARNING', 30)),
            'distance_danger': int(getattr(config, 'DISTANCE_DANGER', 15)),
        }

        # 已下发执行器状态（None 表示从未下发，首 tick 强制初始化）
        self._state = {'fan': None, 'led': None, 'rgb': (None, None, None)}

        # PIR 去抖计数器
        self._pir_on_cnt = 0
        self._pir_off_cnt = 0

        # RGB 闪烁相位（每 tick 翻转）
        self._rgb_phase = False

        # 手动覆盖到期时间戳（time.monotonic 基准）
        self._manual_override = {ch: 0.0 for ch in self.CHANNELS}

        # 最近一次决策原因（暴露给 dashboard）
        self._last_decision_reason = {ch: '' for ch in self.CHANNELS}
        # 当前危气等级缓存（snapshot 用）
        self._last_alert_level = 'normal'
        self._first_tick = True

        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    # ---------- 生命周期 ----------

    def start(self):
        if not self._enabled:
            logger.info('LinkageController 已禁用 (LINKAGE_ENABLED=false)')
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name='linkage_controller', daemon=True
        )
        self._thread.start()
        logger.info(
            f'LinkageController started, tick={self._tick_seconds}s, '
            f'fan_on={self._fan_temp_on}/{self._fan_humi_on}, '
            f'fan_off={self._fan_temp_off}/{self._fan_humi_off}, '
            f'manual_ttl={self._manual_ttl}s'
        )

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info('LinkageController stopped')

    # ---------- 对外接口 ----------

    def notify_manual(self, channel, ttl=None):
        """小程序/Web 手动控制某路时调用，给该路注入静默期"""
        if channel not in self.CHANNELS:
            return
        ttl = self._manual_ttl if ttl is None else int(ttl)
        with self._lock:
            self._manual_override[channel] = time.monotonic() + ttl
        logger.info(f'[Linkage][{channel}] 手动覆盖生效 {ttl}s')

    def get_status_snapshot(self):
        """供 dashboard_service.get_snapshot() 嵌入"""
        with self._lock:
            now = time.monotonic()
            override = {
                ch: max(0, int(self._manual_override[ch] - now))
                for ch in self.CHANNELS
            }
            rgb = self._state['rgb']
            return {
                'enabled': self._enabled,
                'fan': self._state['fan'],
                'led': self._state['led'],
                'rgb': {
                    'r': rgb[0] if rgb[0] is not None else 0,
                    'g': rgb[1] if rgb[1] is not None else 0,
                    'b': rgb[2] if rgb[2] is not None else 0,
                },
                'alertLevel': self._last_alert_level,
                'reasons': dict(self._last_decision_reason),
                'manualOverrideRemaining': override,
                'thresholds': self._build_threshold_dict(),
            }

    def _build_threshold_dict(self):
        """完整阈值快照（联动 + 告警），webapp 设置页拉取用"""
        return {
            # 联动阈值
            'fanTempOn': self._fan_temp_on,
            'fanTempOff': self._fan_temp_off,
            'fanHumiOn': self._fan_humi_on,
            'fanHumiOff': self._fan_humi_off,
            'irPs': self._ir_ps_threshold,
            'irIr': self._ir_ir_threshold,
            'irDebounceOn': self._ir_debounce_on,
            'irDebounceOff': self._ir_debounce_off,
            'tickSeconds': self._tick_seconds,
            'manualOverrideTtl': self._manual_ttl,
            'rgbBlinkHz': self._blink_hz,
            # 告警阈值
            'co2Warning': self._alert_thresholds['co2_warning'],
            'co2Danger': self._alert_thresholds['co2_danger'],
            'tvocWarning': self._alert_thresholds['tvoc_warning'],
            'tvocDanger': self._alert_thresholds['tvoc_danger'],
            'gasMicWarning': self._alert_thresholds['gasmic_warning'],
            'gasMicDanger': self._alert_thresholds['gasmic_danger'],
            'distanceWarning': self._alert_thresholds['distance_warning'],
            'distanceDanger': self._alert_thresholds['distance_danger'],
        }

    def get_config(self):
        """返回完整配置快照，供 WebSocket linkage_config_get 响应"""
        with self._lock:
            return self._build_threshold_dict()

    def get_alert_thresholds(self):
        """供 dashboard_service 调用 evaluate_gas_alert_level 时注入当前阈值"""
        with self._lock:
            return dict(self._alert_thresholds)

    # 字段映射：webapp 字段名（camelCase） → 内部存储位置
    # ('attr', 'cast') -> setattr; ('alert', 'key', 'cast') -> 写入 _alert_thresholds[key]
    _FIELD_MAP = {
        'fanTempOn': ('attr', '_fan_temp_on', float),
        'fanTempOff': ('attr', '_fan_temp_off', float),
        'fanHumiOn': ('attr', '_fan_humi_on', float),
        'fanHumiOff': ('attr', '_fan_humi_off', float),
        'irPs': ('attr', '_ir_ps_threshold', int),
        'irIr': ('attr', '_ir_ir_threshold', int),
        'irDebounceOn': ('attr', '_ir_debounce_on', int),
        'irDebounceOff': ('attr', '_ir_debounce_off', int),
        'tickSeconds': ('attr', '_tick_seconds', float),
        'manualOverrideTtl': ('attr', '_manual_ttl', int),
        'rgbBlinkHz': ('attr', '_blink_hz', float),
        'co2Warning': ('alert', 'co2_warning', int),
        'co2Danger': ('alert', 'co2_danger', int),
        'tvocWarning': ('alert', 'tvoc_warning', int),
        'tvocDanger': ('alert', 'tvoc_danger', int),
        'gasMicWarning': ('alert', 'gasmic_warning', int),
        'gasMicDanger': ('alert', 'gasmic_danger', int),
        'distanceWarning': ('alert', 'distance_warning', int),
        'distanceDanger': ('alert', 'distance_danger', int),
    }

    def update_config(self, updates):
        """运行时更新阈值（部分更新；未识别 key 静默忽略）。

        Args:
            updates: dict[str, number] camelCase webapp 字段
        Returns:
            (applied: dict, ignored: dict) — 实际写入的 key 与被忽略的 key
        """
        applied = {}
        ignored = {}
        if not isinstance(updates, dict):
            return applied, ignored
        with self._lock:
            for key, raw in updates.items():
                if key not in self._FIELD_MAP or raw is None:
                    ignored[key] = raw
                    continue
                spec = self._FIELD_MAP[key]
                try:
                    if spec[0] == 'attr':
                        _, attr_name, cast = spec
                        value = cast(raw)
                        # 简单合理性校验
                        if attr_name == '_tick_seconds' and value <= 0:
                            ignored[key] = raw
                            continue
                        setattr(self, attr_name, value)
                        applied[key] = value
                    else:
                        _, alert_key, cast = spec
                        value = cast(raw)
                        self._alert_thresholds[alert_key] = value
                        applied[key] = value
                except (TypeError, ValueError):
                    ignored[key] = raw
        if applied:
            logger.info(f'[Linkage] update_config applied={applied} ignored={ignored or "{}"}')
        return applied, ignored

    # ---------- 主循环 ----------

    def _loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                logger.exception(f'LinkageController tick 异常: {e}')
            time.sleep(self._tick_seconds)

    def _is_overridden(self, channel):
        return time.monotonic() < self._manual_override.get(channel, 0.0)

    def _send(self, channel, payload, reason, new_state):
        """下发命令并更新状态。返回是否真正下发。"""
        if self._is_overridden(channel):
            logger.debug(f'[Linkage][{channel}] 在手动覆盖静默期内，跳过自动下发')
            return False
        ok = False
        if self.udp_car_service is not None:
            try:
                ok = self.udp_car_service.send_command(payload)
            except Exception as e:
                logger.warning(f'[Linkage][{channel}] send_command 异常: {e}')
                ok = False
        old_state = self._state[channel]
        # 仅在确认下发成功时才更新 _state；失败时保持旧值，下个 tick 会重试
        # 否则可能出现："下发失败但 _state 已变 → 下次 desired==_state → 永不重试"的卡死
        if ok:
            self._state[channel] = new_state
        with self._lock:
            self._last_decision_reason[channel] = reason
        logger.info(
            f'[Linkage][{channel}] reason={reason} old={old_state} new={new_state} sent={ok}'
        )
        return ok

    def _tick(self):
        snapshot = get_latest_sensor_data() or {}
        env = snapshot.get('env', {}) if isinstance(snapshot, dict) else {}

        # 危气分级（注入运行时可调阈值；本控制器只关心环境告警，不传 distance_cm）
        level, _reason, _alerts = evaluate_gas_alert_level(env, thresholds=self.get_alert_thresholds())
        with self._lock:
            self._last_alert_level = level

        # 首 tick 强制初始化（无视当前状态）
        first = self._first_tick
        self._first_tick = False

        self._handle_led(env, force=first)
        self._handle_fan(env, force=first)
        self._handle_rgb(level, force=first)

        # RGB 闪烁相位翻转（每 tick）
        self._rgb_phase = not self._rgb_phase

    # ---------- 三条规则 ----------

    def _handle_led(self, env, force=False):
        ps = _to_int(env.get('ps'), 0)
        ir = _to_int(env.get('ir'), 0)
        present = (ps > self._ir_ps_threshold) or (ir > self._ir_ir_threshold)

        if present:
            self._pir_on_cnt += 1
            self._pir_off_cnt = 0
        else:
            self._pir_off_cnt += 1
            self._pir_on_cnt = 0

        desired = None
        if self._pir_on_cnt >= self._ir_debounce_on:
            desired = 1
        elif self._pir_off_cnt >= self._ir_debounce_off:
            desired = 0

        if force and desired is None:
            # 首 tick 缺数据时默认关灯
            desired = 0

        if desired is None:
            return

        if force or desired != self._state['led']:
            reason = f'ps={ps},ir={ir},on_cnt={self._pir_on_cnt},off_cnt={self._pir_off_cnt}'
            self._send('led', {'led': desired}, reason, desired)

    def _handle_fan(self, env, force=False):
        temp = _to_float(env.get('temp'), 0.0)
        humi = _to_float(env.get('humi'), 0.0)

        cur = self._state['fan']
        desired = cur

        if cur != 1:  # 当前关 / 未初始化
            if temp >= self._fan_temp_on or humi >= self._fan_humi_on:
                desired = 1
            elif force:
                desired = 0
        else:           # 当前开
            if temp <= self._fan_temp_off and humi <= self._fan_humi_off:
                desired = 0

        if desired is None:
            return

        if force or desired != cur:
            reason = f'temp={temp:.1f},humi={humi:.1f}'
            self._send('fan', {'fan': desired}, reason, desired)

    def _handle_rgb(self, level, force=False):
        if level == 'critical':
            desired = (255, 0, 0) if self._rgb_phase else (0, 0, 0)
        elif level == 'danger':
            desired = (255, 0, 0)
        elif level == 'warning':
            desired = (255, 255, 0)
        else:
            desired = (0, 0, 0)

        if force or desired != self._state['rgb']:
            reason = f'alertLevel={level}'
            payload = {'rgb': {'r': desired[0], 'g': desired[1], 'b': desired[2]}}
            self._send('rgb', payload, reason, desired)
