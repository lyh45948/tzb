"""
智能体占位接口路由
- /vision/analyze: 调用 VisionService 进行一次综合视觉分析
- /device/battery/predict: 占位
"""
from flask import jsonify, request
from app.routes import api_bp
from app.services.registry import get_service
from app.utils.logger import get_logger

logger = get_logger('agent_routes')


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


@api_bp.route('/device/battery/predict', methods=['GET'])
def battery_predict():
    """
    设备电量预测告警接口（占位）

    Query 参数：
    - device_id: 设备ID（暂不支持）

    返回：
    {
        "code": 1,
        "message": "功能待实现",
        "data": null,
        "device_id": "car1"
    }
    """
    device_id = request.args.get('device_id')
    logger.warning(f"device/battery/predict 被调用，但功能尚未实现 (device_id={device_id})")
    return jsonify({
        "code": 1,
        "message": "功能待实现",
        "data": None,
        "device_id": device_id
    }), 501