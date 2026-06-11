"""
视觉数据接口路由
接收来自视觉系统的障碍物检测和计数器识别结果
"""
from flask import jsonify, request
from app.routes import api_bp
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger('vision_routes')

# 内存缓存最新视觉数据（不入库，仅实时查询用）
_vision_cache = {
    "obstacles": None,
    "counter": None,
}


@api_bp.route('/vision/obstacles', methods=['POST'])
def receive_obstacles():
    """
    接收障碍物检测结果

    POST JSON:
    {
        "device_id": "esp32_car",
        "obstacles": [
            {"class": "person", "confidence": 0.85, "distance": 2.3, "bbox": [x1, y1, x2, y2]}
        ],
        "timestamp": 1700000000000
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"code": 1, "message": "缺少 JSON 数据"}), 400

        device_id = data.get('device_id', 'esp32_car')
        obstacles = data.get('obstacles', [])
        timestamp = data.get('timestamp', int(datetime.now().timestamp() * 1000))

        _vision_cache['obstacles'] = {
            "device_id": device_id,
            "obstacles": obstacles,
            "count": len(obstacles),
            "timestamp": timestamp,
        }

        # 同步推送到 WebSocket 客户端（如果有的话）
        try:
            from app.services.registry import get_service
            ws = get_service('websocket_service')
            if ws:
                ws.broadcast_vision_data('obstacles', _vision_cache['obstacles'])
        except Exception:
            pass

        logger.info(f"[{device_id}] 收到障碍物数据: {len(obstacles)} 个")
        return jsonify({"code": 0, "message": "ok"})
    except Exception as e:
        logger.error(f"接收障碍物数据失败: {e}")
        return jsonify({"code": 1, "message": str(e)}), 500


@api_bp.route('/vision/counter', methods=['POST'])
def receive_counter():
    """
    接收计数器识别结果

    POST JSON:
    {
        "device_id": "esp32_car",
        "digits": "001234",
        "timestamp": 1700000000000
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"code": 1, "message": "缺少 JSON 数据"}), 400

        device_id = data.get('device_id', 'esp32_car')
        digits = data.get('digits', '')
        timestamp = data.get('timestamp', int(datetime.now().timestamp() * 1000))

        _vision_cache['counter'] = {
            "device_id": device_id,
            "digits": digits,
            "timestamp": timestamp,
        }

        # 同步推送到 WebSocket 客户端
        try:
            from app.services.registry import get_service
            ws = get_service('websocket_service')
            if ws:
                ws.broadcast_vision_data('counter', _vision_cache['counter'])
        except Exception:
            pass

        logger.info(f"[{device_id}] 收到计数器数据: {digits}")
        return jsonify({"code": 0, "message": "ok"})
    except Exception as e:
        logger.error(f"接收计数器数据失败: {e}")
        return jsonify({"code": 1, "message": str(e)}), 500


@api_bp.route('/vision/latest', methods=['GET'])
def get_latest_vision():
    """
    获取最新视觉数据（障碍物 + 计数器）

    返回：
    {
        "code": 0,
        "data": {
            "obstacles": {...} | null,
            "counter": {...} | null
        }
    }
    """
    return jsonify({
        "code": 0,
        "data": {
            "obstacles": _vision_cache['obstacles'],
            "counter": _vision_cache['counter'],
        }
    })
