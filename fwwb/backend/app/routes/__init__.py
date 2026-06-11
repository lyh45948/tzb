"""
API 蓝图模块
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/v1')

from app.routes import sensor_routes
from app.routes import device_routes
from app.routes import agent_routes
from app.routes import imu_routes
from app.routes import vision_routes