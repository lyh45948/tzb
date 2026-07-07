"""
智能小车后端服务入口
"""
import os
import sys
import signal
import subprocess
import threading
import time as os_time
from pathlib import Path

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
        self.agv_task_service = None  # AGV任务调度服务
        self.dashboard_service = None  # 数字孪生大屏服务
        self.dashboard_stream_service = None  # 数字孪生大屏 SSE 推送
        self.imu_service = None  # IMU 服务
        self.vision_service = None  # 视觉识别服务
        self.linkage_controller = None  # 联动控制器（PIR/温湿度/危气）
        self.agent_service = None  # 车辆环境智能体
        self.openmv_gui_process = None  # OpenMV 调试 GUI 子进程
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

        # 初始化AGV任务调度与数字孪生服务
        logger.info("初始化AGV任务调度服务...")
        from app.services.agv_task_service import AGVTaskService
        from app.services.dashboard_service import DashboardService
        self.agv_task_service = AGVTaskService(
            app=self.app,
            data_service=self.data_service,
            udp_car_service=self.udp_car_service
        )
        self.dashboard_service = DashboardService(
            app=self.app,
            data_service=self.data_service,
            udp_car_service=self.udp_car_service,
            agv_task_service=self.agv_task_service
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

        # 初始化视觉识别服务（默认禁用，需 VISION_ENABLED=true 启用）
        if getattr(self.config, 'VISION_ENABLED', False):
            logger.info("初始化视觉识别服务...")
            try:
                from app.vision.vision_service import VisionService
                self.vision_service = VisionService(
                    app=self.app,
                    config=self.config,
                    websocket_service=self.websocket_service,
                    data_service=self.data_service,
                )
                if self.vision_service.init():
                    self.vision_service.start()
                    logger.info("视觉识别服务已启动")
                else:
                    logger.warning("视觉识别服务初始化失败，视觉功能不可用")
            except Exception as e:
                logger.error(f"视觉识别服务启动异常: {e}")
                self.vision_service = None
        else:
            logger.info("视觉识别服务未启用 (VISION_ENABLED=false)")

        # 初始化联动控制器（PIR→LED / 温湿度→风扇 / 危气→RGB）
        if getattr(self.config, 'LINKAGE_ENABLED', True):
            logger.info("初始化联动控制器...")
            from app.services.linkage_service import LinkageController
            self.linkage_controller = LinkageController(
                app=self.app,
                udp_car_service=self.udp_car_service,
                config=self.config,
            )
            self.linkage_controller.start()
        else:
            logger.info("联动控制器未启用 (LINKAGE_ENABLED=false)")

        # 初始化数字孪生 SSE 推送服务（依赖 dashboard_service / linkage_controller / vision_service 已就绪）
        if getattr(self.config, 'DASHBOARD_STREAM_ENABLED', True):
            logger.info("初始化数字孪生 SSE 推送服务...")
            from app.services.dashboard_stream_service import DashboardStreamService
            self.dashboard_stream_service = DashboardStreamService(
                dashboard_service=self.dashboard_service,
                interval=getattr(self.config, 'DASHBOARD_STREAM_INTERVAL', 1.0),
                heartbeat=getattr(self.config, 'DASHBOARD_STREAM_HEARTBEAT', 15),
            )
            self.dashboard_stream_service.start()
        else:
            logger.info("数字孪生 SSE 推送未启用 (DASHBOARD_STREAM_ENABLED=false)")

        # 初始化车辆环境智能体（异常监测 + critical 时自动下发硬件命令）
        if getattr(self.config, 'AGENT_ENABLED', True):
            logger.info("初始化车辆环境智能体...")
            from app.services.agent_service import AgentService
            self.agent_service = AgentService(
                app=self.app,
                config=self.config,
                udp_car_service=self.udp_car_service,
                data_service=self.data_service,
                linkage_controller=self.linkage_controller,
            )
            self.agent_service.start()
        else:
            logger.info("车辆环境智能体未启用 (AGENT_ENABLED=false)")

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
            imu_service=self.imu_service,
            agv_task_service=self.agv_task_service,
            dashboard_service=self.dashboard_service,
            dashboard_stream_service=self.dashboard_stream_service,
            vision_service=self.vision_service,
            linkage_controller=self.linkage_controller,
            agent_service=self.agent_service,
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

        # 可选：启动 OpenMV 调试 GUI 子进程（VISION_OPENMV_GUI=true）
        if getattr(self.config, 'VISION_OPENMV_GUI', False):
            self._launch_openmv_gui()

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
        # threaded=True：SSE 长连接需要多线程，否则会阻塞其他请求
        self.app.run(
            host=flask_config.TCP_HOST,
            port=flask_config.HTTP_PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        )

    def _launch_openmv_gui(self):
        """以子进程方式拉起 OpenMV 调试 GUI

        GUI 通过 BACKEND_BASE_URL 环境变量获知后端地址，
        识别到的计数器数字会 POST /v1/vision/counter 上报，
        进入 VisionService._counter_cache 后由 SSE 推到大屏。
        """
        gui_path = Path(__file__).resolve().parent / 'tools' / 'openmv' / 'main_gui.py'
        if not gui_path.is_file():
            logger.warning(f"OpenMV GUI 入口不存在: {gui_path}，跳过启动")
            return

        backend_url = f"http://127.0.0.1:{getattr(self.config, 'HTTP_PORT', 5000)}"
        env = os.environ.copy()
        env['BACKEND_BASE_URL'] = backend_url

        # GUI 的 stderr 写到独立日志文件，启动失败/崩溃时方便排查
        # （比如缺 tkinter 时会输出 ModuleNotFoundError）
        gui_log_path = Path('/tmp') / 'openmv_gui.log'
        try:
            gui_stderr = open(gui_log_path, 'a', buffering=1)
            gui_stderr.write(f"\n=== {os_time.strftime('%Y-%m-%d %H:%M:%S')} backend spawn ===\n")
        except Exception:
            gui_stderr = subprocess.DEVNULL

        try:
            self.openmv_gui_process = subprocess.Popen(
                [sys.executable, str(gui_path)],
                env=env,
                cwd=str(gui_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=gui_stderr,
            )
            logger.info(
                f"OpenMV GUI 子进程已启动 PID={self.openmv_gui_process.pid} "
                f"→ 上报目标 {backend_url}（GUI 错误日志: {gui_log_path}）"
            )
            # 启动 1.5s 后探活，过早退出说明出了问题
            def _check_gui_alive():
                os_time.sleep(1.5)
                if self.openmv_gui_process and self.openmv_gui_process.poll() is not None:
                    rc = self.openmv_gui_process.returncode
                    logger.error(
                        f"OpenMV GUI 子进程在启动后立即退出（returncode={rc}），"
                        f"详见 {gui_log_path}（常见原因：缺 python3-tk 模块，运行 `sudo apt install python3-tk`）"
                    )
            threading.Thread(target=_check_gui_alive, daemon=True).start()
        except Exception as e:
            logger.error(f"启动 OpenMV GUI 失败: {e}")
            self.openmv_gui_process = None

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

        if self.vision_service:
            try:
                self.vision_service.stop()
                logger.info("视觉识别服务已关闭")
            except Exception as e:
                logger.warning(f"关闭视觉服务异常: {e}")

        if self.linkage_controller:
            try:
                self.linkage_controller.stop()
                logger.info("联动控制器已关闭")
            except Exception as e:
                logger.warning(f"关闭联动控制器异常: {e}")

        if self.agent_service:
            try:
                self.agent_service.stop()
                logger.info("车辆环境智能体已关闭")
            except Exception as e:
                logger.warning(f"关闭车辆环境智能体异常: {e}")

        if self.dashboard_stream_service:
            try:
                self.dashboard_stream_service.stop()
                logger.info("数字孪生 SSE 服务已关闭")
            except Exception as e:
                logger.warning(f"关闭 SSE 服务异常: {e}")

        if self.openmv_gui_process:
            try:
                self.openmv_gui_process.terminate()
                # 给 tkinter 一点时间清理；超时强杀
                try:
                    self.openmv_gui_process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.openmv_gui_process.kill()
                logger.info("OpenMV GUI 子进程已关闭")
            except Exception as e:
                logger.warning(f"关闭 OpenMV GUI 异常: {e}")

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
