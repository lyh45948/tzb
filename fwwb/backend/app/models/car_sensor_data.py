"""
小车实际传感器数据模型
"""
from datetime import datetime
from app import db


class CarSensorData(db.Model):
    """小车实际传感器数据表 - 存储非演示模式下的实际数据"""
    __tablename__ = 'car_sensor_data'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='设备ID')
    timestamp = db.Column(db.DateTime(3), nullable=False, index=True, comment='采集时间')

    # 实际传感器数据
    temperature = db.Column(db.Numeric(5, 2), comment='实际温度(℃)')
    humidity = db.Column(db.Numeric(5, 2), comment='实际湿度(%)')
    lux = db.Column(db.Integer, comment='实际光照强度(lux)')
    proximity = db.Column(db.Integer, comment='接近距离')
    ir_value = db.Column(db.Integer, comment='人体检测值')

    # 模拟数据（基于实际数据推算）
    co2 = db.Column(db.Integer, comment='模拟CO2浓度(ppm)')

    # 危气传感器数据（来自STM32传感器板）
    tvoc = db.Column(db.Integer, comment='TVOC有机挥发物(ppb)')
    gas_status = db.Column(db.Integer, comment='燃气泄漏状态(0=正常,1=泄漏)')
    gas_mic = db.Column(db.Integer, comment='燃气浓度数值')

    # 小车状态
    car_status = db.Column(db.String(20), comment='小车状态')
    car_mode = db.Column(db.String(20), comment='运行模式')
    left_speed = db.Column(db.Integer, comment='左电机速度')
    right_speed = db.Column(db.Integer, comment='右电机速度')
    battery_voltage = db.Column(db.Integer, comment='电池电压')
    distance = db.Column(db.Integer, comment='障碍物距离(mm)')

    # 外设状态
    fan = db.Column(db.Boolean, comment='风扇状态')
    led = db.Column(db.Boolean, comment='LED状态')
    buzzer = db.Column(db.Boolean, comment='蜂鸣器状态')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_device_time', 'device_id', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'temperature': float(self.temperature) if self.temperature else None,
            'humidity': float(self.humidity) if self.humidity else None,
            'lux': self.lux,
            'proximity': self.proximity,
            'ir_value': self.ir_value,
            'co2': self.co2,
            'tvoc': self.tvoc,
            'gas_status': self.gas_status,
            'gas_mic': self.gas_mic,
            'car_status': self.car_status,
            'car_mode': self.car_mode,
            'left_speed': self.left_speed,
            'right_speed': self.right_speed,
            'battery_voltage': self.battery_voltage,
            'distance': self.distance,
            'fan': self.fan,
            'led': self.led,
            'buzzer': self.buzzer,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<CarSensorData {self.device_id} at {self.timestamp}>'
