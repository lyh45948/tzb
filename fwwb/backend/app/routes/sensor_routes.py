"""
传感器数据 API 路由
支持字段筛选、多车辆查询
"""
from flask import jsonify, request
from app.routes import api_bp
from app.services.registry import get_latest_sensor_data, get_service, get_default_sensor_data
from app.services.data_service import DataService


def parse_fields(fields_str):
    """解析字段筛选参数，返回 set 或 None（表示返回全部）"""
    if not fields_str:
        return None
    return {f.strip().lower() for f in fields_str.split(',') if f.strip()}


def filter_env(env, fields):
    """根据字段筛选返回 env 子集"""
    if fields is None:
        return env
    return {k: v for k, v in env.items() if k.lower() in fields}


def env_from_db_record(record):
    """从数据库记录构造 env 字典，兼容 API 文档字段"""
    if record is None:
        return {}
    data = record.to_dict() if hasattr(record, 'to_dict') else record
    return {
        "temp": data.get('temperature'),
        "humi": data.get('humidity'),
        "lux": data.get('lux'),
        "co2": data.get('co2'),
        "tvoc": data.get('tvoc'),
        "gasStatus": data.get('gas_status'),
        "gasMic": data.get('gas_mic'),
        "ps": data.get('proximity'),
        "ir": data.get('ir_value'),
    }


