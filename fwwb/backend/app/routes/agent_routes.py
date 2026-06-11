"""
智能体占位接口路由
用于视觉分析、设备电量预测等尚在规划中的功能
"""
from flask import jsonify, request
from app.routes import api_bp
from app.utils.logger import get_logger

logger = get_logger('agent_routes')


@api_bp.route('/vision/analyze', methods=['GET'])
def vision_analyze():
    """
    视觉分析接口（占位）

    Query 参数：
    - image_url: 图片地址（暂不支持）

    返回：
    {
        "code": 1,
        "message": "功能待实现",
        "data": null
    }
    """
    logger.warning("vision/analyze 被调用，但功能尚未实现")
    return jsonify({
        "code": 1,
        "message": "功能待实现",
        "data": None
    }), 501


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