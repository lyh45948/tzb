"""
车辆环境监测智能体（嵌入式版本）

由 SmartCarBackend 在主进程内拉起，与 LinkageController / DashboardStreamService 同生命周期。

职责：
1. 周期性读取 registry.get_latest_sensor_data() 的环境数据
2. 规则判定异常等级：normal / warning / critical
3. critical 时直接通过 udp_car_service.send_command 下发硬件动作
   （fan=1 通风、buzzer=1 报警、carStatus=stop 停车），同时给 LinkageController
   注入手动覆盖避免自动联动反向决策
4. 维护内存 ring buffer：alerts / analyses / predictions / reports
5. 暴露 get_snapshot()，被 DashboardService 嵌入到 dashboard 快照的 aiAgent 字段，
   通过现有 SSE 通道推送到 dashboard1 大屏

设计要点：
- 不开 HTTP 自调用、不依赖 ollama 强装。ollama 通过 requests 走 /api/chat，
  默认 disabled；任何异常都走模板兜底（保证没有大模型也能跑完整流程）。
- 共用 evaluate_gas_alert_level 的告警判定可能更强，但本服务的判定面向
  AGV 车舱环境（CO/温度/TVOC/燃气泄漏），与 dashboard 用的工厂级判定互补，
  不复用以避免参数语义错位。
"""
import json
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta

from app.services.registry import get_latest_sensor_data
from app.utils.logger import get_logger

logger = get_logger('agent_service')


