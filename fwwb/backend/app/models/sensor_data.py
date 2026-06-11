"""
传感器数据模型
"""
from datetime import datetime
from app import db


class SensorData(db.Model):
    """传感器数据表"""
    __tablename__ = 'sensor_data'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='设备ID')
    timestamp = db.Column(db.DateTime(3), nullable=False, index=True, comment='采集时间')
    temperature = db.Column(db.Numeric(5, 2), comment='温度(℃)')
    humidity = db.Column(db.Numeric(5, 2), comment='湿度(%)')
    lux = db.Column(db.Integer, comment='光照强度(lux)')
    proximity = db.Column(db.Integer, comment='接近距离')
    ir_value = db.Column(db.Integer, comment='人体检测值')
    co2 = db.Column(db.Integer, comment='CO2浓度(ppm)')
    is_simulated = db.Column(db.Boolean, default=False, comment='是否模拟数据')
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
            'is_simulated': self.is_simulated,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<SensorData {self.device_id} at {self.timestamp}>'
