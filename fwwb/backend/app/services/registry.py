"""
Flask 应用与后端服务分离运行：
- Flask app 处理 HTTP REST API 请求
- SmartCarBackend 处理 UDP 服务（sensor数据推流）
两者通过全局 registry 共享数据
"""
from datetime import datetime
from app.utils.protocol import normalize_car_data

_registry = {}


def register_services(udp_car_service=None, udp_miniapp_service=None, websocket_service=None, simulation_service=None, data_service=None, imu_service=None):
    """注册服务实例，供 API 路由调用"""
    _registry['udp_car_service'] = udp_car_service
    _registry['udp_miniapp_service'] = udp_miniapp_service
    _registry['websocket_service'] = websocket_service
    _registry['simulation_service'] = simulation_service
    _registry['data_service'] = data_service
    _registry['imu_service'] = imu_service


def get_service(name):
    """获取已注册的服务实例"""
    return _registry.get(name)


def get_default_sensor_data():
    """获取默认空传感器数据结构（无小车连接时返回）"""
    return {
        "carStatus": "off",
        "carMode": "manual",
        "L_spd": 0,
        "R_spd": 0,
        "carPower": None,
        "distance": None,
        "env": {
            "temp": None,
            "humi": None,
            "lux": None,
            "co2": None,
            "tvoc": None,
            "gasStatus": None,
            "gasMic": None,
            "ps": None,
            "ir": None,
            "fan": 0,
            "led": 0,
            "buzzer": 0
        },
        "timestamp": int(datetime.now().timestamp() * 1000)
    }


def get_latest_sensor_data():
    """获取最新的传感器数据（优先真实数据，其次模拟数据）"""
    # 优先获取真实数据
    udp_car = _registry.get('udp_car_service')
    if udp_car and udp_car.latest_data:
        return normalize_car_data(udp_car.latest_data)

    # 其次获取模拟数据
    sim = _registry.get('simulation_service')
    if sim and sim.demo_mode:
        return sim.get_latest_simulated_data()

    # 没有数据则生成一个模拟快照
    if sim:
        return sim.generate_single_data()

    # 所有服务均未注册，返回默认空数据结构
    return get_default_sensor_data()
