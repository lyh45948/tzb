"""
联动控制 REST 接口

为 dashboard1（无 WebSocket 模式）提供：
- GET  /v1/linkage/config       读取联动 + 告警阈值快照
- PUT  /v1/linkage/config       部分更新阈值（camelCase 字段）
- POST /v1/linkage/fan          手动开关风扇 / 设置档位
- GET  /v1/linkage/fan          风扇当前状态（snapshot 子集）

WebSocket 链路（webapp 设置页）原有 linkage_config_get/set 不变，REST 与之共用
LinkageController.update_config() / get_config()，同源同效。
"""
from flask import jsonify, request

from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('linkage_routes')


def _ok(data=None, message='ok'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def _error(message, status=400):
    return jsonify({'code': 1, 'message': message}), status


def _controller():
    ctl = get_service('linkage_controller')
    if not ctl:
        return None
    return ctl


@api_bp.route('/linkage/config', methods=['GET'])
def get_linkage_config():
    """读取当前联动 + 告警阈值快照"""
    ctl = _controller()
    if ctl is None:
        return _error('LinkageController 未初始化', 503)
    try:
        return _ok(ctl.get_config())
    except Exception as e:
        logger.error(f'读取联动配置失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/linkage/config', methods=['PUT', 'POST'])
def update_linkage_config():
    """部分更新阈值（camelCase）。请求体：{"fanTempOn": 30, "fanTempOff": 28, ...}"""
    ctl = _controller()
    if ctl is None:
        return _error('LinkageController 未初始化', 503)

    payload = request.get_json(silent=True) or {}
    # 兼容两种风格：直接传字段，或包成 {"config": {...}}
    updates = payload.get('config') if isinstance(payload.get('config'), dict) else payload
    if not isinstance(updates, dict) or not updates:
        return _error('缺少阈值字段或格式错误', 400)

    try:
        applied, ignored = ctl.update_config(updates)
        return _ok({
            'applied': applied,
            'ignored': ignored,
            'config': ctl.get_config(),
        })
    except Exception as e:
        logger.exception(f'更新联动配置失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/linkage/fan', methods=['GET'])
def get_fan_status():
    """读取风扇当前状态（联动决策状态 + 手动覆盖剩余秒）"""
    ctl = _controller()
    if ctl is None:
        return _error('LinkageController 未初始化', 503)
    try:
        snap = ctl.get_status_snapshot()
        return _ok({
            'fan': snap.get('fan'),
            'reason': (snap.get('reasons') or {}).get('fan', ''),
            'manualOverrideRemaining': (snap.get('manualOverrideRemaining') or {}).get('fan', 0),
            'thresholds': {
                'fanTempOn': snap.get('thresholds', {}).get('fanTempOn'),
                'fanTempOff': snap.get('thresholds', {}).get('fanTempOff'),
                'fanHumiOn': snap.get('thresholds', {}).get('fanHumiOn'),
                'fanHumiOff': snap.get('thresholds', {}).get('fanHumiOff'),
            },
        })
    except Exception as e:
        logger.error(f'读取风扇状态失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/linkage/fan', methods=['POST'])
def set_fan_manual():
    """手动设置风扇状态。

    请求体：
        {"fan": 0|1}             # 关 / 开
        {"fan": 0|1, "ttl": 30}  # 自定义手动覆盖时长（秒），不传走默认 MANUAL_OVERRIDE_TTL
        {"gear": 0..3}           # 档位（兼容前端档位语义；>=1 视为开）

    实际下发只有 0/1（硬件 PCF8574 P0 单 bit）；档位是前端可视化层的概念，
    后端在收到档位>=1 时按 fan=1 处理，并把 gear 透传到 reason 文本里方便溯源。
    """
    ctl = _controller()
    if ctl is None:
        return _error('LinkageController 未初始化', 503)

    udp_car = get_service('udp_car_service')
    if udp_car is None:
        return _error('UDP 服务未初始化', 503)

    payload = request.get_json(silent=True) or {}
    fan_val = payload.get('fan')
    gear = payload.get('gear')

    # 解析最终的 fan_state (0/1)
    fan_state = None
    if fan_val is not None:
        try:
            fan_state = 1 if int(fan_val) else 0
        except (TypeError, ValueError):
            return _error('fan 必须是 0 或 1', 400)
    elif gear is not None:
        try:
            g = int(gear)
            if g < 0 or g > 3:
                return _error('gear 必须在 0..3 之间', 400)
            fan_state = 1 if g >= 1 else 0
        except (TypeError, ValueError):
            return _error('gear 必须是整数', 400)
    else:
        return _error('需要 fan 或 gear 字段', 400)

    ttl = payload.get('ttl')
    try:
        ttl = int(ttl) if ttl is not None else None
    except (TypeError, ValueError):
        ttl = None

    # 1) 让自动联动静默
    ctl.notify_manual('fan', ttl=ttl)

    # 2) 下发硬件命令
    cmd = {'fan': fan_state}
    sent = False
    try:
        sent = bool(udp_car.send_command(cmd))
    except Exception as e:
        logger.warning(f'手动风扇下发异常: {e}')
        sent = False

    # 3) 写控制日志
    data_service = get_service('data_service')
    if data_service is not None:
        try:
            data_service.save_control_command(
                'system',
                'fan',
                {**cmd, **({'gear': gear} if gear is not None else {})},
                source='dashboard',
                is_simulated=not sent,
            )
        except Exception as e:
            logger.debug(f'save_control_command 失败: {e}')

    return _ok({
        'fan': fan_state,
        'gear': gear,
        'sent': sent,
        'reason': 'manual override',
    })
