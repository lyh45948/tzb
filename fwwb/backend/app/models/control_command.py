"""
指令记录模型
"""
from datetime import datetime
from app import db


class ControlCommand(db.Model):
    """指令记录表 - 记录微信小程序向小车发送的所有指令"""
    __tablename__ = 'control_commands'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='设备ID')
    timestamp = db.Column(db.DateTime(3), nullable=False, index=True, comment='指令发送时间')
    command_type = db.Column(db.String(50), nullable=False, comment='指令类型')
    command_data = db.Column(db.JSON, comment='指令详细内容')
    source = db.Column(db.String(20), default='miniapp', comment='指令来源')
    is_simulated = db.Column(db.Boolean, default=False, comment='是否演示模式下发送')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_device_time', 'device_id', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'command_type': self.command_type,
            'command_data': self.command_data,
            'source': self.source,
            'is_simulated': self.is_simulated,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<ControlCommand {self.device_id} {self.command_type} at {self.timestamp}>'
