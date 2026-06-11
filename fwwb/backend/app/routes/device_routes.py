"""
设备注册列表 API 路由
"""
from flask import jsonify
from app.routes import api_bp
from app.models.device import Device
from app import db


@api_bp.route('/devices', methods=['GET'])
def list_devices():
    """
    获取所有注册车辆列表

    返回格式：
    {
        "code": 0,
        "data": [
            {
                "device_id": "car1",
                "name": "小车1号",
                "ip_address": "192.168.1.100",
                "port": 7788,
                "last_seen": "2026-05-24T10:00:00",
                "status": "online"
            },
            ...
        ]
    }
    """
    try:
        devices = Device.query.order_by(Device.status.desc(), Device.last_seen.desc()).all()
        return jsonify({
            "code": 0,
            "data": [d.to_dict() for d in devices]
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500