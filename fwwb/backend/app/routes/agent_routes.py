"""
智能体接口路由

视觉分析（vision_service）：
- POST/GET /v1/vision/analyze   一次综合视觉分析

车辆环境智能体（agent_service）：
- GET  /v1/agent/status         当前状态 + 最近一次分析摘要
- GET  /v1/agent/alerts         最近告警 ring buffer
- GET  /v1/agent/analyses       最近 AI 分析
- GET  /v1/agent/predictions    最近趋势预测
- GET  /v1/agent/reports        最近日/周报
- POST /v1/agent/trigger        手动触发 (analysis|daily|weekly)
"""
from flask import jsonify, request

from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('agent_routes')


# ============ 视觉分析 ============
@api_bp.route('/vision/analyze', methods=['GET', 'POST'])
def vision_analyze():
    """视觉综合分析

    GET: 摄像头采一帧，依次跑障碍物检测 + 计数器识别
    POST {base64_image}: 对外部图像执行同样分析
    返回 {obstacles, counter, message}
    """
    vs = get_service('vision_service')
    if vs is None:
        return jsonify({"code": 1, "message": "VisionService 未启用", "data": None}), 503

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        base64_image = data.get('base64_image')
        if not base64_image:
            return jsonify({"code": 1, "message": "缺少 base64_image"}), 400
        import base64 as _b64
        import cv2 as _cv2
        import numpy as _np
        try:
            arr = _np.frombuffer(_b64.b64decode(base64_image), _np.uint8)
            frame = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({"code": 1, "message": "图像解码失败"}), 400
        except Exception as e:
            return jsonify({"code": 1, "message": f"图像解码异常: {e}"}), 400
        ob = vs.capture_and_detect_obstacles(frame_override=frame)
        cnt = vs.capture_and_recognize_counter(frame_override=frame)
    else:
        ob = vs.capture_and_detect_obstacles()
        cnt = vs.capture_and_recognize_counter()

    return jsonify({
        "code": 0,
        "data": {
            "obstacles": ob.get('data'),
            "counter": cnt.get('data'),
        },
        "message": "ok",
    })


# ============ 车辆环境智能体 ============
def _agent():
    return get_service('agent_service')


def _ok(data=None, message='ok'):
    return jsonify({'code': 0, 'data': data, 'message': message})


def _error(message, status=400):
    return jsonify({'code': 1, 'message': message}), status


def _safe_limit(raw, default=20, maximum=200):
    try:
        v = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        v = default
    return max(1, min(maximum, v))


@api_bp.route('/agent/status', methods=['GET'])
def agent_status():
    """智能体当前状态 + 最近一次分析摘要"""
    agent = _agent()
    if agent is None:
        return _error('AgentService 未启用', 503)
    try:
        return _ok(agent.get_status())
    except Exception as e:
        logger.error(f'读取智能体状态失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agent/alerts', methods=['GET'])
def agent_alerts():
    """最近告警 ring buffer"""
    agent = _agent()
    if agent is None:
        return _error('AgentService 未启用', 503)
    limit = _safe_limit(request.args.get('limit'), default=20, maximum=100)
    try:
        return _ok(agent.list_alerts(limit=limit))
    except Exception as e:
        logger.error(f'读取智能体告警失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agent/analyses', methods=['GET'])
def agent_analyses():
    """最近 AI 分析"""
    agent = _agent()
    if agent is None:
        return _error('AgentService 未启用', 503)
    limit = _safe_limit(request.args.get('limit'), default=10, maximum=50)
    try:
        return _ok(agent.list_analyses(limit=limit))
    except Exception as e:
        logger.error(f'读取智能体分析失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agent/predictions', methods=['GET'])
def agent_predictions():
    """最近趋势预测"""
    agent = _agent()
    if agent is None:
        return _error('AgentService 未启用', 503)
    limit = _safe_limit(request.args.get('limit'), default=10, maximum=50)
    try:
        return _ok(agent.list_predictions(limit=limit))
    except Exception as e:
        logger.error(f'读取智能体预测失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agent/reports', methods=['GET'])
def agent_reports():
    """最近日/周报。type=daily|weekly"""
    agent = _agent()
    if agent is None:
        return _error('AgentService 未启用', 503)
    kind = (request.args.get('type') or 'daily').lower()
    if kind not in ('daily', 'weekly'):
        return _error('type 必须是 daily 或 weekly', 400)
    limit = _safe_limit(request.args.get('limit'), default=7, maximum=30)
    try:
        return _ok(agent.list_reports(kind=kind, limit=limit))
    except Exception as e:
        logger.error(f'读取智能体报告失败: {e}')
        return _error(str(e), 500)


@api_bp.route('/agent/trigger', methods=['POST'])
def agent_trigger():
    """手动触发：?type=analysis|daily|weekly"""
    agent = _agent()
    if agent is None:
        return _error('AgentService 未启用', 503)
    kind = (request.args.get('type') or 'analysis').lower()
    if kind not in ('analysis', 'daily', 'weekly'):
        return _error('type 必须是 analysis|daily|weekly', 400)
    try:
        result = agent.trigger(kind)
        return _ok(result)
    except Exception as e:
        logger.error(f'触发智能体 {kind} 失败: {e}')
        return _error(str(e), 500)
