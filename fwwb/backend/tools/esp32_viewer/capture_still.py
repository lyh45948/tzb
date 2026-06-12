"""
ESP32摄像头单张图片获取器 + 视觉识别
- 摄像头线程持续运行，按需截取单帧图片
- 获取图片后传给视觉识别模块进行分析
- 分析完后删除图片
- 支持本地LLaVA模型和远程API两种模式
"""

import cv2
import numpy as np
import requests
import time
import threading
import tempfile
import os
import sys
import logging
import base64
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ESP32Capture")

# 项目路径与配置
PROJECT_ROOT = Path(__file__).resolve().parents[1]
vision_only_path = PROJECT_ROOT / "vision_only"
if vision_only_path.exists() and str(vision_only_path) not in sys.path:
    sys.path.insert(0, str(vision_only_path))

try:
    from src.utils.config_manager import ConfigManager
    CONFIG = ConfigManager.get_instance()
except Exception as e:
    logger.warning(f"配置管理器加载失败，使用默认配置: {e}")
    CONFIG = None


def _get_config(path, default=None):
    """安全读取配置"""
    if CONFIG is None:
        return default
    return CONFIG.get_config(path, default)


def _resolve_path(path_value, default=None):
    """安全解析项目路径"""
    if CONFIG is None:
        value = path_value or default or "."
        path = Path(value).expanduser()
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    return CONFIG.resolve_path(path_value, default)


# ESP32 IP地址（可通过环境变量 ESP32_IP 覆盖）
ESP32_IP = os.environ.get("ESP32_IP", _get_config("ESP32.IP", "192.168.137.213"))
CAPTURE_PATH = _get_config("ESP32.CAPTURE_PATH", "/capture")
CAPTURE_URL = f"http://{ESP32_IP}{CAPTURE_PATH}"
OBSTACLE_YOLO_PATH = _resolve_path(_get_config("PATHS.OBSTACLE_YOLO", "yolo11s.pt"))

# 摄像头配置
# ESP32 固件固定输出 320x240，/control 接口无法改变分辨率
CAMERA_CONFIG = {
    "frame_width": int(_get_config("ESP32.FRAME_WIDTH", 320)),
    "frame_height": int(_get_config("ESP32.FRAME_HEIGHT", 240)),
    "fps": int(_get_config("ESP32.FPS", 1)),
}

# ESP32 分辨率控制接口
# framesize 值对应关系（esp32-camera 库）：
# 5=320x240, 6=400x296, 7=480x320, 8=640x480, 9=800x600, 10=1024x768, 11=1280x720
ESP32_FRAME_SIZE_MAP = {
    (320, 240): 5,
    (400, 296): 6,
    (480, 320): 7,
    (640, 480): 8,
    (800, 600): 9,
    (1024, 768): 10,
    (1280, 720): 11,
}

def set_esp32_resolution(width: int = 320, height: int = 240) -> bool:
    """通过 HTTP 控制接口设置 ESP32 摄像头分辨率
    
    注意：设置分辨率需要 ESP32 重新初始化摄像头传感器，耗时较长（5-15秒），
    因此使用较长的超时时间。
    
    Args:
        width: 目标宽度
        height: 目标高度
        
    Returns:
        是否设置成功
    """
    framesize = ESP32_FRAME_SIZE_MAP.get((width, height))
    if framesize is None:
        logger.warning(f"不支持的分辨率 {width}x{height}，使用 320x240")
        framesize = 5
        width, height = 320, 240
    
    control_url = f"http://{ESP32_IP}/control"
    try:
        # 先快速测试连通性
        try:
            requests.get(f"http://{ESP32_IP}/", timeout=2)
        except Exception:
            pass  # 即使根路径不通也继续尝试 control
        
        # 设置分辨率：超时 15 秒，因为需要重新初始化传感器
        resp = requests.get(control_url, params={"var": "framesize", "val": framesize}, timeout=15)
        if resp.status_code == 200:
            logger.info(f"ESP32 分辨率已设置为 {width}x{height} (framesize={framesize})")
            CAMERA_CONFIG["frame_width"] = width
            CAMERA_CONFIG["frame_height"] = height
            return True
        else:
            logger.warning(f"设置分辨率失败: HTTP {resp.status_code}")
    except requests.exceptions.ConnectTimeout:
        logger.warning(f"设置分辨率连接超时（ESP32 正在初始化传感器），实际分辨率可能已生效")
        # 即使超时，分辨率设置可能已经生效，同步配置
        CAMERA_CONFIG["frame_width"] = width
        CAMERA_CONFIG["frame_height"] = height
        return True
    except Exception as e:
        logger.warning(f"设置分辨率请求失败: {e}")
    return False


