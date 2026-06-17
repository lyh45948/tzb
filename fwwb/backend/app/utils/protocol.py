"""
协议解析模块
处理TCP和UDP通信的JSON协议解析
"""
import json
from enum import Enum
from app.utils.logger import get_logger

logger = get_logger('protocol')


class MessageType(Enum):
    """消息类型枚举"""
    # TCP消息类型 (小程序 <-> 后端)
    CONNECT = "connect"              # 连接小车请求
    CONNECT_RESULT = "connect_result"  # 连接结果
    DISCONNECT = "disconnect"         # 断开连接
    DISCONNECT_RESULT = "disconnect_result"
    REALTIME = "realtime"             # 实时数据推送
    CONTROL = "control"               # 控制命令
    CONTROL_RESULT = "control_result"
    QUERY = "query"                   # 历史数据查询
    QUERY_RESULT = "query_result"
    STATUS = "status"                 # 连接状态
    ERROR = "error"                   # 错误消息


class ProtocolParser:
    """协议解析器"""

    @staticmethod
    def parse_message(data):
        """
        解析JSON消息
        :param data: 字符串或字节
        :return: dict or None
        """
        try:
            if isinstance(data, bytes):
                data = data.decode('utf-8')

            # 去除首尾空白和换行符
            data = data.strip()
            if not data:
                return None

            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 原始数据: {data[:100]}")
            return None
        except Exception as e:
            logger.error(f"消息解析异常: {e}")
            return None

    # 别名，保持兼容性
    @staticmethod
    def parse(data):
        """parse_message的别名"""
        return ProtocolParser.parse_message(data)

    @staticmethod
    def encode_message(msg_dict):
        """
        编码为JSON消息
        :param msg_dict: dict
        :return: bytes
        """
        try:
            return (json.dumps(msg_dict, ensure_ascii=False) + '\n').encode('utf-8')
        except Exception as e:
            logger.error(f"消息编码失败: {e}")
            return b''

    @staticmethod
    def create_connect_request(car_ip, car_port=7788, device_id=None):
        """创建连接小车请求"""
        return {
            "type": MessageType.CONNECT.value,
            "carIp": car_ip,
            "carPort": car_port,
            "deviceId": device_id or f"car_{car_ip.replace('.', '_')}"
        }

    @staticmethod
    def create_connect_result(success, message, device_id=None):
        """创建连接结果响应"""
        return {
            "type": MessageType.CONNECT_RESULT.value,
            "success": success,
            "message": message,
            "deviceId": device_id
        }

    @staticmethod
    def create_realtime_message(data, timestamp=None):
        """创建实时数据推送消息"""
        from datetime import datetime
        return {
            "type": MessageType.REALTIME.value,
            "data": data,
            "timestamp": timestamp or int(datetime.now().timestamp() * 1000)
        }

    @staticmethod
    def create_control_command(command):
        """创建控制命令"""
        return {
            "type": MessageType.CONTROL.value,
            "command": command
        }

    @staticmethod
    def create_query_request(action, params):
        """创建查询请求"""
        return {
            "type": MessageType.QUERY.value,
            "action": action,
            "params": params
        }

    @staticmethod
    def create_query_result(action, data):
        """创建查询结果"""
        return {
            "type": MessageType.QUERY_RESULT.value,
            "action": action,
            "data": data
        }

    @staticmethod
    def create_error_message(message, code=None):
        """创建错误消息"""
        return {
            "type": MessageType.ERROR.value,
            "message": message,
            "code": code
        }

    @staticmethod
    def create_status_message(connected, device_id=None, message=""):
        """创建状态消息"""
        return {
            "type": MessageType.STATUS.value,
            "connected": connected,
            "deviceId": device_id,
            "message": message
        }

    @staticmethod
    def create_connect_result(success, message, device_id=None):
        """创建连接结果"""
        return {
            "type": MessageType.CONNECT_RESULT.value,
            "success": success,
            "message": message,
            "deviceId": device_id
        }


def normalize_car_data(data):
    """
    规范化小车数据格式
    将 env.agri 中的传感器字段提升到 env 顶层，兼容新旧数据格式
    """
    if not isinstance(data, dict):
        return data
    env = data.get('env', {})
    if not isinstance(env, dict):
        return data
    agri = env.get('agri')
    if isinstance(agri, dict):
        field_map = {
            'co2': 'co2',
            'tvoc': 'tvoc',
            'gasStatus': 'gasStatus',
            'gasMic': 'gasMic',
            'flameStatus': 'flameStatus',
        }
        for src_key, dst_key in field_map.items():
            if src_key in agri and agri[src_key] is not None:
                env[dst_key] = agri[src_key]
    data['env'] = env

    vision = data.get('vision')
    if isinstance(vision, dict):
        obstacles = vision.get('obstacles')
        if not isinstance(obstacles, list):
            obstacles = []
        try:
            obstacle_count = int(vision.get('obstacleCount', len(obstacles)) or 0)
        except (TypeError, ValueError):
            obstacle_count = len(obstacles)
        vision['obstacleCount'] = obstacle_count
        vision['obstacles'] = obstacles
        vision['valid'] = 1 if vision.get('valid') else 0
        if 'source' not in vision:
            vision['source'] = 'openmv_spi'
        data['vision'] = vision
    return data


# 为保持兼容性，创建模块级别的便捷函数
parse_message = ProtocolParser.parse_message
encode_message = ProtocolParser.encode_message
create_error_message = ProtocolParser.create_error_message
create_connect_result = ProtocolParser.create_connect_result
create_realtime_message = ProtocolParser.create_realtime_message
create_query_result = ProtocolParser.create_query_result