# ==================== 工具：趋势 + 异常判定 ====================
class EnvironmentPredictor:
    """环境趋势 + 异常判定（移植自 vehicle_agent1.2.py，去掉 print 噪声）"""

    @staticmethod
    def calculate_trend(values):
        """对一维数值序列做最小二乘斜率，返回趋势字典"""
        values = [float(v) for v in values if v is not None]
        if len(values) < 3:
            return {'trend': 'unknown', 'change_rate': 0.0,
                    'current': values[-1] if values else None,
                    'next_prediction': None, 'confidence': 0.0}

        n = len(values)
        x = list(range(n))
        denom = n * sum(i * i for i in x) - sum(x) ** 2
        if denom == 0:
            slope = 0.0
        else:
            slope = (n * sum(x[i] * values[i] for i in range(n))
                     - sum(x) * sum(values)) / denom

        change_rate = slope / (values[-1] + 1e-6) * 100
        if slope > 0.01:
            trend = 'up'
        elif slope < -0.01:
            trend = 'down'
        else:
            trend = 'flat'

        return {
            'trend': trend,
            'change_rate': round(change_rate, 2),
            'current': values[-1],
            'next_prediction': round(values[-1] + slope, 2),
            'confidence': min(0.9, 0.7 + n / 100),
        }

    @staticmethod
    def check_anomaly(env, thresholds):
        """根据当前环境数据 + 阈值判定异常。

        返回 dict：
        {
            has_anomaly: bool,
            level: 'normal'|'warning'|'critical',
            anomalies: List[str],           # 人类可读的异常描述
            recommendations: List[str],     # 配套建议
            metrics: dict,                  # 关键数值（co/temp/tvoc/gasStatus）
            action_stop_car: bool,          # 是否需要触发停车
        }
        """
        anomalies = []
        recommendations = []
        level = 'normal'
        action_stop_car = False

        env = env or {}
        co_warning = thresholds['co_warning']
        co_critical = thresholds['co_critical']
        temp_min = thresholds['temp_min']
        temp_max = thresholds['temp_max']
        tvoc_warning = thresholds['tvoc_warning']

        # CO（一氧化碳）—— 必须使用 env.co 字段（来自 MQ-7）。
        # 不退回 env.co2：CO2(SGP30) 与 CO 量级完全不同（400~1500ppm vs 0~50ppm），
        # 用 CO2 判 CO 一定误报。dashboardAdapter 在前端做的"CO2→CO 量级映射"
        # 是显示层的脏 hack，后端判定不能依赖。
        co_value = env.get('co')
        if co_value is not None:
            try:
                co_v = float(co_value)
            except (TypeError, ValueError):
                co_v = None
            if co_v is not None:
                if co_v > co_critical:
                    anomalies.append(f'一氧化碳浓度严重超标: {co_v:.1f}ppm')
                    recommendations.append('立即撤离！开启通风、关闭明火、拨打急救电话')
                    level = 'critical'
                    action_stop_car = True
                elif co_v > co_warning:
                    anomalies.append(f'一氧化碳浓度偏高: {co_v:.1f}ppm')
                    recommendations.append('立即开窗通风，检查燃气设备')
                    if level != 'critical':
                        level = 'warning'

        # 燃气泄漏（数字信号）—— 直接 critical
        gas_status = env.get('gasStatus')
        if gas_status in (1, '1', True):
            anomalies.append('检测到燃气泄漏')
            recommendations.append('立即关闭燃气阀门、开窗通风、不要使用电器')
            level = 'critical'
            action_stop_car = True

        # 火焰
        flame_status = env.get('flameStatus')
        if flame_status in (1, '1', True):
            anomalies.append('检测到火焰风险')
            recommendations.append('立即停机、撤离并拨打消防电话')
            level = 'critical'
            action_stop_car = True

        # 温度
        temp = env.get('temp')
        if temp is not None:
            try:
                temp_v = float(temp)
                if temp_v < temp_min:
                    anomalies.append(f'温度过低: {temp_v:.1f}°C')
                    recommendations.append('检查空调系统或通风口设置')
                    if level == 'normal':
                        level = 'warning'
                elif temp_v > temp_max:
                    anomalies.append(f'温度过高: {temp_v:.1f}°C')
                    recommendations.append('开启风扇/空调，检查热源')
                    if level == 'normal':
                        level = 'warning'
            except (TypeError, ValueError):
                pass

        # TVOC
        tvoc = env.get('tvoc')
        if tvoc is not None:
            try:
                tvoc_v = float(tvoc)
                if tvoc_v > tvoc_warning:
                    anomalies.append(f'TVOC 超标: {tvoc_v:.0f}ppb')
                    recommendations.append('开启空气净化器，检查装修材料')
                    if level == 'normal':
                        level = 'warning'
            except (TypeError, ValueError):
                pass

        return {
            'has_anomaly': len(anomalies) > 0,
            'level': level,
            'anomalies': anomalies,
            'recommendations': recommendations,
            'metrics': {
                'co': co_value,
                'temp': env.get('temp'),
                'tvoc': env.get('tvoc'),
                'gasStatus': gas_status,
                'flameStatus': flame_status,
            },
            'action_stop_car': action_stop_car,
        }