def set_esp32_quality(quality: int = 12) -> bool:
    """通过 HTTP 控制接口设置 ESP32 摄像头 JPEG 质量（降低带宽）
    
    Args:
        quality: JPEG 质量 4-63，越小画质越差但带宽越低。
                 推荐 10-15（平衡），默认 12。
        
    Returns:
        是否设置成功
    """
    control_url = f"http://{ESP32_IP}/control"
    try:
        resp = requests.get(control_url, params={"var": "quality", "val": quality}, timeout=5)
        if resp.status_code == 200:
            logger.info(f"ESP32 JPEG 质量已设置为 {quality}")
            return True
        else:
            logger.warning(f"设置 JPEG 质量失败: HTTP {resp.status_code}")
    except Exception as e:
        logger.warning(f"设置 JPEG 质量请求失败: {e}")
    return False

# 临时文件目录
TEMP_DIR = tempfile.gettempdir()

# 图片保存目录
CAPTURE_DIR = str(_resolve_path(_get_config("PATHS.CAPTURE_DIR", "captured_images")))


class ESP32CameraStream:
    """ESP32摄像头流管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self.latest_frame = None
        self.is_running = False
        self.capture_thread = None
        self.lock = threading.Lock()

        # 添加 src 目录到路径以便导入视觉识别模块
        vision_only_path = Path(__file__).parent.parent / "vision_only"
        if vision_only_path.exists():
            sys.path.insert(0, str(vision_only_path))

    def _capture_loop(self):
        """持续获取摄像头最新帧"""
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self.is_running:
            try:
                response = requests.get(CAPTURE_URL, timeout=10)
                if response.status_code == 200:
                    img_array = np.frombuffer(response.content, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                    if img is not None:
                        consecutive_errors = 0
                        with self.lock:
                            self.latest_frame = img.copy()
                    else:
                        consecutive_errors += 1
                else:
                    consecutive_errors += 1
                    logger.warning(f"请求失败，状态码: {response.status_code}")

            except requests.exceptions.Timeout:
                consecutive_errors += 1
                logger.warning("请求超时")
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"获取图片时出错: {e}")

            # 连续失败过多时停止捕获线程
            if consecutive_errors > max_consecutive_errors:
                logger.error("连续获取失败，摄像头可能断开，停止捕获线程")
                self.is_running = False
                break

            # 控制帧率
            time.sleep(1.0 / CAMERA_CONFIG["fps"])

        logger.info("摄像头捕获线程已停止")

    def start(self):
        """启动摄像头捕获线程"""
        with self._lock:
            if self.is_running:
                logger.warning("摄像头捕获线程已在运行")
                return True

            self.is_running = True
            self.capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name="ESP32CaptureThread"
            )
            self.capture_thread.start()
            logger.info("摄像头捕获线程已启动")
            return True

    def stop(self):
        """停止摄像头捕获线程"""
        with self._lock:
            self.is_running = False
            if self.capture_thread is not None:
                self.capture_thread.join(timeout=3.0)
                self.capture_thread = None
            logger.info("摄像头捕获线程已停止")

    def get_frame(self):
        """获取当前最新帧（不复制）"""
        with self.lock:
            return self.latest_frame

    def capture_frame(self):
        """截取当前帧（复制一份）"""
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
        return None

    def capture_to_base64(self):
        """截取当前帧并转换为 Base64 编码"""
        frame = self.capture_frame()
        if frame is None:
            return None

        try:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            logger.error(f"Base64编码失败: {e}")
            return None

    def on_demand_capture(self):
        """按需获取当前帧（直接从ESP32获取，不依赖后台线程）"""
        try:
            response = requests.get(CAPTURE_URL, timeout=10)
            if response.status_code == 200:
                img_array = np.frombuffer(response.content, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img is not None:
                    with self.lock:
                        self.latest_frame = img.copy()
                    return img.copy()
        except Exception as e:
            logger.error(f"按需获取图片失败: {e}")
        return None


def capture_still():
    """获取单张图片（兼容原接口）"""
    try:
        print(f"正在获取图片: {CAPTURE_URL}")
        response = requests.get(CAPTURE_URL, timeout=10)
        if response.status_code == 200:
            img_array = np.frombuffer(response.content, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                print("图片获取成功")
                return img
            else:
                print("图片解码失败")
        else:
            print(f"请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"获取图片时出错: {e}")
    return None


def init_vision_analyzer():
    """初始化视觉分析器（仅本地模式）"""

    try:
        # 添加 vision_only 路径到 sys.path
        vision_only_path = Path(__file__).parent.parent / "vision_only"
        if vision_only_path.exists():
            sys.path.insert(0, str(vision_only_path))

        from src.utils.VL import ImageAnalyzer
        from src.utils.config_manager import ConfigManager

        config = ConfigManager.get_instance()

        logger.info("正在初始化本地 YOLO/CRNN 视觉模型...")

        analyzer = ImageAnalyzer.get_instance()
        analyzer.init()
        logger.info("本地 YOLO/CRNN 视觉模型已加载")

        return analyzer

    except ImportError as e:
        logger.error(f"导入视觉模块失败: {e}")
        return None
    except Exception as e:
        logger.error(f"初始化视觉分析器失败: {e}")
        return None


def save_temp_image(frame, save_to_captured=False):
    """保存图片到文件

    Args:
        frame: 图像帧
        save_to_captured: 是否保存到 captured_images 文件夹（不删除）
                         False 则保存到临时目录（会被删除）
    Returns:
        保存的文件路径或 None
    """
    if frame is None:
        return None

    try:
        # 确保目录存在
        save_dir = CAPTURE_DIR if save_to_captured else TEMP_DIR
        os.makedirs(save_dir, exist_ok=True)

        filename = f"esp32_capture_{int(time.time()*1000)}.jpg"
        save_path = os.path.join(save_dir, filename)

        # 使用 PIL 保存（PIL 支持中文路径）
        from PIL import Image
        # OpenCV BGR 转 RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        pil_img.save(save_path, 'JPEG')

        return save_path
    except Exception as e:
        logger.error(f"保存图片失败: {e}")
        return None


def delete_temp_image(temp_path):
    """删除临时图片"""
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info(f"已删除临时图片: {temp_path}")
    except Exception as e:
        logger.error(f"删除临时图片失败: {e}")


def encode_frame_to_base64(frame):
    """将图片帧直接编码为Base64"""
    if frame is None:
        return None
    try:
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.error(f"Base64编码失败: {e}")
        return None


def detect_obstacles(analyzer, base64_image):
    """检测障碍物"""
    if analyzer is None or base64_image is None:
        return None, None

    try:
        logger.info(f"base64_image 长度: {len(base64_image)}")
        obstacles, annotated_base64 = analyzer.detect_obstacles(base64_image)
        logger.info(f"检测到障碍物数量: {len(obstacles) if obstacles else 0}")
        for obs in obstacles:
            logger.info(f"  - {obs['class']}: {obs['confidence']:.3f}, distance: {obs['distance']}")
        report = analyzer.analyze_obstacles(obstacles) if obstacles else ""
        return obstacles, report
    except Exception as e:
        logger.error(f"障碍物检测失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None


def analyze_image(analyzer, base64_image, prompt=None):
    """视觉大模型分析"""
    if analyzer is None:
        return None

    if prompt is None:
        prompt = "图中描绘的是什么景象,请详细描述，因为用户可能是盲人"

    if not hasattr(analyzer, 'analyze_image'):
        return "当前 Linux 适配版未启用视觉大模型场景分析，请使用 obstacle/障碍物 或 counter/计数器识别。"

    try:
        return analyzer.analyze_image(base64_image, prompt)
    except Exception as e:
        logger.error(f"视觉分析失败: {e}")
        return None


def print_obstacles(obstacles, report):
    """打印障碍物检测结果"""
    print("\n" + "=" * 50)
    print("障碍物检测结果")
    print("=" * 50)

    if not obstacles:
        print("未检测到障碍物")
    else:
        print(f"\n检测到 {len(obstacles)} 个障碍物:\n")
        print(report)

    print("=" * 50)


def recognize_counter(analyzer, frame):
    """识别计数器数字"""
    if analyzer is None or frame is None:
        return None, None
    try:
        digit, annotated = analyzer.recognize_counter(frame, use_temporal=True)
        return digit, annotated
    except Exception as e:
        logger.error(f"计数器识别失败: {e}")
        return None, None


def main():
    print("=" * 50)
    print("ESP32 摄像头 + 视觉识别系统")
    print(f"图片捕获地址: {CAPTURE_URL}")
    print("=" * 50)

    # 先初始化视觉分析器（模型加载期间不访问ESP32）
    print("\n正在加载视觉模型，请稍候...")
    analyzer = init_vision_analyzer()

    # 模型加载完成后再启动摄像头捕获线程
    print("\n模型加载完成，正在启动摄像头...")
    camera = ESP32CameraStream()
    camera.start()

    print("\n操作指令:")
    print("  1. obstacle / 障碍物 - 障碍物检测+距离估算")
    print("  2. counter / 计数器 - 数字计数器识别")
    print("  3. capture / 拍照 - 仅获取当前画面")
    print("  4. calibrate / 标定 - 标定摄像头焦距")
    print("  5. debug / 调试 - 显示当前画面信息")
    print("  6. look / 看看 - 场景分析（当前适配版降级提示）")
    print("  7. quit / 退出 - 退出程序")
    print("=" * 50 + "\n")

    last_obstacles = None
    last_report = None

    while True:
        try:
            user_input = input("请输入指令: ").strip().lower()

            if user_input in ['quit', '退出', 'q', 'exit']:
                print("正在退出...")
                break

            elif user_input in ['capture', '拍照', 'c']:
                # 保存当前画面到 captured_images 目录（不删除）
                frame = camera.on_demand_capture()
                if frame is not None:
                    # 保存到 captured_images，不删除
                    saved_path = save_temp_image(frame, save_to_captured=True)
                    if saved_path:
                        print(f"\n图片已保存到: {saved_path}")
                        print("（此目录的图片不会被自动删除）")
                else:
                    print("\n获取图片失败")

            elif user_input in ['calibrate', '标定', 'cal']:
                # 标定摄像头焦距
                print("\n摄像头焦距标定")
                print("=" * 30)
                print("请准备一个已知宽度的参考物体（如标准A4纸宽度0.21米）")
                print("将物体放置在已知距离处，然后按回车继续...")
                input("按回车拍照标定...")
                
                frame = camera.on_demand_capture()
                if frame is None:
                    print("获取图片失败")
                    continue
                
                try:
                    # 获取用户输入的标定参数
                    known_distance = float(input("请输入物体到摄像头的距离（米）: ").strip())
                    known_width = float(input("请输入物体的实际宽度（米）: ").strip())
                    
                    # 检测画面中的物体
                    base64_image = encode_frame_to_base64(frame)
                    if base64_image:
                        obstacles, _ = detect_obstacles(analyzer, base64_image)
                        if obstacles and len(obstacles) > 0:
                            # 使用检测到的第一个物体的宽度进行标定
                            first_obstacle = obstacles[0]
                            x1, y1, x2, y2 = first_obstacle['bbox']
                            measured_width = x2 - x1
                            
                            # 计算并设置新的焦距
                            new_focal_length = (measured_width * known_distance) / known_width
                            print(f"\n标定完成！")
                            print(f"检测到物体: {first_obstacle['class']}")
                            print(f"检测框宽度: {measured_width} 像素")
                            print(f"新焦距: {new_focal_length:.2f} 像素")
                            print(f"原焦距: {analyzer.obstacle_detector.focal_length:.2f} 像素")
                            
                            # 更新焦距
                            analyzer.obstacle_detector.focal_length = new_focal_length
                            print("\n焦距已更新，距离估算将更加准确")
                        else:
                            print("\n未检测到物体，请确保画面中有明显物体")
                    else:
                        print("\n图片编码失败")
                except ValueError:
                    print("\n输入无效，请输入数字")
                except Exception as e:
                    print(f"\n标定失败: {e}")

            elif user_input in ['debug', '调试', 'd']:
                # 调试功能：显示当前画面信息
                print("\n调试信息")
                print("=" * 30)
                
                frame = camera.on_demand_capture()
                if frame is None:
                    print("获取图片失败")
                    continue
                
                # 显示图像基本信息
                print(f"图像尺寸: {frame.shape[1]} x {frame.shape[0]}")
                print(f"平均亮度: {frame.mean():.1f}")
                print(f"像素值范围: {frame.min()} - {frame.max()}")
                
                # 测试不同阈值的检测结果
                print("\n不同阈值检测结果:")
                base64_image = encode_frame_to_base64(frame)
                if base64_image:
                    from ultralytics import YOLO
                    model = YOLO(str(OBSTACLE_YOLO_PATH))

                    for conf in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
                        results = model(frame, conf=conf, verbose=False)[0]
                        count = len(results.boxes)
                        print(f"  阈值 {conf}: {count} 个物体")

                        if count > 0 and conf == 0.05:
                            print("    检测到的物体:")
                            for box in results.boxes:
                                class_name = results.names[int(box.cls.cpu().numpy()[0])]
                                confidence = float(box.conf.cpu().numpy()[0])
                                print(f"      - {class_name}: {confidence:.3f}")
                
                # 保存图像到 captured_images 用于调试查看
                temp_path = save_temp_image(frame, save_to_captured=True)
                if temp_path:
                    print(f"\n当前画面已保存: {temp_path}")
                    print("可以打开查看当前摄像头画面")
                    # 调试模式下不删除图片
                    logger.info(f"调试图片已保存: {temp_path}")

            elif user_input in ['obstacle', 'obstacles', '障碍物', '检测']:
                # 障碍物检测
                frame = camera.on_demand_capture()
                if frame is None:
                    print("获取图片失败")
                    continue

                # 保存临时文件用于分析
                temp_path = save_temp_image(frame)
                if temp_path is None:
                    print("保存临时文件失败")
                    continue

                try:
                    base64_image = encode_frame_to_base64(frame)
                    if base64_image:
                        obstacles, report = detect_obstacles(analyzer, base64_image)
                        if obstacles is not None:
                            last_obstacles = obstacles
                            last_report = report
                            print_obstacles(obstacles, report)
                        else:
                            print("\n检测失败")
                    else:
                        print("\n图片编码失败")
                finally:
                    # 分析完成后删除临时图片
                    delete_temp_image(temp_path)

            elif user_input in ['counter', 'count', '计数器', '数字识别', '数字']:
                # 数字计数器识别
                frame = camera.on_demand_capture()
                if frame is None:
                    print("获取图片失败")
                    continue

                digit, annotated = recognize_counter(analyzer, frame)
                if digit is not None:
                    print("\n" + "=" * 50)
                    print(f"计数器识别结果: {digit}")
                    print("=" * 50)
                    if annotated is not None:
                        saved_path = save_temp_image(annotated, save_to_captured=True)
                        if saved_path:
                            print(f"标注图片已保存: {saved_path}")
                else:
                    print("\n计数器识别失败")

            elif user_input in ['look', '看看', 'vision', '视觉', '分析']:
                # 视觉大模型分析
                frame = camera.on_demand_capture()
                if frame is None:
                    print("获取图片失败")
                    continue

                temp_path = save_temp_image(frame)
                if temp_path is None:
                    print("保存临时文件失败")
                    continue

                try:
                    base64_image = encode_frame_to_base64(frame)
                    if base64_image:
                        result = analyze_image(analyzer, base64_image)
                        if result:
                            print(f"\n分析结果:\n{result}\n")
                        else:
                            print("\n分析失败")
                finally:
                    delete_temp_image(temp_path)

            else:
                # 自定义提示词分析
                frame = camera.on_demand_capture()
                if frame is None:
                    print("获取图片失败")
                    continue

                temp_path = save_temp_image(frame)
                if temp_path is None:
                    print("保存临时文件失败")
                    continue

                try:
                    base64_image = encode_frame_to_base64(frame)
                    if base64_image:
                        result = analyze_image(analyzer, base64_image, user_input)
                        if result:
                            print(f"\n分析结果:\n{result}\n")
                        else:
                            print("\n分析失败")
                finally:
                    delete_temp_image(temp_path)

        except KeyboardInterrupt:
            print("\n正在退出...")
            break
        except Exception as e:
            logger.error(f"程序异常: {e}")

    # 清理
    camera.stop()
    print("程序已退出")


if __name__ == "__main__":
    main()