@api_bp.route('/sensors/current', methods=['GET'])
def get_current_sensor_data():
    """
    获取当前传感器数据（默认车，兼容模式）

    Query 参数：
    - fields: 逗号分隔的字段名，如 ?fields=temp,humi

    返回格式：同 /sensors/current/<device_id>
    """
    try:
        data = get_latest_sensor_data()
        if data is None:
            data = get_default_sensor_data()

        env = data.get('env', {})
        timestamp = data.get('timestamp', 0)
        if timestamp == 0:
            from datetime import datetime
            timestamp = int(datetime.now().timestamp() * 1000)

        fields = parse_fields(request.args.get('fields'))
        filtered_env = filter_env(env, fields)

        return jsonify({
            "code": 0,
            "data": {
                "env": filtered_env,
                "timestamp": timestamp
            }
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500


@api_bp.route('/sensors/current/all', methods=['GET'])
def get_all_sensors_current():
    """
    获取所有车辆的最新传感器数据

    Query 参数：
    - fields: 逗号分隔的字段名，如 ?fields=temp,humi

    返回格式：
    {
        "code": 0,
        "data": {
            "car1": {"env": {...}, "timestamp": 1700000000000},
            "car2": {"env": {...}, "timestamp": 1700000000001}
        }
    }
    """
    try:
        fields = parse_fields(request.args.get('fields'))
        result = {}
        from datetime import datetime

        # 在线车辆：从 device_registry 获取
        udp_car = get_service('udp_car_service')
        if udp_car and udp_car.device_registry:
            for device_id, info in udp_car.device_registry.items():
                data = info.get('latest_data', {})
                env = data.get('env', {})
                ts = data.get('timestamp', 0)
                if ts == 0:
                    ts = int(datetime.now().timestamp() * 1000)
                result[device_id] = {
                    "env": filter_env(env, fields),
                    "timestamp": ts,
                    "online": True
                }

        # 离线车辆：从数据库查询最新记录
        data_service = get_service('data_service')
        if data_service:
            # 查询所有已知设备（包括默认设备）
            with data_service.app.app_context():
                from app.models.device import Device
                all_devices = Device.query.all()
                all_device_ids = set(result.keys())
                for d in all_devices:
                    all_device_ids.add(d.device_id)

            # 查询各车最新记录（补充离线车辆）
            for device_id in all_device_ids:
                if device_id in result:
                    continue  # 已在线
                latest = data_service.get_latest_data(device_id)
                car_data = latest.get('car_data') if latest else None
                if car_data:
                    result[device_id] = {
                        "env": filter_env(env_from_db_record(car_data), fields),
                        "timestamp": int(car_data.timestamp.timestamp() * 1000) if hasattr(car_data, 'timestamp') and car_data.timestamp else int(datetime.now().timestamp() * 1000),
                        "online": False
                    }

        # 没有任何数据时返回默认空结构
        if not result:
            result['demo_car'] = {
                "env": filter_env(get_default_sensor_data()['env'], fields),
                "timestamp": int(datetime.now().timestamp() * 1000),
                "online": False
            }

        return jsonify({
            "code": 0,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500


@api_bp.route('/sensors/current/<device_id>', methods=['GET'])
def get_device_current(device_id):
    """
    获取指定车辆的最新传感器数据

    Path 参数：
    - device_id: 车辆 ID，如 car1, demo_car

    Query 参数：
    - fields: 逗号分隔的字段名，如 ?fields=temp

    返回格式：
    {
        "code": 0,
        "data": {
            "device_id": "car1",
            "env": {...},
            "timestamp": 1700000000000,
            "online": true/false
        }
    }
    """
    try:
        fields = parse_fields(request.args.get('fields'))
        from datetime import datetime

        # 在线：从 device_registry 获取
        udp_car = get_service('udp_car_service')
        if udp_car and device_id in udp_car.device_registry:
            info = udp_car.device_registry[device_id]
            data = info.get('latest_data', {})
            env = data.get('env', {})
            ts = data.get('timestamp', 0)
            if ts == 0:
                ts = int(datetime.now().timestamp() * 1000)
            return jsonify({
                "code": 0,
                "data": {
                    "device_id": device_id,
                    "env": filter_env(env, fields),
                    "timestamp": ts,
                    "online": True
                }
            })

        # 离线：查数据库
        data_service = get_service('data_service')
        if data_service:
            latest = data_service.get_latest_data(device_id)
            car_data = latest.get('car_data') if latest else None
            if car_data:
                return jsonify({
                    "code": 0,
                    "data": {
                        "device_id": device_id,
                        "env": filter_env(env_from_db_record(car_data), fields),
                        "timestamp": int(car_data.timestamp.timestamp() * 1000) if hasattr(car_data, 'timestamp') and car_data.timestamp else int(datetime.now().timestamp() * 1000),
                        "online": False
                    }
                })

        # 无数据：返回默认空结构
        return jsonify({
            "code": 0,
            "data": {
                "device_id": device_id,
                "env": filter_env(get_default_sensor_data()['env'], fields),
                "timestamp": int(datetime.now().timestamp() * 1000),
                "online": False
            }
        })

    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500


@api_bp.route('/sensors/history', methods=['GET'])
def get_sensor_history():
    """
    查询历史传感器数据（默认车 demo_car）

    Query 参数：
    - startTime: 开始时间，格式 YYYY-MM-DD HH:MM:SS
    - endTime: 结束时间，格式 YYYY-MM-DD HH:MM:SS
    - interval: 采样间隔（秒），可选
    - fields: 逗号分隔的字段名，如 ?fields=temp,humi
    """
    return _query_history(request.args.get('device_id'), request.args)


@api_bp.route('/sensors/history/<device_id>', methods=['GET'])
def get_device_history(device_id):
    """
    查询指定车辆的历史传感器数据

    Path 参数：
    - device_id: 车辆 ID

    Query 参数：
    - startTime: 开始时间，格式 YYYY-MM-DD HH:MM:SS
    - endTime: 结束时间，格式 YYYY-MM-DD HH:MM:SS
    - interval: 采样间隔（秒），可选
    - fields: 逗号分隔的字段名
    """
    return _query_history(device_id, request.args)


def _query_history(device_id, args):
    """通用历史查询实现"""
    start_time = args.get('startTime')
    end_time = args.get('endTime')
    interval = args.get('interval', type=int)
    fields = parse_fields(args.get('fields'))

    if not start_time or not end_time:
        return jsonify({
            "code": 1,
            "message": "缺少 startTime 或 endTime 参数"
        }), 400

    device_id = device_id or 'demo_car'

    try:
        data_service = get_service('data_service')
        if data_service is None:
            # 服务未初始化时返回空数组，而非报错
            return jsonify({
                "code": 0,
                "data": []
            })

        result = data_service.query_sensor_history(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )

        # 字段筛选（支持 API 文档中的全部字段别名）
        if fields is not None:
            for item in result:
                item['temperature'] = item.get('temperature') if 'temperature' in fields else None
                item['humidity'] = item.get('humidity') if 'humidity' in fields else None
                item['lux'] = item.get('lux') if 'lux' in fields else None
                item['co2'] = item.get('co2') if 'co2' in fields else None
                item['tvoc'] = item.get('tvoc') if 'tvoc' in fields else None
                item['gas_status'] = item.get('gas_status') if 'gasstatus' in fields else None
                item['gas_mic'] = item.get('gas_mic') if 'gasmic' in fields else None

        return jsonify({
            "code": 0,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "code": 1,
            "message": str(e)
        }), 500
