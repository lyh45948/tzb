"""
AGV任务模型
"""
from datetime import datetime
from app import db


class AGVTask(db.Model):
    """AGV任务表 - 记录任务调度、路径规划占位和下发状态"""
    __tablename__ = 'agv_tasks'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    task_no = db.Column(db.String(64), unique=True, nullable=False, index=True, comment='任务编号')
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='目标小车ID')

    task_type = db.Column(db.String(50), default='materialTransfer', comment='任务类型')
    template_id = db.Column(db.String(50), comment='演示任务模板ID')
    title = db.Column(db.String(100), comment='任务标题')
    description = db.Column(db.String(255), comment='任务说明')
    source = db.Column(db.String(30), default='api', comment='任务来源')

    start_point = db.Column(db.String(50), nullable=False, comment='起点')
    end_point = db.Column(db.String(50), nullable=False, comment='终点')
    status = db.Column(db.String(20), nullable=False, default='created', index=True, comment='任务状态')
    priority = db.Column(db.Integer, default=0, comment='优先级')

    path_waypoints = db.Column(db.JSON, comment='展示用路径点')
    path_commands = db.Column(db.JSON, comment='固件路径命令')
    command_payload = db.Column(db.JSON, comment='完整下发命令')
    planner_version = db.Column(db.String(50), default='placeholder-v1', comment='规划器版本')

    dispatched_at = db.Column(db.DateTime, comment='下发时间')
    completed_at = db.Column(db.DateTime, comment='完成时间')
    error_message = db.Column(db.String(255), comment='错误信息')

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_agv_device_status', 'device_id', 'status'),
        db.Index('idx_agv_template', 'template_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'task_no': self.task_no,
            'device_id': self.device_id,
            'task_type': self.task_type,
            'template_id': self.template_id,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'start_point': self.start_point,
            'end_point': self.end_point,
            'status': self.status,
            'priority': self.priority,
            'path_waypoints': self.path_waypoints or [],
            'path_commands': self.path_commands or [],
            'command_payload': self.command_payload or {},
            'planner_version': self.planner_version,
            'dispatched_at': self.dispatched_at.isoformat() if self.dispatched_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<AGVTask {self.task_no} {self.device_id} {self.status}>'
