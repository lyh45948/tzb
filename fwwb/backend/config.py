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

    # ============ 数字孪生大屏 SSE 推送 ============
    # 后端周期性把 dashboard 快照通过 SSE 推送到前端大屏
    DASHBOARD_STREAM_ENABLED = os.getenv('DASHBOARD_STREAM_ENABLED', 'true').lower() in ('true', '1', 'yes')
    DASHBOARD_STREAM_INTERVAL = float(os.getenv('DASHBOARD_STREAM_INTERVAL', 1.0))  # 秒
    DASHBOARD_STREAM_HEARTBEAT = int(os.getenv('DASHBOARD_STREAM_HEARTBEAT', 15))  # 秒

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

    # ============ 视觉识别配置 ============
    # 整合自原 sjsb 项目，提供障碍物检测与计数器识别能力。
    # 所有视觉相关功能默认关闭；需在 .env 中显式开启。
    VISION_ENABLED = os.getenv('VISION_ENABLED', 'false').lower() in ('true', '1', 'yes')

    # 摄像头类型: none(仅接收外部 POST) / usb(本地 USB 摄像头) / esp32(ESP32-CAM HTTP)
    VISION_CAMERA_TYPE = os.getenv('VISION_CAMERA_TYPE', 'none')

    # 摄像头通用配置
    VISION_CAMERA_INDEX = int(os.getenv('VISION_CAMERA_INDEX', 0))
    VISION_FRAME_WIDTH = int(os.getenv('VISION_FRAME_WIDTH', 320))
    VISION_FRAME_HEIGHT = int(os.getenv('VISION_FRAME_HEIGHT', 240))
    VISION_FPS = int(os.getenv('VISION_FPS', 1))

    # ESP32-CAM 配置
    VISION_ESP32_IP = os.getenv('VISION_ESP32_IP', '192.168.137.213')
    VISION_ESP32_CAPTURE_PATH = os.getenv('VISION_ESP32_CAPTURE_PATH', '/capture')
    VISION_ESP32_TIMEOUT = float(os.getenv('VISION_ESP32_TIMEOUT', 3.0))

    # OpenMV 串口配置（VISION_CAMERA_TYPE=openmv 时使用）
    # 板侧需运行 tools/openmv/openmv_camera.py 固件
    VISION_OPENMV_PORT = os.getenv('VISION_OPENMV_PORT')              # 缺省 None=自动扫描 USB/CDC/ACM
    VISION_OPENMV_BAUDRATE = int(os.getenv('VISION_OPENMV_BAUDRATE', 115200))
    VISION_OPENMV_TIMEOUT = float(os.getenv('VISION_OPENMV_TIMEOUT', 3.0))

    # 启动后端时是否自动弹出 OpenMV 调试 GUI（子进程方式）
    # GUI 通过 HTTP POST /v1/vision/counter 把识别结果上报给后端
    VISION_OPENMV_GUI = os.getenv('VISION_OPENMV_GUI', 'false').lower() in ('true', '1', 'yes')

    # 模型存放目录与文件名(相对路径基于 VISION_MODELS_DIR，绝对路径直用)
    VISION_MODELS_DIR = os.getenv(
        'VISION_MODELS_DIR',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
    )
    VISION_OBSTACLE_MODEL = os.getenv('VISION_OBSTACLE_MODEL', 'yolo11s.pt')
    VISION_DIGIT_PANEL_MODEL = os.getenv('VISION_DIGIT_PANEL_MODEL', 'digit_panel_yolov8s.pt')
    VISION_CRNN_MODEL = os.getenv('VISION_CRNN_MODEL', 'best_crnn.pth')

    # 检测阈值
    VISION_OBSTACLE_CONF = float(os.getenv('VISION_OBSTACLE_CONF', 0.05))
    VISION_COUNTER_CONF = float(os.getenv('VISION_COUNTER_CONF', 0.3))

    # 推理设备: auto / cpu / cuda
    VISION_DEVICE = os.getenv('VISION_DEVICE', 'auto')

    # 后台检测循环间隔(秒)，0 表示禁用对应循环
    VISION_OBSTACLE_INTERVAL = float(os.getenv('VISION_OBSTACLE_INTERVAL', 1.0))
    VISION_COUNTER_INTERVAL = float(os.getenv('VISION_COUNTER_INTERVAL', 1.0))

    # 持久化间隔(秒)，0 表示不写库
    VISION_PERSIST_INTERVAL = float(os.getenv('VISION_PERSIST_INTERVAL', 5.0))

    # 是否在持久化时保存标注图像 base64（占空间，默认关闭）
    VISION_PERSIST_IMAGE = os.getenv('VISION_PERSIST_IMAGE', 'false').lower() in ('true', '1', 'yes')

    # ============ 联动控制配置（LinkageController） ============
    # 后端集中决策三条传感器联动：
    #   - PIR(AP3216C ps/ir) → LED 自动照明
    #   - 温湿度 → 风扇自动启停（带回滞）
    #   - 危气 alertLevel → AW2013 RGB 颜色（黄/红/红闪烁/灭）
    LINKAGE_ENABLED = os.getenv('LINKAGE_ENABLED', 'true').lower() in ('true', '1', 'yes')
    LINKAGE_TICK_SECONDS = float(os.getenv('LINKAGE_TICK_SECONDS', 1.0))

    # 风扇阈值（双门限回滞，避免临界抖动）
    FAN_TEMP_ON = float(os.getenv('FAN_TEMP_ON', 32.0))
    FAN_TEMP_OFF = float(os.getenv('FAN_TEMP_OFF', 30.0))
    FAN_HUMI_ON = float(os.getenv('FAN_HUMI_ON', 80.0))
    FAN_HUMI_OFF = float(os.getenv('FAN_HUMI_OFF', 75.0))

    # PIR 人体判定阈值（AP3216C ps/ir 通道，单位非 lux，需现场标定）
    IR_PS_THRESHOLD = int(os.getenv('IR_PS_THRESHOLD', 200))
    IR_IR_THRESHOLD = int(os.getenv('IR_IR_THRESHOLD', 100))
    # 去抖：连续 N 次有人才点亮，连续 M 次无人才熄灭（单位 = tick）
    IR_DEBOUNCE_ON = int(os.getenv('IR_DEBOUNCE_ON', 2))
    IR_DEBOUNCE_OFF = int(os.getenv('IR_DEBOUNCE_OFF', 5))

    # RGB 闪烁频率（Hz），critical 等级时使用
    RGB_BLINK_HZ = float(os.getenv('RGB_BLINK_HZ', 1.0))

    # 手动控制后该路自动联动静默秒数
    MANUAL_OVERRIDE_TTL = int(os.getenv('MANUAL_OVERRIDE_TTL', 30))

    # 危气分级阈值（webapp 设置页可在线修改，初始值取自此处）
    CO2_WARNING = int(os.getenv('CO2_WARNING', 800))
    CO2_DANGER = int(os.getenv('CO2_DANGER', 1000))
    TVOC_WARNING = int(os.getenv('TVOC_WARNING', 600))
    TVOC_DANGER = int(os.getenv('TVOC_DANGER', 900))
    GASMIC_WARNING = int(os.getenv('GASMIC_WARNING', 300))
    GASMIC_DANGER = int(os.getenv('GASMIC_DANGER', 500))
    DISTANCE_WARNING = int(os.getenv('DISTANCE_WARNING', 30))
    DISTANCE_DANGER = int(os.getenv('DISTANCE_DANGER', 15))

    # ============ 车辆环境智能体 (AgentService) ============
    # 以独立线程跑，从 registry.get_latest_sensor_data() 取数据，
    # critical 级异常通过 udp_car_service.send_command 直接下发硬件动作。
    AGENT_ENABLED = os.getenv('AGENT_ENABLED', 'true').lower() in ('true', '1', 'yes')
    AGENT_TICK_SECONDS = float(os.getenv('AGENT_TICK_SECONDS', 5.0))
    AGENT_PREDICTION_INTERVAL = float(os.getenv('AGENT_PREDICTION_INTERVAL', 60.0))
    AGENT_DEVICE_ID = os.getenv('AGENT_DEVICE_ID', 'car1')

    # critical 命令冷却：同一 critical 状态下不重复下发命令的最小间隔(秒)
    AGENT_CRITICAL_COOLDOWN = float(os.getenv('AGENT_CRITICAL_COOLDOWN', 30))

    # 报告时间（24h 制，本地时间）
    AGENT_DAILY_REPORT_HOUR = int(os.getenv('AGENT_DAILY_REPORT_HOUR', 20))
    AGENT_WEEKLY_REPORT_DAY = int(os.getenv('AGENT_WEEKLY_REPORT_DAY', 6))   # 周一=0，周日=6
    AGENT_WEEKLY_REPORT_HOUR = int(os.getenv('AGENT_WEEKLY_REPORT_HOUR', 20))

    # 智能体内部判定阈值（与 LinkageController 阈值独立，面向 AGV 车舱环境）
    AGENT_CO_WARNING = float(os.getenv('AGENT_CO_WARNING', 10))      # CO ppm
    AGENT_CO_CRITICAL = float(os.getenv('AGENT_CO_CRITICAL', 30))    # CO ppm，触发停车
    AGENT_TEMP_MIN = float(os.getenv('AGENT_TEMP_MIN', 15))          # 摄氏度
    AGENT_TEMP_MAX = float(os.getenv('AGENT_TEMP_MAX', 35))
    AGENT_TVOC_WARNING = float(os.getenv('AGENT_TVOC_WARNING', 300)) # ppb

    # Ollama 大模型（可选，未安装时自动走模板兜底）
    AGENT_OLLAMA_ENABLED = os.getenv('AGENT_OLLAMA_ENABLED', 'false').lower() in ('true', '1', 'yes')
    AGENT_OLLAMA_URL = os.getenv('AGENT_OLLAMA_URL', 'http://localhost:11434')
    AGENT_OLLAMA_MODEL = os.getenv('AGENT_OLLAMA_MODEL', 'deepseek-r1:7b')


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
