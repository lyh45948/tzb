"""
小车状态模型（旧版兼容）
当前业务已合并至 car_sensor_data，保留模型定义以兼容历史数据
"""
from datetime import datetime
from app import db


class CarStatus(db.Model):
    """小车状态表"""
    __tablename__ = 'car_status'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='设备ID')
    timestamp = db.Column(db.DateTime(3), nullable=False, index=True, comment='采集时间')
    car_status = db.Column(db.String(20), comment='小车状态')
    car_mode = db.Column(db.String(20), comment='运行模式')
    left_speed = db.Column(db.Integer, comment='左电机速度')
    right_speed = db.Column(db.Integer, comment='右电机速度')
    battery_voltage = db.Column(db.Integer, comment='电池电压')
    distance = db.Column(db.Integer, comment='障碍物距离(mm)')
    fan = db.Column(db.Boolean, default=False, comment='风扇状态')
    led = db.Column(db.Boolean, default=False, comment='LED状态')
    buzzer = db.Column(db.Boolean, default=False, comment='蜂鸣器状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_device_time', 'device_id', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
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
        return f'<CarStatus {self.device_id} at {self.timestamp}>'
