"""
数据服务
处理数据存储和查询
"""
from datetime import datetime, timedelta
from app import db
from app.models import (
    ControlCommand, SimulatedSensorData, CarSensorData
)
from app.utils.logger import get_logger
from app.utils.protocol import normalize_car_data

logger = get_logger('data_service')


class DataService:
    """数据服务"""

    def __init__(self, app):
        self.app = app

    def save_simulated_data(self, device_id, data, time_period=None):
        """
        保存模拟数据到 simulated_sensor_data 表
        :param device_id: 设备ID
        :param data: 模拟数据dict
        :param time_period: 时间段
        """
        try:
            with self.app.app_context():
                timestamp = datetime.now()
                env = data.get('env', {})

                simulated = SimulatedSensorData(
                    device_id=device_id,
                    timestamp=timestamp,
                    temperature=env.get('temp'),
                    humidity=env.get('humi'),
                    lux=env.get('lux'),
                    co2=env.get('co2'),
                    time_period=time_period
                )
                db.session.add(simulated)
                db.session.commit()
                print(f"[DataService] 模拟数据已保存: device={device_id}, temp={env.get('temp')}, time_period={time_period}")
                logger.debug(f"模拟数据已保存: {device_id}")
                return True

        except Exception as e:
            print(f"[DataService] 保存模拟数据失败: {e}")
            logger.error(f"保存模拟数据失败: {e}")
            db.session.rollback()
            return False

    def save_car_data(self, device_id, data):
        """
        保存小车实际数据到 car_sensor_data 表
        :param device_id: 设备ID
        :param data: 小车数据dict（已包含模拟的CO2和土壤湿度）
        """
        try:
            with self.app.app_context():
                timestamp = datetime.now()

                # 规范化数据格式（将 agri 字段提升到顶层）
                data = normalize_car_data(data)

                # 保存小车实际传感器数据
                env = data.get('env', {})
                car_data = CarSensorData(
                    device_id=device_id,
                    timestamp=timestamp,
                    # 实际传感器数据
                    temperature=env.get('temp'),
                    humidity=env.get('humi'),
                    lux=env.get('lux'),
                    proximity=env.get('ps'),
                    ir_value=env.get('ir'),
                    # 模拟数据（基于实际数据推算）
                    co2=env.get('co2'),
                    tvoc=env.get('tvoc'),
                    gas_status=env.get('gasStatus'),
                    gas_mic=env.get('gasMic'),
                    # 小车状态
                    car_status=data.get('carStatus'),
                    car_mode=data.get('carMode'),
                    left_speed=data.get('L_spd'),
                    right_speed=data.get('R_spd'),
                    battery_voltage=data.get('carPower'),
                    distance=data.get('distance'),
                    # 外设状态
                    fan=env.get('fan', 0) == 1,
                    led=env.get('led', 0) == 1,
                    buzzer=env.get('buzzer', 0) == 1
                )
                db.session.add(car_data)

                db.session.commit()
                logger.debug(f"小车数据已保存: {device_id}")
                return True

        except Exception as e:
            logger.error(f"保存小车数据失败: {e}")
            db.session.rollback()
            return False

    def save_control_command(self, device_id, command_type, command_data, source='miniapp', is_simulated=False):
        """
        保存控制指令到 control_commands 表
        :param device_id: 设备ID
        :param command_type: 指令类型
        :param command_data: 指令数据
        :param source: 指令来源
        :param is_simulated: 是否演示模式下发送
        """
        try:
            with self.app.app_context():
                command = ControlCommand(
                    device_id=device_id,
                    timestamp=datetime.now(),
                    command_type=command_type,
                    command_data=command_data,
                    source=source,
                    is_simulated=is_simulated
                )
                db.session.add(command)
                db.session.commit()
                logger.info(f"控制指令已记录: {device_id} - {command_type}")
                return True

        except Exception as e:
            logger.error(f"保存控制指令失败: {e}")
            db.session.rollback()
            return False

    # 保留旧方法以兼容现有代码
    def save_control_log(self, device_id, command_type, command_data, source='miniapp'):
        """保存控制日志（兼容旧接口）"""
        return self.save_control_command(device_id, command_type, command_data, source)

    def query_simulated_history(self, device_id, start_time=None, end_time=None, limit=1000):
        """查询模拟数据历史"""
        try:
            with self.app.app_context():
                query = SimulatedSensorData.query.filter_by(device_id=device_id)

                if start_time:
                    query = query.filter(SimulatedSensorData.timestamp >= start_time)
                if end_time:
                    query = query.filter(SimulatedSensorData.timestamp <= end_time)

                query = query.order_by(SimulatedSensorData.timestamp.desc())
                query = query.limit(limit)

                results = query.all()
                return [r.to_dict() for r in results]

        except Exception as e:
            logger.error(f"查询模拟数据历史失败: {e}")
            return []

    def query_car_data_history(self, device_id, start_time=None, end_time=None, limit=1000):
        """查询小车实际数据历史"""
        try:
            with self.app.app_context():
                query = CarSensorData.query.filter_by(device_id=device_id)

                if start_time:
                    query = query.filter(CarSensorData.timestamp >= start_time)
                if end_time:
                    query = query.filter(CarSensorData.timestamp <= end_time)

                query = query.order_by(CarSensorData.timestamp.desc())
                query = query.limit(limit)

                results = query.all()
                return [r.to_dict() for r in results]

        except Exception as e:
            logger.error(f"查询小车数据历史失败: {e}")
            return []

    def query_sensor_history(self, device_id, start_time=None, end_time=None, interval='1h'):
        """
        查询传感器历史数据（兼容旧接口，查询小车实际数据）
        """
        return self.query_car_data_history(device_id, start_time, end_time)

    def query_command_history(self, device_id, start_time=None, end_time=None, limit=500):
        """查询指令历史"""
        try:
            with self.app.app_context():
                query = ControlCommand.query.filter_by(device_id=device_id)

                if start_time:
                    query = query.filter(ControlCommand.timestamp >= start_time)
                if end_time:
                    query = query.filter(ControlCommand.timestamp <= end_time)

                query = query.order_by(ControlCommand.timestamp.desc())
                query = query.limit(limit)

                results = query.all()
                return [r.to_dict() for r in results]

        except Exception as e:
            logger.error(f"查询指令历史失败: {e}")
            return []

    def get_latest_data(self, device_id):
        """获取最新数据"""
        try:
            with self.app.app_context():
                # 获取最新的小车数据
                car_data = CarSensorData.query.filter_by(device_id=device_id) \
                    .order_by(CarSensorData.timestamp.desc()).first()

                return {
                    'car_data': car_data.to_dict() if car_data else None
                }
        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            return None

    def get_statistics(self, device_id, hours=24, data_type='car'):
        """
        获取统计数据
        :param device_id: 设备ID
        :param hours: 统计时长
        :param data_type: 数据类型 ('car' 或 'simulated')
        """
        try:
            with self.app.app_context():
                start_time = datetime.now() - timedelta(hours=hours)

                if data_type == 'simulated':
                    model = SimulatedSensorData
                else:
                    model = CarSensorData

                # 温度统计
                temp_stats = db.session.query(
                    db.func.avg(model.temperature).label('avg'),
                    db.func.min(model.temperature).label('min'),
                    db.func.max(model.temperature).label('max')
                ).filter(
                    model.device_id == device_id,
                    model.timestamp >= start_time
                ).first()

                # 湿度统计
                humi_stats = db.session.query(
                    db.func.avg(model.humidity).label('avg'),
                    db.func.min(model.humidity).label('min'),
                    db.func.max(model.humidity).label('max')
                ).filter(
                    model.device_id == device_id,
                    model.timestamp >= start_time
                ).first()

                # 数据点数量
                count = model.query.filter(
                    model.device_id == device_id,
                    model.timestamp >= start_time
                ).count()

                return {
                    'period_hours': hours,
                    'data_type': data_type,
                    'data_count': count,
                    'temperature': {
                        'avg': float(temp_stats.avg) if temp_stats and temp_stats.avg else None,
                        'min': float(temp_stats.min) if temp_stats and temp_stats.min else None,
                        'max': float(temp_stats.max) if temp_stats and temp_stats.max else None
                    },
                    'humidity': {
                        'avg': float(humi_stats.avg) if humi_stats and humi_stats.avg else None,
                        'min': float(humi_stats.min) if humi_stats and humi_stats.min else None,
                        'max': float(humi_stats.max) if humi_stats and humi_stats.max else None
                    }
                }

        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")
            return None
