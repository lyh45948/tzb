"""
智能小车后端服务入口
"""
import os
import sys
import signal
import threading
import time as os_time
from config import config

# 确保app模块可以被导入
sys.path.insert(0, '.')

from app import create_app, db
from app.services.udp_service import UDPService
from app.services.udp_miniapp_service import UDPMiniAppService
from app.services.websocket_service import WebSocketService
from app.services.data_service import DataService
from app.services.imu_service import IMUService
from app.utils.logger import setup_logger, get_logger

logger = get_logger('main')


class SmartCarBackend:
    """智能小车后端服务管理器"""

    def __init__(self, config_name='default'):
        self.config = config[config_name]
        self.app = create_app(config_name)
        self.udp_car_service = None  # UDP服务 - 连接小车
        self.udp_miniapp_service = None  # UDP服务 - 小程序连接
        self.websocket_service = None  # WebSocket服务 - Web应用连接
        self.data_service = None
        self.imu_service = None  # IMU 服务
        self.running = False

    def start(self):
        """启动所有服务"""
        logger.info("=" * 50)
        logger.info("智能小车后端服务启动中...")
        logger.info("=" * 50)

        self.running = True

        # 初始化数据服务
        logger.info("初始化数据服务...")
        self.data_service = DataService(self.app)

        # 初始化UDP服务 (连接小车)
        logger.info("初始化UDP服务(小车连接)...")
        self.udp_car_service = UDPService(
            app=self.app,
            data_service=self.data_service,
            config=self.config
        )

        # 初始化UDP服务 (小程序连接)
        logger.info("初始化UDP服务(小程序连接)...")
        self.udp_miniapp_service = UDPMiniAppService(
            app=self.app,
            udp_car_service=self.udp_car_service,
            data_service=self.data_service,
            config=self.config
        )

        # 初始化 IMU 服务
        logger.info("初始化IMU服务...")
        self.imu_service = IMUService(app=self.app, config=self.config)
        self.imu_service.start()

        # 初始化 WebSocket 服务（Web 应用连接）
        if getattr(self.config, 'WS_ENABLED', True):
            logger.info("初始化 WebSocket 服务(Web应用连接)...")
            self.websocket_service = WebSocketService(
                app=self.app,
                udp_car_service=self.udp_car_service,
                data_service=self.data_service,
                config=self.config
            )

        # 注册服务实例到registry（供REST API调用）
        from app.services.registry import register_services
        from app.services.simulation_service import SimulationService
        sim_service = SimulationService(self.data_service, self.udp_miniapp_service, self.udp_car_service)
        register_services(
            udp_car_service=self.udp_car_service,
            udp_miniapp_service=self.udp_miniapp_service,
            websocket_service=self.websocket_service,
            simulation_service=sim_service,
            data_service=self.data_service,
            imu_service=self.imu_service
        )
        logger.info("服务实例已注册到registry")

        # 启动Flask REST API（独立线程）
        flask_thread = threading.Thread(target=self._start_flask, daemon=True)
        flask_thread.start()
        logger.info("Flask REST API线程已启动")

        # 启动UDP小程序服务
        if self.udp_miniapp_service.start():
            logger.info(f"UDP小程序服务启动在 {self.config.TCP_HOST}:{self.config.TCP_PORT}")
        else:
            logger.error("UDP小程序服务启动失败")
            return

        # 启动 WebSocket 服务
        if self.websocket_service:
            if self.websocket_service.start():
                logger.info(f"WebSocket服务启动在 {getattr(self.config, 'WS_HOST', self.config.TCP_HOST)}:{getattr(self.config, 'WS_PORT', 8889)}")
            else:
                logger.error("WebSocket服务启动失败")

        # 注册信号处理
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        logger.info("等待小程序连接...")
        logger.info("=" * 50)

        # 保持主线程运行
        try:
            while self.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def _start_flask(self):
        """启动Flask REST API服务"""
        from config import config
        flask_config = config[os.getenv('FLASK_ENV', 'default')]
        self.app.run(
            host=flask_config.TCP_HOST,
            port=flask_config.HTTP_PORT,
            debug=False,
            use_reloader=False
        )

    def shutdown(self, signum=None, frame=None):
        """关闭所有服务"""
        if getattr(self, '_shutdown_called', False):
            return
        self._shutdown_called = True

        # 启动保险线程：无论 shutdown 是否卡住，3 秒后强制退出
        def _force_exit():
            os_time.sleep(3)
            os._exit(0)
        threading.Thread(target=_force_exit, daemon=True).start()

        logger.info("=" * 50)
        logger.info("正在关闭服务...")

        self.running = False

        if self.websocket_service:
            self.websocket_service.stop()
            logger.info("WebSocket服务已关闭")

        if self.udp_miniapp_service:
            self.udp_miniapp_service.stop()
            logger.info("UDP小程序服务已关闭")

        if self.udp_car_service:
            self.udp_car_service.stop()
            logger.info("UDP小车服务已关闭")

        if self.imu_service:
            self.imu_service.stop()
            logger.info("IMU服务已关闭")

        logger.info("服务已全部关闭")
        logger.info("=" * 50)

        # 强制退出进程（os._exit 不触发异常清理，直接终止）
        os._exit(0)


def main():
    """主函数"""
    # 设置日志
    setup_logger()

    # 获取配置名称
    import os
    config_name = os.getenv('FLASK_ENV', 'default')

    # 创建并启动服务
    backend = SmartCarBackend(config_name)
    backend.start()


if __name__ == '__main__':
    main()
