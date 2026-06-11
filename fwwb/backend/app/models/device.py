"""
设备模型
"""
from datetime import datetime
from app import db


class Device(db.Model):
    """设备表"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False, comment='设备ID')
    name = db.Column(db.String(100), comment='设备名称')
    ip_address = db.Column(db.String(50), comment='设备IP地址')
    port = db.Column(db.Integer, default=7788, comment='设备端口')
    last_seen = db.Column(db.DateTime, comment='最后在线时间')
    status = db.Column(db.Enum('online', 'offline'), default='offline', comment='在线状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'name': self.name,
            'ip_address': self.ip_address,
            'port': self.port,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Device {self.device_id}>'
