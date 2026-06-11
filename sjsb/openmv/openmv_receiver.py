"""
OpenMV图像接收和识别系统
- 从OpenMV接收图像
- 使用YOLOv11s进行货物识别
- 使用CRNN进行计数器数字识别
"""

import cv2
import numpy as np
import serial
import serial.tools.list_ports
import time
import threading
import queue
import os
import sys
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "szsb"))

class OpenMVReceiver:
    """OpenMV图像接收器"""

    def __init__(self, port=None, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.is_running = False

        # 图像缓冲
        self.frame_queue = queue.Queue(maxsize=5)
        self.latest_frame = None
        self.frame_lock = threading.Lock()

        # 统计
        self.frame_count = 0
        self.error_count = 0

    def find_openmv_port(self):
        """自动查找OpenMV设备"""
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "USB" in p.description or "OpenMV" in p.description or "CDC" in p.description:
                return p.device
        return None

    def connect(self):
        """连接OpenMV"""
        if self.port is None:
            self.port = self.find_openmv_port()
            if self.port is None:
                print("未找到OpenMV设备")
                return False

        try:
            self.serial_conn = serial.Serial(
                self.port,
                self.baudrate,
                timeout=5,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            time.sleep(2)  # 等待连接稳定
            self.is_connected = True
            print(f"已连接到 {self.port}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.is_connected = False
        print("已断开连接")

    def send_command(self, cmd):
        """发送命令到OpenMV"""
        if not self.is_connected:
            return False
        try:
            self.serial_conn.write(f"{cmd}\n".encode())
            return True
        except Exception as e:
            print(f"发送命令失败: {e}")
            return False

    def receive_image(self):
        """接收一张图像"""
        if not self.is_connected:
            return None

        try:
            # 清空缓冲区
            self.serial_conn.read(self.serial_conn.in_waiting)

            # 发送捕获命令
            self.send_command("capture")

            # 等待OpenMV处理
            time.sleep(0.3)

            # 读取所有可用数据
            all_data = bytearray()
            start_time = time.time()

            while time.time() - start_time < 3:  # 3秒超时
                if self.serial_conn.in_waiting:
                    chunk = self.serial_conn.read(self.serial_conn.in_waiting)
                    all_data.extend(chunk)
                    time.sleep(0.05)  # 等待更多数据
                else:
                    if len(all_data) > 0:
                        break  # 已收到一些数据，检查是否是图像
                    time.sleep(0.01)

            if len(all_data) == 0:
                return None

            # 检查是否是JPEG数据（以FF D8开头）
            jpeg_start = -1
            for i in range(len(all_data) - 1):
                if all_data[i] == 0xFF and all_data[i+1] == 0xD8:
                    jpeg_start = i
                    break

            if jpeg_start < 0:
                # 不是JPEG数据，可能是文本响应
                try:
                    text = all_data.decode('utf-8', errors='ignore').strip()
                    if "capture" in text.lower() or "started" in text.lower():
                        # OpenMV回显了命令，说明脚本没有正确运行
                        print(f"警告: 收到文本响应而非图像数据")
                        print(f"请确保OpenMV正在运行 openmv_camera.py 脚本")
                    else:
                        print(f"收到非图像数据: {text[:100]}")
                except:
                    pass
                return None

            # 查找JPEG结束标记（FF D9）
            jpeg_end = -1
            for i in range(jpeg_start + 2, len(all_data) - 1):
                if all_data[i] == 0xFF and all_data[i+1] == 0xD9:
                    jpeg_end = i + 2
                    break

            if jpeg_end < 0:
                # JPEG数据不完整
                print(f"JPEG数据不完整，大小: {len(all_data) - jpeg_start} 字节")
                return None

            # 提取JPEG数据
            jpeg_data = all_data[jpeg_start:jpeg_end]
            img_size = len(jpeg_data)

            if img_size > 500000:  # 500KB限制
                print(f"图像太大: {img_size} 字节")
                return None

            # 解码JPEG
            img_array = np.frombuffer(jpeg_data, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                self.frame_count += 1

            return frame

        except Exception as e:
            self.error_count += 1
            print(f"接收图像失败: {e}")
            return None

    def start_stream(self):
        """开始视频流"""
        self.send_command("stream")

    def stop_stream(self):
        """停止视频流"""
        self.send_command("stream")

    def set_quality(self, quality):
        """设置JPEG质量"""
        self.send_command(f"quality:{quality}")

    def capture_loop(self, callback=None):
        """持续捕获循环"""
        self.is_running = True
        print("开始捕获循环...")

        while self.is_running:
            frame = self.receive_image()
            if frame is not None:
                with self.frame_lock:
                    self.latest_frame = frame.copy()

                # 放入队列
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)

                # 回调
                if callback:
                    callback(frame)

            time.sleep(0.05)  # 约20fps

    def get_latest_frame(self):
        """获取最新帧"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None


class CargoDetector:
    """货物检测器（使用YOLOv11s）"""

    def __init__(self, model_path=None):
        self.model = None
        self.model_path = model_path
        self.class_names = []

    def load_model(self, model_path=None):
        """加载YOLO模型"""
        if model_path:
            self.model_path = model_path

        if self.model_path is None:
            self.model_path = str(project_root / "yolo11s.pt")

        try:
            print(f"加载YOLO模型: {self.model_path}")
            self.model = YOLO(self.model_path)
            self.class_names = list(self.model.names.values())
            print(f"模型加载成功，类别数: {len(self.class_names)}")
            return True
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False

    def detect(self, frame, conf=0.25):
        """检测货物"""
        if self.model is None:
            return []

        try:
            results = self.model(frame, conf=conf, verbose=False)[0]

            detections = []
            for box in results.boxes:
                cls_id = int(box.cls.cpu().numpy()[0])
                confidence = float(box.conf.cpu().numpy()[0])
                bbox = box.xyxy.cpu().numpy()[0].tolist()  # [x1, y1, x2, y2]

                detections.append({
                    'class_id': cls_id,
                    'class_name': results.names[cls_id],
                    'confidence': confidence,
                    'bbox': bbox
                })

            return detections

        except Exception as e:
            print(f"检测失败: {e}")
            return []

    def draw_detections(self, frame, detections):
        """绘制检测结果"""
        annotated = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            label = f"{det['class_name']}: {det['confidence']:.2f}"

            # 绘制边界框
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 绘制标签背景
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - label_h - 10), (x1 + label_w, y1), (0, 255, 0), -1)

            # 绘制标签文字
            cv2.putText(annotated, label, (x1, y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        return annotated


class CounterRecognizer:
    """计数器数字识别器（使用CRNN）"""

    def __init__(self):
        self.yolo_model = None  # 用于检测计数器面板
        self.crnn_model = None  # 用于识别数字
        self.device = None

    def load_models(self, yolo_path=None, crnn_path=None):
        """加载模型"""
        import torch

        # 加载YOLO模型（检测计数器面板）
        if yolo_path is None:
            yolo_path = str(project_root / "yolo11s.pt")

        try:
            print(f"加载计数器检测模型: {yolo_path}")
            self.yolo_model = YOLO(yolo_path)
        except Exception as e:
            print(f"YOLO模型加载失败: {e}")
            return False

        # 加载CRNN模型（识别数字）
        if crnn_path is None:
            crnn_path = str(project_root / "szsb" / "checkpoints_v3" / "best_crnn.pth")

        try:
            print(f"加载CRNN模型: {crnn_path}")

            # 导入CRNN定义
            from infer_crnn import CRNN, NUM_CLASSES, BLANK_INDEX

            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

            # 加载checkpoint
            ckpt = torch.load(crnn_path, map_location=self.device, weights_only=False)
            saved_args = ckpt.get('args', {})
            hidden_size = saved_args.get('hidden_size', 256)

            self.crnn_model = CRNN(num_classes=NUM_CLASSES, hidden_size=hidden_size)
            self.crnn_model.load_state_dict(ckpt['model_state_dict'])
            self.crnn_model.to(self.device)
            self.crnn_model.eval()

            print("CRNN模型加载成功")
            return True

        except Exception as e:
            print(f"CRNN模型加载失败: {e}")
            return False

    def detect_counter_panel(self, frame):
        """检测计数器面板"""
        if self.yolo_model is None:
            return []

        try:
            results = self.yolo_model(frame, conf=0.3, verbose=False)[0]

            panels = []
            for box in results.boxes:
                cls_id = int(box.cls.cpu().numpy()[0])
                confidence = float(box.conf.cpu().numpy()[0])
                bbox = box.xyxy.cpu().numpy()[0].tolist()

                # 假设计数器面板的类别名包含"counter"或"meter"
                class_name = results.names[cls_id].lower()
                if 'counter' in class_name or 'meter' in class_name or 'display' in class_name:
                    panels.append({
                        'class_id': cls_id,
                        'class_name': results.names[cls_id],
                        'confidence': confidence,
                        'bbox': bbox
                    })

            # 如果没有特定类别，返回所有检测结果
            if not panels:
                for box in results.boxes:
                    cls_id = int(box.cls.cpu().numpy()[0])
                    confidence = float(box.conf.cpu().numpy()[0])
                    bbox = box.xyxy.cpu().numpy()[0].tolist()
                    panels.append({
                        'class_id': cls_id,
                        'class_name': results.names[cls_id],
                        'confidence': confidence,
                        'bbox': bbox
                    })

            return panels

        except Exception as e:
            print(f"计数器面板检测失败: {e}")
            return []

    def recognize_digits(self, frame, bbox):
        """识别计数器数字"""
        import torch
        from infer_crnn import preprocess_image, ctc_decode

        if self.crnn_model is None:
            return ""

        try:
            # 裁剪计数器区域
            x1, y1, x2, y2 = [int(v) for v in bbox]
            roi = frame[y1:y2, x1:x2]

            if roi.size == 0:
                return ""

            # 预处理
            img_array = preprocess_image(roi, [0.5, 0.5, 1.0, 1.0], img_size=(32, 128))
            img_tensor = torch.from_numpy(img_array).unsqueeze(0).unsqueeze(0).to(self.device)

            # 推理
            with torch.no_grad():
                output = self.crnn_model(img_tensor)

            # 解码
            preds = output.argmax(dim=2).cpu().numpy()
            digits = ctc_decode(preds)[0]

            return digits

        except Exception as e:
            print(f"数字识别失败: {e}")
            return ""

    def recognize_counter(self, frame):
        """完整的计数器识别流程"""
        # 1. 检测计数器面板
        panels = self.detect_counter_panel(frame)

        if not panels:
            return [], frame

        # 2. 识别每个面板的数字
        results = []
        annotated_frame = frame.copy()

        for panel in panels:
            digits = self.recognize_digits(frame, panel['bbox'])

            results.append({
                'bbox': panel['bbox'],
                'confidence': panel['confidence'],
                'digits': digits
            })

            # 绘制结果
            x1, y1, x2, y2 = [int(v) for v in panel['bbox']]
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

            label = f"Counter: {digits}"
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        return results, annotated_frame


def main():
    """主函数"""
    print("=" * 60)
    print("OpenMV货物识别和计数器识别系统")
    print("=" * 60)

    # 初始化组件
    receiver = OpenMVReceiver()
    cargo_detector = CargoDetector()
    counter_recognizer = CounterRecognizer()

    # 加载模型
    print("\n正在加载模型...")
    cargo_detector.load_model()
    counter_recognizer.load_models()

    # 连接OpenMV
    print("\n正在连接OpenMV...")
    if not receiver.connect():
        print("无法连接OpenMV，程序退出")
        return

    print("\n系统就绪！")
    print("操作说明:")
    print("  'c' - 捕获并检测货物")
    print("  'n' - 捕获并识别计数器")
    print("  'b' - 捕获并执行所有识别")
    print("  's' - 开始/停止视频流")
    print("  'q' - 退出")

    # 创建保存目录
    save_dir = project_root / "captured_images" / "openmv"
    save_dir.mkdir(parents=True, exist_ok=True)

    streaming = False

    while True:
        try:
            cmd = input("\n请输入命令: ").strip().lower()

            if cmd == 'q':
                break

            elif cmd == 'c':
                # 货物检测
                print("正在捕获图像...")
                frame = receiver.receive_image()
                if frame is None:
                    print("捕获失败")
                    continue

                print("正在检测货物...")
                detections = cargo_detector.detect(frame)

                # 绘制结果
                annotated = cargo_detector.draw_detections(frame, detections)

                # 显示结果
                print(f"\n检测到 {len(detections)} 个货物:")
                for i, det in enumerate(detections, 1):
                    print(f"  {i}. {det['class_name']}: {det['confidence']:.2f}")

                # 保存图像
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = save_dir / f"cargo_{timestamp}.jpg"
                cv2.imwrite(str(save_path), annotated)
                print(f"结果已保存: {save_path}")

                # 显示图像
                cv2.imshow("Cargo Detection", annotated)
                cv2.waitKey(1)

            elif cmd == 'n':
                # 计数器识别
                print("正在捕获图像...")
                frame = receiver.receive_image()
                if frame is None:
                    print("捕获失败")
                    continue

                print("正在识别计数器...")
                results, annotated = counter_recognizer.recognize_counter(frame)

                # 显示结果
                print(f"\n识别到 {len(results)} 个计数器:")
                for i, res in enumerate(results, 1):
                    print(f"  {i}. 数字: {res['digits']}, 置信度: {res['confidence']:.2f}")

                # 保存图像
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = save_dir / f"counter_{timestamp}.jpg"
                cv2.imwrite(str(save_path), annotated)
                print(f"结果已保存: {save_path}")

                # 显示图像
                cv2.imshow("Counter Recognition", annotated)
                cv2.waitKey(1)

            elif cmd == 'b':
                # 完整识别
                print("正在捕获图像...")
                frame = receiver.receive_image()
                if frame is None:
                    print("捕获失败")
                    continue

                # 货物检测
                print("正在检测货物...")
                cargo_detections = cargo_detector.detect(frame)
                annotated = cargo_detector.draw_detections(frame, cargo_detections)

                # 计数器识别
                print("正在识别计数器...")
                counter_results, annotated = counter_recognizer.recognize_counter(annotated)

                # 显示结果
                print(f"\n货物检测: {len(cargo_detections)} 个")
                for i, det in enumerate(cargo_detections, 1):
                    print(f"  {i}. {det['class_name']}: {det['confidence']:.2f}")

                print(f"\n计数器识别: {len(counter_results)} 个")
                for i, res in enumerate(counter_results, 1):
                    print(f"  {i}. 数字: {res['digits']}")

                # 保存图像
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = save_dir / f"full_{timestamp}.jpg"
                cv2.imwrite(str(save_path), annotated)
                print(f"\n结果已保存: {save_path}")

                # 显示图像
                cv2.imshow("Full Recognition", annotated)
                cv2.waitKey(1)

            elif cmd == 's':
                # 视频流
                streaming = not streaming
                if streaming:
                    print("开始视频流...")
                    receiver.start_stream()
                else:
                    print("停止视频流...")
                    receiver.stop_stream()

            else:
                print("未知命令")

        except KeyboardInterrupt:
            print("\n正在退出...")
            break
        except Exception as e:
            print(f"错误: {e}")

    # 清理
    receiver.disconnect()
    cv2.destroyAllWindows()
    print("程序已退出")


if __name__ == "__main__":
    main()
