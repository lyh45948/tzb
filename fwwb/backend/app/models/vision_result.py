"""
视觉识别结果数据模型

按 result_type 区分两类结果：
- obstacle: 障碍物检测（含 APF 避障参数）
- counter:  工业计数器识别（CRNN+CTC 识别结果）

注：实时数据走 WebSocket 广播 + 内存缓存，本表用于历史回溯，写入由
VisionService 按 VISION_PERSIST_INTERVAL 限流，避免每秒一行。
"""
from datetime import datetime
from app import db


class VisionResult(db.Model):
    """视觉识别结果表 - 持久化障碍物检测和计数器识别结果"""
    __tablename__ = 'vision_results'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    device_id = db.Column(db.String(50), nullable=False, index=True, comment='设备ID')
    timestamp = db.Column(db.DateTime(3), nullable=False, index=True, comment='采集时间')

    # 结果类型: 'obstacle' | 'counter'
    result_type = db.Column(db.String(20), nullable=False, index=True, comment='结果类型')

    # ---- 障碍物检测字段 ----
    obstacles = db.Column(db.JSON, comment='障碍物列表(JSON)')
    obstacle_count = db.Column(db.Integer, comment='障碍物数量')
    nearest_distance = db.Column(db.Numeric(6, 2), comment='最近障碍物距离(米)')
    nearest_class = db.Column(db.String(50), comment='最近障碍物类别')
    danger_level = db.Column(db.String(20), comment='危险等级 safe/medium/high/critical')
    steer_angle = db.Column(db.Numeric(6, 2), comment='APF 推荐转向角(度)')
    speed_ratio = db.Column(db.Numeric(4, 2), comment='APF 推荐速度比例 0~1')

    # ---- 计数器识别字段 ----
    counter_digits = db.Column(db.String(20), comment='平滑后计数器数字')
    counter_raw = db.Column(db.String(20), comment='原始识别值(平滑前)')
    counter_smooth_status = db.Column(db.String(30), comment='时序平滑状态')

    # ---- 通用字段 ----
    annotated_image = db.Column(db.Text, comment='标注图像 base64(可选)')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_vision_device_time', 'device_id', 'timestamp'),
        db.Index('idx_vision_type_time', 'result_type', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'result_type': self.result_type,
            'obstacles': self.obstacles,
            'obstacle_count': self.obstacle_count,
            'nearest_distance': float(self.nearest_distance) if self.nearest_distance is not None else None,
            'nearest_class': self.nearest_class,
            'danger_level': self.danger_level,
            'steer_angle': float(self.steer_angle) if self.steer_angle is not None else None,
            'speed_ratio': float(self.speed_ratio) if self.speed_ratio is not None else None,
            'counter_digits': self.counter_digits,
            'counter_raw': self.counter_raw,
            'counter_smooth_status': self.counter_smooth_status,
            'annotated_image': self.annotated_image,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<VisionResult {self.result_type} {self.device_id} at {self.timestamp}>'
