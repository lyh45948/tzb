"""
智能小车后端应用
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()


def create_app(config_name='default'):
    """创建Flask应用"""
    from config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化数据库
    db.init_app(app)

    # 配置 CORS，允许 Web 应用跨域访问
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"], supports_credentials=True)

    # 注册蓝图
    from app.routes import api_bp
    app.register_blueprint(api_bp)

    # 注册服务实例
    from app.services.registry import register_services

    # 注册蓝图和服务
    with app.app_context():
        # 导入模型
        from app import models

        # 创建数据库表
        db.create_all()

    return app