# ==================== 主服务 ====================
class AgentService:
    """嵌入式车辆环境智能体"""

    # ring buffer 容量
    MAX_ALERTS = 100
    MAX_ANALYSES = 30
    MAX_PREDICTIONS = 30
    MAX_REPORTS = 14   # 两周

    def __init__(self, app, config,
                 udp_car_service=None,
                 data_service=None,
                 linkage_controller=None):
        self.app = app
        self.config = config
        self.udp_car_service = udp_car_service
        self.data_service = data_service
        self.linkage_controller = linkage_controller

        self._enabled = bool(getattr(config, 'AGENT_ENABLED', True))
        self._tick = max(1.0, float(getattr(config, 'AGENT_TICK_SECONDS', 5.0)))
        self._analysis_interval = max(self._tick,
                                      float(getattr(config, 'AGENT_PREDICTION_INTERVAL', 60.0)))
        self._device_id = str(getattr(config, 'AGENT_DEVICE_ID', 'car1'))

        self._daily_hour = int(getattr(config, 'AGENT_DAILY_REPORT_HOUR', 20))
        # 周一=0，周日=6（与 vehicle_agent1.2.py 一致）
        self._weekly_day = int(getattr(config, 'AGENT_WEEKLY_REPORT_DAY', 6))
        self._weekly_hour = int(getattr(config, 'AGENT_WEEKLY_REPORT_HOUR', 20))

        self._thresholds = {
            'co_warning': float(getattr(config, 'AGENT_CO_WARNING', 10)),
            'co_critical': float(getattr(config, 'AGENT_CO_CRITICAL', 30)),
            'temp_min': float(getattr(config, 'AGENT_TEMP_MIN', 15)),
            'temp_max': float(getattr(config, 'AGENT_TEMP_MAX', 35)),
            'tvoc_warning': float(getattr(config, 'AGENT_TVOC_WARNING', 300)),
        }

        # ollama 兜底配置
        self._ollama_enabled = bool(getattr(config, 'AGENT_OLLAMA_ENABLED', False))
        self._ollama_url = str(getattr(config, 'AGENT_OLLAMA_URL', 'http://localhost:11434')).rstrip('/')
        self._ollama_model = str(getattr(config, 'AGENT_OLLAMA_MODEL', 'deepseek-r1:7b'))
        # 默认 90s —— deepseek-r1:7b 是 reasoning 模型，首次冷启动 + 推理常 50s 起
        self._ollama_chat_timeout = float(getattr(config, 'AGENT_OLLAMA_TIMEOUT', 90))
        self._ollama_report_timeout = float(getattr(config, 'AGENT_OLLAMA_REPORT_TIMEOUT', 180))
        self._ollama_ok = False  # 探活后真实状态
        self._ollama_last_check = 0.0

        # critical 命令冷却，避免每秒下发同一组命令
        self._critical_cooldown = float(getattr(config, 'AGENT_CRITICAL_COOLDOWN', 30))
        self._last_critical_action_at = 0.0

        # 内存缓存
        self._lock = threading.Lock()
        self._alerts = deque(maxlen=self.MAX_ALERTS)
        self._analyses = deque(maxlen=self.MAX_ANALYSES)
        self._predictions = deque(maxlen=self.MAX_PREDICTIONS)
        self._reports = {'daily': deque(maxlen=self.MAX_REPORTS),
                         'weekly': deque(maxlen=self.MAX_REPORTS)}
        # 历史采样窗（每 tick 推一帧，最长 720 帧 = 1h@5s）
        self._history = deque(maxlen=720)

        # 内部状态
        self._status = 'idle'
        self._predictor = EnvironmentPredictor()
        self._last_anomaly_key = None      # 用于去重连续相同告警
        self._last_analysis_at = 0.0
        self._last_daily_report_date = None
        self._last_weekly_week = None

        self._running = False
        self._thread = None

    # ------------- 生命周期 -------------
    def start(self):
        if not self._enabled:
            logger.info('AgentService 已禁用 (AGENT_ENABLED=false)')
            return
        if self._running:
            return
        self._running = True
        self._status = 'running'
        self._thread = threading.Thread(target=self._loop,
                                        name='agent_service', daemon=True)
        self._thread.start()
        # 启动时探活 ollama
        if self._ollama_enabled:
            self._probe_ollama()
        logger.info(
            f'AgentService started, device={self._device_id}, tick={self._tick}s, '
            f'analysis_interval={self._analysis_interval}s, '
            f'ollama={"connected" if self._ollama_ok else ("disabled" if not self._ollama_enabled else "not reachable, fallback to template")}'
        )

    def stop(self):
        self._running = False
        self._status = 'stopped'
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info('AgentService stopped')

    # ------------- 主循环 -------------
    def _loop(self):
        while self._running:
            try:
                self._do_tick()
            except Exception as e:
                logger.exception(f'AgentService tick 异常: {e}')
            time.sleep(self._tick)

    def _do_tick(self):
        now_ts = time.time()
        now = datetime.now()

        snapshot = get_latest_sensor_data() or {}
        env = snapshot.get('env', {}) if isinstance(snapshot, dict) else {}

        # 入历史缓存（co 不退回 co2 — 量级语义不同）
        self._history.append({
            'ts': int(now_ts * 1000),
            'temp': env.get('temp'),
            'humi': env.get('humi'),
            'co': env.get('co'),
            'tvoc': env.get('tvoc'),
            'gasStatus': env.get('gasStatus'),
        })

        # 异常判定
        result = self._predictor.check_anomaly(env, self._thresholds)
        if result['has_anomaly']:
            self._record_alert(result, env, now)
            if result['level'] == 'critical':
                self._status = 'critical'
                if now_ts - self._last_critical_action_at >= self._critical_cooldown:
                    self._execute_critical_action(result)
                    self._last_critical_action_at = now_ts
            else:
                self._status = 'alert'
        else:
            self._last_anomaly_key = None
            self._status = 'normal'

        # 趋势分析（独立周期）
        if now_ts - self._last_analysis_at >= self._analysis_interval:
            self._run_analysis(env)
            self._last_analysis_at = now_ts

        # 日报
        if (now.hour == self._daily_hour
                and self._last_daily_report_date != now.date()):
            self._safe(self.generate_daily_report)
            self._last_daily_report_date = now.date()

        # 周报
        if (now.weekday() == self._weekly_day
                and now.hour == self._weekly_hour):
            week_key = now.strftime('%Y-%W')
            if self._last_weekly_week != week_key:
                self._safe(self.generate_weekly_report)
                self._last_weekly_week = week_key

    def _safe(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.exception(f'AgentService 调用 {fn.__name__} 失败: {e}')
            return None

    # ------------- 告警 + 硬件动作 -------------
    def _record_alert(self, result, env, now):
        """把判定结果写入 ring buffer；连续相同 level+anomalies 不重复入队"""
        anomaly_key = (result['level'], '|'.join(result['anomalies']))
        if anomaly_key == self._last_anomaly_key:
            return
        self._last_anomaly_key = anomaly_key

        record = {
            'id': int(now.timestamp() * 1000),
            'timestamp': now.isoformat(),
            'device_id': self._device_id,
            'level': result['level'],
            'message': '；'.join(result['anomalies']) or '环境异常',
            'recommendations': list(result['recommendations']),
            'metrics': result['metrics'],
            'env': {k: env.get(k) for k in ('temp', 'humi', 'co', 'co2', 'tvoc',
                                            'gasStatus', 'flameStatus')},
            'actionTaken': None,
        }
        with self._lock:
            self._alerts.append(record)
        logger.warning(
            f"[Agent] level={result['level']} {record['message']}"
        )

    def _execute_critical_action(self, result):
        """critical 时下发硬件命令并写控制日志"""
        actions = {'fan': 1, 'buzzer': 1}
        if result['action_stop_car']:
            actions['carStatus'] = 'stop'

        sent_results = {}
        if self.udp_car_service is not None:
            for cmd_key, cmd_val in actions.items():
                payload = {cmd_key: cmd_val}
                ok = False
                try:
                    ok = bool(self.udp_car_service.send_command(payload))
                except Exception as e:
                    logger.warning(f'[Agent] 下发 {payload} 异常: {e}')
                sent_results[cmd_key] = ok
        else:
            logger.warning('[Agent] udp_car_service 未注入，无法执行硬件动作')
            sent_results = {k: False for k in actions}

        # 防止 LinkageController 立刻把风扇关掉
        if self.linkage_controller is not None:
            try:
                self.linkage_controller.notify_manual('fan', ttl=60)
            except Exception as e:
                logger.debug(f'[Agent] notify_manual 失败: {e}')

        # 控制日志
        if self.data_service is not None:
            try:
                self.data_service.save_control_command(
                    self._device_id,
                    'agent_critical',
                    actions,
                    source='agent',
                    is_simulated=not any(sent_results.values()),
                )
            except Exception as e:
                logger.debug(f'[Agent] save_control_command 失败: {e}')

        # 把动作回填到最近一次告警上
        with self._lock:
            if self._alerts:
                self._alerts[-1]['actionTaken'] = {
                    'commands': actions,
                    'sent': sent_results,
                }
        logger.error(
            f'[Agent] critical 动作已下发: {actions} '
            f'sent={sent_results}'
        )

    # ------------- 趋势分析 -------------
    def _run_analysis(self, env):
        """计算 CO/温度/湿度趋势，并产出 AI 文本（ollama 或模板）"""
        if len(self._history) < 5:
            return

        trends = {}
        for field in ('co', 'temp', 'humi', 'tvoc'):
            series = [row.get(field) for row in self._history
                      if row.get(field) is not None]
            if len(series) < 3:
                continue
            trends[field] = self._predictor.calculate_trend(series[-30:])

        # 风险预测：CO 上升 + 预测越线 → 入预测队列
        for field, trend in trends.items():
            if trend['trend'] != 'up' or trend.get('change_rate', 0) < 5:
                continue
            next_v = trend.get('next_prediction')
            if next_v is None:
                continue
            risk = None
            msg = None
            if field == 'co' and next_v > self._thresholds['co_warning']:
                risk = 'critical' if next_v > self._thresholds['co_critical'] else 'warning'
                msg = f'预测一氧化碳将上升到 {next_v}ppm，已接近告警阈值'
            elif field == 'temp' and next_v > self._thresholds['temp_max']:
                risk = 'warning'
                msg = f'预测温度将上升到 {next_v}°C，建议提前通风'
            elif field == 'tvoc' and next_v > self._thresholds['tvoc_warning']:
                risk = 'warning'
                msg = f'预测 TVOC 将上升到 {next_v}ppb，建议开启净化器'
            if risk and msg:
                self._record_prediction(field, trend, risk, msg)

        # AI 文本
        text = self._call_ai_routine(env, trends)
        with self._lock:
            self._analyses.append({
                'id': int(time.time() * 1000),
                'timestamp': datetime.now().isoformat(),
                'device_id': self._device_id,
                'text': text,
                'trends': trends,
                'has_anomaly': self._last_anomaly_key is not None,
                'aiBackend': 'ollama' if self._ollama_ok else 'template',
            })
        logger.debug(f'[Agent] analysis: {text}')

    def _record_prediction(self, field, trend, risk, msg):
        record = {
            'id': int(time.time() * 1000),
            'timestamp': datetime.now().isoformat(),
            'device_id': self._device_id,
            'field': field,
            'trend': trend['trend'],
            'changeRate': trend.get('change_rate'),
            'currentValue': trend.get('current'),
            'nextPrediction': trend.get('next_prediction'),
            'riskLevel': risk,
            'message': msg,
        }
        with self._lock:
            self._predictions.append(record)
        logger.info(f'[Agent] prediction {field} -> {msg}')

    # ------------- 报告 -------------
    def generate_daily_report(self):
        today = datetime.now().strftime('%Y-%m-%d')
        history = self._fetch_history(start=f'{today} 00:00:00',
                                      end=f'{today} 23:59:59')
        if not history:
            logger.info('[Agent] 今日无历史数据，跳过日报生成')
            return None
        return self._build_report('daily', today, history)

    def generate_weekly_report(self):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        history = self._fetch_history(
            start=start_date.strftime('%Y-%m-%d 00:00:00'),
            end=end_date.strftime('%Y-%m-%d 23:59:59'),
        )
        if not history:
            logger.info('[Agent] 本周无历史数据，跳过周报生成')
            return None
        date_label = f"{start_date.strftime('%Y-%m-%d')}~{end_date.strftime('%Y-%m-%d')}"
        return self._build_report('weekly', date_label, history)

    def _fetch_history(self, start, end):
        """优先查 DB，失败时退回内存历史"""
        if self.data_service is not None:
            try:
                rows = self.data_service.query_sensor_history(
                    device_id=self._device_id,
                    start_time=start,
                    end_time=end,
                ) or []
                if rows:
                    return rows
            except Exception as e:
                logger.debug(f'[Agent] query_sensor_history 失败: {e}')
        # 内存兜底
        return list(self._history)

    def _build_report(self, kind, date_label, history):
        temps = []
        cos = []
        alerts_count = 0
        for row in history:
            t = row.get('temperature') if row.get('temperature') is not None \
                else row.get('temp')
            if t is not None:
                try:
                    temps.append(float(t))
                except (TypeError, ValueError):
                    pass
            # 报告里的 CO 也只取 env.co，避免 CO2 误入
            c = row.get('co')
            if c is not None:
                try:
                    cos.append(float(c))
                except (TypeError, ValueError):
                    pass
            if row.get('gasStatus') in (1, '1', True):
                alerts_count += 1
            elif c is not None:
                try:
                    if float(c) > self._thresholds['co_warning']:
                        alerts_count += 1
                except (TypeError, ValueError):
                    pass

        avg_temp = round(sum(temps) / len(temps), 1) if temps else 0.0
        max_temp = round(max(temps), 1) if temps else 0.0
        min_temp = round(min(temps), 1) if temps else 0.0
        max_co = round(max(cos), 1) if cos else 0.0

        text = self._call_ai_report(kind, date_label,
                                    len(history), avg_temp, max_temp, min_temp,
                                    max_co, alerts_count)
        record = {
            'id': int(time.time() * 1000),
            'reportType': kind,
            'date': date_label,
            'createdAt': datetime.now().isoformat(),
            'device_id': self._device_id,
            'summary': text[:200],
            'fullReport': text,
            'stats': {
                'count': len(history),
                'avgTemp': avg_temp,
                'maxTemp': max_temp,
                'minTemp': min_temp,
                'maxCo': max_co,
                'alertCount': alerts_count,
            },
            'aiBackend': 'ollama' if self._ollama_ok else 'template',
        }
        with self._lock:
            self._reports[kind].append(record)
        logger.info(f'[Agent] {kind} 报告已生成: {date_label}')
        return record

    # ------------- AI 文本（ollama 可选 + 模板兜底） -------------
    def _probe_ollama(self):
        """探活 ollama；任何异常都落到 template"""
        if not self._ollama_enabled:
            self._ollama_ok = False
            return False
        now = time.monotonic()
        # 5 分钟内不重复探活
        if now - self._ollama_last_check < 300 and self._ollama_ok:
            return True
        self._ollama_last_check = now
        try:
            import requests
            resp = requests.get(f'{self._ollama_url}/api/tags', timeout=3)
            self._ollama_ok = resp.status_code == 200
        except Exception as e:
            logger.debug(f'[Agent] ollama 探活失败: {e}')
            self._ollama_ok = False
        return self._ollama_ok

    def _ollama_chat(self, prompt, timeout=None):
        """调用 ollama，返回纯文本；任何异常返回 None 让上层走模板"""
        if not self._ollama_enabled:
            return None
        if not self._probe_ollama():
            return None
        if timeout is None:
            timeout = self._ollama_chat_timeout
        try:
            import requests
            payload = {
                'model': self._ollama_model,
                'messages': [{'role': 'user', 'content': prompt}],
                'stream': False,
            }
            resp = requests.post(f'{self._ollama_url}/api/chat',
                                 json=payload, timeout=timeout)
            if resp.status_code != 200:
                return None
            body = resp.json()
            content = (body.get('message') or {}).get('content', '').strip()
            # deepseek-r1 等 reasoning 模型会输出 <think>...</think>，前端不需要看推理过程
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            return content or None
        except Exception as e:
            logger.debug(f'[Agent] ollama 调用失败: {e}')
            self._ollama_ok = False
            return None

    def _call_ai_routine(self, env, trends):
        prompt = (
            f"分析车辆「{self._device_id}」环境数据并给出 50 字内简评（仅一句）：\n"
            f"温度 {env.get('temp')}°C, CO {env.get('co')}ppm, "
            f"湿度 {env.get('humi')}%, TVOC {env.get('tvoc')}ppb, "
            f"燃气 {'泄漏' if env.get('gasStatus') else '正常'}\n"
            f"趋势 {json.dumps(trends, ensure_ascii=False)}\n"
            f"输出格式：环境状态(正常/注意/危险)+1句话建议。"
        )
        text = self._ollama_chat(prompt)
        if text:
            return text
        # 模板兜底
        if self._last_anomaly_key:
            return f"注意：{self._last_anomaly_key[1] or '环境存在风险'}，建议加强通风并持续观察。"
        return '正常：环境指标在阈值范围内，继续保持通风。'

    def _call_ai_report(self, kind, date_label, count, avg_t, max_t, min_t,
                        max_co, alert_count):
        prompt = (
            f"请根据以下{('日报' if kind == 'daily' else '周报')}数据生成 150 字内简洁报告：\n"
            f"周期：{date_label}\n数据条数：{count}\n"
            f"平均温度：{avg_t}°C（最高{max_t}°C / 最低{min_t}°C）\n"
            f"最高一氧化碳：{max_co}ppm\n异常事件：{alert_count} 次\n"
            f"要求：1) 评估环境状况 2) 指出主要风险 3) 给出改进建议。"
        )
        text = self._ollama_chat(prompt, timeout=30)
        if text:
            return text
        # 模板兜底
        risk = '存在异常' if alert_count > 0 else '运行平稳'
        return (
            f"【{('日报' if kind == 'daily' else '周报')}·{date_label}】"
            f"共采集 {count} 条数据，平均温度 {avg_t}°C "
            f"（{min_t}~{max_t}°C），最高 CO {max_co}ppm，"
            f"异常事件 {alert_count} 次，整体{risk}。"
            f"建议：保持通风、定期校验传感器、对异常时段重点回放。"
        )

    # ------------- 对外接口 -------------
    def get_snapshot(self):
        """供 DashboardService 嵌入到 dashboard 快照"""
        with self._lock:
            latest_alert = self._alerts[-1] if self._alerts else None
            latest_analysis = self._analyses[-1] if self._analyses else None
            latest_daily = self._reports['daily'][-1] if self._reports['daily'] else None
            latest_weekly = self._reports['weekly'][-1] if self._reports['weekly'] else None
            return {
                'enabled': self._enabled,
                'status': self._status,
                'device_id': self._device_id,
                'aiBackend': 'ollama' if self._ollama_ok else 'template',
                'thresholds': dict(self._thresholds),
                'latestAlert': latest_alert,
                'latestAnalysis': latest_analysis,
                'alerts': list(self._alerts)[-10:],
                'predictions': list(self._predictions)[-5:],
                'reports': {
                    'daily': latest_daily,
                    'weekly': latest_weekly,
                },
                'updatedAt': int(time.time() * 1000),
            }

    def get_status(self):
        with self._lock:
            return {
                'enabled': self._enabled,
                'running': self._running,
                'status': self._status,
                'device_id': self._device_id,
                'aiBackend': 'ollama' if self._ollama_ok else 'template',
                'tickSeconds': self._tick,
                'analysisInterval': self._analysis_interval,
                'thresholds': dict(self._thresholds),
                'lastAnalysis': self._analyses[-1] if self._analyses else None,
                'historySize': len(self._history),
            }

    def list_alerts(self, limit=20):
        with self._lock:
            return list(self._alerts)[-int(limit):]

    def list_analyses(self, limit=10):
        with self._lock:
            return list(self._analyses)[-int(limit):]

    def list_predictions(self, limit=10):
        with self._lock:
            return list(self._predictions)[-int(limit):]

    def list_reports(self, kind='daily', limit=7):
        if kind not in self._reports:
            return []
        with self._lock:
            return list(self._reports[kind])[-int(limit):]

    def trigger(self, kind):
        """手动触发：analysis / daily / weekly"""
        if kind == 'analysis':
            snapshot = get_latest_sensor_data() or {}
            env = snapshot.get('env', {}) if isinstance(snapshot, dict) else {}
            self._run_analysis(env)
            return self._analyses[-1] if self._analyses else None
        if kind == 'daily':
            return self.generate_daily_report()
        if kind == 'weekly':
            return self.generate_weekly_report()
        return None
