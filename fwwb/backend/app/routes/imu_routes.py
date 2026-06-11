"""
IMU 数据 API 路由
提供 IMU 实时数据查询和状态查询
"""
from flask import jsonify, request
from app.routes import api_bp
from app.services.registry import get_service


@api_bp.route('/imu/current', methods=['GET'])
def get_imu_current():
    """
    获取最新 IMU 数据

    Query 参数：
    - fields: 逗号分隔的字段名，如 ?fields=accel,gyro,euler

    返回格式：
    {
        "code": 0,
        "data": {
            "tid": 123,
            "temperature": 25.5,
            "accel": {"x": 0.0, "y": 0.0, "z": 9.8},
            "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
            "euler": {"pitch": 0.0, "roll": 0.0, "yaw": 0.0},
            "quaternion": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
            "fusion_status": 1
        }
    }
    """
    try:
        imu_service = get_service('imu_service')
        if imu_service is None:
            return jsonify({
                "code": 1,
                "message": "IMU 服务未初始化"
            }), 503

        data = imu_service.get_latest_data()
        if data is None:
            return jsonify({
                "code": 0,
                "data": None,
                "message": "暂无 IMU 数据"
            })

        # 字段筛选
        fields_str = request.args.get('fields')
        if fields_str:
            fields = {f.strip().lower() for f in fields_str.split(',') if f.strip()}
            filtered = {'tid': data.get('tid')}
            if 'temperature' in fields:
                filtered['temperature'] = data.get('temperature')
            if 'accel' in fields:
                filtered['accel'] = data.get('accel')
            if 'gyro' in fields:
                filtered['gyro'] = data.get('gyro')
            if 'mag' in fields:
                filtered['mag'] = data.get('mag')
            if 'euler' in fields:
                filtered['euler'] = data.get('euler')
            if 'quaternion' in fields:
                filtered['quaternion'] = data.get('quaternion')
            if 'fusion_status' in fields:
                filtered['fusion_status'] = data.get('fusion_status')
            if 'sample_timestamp' in fields:
                filtered['sample_timestamp'] = data.get('sample_timestamp')
            data = filtered

        return jsonify({
            "code": 0,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500


@api_bp.route('/imu/status', methods=['GET'])
def get_imu_status():
    """
    获取 IMU 服务状态

    返回格式：
    {
        "code": 0,
        "data": {
            "enabled": true,
            "connected": true,
            "port": "/dev/ttyUSB0",
            "baudrate": 460800,
            "frame_count": 1000,
            "error_count": 0,
            "last_receive_time": "2024-01-01T12:00:00",
            "has_data": true
        }
    }
    """
    try:
        imu_service = get_service('imu_service')
        if imu_service is None:
            return jsonify({
                "code": 1,
                "message": "IMU 服务未初始化"
            }), 503

        return jsonify({
            "code": 0,
            "data": imu_service.get_status()
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500
