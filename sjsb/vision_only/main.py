"""
视觉识别主程序 - 障碍物检测版本
支持障碍物检测、距离测算和视觉分析
"""
import logging
import sys
import time
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_manager import ConfigManager
from src.utils.Camera import CameraManager
from src.utils.VL import ImageAnalyzer
from src.utils.TTS import TextToSpeech

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VisionApp")


class VisionApp:
    """视觉识别应用程序"""

    def __init__(self):
        """初始化应用程序"""
        # 初始化配置管理器
        self.config = ConfigManager.get_instance()

        # 检查视觉功能是否启用
        if not self.config.get_config("VISION.ENABLED", False):
            logger.error("视觉功能未启用，请在 config/config.json 中设置 VISION.ENABLED 为 true")
            sys.exit(1)

        # 初始化摄像头管理器
        self.camera_manager = CameraManager.get_instance()

        # 初始化图像分析器（仅 YOLOv8）
        self.image_analyzer = ImageAnalyzer.get_instance()
        self.image_analyzer.init()

        # 初始化 TTS 引擎
        self.tts_engine = TextToSpeech.get_instance()

        # 存储上次检测结果
        self.last_obstacles = None
        self.last_report = None

        logger.info("视觉识别应用程序初始化完成")

    def start_camera(self):
        """启动摄像头"""
        logger.info("启动摄像头...")
        if self.camera_manager.start_camera():
            logger.info("摄像头启动成功")
        else:
            logger.error("摄像头启动失败")
            sys.exit(1)

    def detect_obstacles(self) -> tuple:
        """捕获图像并检测障碍物

        Returns:
            (obstacles_list, annotated_base64, report_text)
        """
        # 捕获图像
        logger.info("捕获图像...")
        frame_base64 = self.camera_manager.capture_frame_to_base64()
        if not frame_base64:
            logger.error("无法捕获图像")
            return None, None, None

        # 检测障碍物
        logger.info("检测障碍物...")
        obstacles, annotated_base64 = self.image_analyzer.detect_obstacles(frame_base64)
        self.last_obstacles = obstacles

        # 生成报告
        report = self.image_analyzer.analyze_obstacles(obstacles)
        self.last_report = report

        return obstacles, annotated_base64, report

    def speak_result(self, text):
        """语音播报结果"""
        logger.info(f"语音播报: {text}")
        self.tts_engine.speak_text(text)

    def print_obstacles(self, obstacles, report):
        """打印障碍物检测结果"""
        print("\n" + "="*50)
        print("障碍物检测结果")
        print("="*50)

        if not obstacles:
            print("未检测到障碍物")
        else:
            print(f"\n检测到 {len(obstacles)} 个障碍物:\n")
            print(report)

        print("="*50)

    def run_interactive(self):
        """交互式运行"""
        print("\n" + "="*50)
        print("视觉识别系统已启动 (障碍物检测版)")
        print("="*50)
        print("\n操作指令:")
        print("  1. obstacle / 障碍物 - 检测障碍物并估算距离")
        print("  2. speak / 播报 - 语音播报上次检测结果")
        print("  3. quit / 退出 - 退出程序")
        print("="*50 + "\n")

        while True:
            try:
                user_input = input("请输入指令: ").strip().lower()

                if user_input in ['quit', '退出', 'q', 'exit']:
                    print("正在退出...")
                    break

                elif user_input in ['obstacle', 'obstacles', '障碍物', '障碍', '检测']:
                    # 障碍物检测模式
                    obstacles, annotated_base64, report = self.detect_obstacles()
                    if obstacles is not None:
                        self.print_obstacles(obstacles, report)
                    else:
                        print("\n检测失败\n")

                elif user_input in ['speak', 'speech', '播报', '语音']:
                    if self.last_report:
                        self.speak_result(self.last_report)
                    else:
                        print("没有可播报的结果，请先进行障碍物检测")

                elif user_input in ['speak_last', '播报上次']:
                    # 播报最近一次结果
                    if self.last_report:
                        self.speak_result(self.last_report)
                    else:
                        print("没有历史结果")

                else:
                    print("未知指令，请输入 obstacle / speak / quit")

            except KeyboardInterrupt:
                print("\n正在退出...")
                break

        self.cleanup()

    def cleanup(self):
        """清理资源"""
        logger.info("正在停止摄像头...")
        self.camera_manager.stop_camera()
        logger.info("程序已退出")


def main():
    """主入口"""
    app = VisionApp()
    app.start_camera()

    # 等待摄像头启动
    time.sleep(1.0)

    app.run_interactive()


if __name__ == "__main__":
    main()