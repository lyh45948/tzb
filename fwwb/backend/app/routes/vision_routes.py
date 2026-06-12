"""
视觉数据接口路由

委托 VisionService 处理：
- 接收外部 POST 视觉结果（兼容原 /vision/obstacles, /vision/counter）
- 后端主动捕帧推理（/vision/detect, /vision/recognize）
- 控制后台循环（/vision/start, /vision/stop, /vision/status）
- 历史回溯（/vision/history）
"""
from datetime import datetime

from flask import jsonify, request

from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('vision_routes')


def _vs():
    return get_service('vision_service')


def _ws():
    return get_service('websocket_service')


# ================ 接收型路由（兼容原协议） ================

@api_bp.route('/vision/obstacles', methods=['POST'])
def receive_obstacles():
    """接收外部视觉系统 POST 的障碍物结果

    POST JSON:
      {device_id, obstacles: [...], timestamp}
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"code": 1, "message": "缺少 JSON 数据"}), 400

        device_id = data.get('device_id', 'esp32_car')
        obstacles = data.get('obstacles', [])
        timestamp = data.get('timestamp', int(datetime.now().timestamp() * 1000))

        payload = {
            "device_id": device_id,
            "obstacles": obstacles,
            "count": len(obstacles),
            "timestamp": timestamp,
        }

        vs = _vs()
        if vs is not None:
            vs.receive_external_obstacles(payload)
        else:
            ws = _ws()
            if ws:
                try:
                    ws.broadcast_vision_data('obstacles', payload)
                except Exception:
                    pass

        logger.info(f"[{device_id}] 收到障碍物数据: {len(obstacles)} 个")
        return jsonify({"code": 0, "message": "ok"})
    except Exception as e:
        logger.error(f"接收障碍物数据失败: {e}")
        return jsonify({"code": 1, "message": str(e)}), 500


@api_bp.route('/vision/counter', methods=['POST'])
def receive_counter():
    """接收外部视觉系统 POST 的计数器结果"""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"code": 1, "message": "缺少 JSON 数据"}), 400

        device_id = data.get('device_id', 'esp32_car')
        digits = data.get('digits', '')
        timestamp = data.get('timestamp', int(datetime.now().timestamp() * 1000))

        payload = {
            "device_id": device_id,
            "digits": digits,
            "timestamp": timestamp,
        }

        vs = _vs()
        if vs is not None:
            vs.receive_external_counter(payload)
        else:
            ws = _ws()
            if ws:
                try:
                    ws.broadcast_vision_data('counter', payload)
                except Exception:
                    pass

        logger.info(f"[{device_id}] 收到计数器数据: {digits}")
        return jsonify({"code": 0, "message": "ok"})
    except Exception as e:
        logger.error(f"接收计数器数据失败: {e}")
        return jsonify({"code": 1, "message": str(e)}), 500


@api_bp.route('/vision/latest', methods=['GET'])
def get_latest_vision():
    """获取最新视觉数据（障碍物 + 计数器）"""
    vs = _vs()
    if vs is None:
        return jsonify({"code": 0, "data": {"obstacles": None, "counter": None}})
    return jsonify({
        "code": 0,
        "data": {
            "obstacles": vs.get_latest_obstacles(),
            "counter": vs.get_latest_counter(),
        }
    })


# ================ 主动推理路由 ================

@api_bp.route('/vision/status', methods=['GET'])
def vision_status():
    """视觉服务状态"""
    vs = _vs()
    if vs is None:
        return jsonify({"code": 0, "data": {"enabled": False}})
    return jsonify({"code": 0, "data": vs.get_status()})


@api_bp.route('/vision/start', methods=['POST'])
def vision_start():
    vs = _vs()
    if vs is None:
        return jsonify({"code": 1, "message": "VisionService 未启用"}), 503
    ok = vs.start()
    return jsonify({"code": 0 if ok else 1, "data": vs.get_status()})


@api_bp.route('/vision/stop', methods=['POST'])
def vision_stop():
    vs = _vs()
    if vs is None:
        return jsonify({"code": 1, "message": "VisionService 未启用"}), 503
    vs.stop()
    return jsonify({"code": 0, "data": vs.get_status()})


@api_bp.route('/vision/detect', methods=['POST'])
def vision_detect():
    """单次障碍物检测：可传 base64_image 或由摄像头采集"""
    vs = _vs()
    if vs is None:
        return jsonify({"code": 1, "message": "VisionService 未启用"}), 503

    data = request.get_json(silent=True) or {}
    base64_image = data.get('base64_image')
    if base64_image:
        # 走 base64 兼容入口
        if vs.analyzer is None:
            return jsonify({"code": 1, "message": "模型未加载"}), 503
        obstacles, annotated_b64 = vs.analyzer.detect_obstacles(base64_image)
        return jsonify({
            "code": 0,
            "data": {
                "obstacles": vs._serialize_obstacles(obstacles),
                "count": len(obstacles),
                "annotated_image": annotated_b64,
            },
        })

    result = vs.capture_and_detect_obstacles()
    code = 0 if result.get('success') else 1
    return jsonify({"code": code, "data": result.get('data'), "message": result.get('message', 'ok')})


@api_bp.route('/vision/recognize', methods=['POST'])
def vision_recognize():
    """单次计数器识别"""
    vs = _vs()
    if vs is None:
        return jsonify({"code": 1, "message": "VisionService 未启用"}), 503

    data = request.get_json(silent=True) or {}
    base64_image = data.get('base64_image')
    if base64_image:
        if vs.analyzer is None or vs.analyzer.counter_crnn is None:
            return jsonify({"code": 1, "message": "CRNN 模型未加载"}), 503
        import base64 as _b64
        import cv2 as _cv2
        import numpy as _np
        try:
            arr = _np.frombuffer(_b64.b64decode(base64_image), _np.uint8)
            frame = _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({"code": 1, "message": "base64 图像解码失败"}), 400
        except Exception as e:
            return jsonify({"code": 1, "message": f"图像解码异常: {e}"}), 400
        result = vs.capture_and_recognize_counter(frame_override=frame)
    else:
        result = vs.capture_and_recognize_counter()
    code = 0 if result.get('success') else 1
    return jsonify({"code": code, "data": result.get('data'), "message": result.get('message', 'ok')})


@api_bp.route('/vision/history', methods=['GET'])
def vision_history():
    """查询持久化的视觉结果

    Query: device_id, result_type(obstacle/counter), start_time(ISO), end_time(ISO), limit(默认100, 最大500)
    """
    try:
        from app import db
        from app.models.vision_result import VisionResult
    except Exception as e:
        return jsonify({"code": 1, "message": f"模型不可用: {e}"}), 500

    device_id = request.args.get('device_id')
    result_type = request.args.get('result_type')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    try:
        limit = max(1, min(int(request.args.get('limit', 100)), 500))
    except ValueError:
        limit = 100

    q = VisionResult.query
    if device_id:
        q = q.filter(VisionResult.device_id == device_id)
    if result_type:
        q = q.filter(VisionResult.result_type == result_type)
    if start_time:
        try:
            q = q.filter(VisionResult.timestamp >= datetime.fromisoformat(start_time))
        except ValueError:
            pass
    if end_time:
        try:
            q = q.filter(VisionResult.timestamp <= datetime.fromisoformat(end_time))
        except ValueError:
            pass
    rows = q.order_by(VisionResult.timestamp.desc()).limit(limit).all()
    return jsonify({"code": 0, "data": [r.to_dict() for r in rows], "count": len(rows)})
