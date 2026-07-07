"""
危气/告警分级规则

把 dashboard_service 中的危气分级逻辑抽出，供 dashboard 显示与 linkage 控制共用，
避免 dashboard_service ↔ linkage_service 循环依赖。

分级阈值：
- critical: 火焰检测信号
- danger:  数字危气信号 / gasMic≥dangerGasMic / co2≥dangerCo2 / tvoc≥dangerTvoc / 距离≤15cm
- warning: gasMic≥warningGasMic / co2≥warningCo2 / tvoc≥warningTvoc / 距离≤30cm
- normal:  以上均不满足

阈值可由 LinkageController 动态注入（webapp 设置页修改后立即生效），
默认值与 fwwb/CLAUDE.md 中文档一致。
"""
from app.utils.logger import get_logger

logger = get_logger('alert_rules')

DEFAULT_ALERT_THRESHOLDS = {
    'co2_warning': 800,
    'co2_danger': 1000,
    'tvoc_warning': 600,
    'tvoc_danger': 900,
    'gasmic_warning': 300,
    'gasmic_danger': 500,
    'distance_warning': 30,
    'distance_danger': 15,
}


def _to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def evaluate_gas_alert_level(env, distance_cm=None, device_id='factory_001', timestamp=0, thresholds=None):
    """评估危气/障碍告警等级。

    Args:
        env: dict, 环境传感器读数（co2/tvoc/gasMic/gasStatus/flameStatus）
        distance_cm: float|None, AGV 到障碍物距离（cm）
        device_id: str, 设备 id
        timestamp: int, 用于告警事件 id 生成
        thresholds: dict|None, 覆盖默认阈值，缺省 key 走 DEFAULT_ALERT_THRESHOLDS

    返回 (level, reason, alerts)。
    """
    env = env or {}
    co2 = _to_int(env.get('co2'), 520)
    tvoc = _to_int(env.get('tvoc'), 180)
    gas_mic = _to_int(env.get('gasMic'), 120)
    gas_status = _to_int(env.get('gasStatus'), 0)
    flame_status = _to_int(env.get('flameStatus'), 0)

    th = dict(DEFAULT_ALERT_THRESHOLDS)
    if thresholds:
        for k, v in thresholds.items():
            if k in th and v is not None:
                try:
                    th[k] = int(float(v))
                except (TypeError, ValueError):
                    pass

    alerts = []

    def push(level, alert_type, message, metric, value, threshold, suggestion):
        alerts.append({
            'id': timestamp + len(alerts),
            'timestamp': timestamp,
            'level': level,
            'type': alert_type,
            'asset': '智慧工厂',
            'device_id': device_id,
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
    elif gas_status or gas_mic >= th['gasmic_danger'] or co2 >= th['co2_danger'] or tvoc >= th['tvoc_danger']:
        level = 'danger'
        reason = '危气指标达到危险阈值，建议开启通风并暂停AGV任务'
        push('danger', 'gas', '危气指标达到危险阈值', '危气/CO2/TVOC',
             max(gas_mic, co2, tvoc), 'danger', '开启通风并检查危气源')
    elif gas_mic >= th['gasmic_warning'] or co2 >= th['co2_warning'] or tvoc >= th['tvoc_warning']:
        level = 'warning'
        reason = '危气指标偏高，建议关注通风状态'
        push('warning', 'gas', '危气指标偏高', '危气/CO2/TVOC',
             max(gas_mic, co2, tvoc), 'warning', '加强通风并持续观察')
    elif distance_cm is not None and distance_cm <= th['distance_danger']:
        level = 'danger'
        reason = 'AGV距离障碍物过近，建议立即停车'
        push('danger', 'obstacle', f'AGV距离障碍物过近 {distance_cm}cm',
             '安全距离', distance_cm, f"{th['distance_danger']}cm", 'AGV停车，清理通道障碍')
    elif distance_cm is not None and distance_cm <= th['distance_warning']:
        level = 'warning'
        reason = 'AGV接近障碍物，建议减速避障'
        push('warning', 'obstacle', f'AGV接近障碍物 {distance_cm}cm',
             '安全距离', distance_cm, f"{th['distance_warning']}cm", 'AGV减速，检查通道')
    else:
        level = 'normal'
        reason = '系统运行正常，无联动动作'

    return level, reason, alerts
