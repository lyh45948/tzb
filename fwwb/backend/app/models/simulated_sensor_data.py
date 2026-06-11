"""
模拟传感器数据模型
"""
from datetime import datetime
from app import db


class SimulatedSensorData(db.Model):
    """模拟传感器数据表 - 存储演示模式下的模拟数据"""
    __tablename__ = 'simulated_sensor_data'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='设备ID')
    timestamp = db.Column(db.DateTime(3), nullable=False, index=True, comment='模拟时间')
    temperature = db.Column(db.Numeric(5, 2), comment='模拟温度(℃)')
    humidity = db.Column(db.Numeric(5, 2), comment='模拟湿度(%)')
    lux = db.Column(db.Integer, comment='模拟光照强度(lux)')
    co2 = db.Column(db.Integer, comment='模拟CO2浓度(ppm)')
    time_period = db.Column(db.Integer, comment='时间段(0-5: 黎明/上午/下午/黄昏/夜晚/深夜)')
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
            'co2': self.co2,
            'time_period': self.time_period,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<SimulatedSensorData {self.device_id} at {self.timestamp}>'
