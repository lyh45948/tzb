"""
智能小车后端配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """基础配置"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'smart-car-backend-secret-key')

    # MySQL配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'smart_car')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # 生产环境设为False

    # TCP服务器配置 (小程序连接)
    TCP_HOST = os.getenv('TCP_HOST', '0.0.0.0')
    TCP_PORT = int(os.getenv('TCP_PORT', 8888))

    # WebSocket 配置 (Web 应用连接)
    WS_HOST = os.getenv('WS_HOST', '0.0.0.0')
    WS_PORT = int(os.getenv('WS_PORT', 8889))
    WS_ENABLED = os.getenv('WS_ENABLED', 'true').lower() in ('true', '1', 'yes')

    # HTTP REST API配置
    HTTP_PORT = int(os.getenv('HTTP_PORT', 5000))

    # UDP配置 (连接Hi3861小车)
    UDP_PORT = int(os.getenv('UDP_PORT', 7788))
    UDP_TIMEOUT = float(os.getenv('UDP_TIMEOUT', 5.0))  # 秒

    # 数据存储配置
    DATA_SAVE_INTERVAL = int(os.getenv('DATA_SAVE_INTERVAL', 1))  # 秒

    # 连接配置
    MAX_TCP_CLIENTS = int(os.getenv('MAX_TCP_CLIENTS', 10))

    # IMU 配置 (Yesense H30)
    # 支持模式: tcp（网口版）, serial（USB串口版）, udp_passive（Hi3861 JSON透传）
    IMU_ENABLED = os.getenv('IMU_ENABLED', 'false').lower() in ('true', '1', 'yes')
    IMU_MODE = os.getenv('IMU_MODE', 'tcp')

    # TCP 模式配置（网口版 H30，连接网口模块）
    IMU_TCP_HOST = os.getenv('IMU_TCP_HOST', '192.168.1.200')
    IMU_TCP_PORT = int(os.getenv('IMU_TCP_PORT', 8899))
    IMU_TCP_TIMEOUT = float(os.getenv('IMU_TCP_TIMEOUT', 5.0))

    # 串口模式配置（USB 串口版 H30）
    IMU_SERIAL_PORT = os.getenv('IMU_SERIAL_PORT', '/dev/ttyUSB0')
    IMU_SERIAL_BAUDRATE = int(os.getenv('IMU_SERIAL_BAUDRATE', 460800))
    IMU_SERIAL_TIMEOUT = float(os.getenv('IMU_SERIAL_TIMEOUT', 0.1))


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    MYSQL_DATABASE = 'smart_car_test'
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{Config.MYSQL_USER}:{Config.MYSQL_PASSWORD}@"
        f"{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/smart_car_test?charset=utf8mb4"
    )


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
