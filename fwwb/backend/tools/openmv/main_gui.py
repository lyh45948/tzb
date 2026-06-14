"""
OpenMV货物识别和计数器识别系统 - GUI版本
功能分离：实时预览、货物检测、计数器识别各自独立运行
"""

import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from urllib import request as urlrequest
from urllib.error import URLError
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import queue
import time
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
# 整合到 backend 后, 实际项目根是 backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
project_root = BACKEND_ROOT
sys.path.insert(0, str(Path(__file__).parent))                   # tools/openmv 自身, 用于导入 openmv_receiver
sys.path.insert(0, str(BACKEND_ROOT / "training" / "szsb"))      # CRNN 训练代码所在目录

from openmv_receiver import OpenMVReceiver, CargoDetector, CounterRecognizer


class OpenMVVisionGUI:
    """OpenMV视觉识别GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("OpenMV货物识别和计数器识别系统")
        self.root.geometry("1200x800")

        # 核心组件
        self.receiver = OpenMVReceiver()
        self.cargo_detector = CargoDetector()
        self.counter_recognizer = CounterRecognizer()

        # 线程和队列
        self.result_queue = queue.Queue(maxsize=10)

        # 状态标志
        self.connected = False
        self.models_loaded = False

        # 预览状态
        self.preview_thread = None
        self.is_previewing = False

        # 货物检测状态
        self.cargo_thread = None
        self.is_detecting_cargo = False

        # 计数器识别状态
        self.counter_thread = None
        self.is_recognizing_counter = False

        # 最新帧
        self.latest_frame = None
        self.frame_lock = threading.Lock()

        # 统计
        self.preview_frame_count = 0
        self.cargo_detect_count = 0
        self.counter_recognize_count = 0

        # 保存目录
        self.save_dir = project_root / "captured_images" / "openmv"
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 后端上报地址（主后端 spawn GUI 时通过环境变量传入）
        # 默认 http://127.0.0.1:5000；空字符串等同未设置 → 不上报
        self.backend_base_url = (os.getenv('BACKEND_BASE_URL', 'http://127.0.0.1:5000') or '').rstrip('/')
        self._post_lock = threading.Lock()
        self._last_post_log_at = 0.0  # 错误节流

        # 构建UI
        self._build_ui()

        # 延迟初始化
        self.root.after(100, self._delayed_init)

        # 启动队列检查
        self._check_queue()

    def _build_ui(self):
        """构建UI"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部状态栏
        self._build_status_bar(main_frame)

        # 中部内容区
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        # 左侧：预览
        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_preview_panel(left_frame)

        # 右侧：控制和结果
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        self._build_control_panel(right_frame)

    def _build_status_bar(self, parent):
        """构建状态栏"""
        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(bar, text="OpenMV视觉识别系统",
                 font=('Microsoft YaHei', 14, 'bold')).pack(side=tk.LEFT)

        self.status_model = ttk.Label(bar, text="● 模型: 未加载", foreground='red')
        self.status_model.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_camera = ttk.Label(bar, text="● OpenMV: 未连接", foreground='red')
        self.status_camera.pack(side=tk.RIGHT, padx=(10, 0))

    def _build_preview_panel(self, parent):
        """构建预览面板"""
        # 预览区域
        preview_frame = ttk.LabelFrame(parent, text="实时预览", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_label = tk.Label(preview_frame, bg='#1a1a1a',
                                     text="等待连接...",
                                     fg='#666666',
                                     font=('Microsoft YaHei', 12))
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        # 统计信息
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=tk.X, pady=(5, 0))

        self.stats_label = ttk.Label(stats_frame, text="预览帧数: 0")
        self.stats_label.pack(side=tk.LEFT)

    def _build_control_panel(self, parent):
        """构建控制面板"""
        # 连接控制
        conn_frame = ttk.LabelFrame(parent, text="连接控制", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_connect = ttk.Button(conn_frame, text="连接OpenMV",
                                     command=self._connect_camera)
        self.btn_connect.pack(fill=tk.X, pady=2)

        self.btn_disconnect = ttk.Button(conn_frame, text="断开连接",
                                        command=self._disconnect_camera,
                                        state=tk.DISABLED)
        self.btn_disconnect.pack(fill=tk.X, pady=2)

        # 实时预览控制
        preview_frame = ttk.LabelFrame(parent, text="实时预览", padding=10)
        preview_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_start_preview = ttk.Button(preview_frame, text="▶ 开始实时预览",
                                           command=self._start_preview,
                                           state=tk.DISABLED)
        self.btn_start_preview.pack(fill=tk.X, pady=2)

        self.btn_stop_preview = ttk.Button(preview_frame, text="⏹ 停止实时预览",
                                          command=self._stop_preview,
                                          state=tk.DISABLED)
        self.btn_stop_preview.pack(fill=tk.X, pady=2)

        # 货物检测控制
        cargo_frame = ttk.LabelFrame(parent, text="货物检测", padding=10)
        cargo_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_start_cargo = ttk.Button(cargo_frame, text="▶ 开始货物检测",
                                         command=self._start_cargo_detect,
                                         state=tk.DISABLED)
        self.btn_start_cargo.pack(fill=tk.X, pady=2)

        self.btn_stop_cargo = ttk.Button(cargo_frame, text="⏹ 停止货物检测",
                                        command=self._stop_cargo_detect,
                                        state=tk.DISABLED)
        self.btn_stop_cargo.pack(fill=tk.X, pady=2)

        # 计数器识别控制
        counter_frame = ttk.LabelFrame(parent, text="计数器识别", padding=10)
        counter_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_start_counter = ttk.Button(counter_frame, text="▶ 开始计数器识别",
                                           command=self._start_counter_recognize,
                                           state=tk.DISABLED)
        self.btn_start_counter.pack(fill=tk.X, pady=2)

        self.btn_stop_counter = ttk.Button(counter_frame, text="⏹ 停止计数器识别",
                                          command=self._stop_counter_recognize,
                                          state=tk.DISABLED)
        self.btn_stop_counter.pack(fill=tk.X, pady=2)

        # 其他功能
        other_frame = ttk.LabelFrame(parent, text="其他功能", padding=10)
        other_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_capture = ttk.Button(other_frame, text="拍照保存",
                                     command=self._capture_image,
                                     state=tk.DISABLED)
        self.btn_capture.pack(fill=tk.X, pady=2)

        # 结果显示
        result_frame = ttk.LabelFrame(parent, text="识别结果", padding=5)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = scrolledtext.ScrolledText(result_frame,
                                                    wrap=tk.WORD,
                                                    font=('Microsoft YaHei', 10),
                                                    height=10)
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # 日志
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                 wrap=tk.WORD,
                                                 font=('Consolas', 9),
                                                 height=5)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _delayed_init(self):
        """延迟初始化"""
        self._log("系统启动中...")
        if self.backend_base_url:
            self._log(f"识别结果将上报至: {self.backend_base_url}/v1/vision/counter")
        else:
            self._log("未配置 BACKEND_BASE_URL，识别结果不会上报后端")
        self._log("正在加载模型...")
        threading.Thread(target=self._load_models, daemon=True).start()

    def _load_models(self):
        """加载模型"""
        try:
            self._log("加载YOLOv11s模型...")
            if self.cargo_detector.load_model():
                self._log("YOLO模型加载成功")
            else:
                self._log("YOLO模型加载失败")
                self.result_queue.put(("error", "YOLO模型加载失败"))
                return

            self._log("加载CRNN计数器识别模型...")
            if self.counter_recognizer.load_models():
                self._log("CRNN模型加载成功")
            else:
                self._log("CRNN模型加载失败")

            self.result_queue.put(("models_loaded", True))

        except Exception as e:
            self._log(f"模型加载失败: {e}")
            self.result_queue.put(("error", f"模型加载失败: {e}"))

    def _connect_camera(self):
        """连接摄像头"""
        # 先看看 pyserial 能否扫到 OpenMV，便于诊断
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            if ports:
                self._log(f"扫描到 {len(ports)} 个串口：")
                for p in ports:
                    self._log(f"  {p.device} — {p.description}")
            else:
                self._log("扫描串口：未发现任何串口设备")
                self._log("  → 请检查 OpenMV 是否已通过 USB 接到电脑")
        except Exception as e:
            self._log(f"扫描串口异常: {e}")

        self._log("正在连接OpenMV...")
        self.btn_connect.config(state=tk.DISABLED)

        def connect_task():
            # 把底层 print 错误也捕获到 GUI，方便排查权限/被占用等问题
            import io
            import contextlib
            err_buf = io.StringIO()
            success = False
            try:
                with contextlib.redirect_stdout(err_buf), contextlib.redirect_stderr(err_buf):
                    success = self.receiver.connect()
            except Exception as e:
                err_buf.write(f"\n连接异常: {e}")
            captured = err_buf.getvalue().strip()
            if captured:
                # OpenMVReceiver 只用 print 报错，把它们带到 GUI 日志区
                for line in captured.splitlines():
                    self.result_queue.put(("log", line))
            if not success:
                # 给出权限相关的诊断提示
                low = captured.lower()
                if 'permission' in low or 'denied' in low:
                    self.result_queue.put(("log",
                        "→ 权限不足。Linux 下需把当前用户加入 dialout 组："
                        "  sudo usermod -aG dialout $USER  （之后重新登录）"
                        "  或临时执行: sudo chmod 666 /dev/ttyACM0"))
                elif 'busy' in low or 'resource' in low:
                    self.result_queue.put(("log",
                        "→ 串口被占用，可能其它程序（IDE / 之前的 backend 实例）正连着 OpenMV，先关掉再试"))
            self.result_queue.put(("connected", success))

        threading.Thread(target=connect_task, daemon=True).start()

    def _disconnect_camera(self):
        """断开连接"""
        # 停止所有任务
        self._stop_preview()
        self._stop_cargo_detect()
        self._stop_counter_recognize()

        self.receiver.disconnect()
        self.connected = False
        self.status_camera.config(text="● OpenMV: 未连接", foreground='red')
        self.btn_connect.config(state=tk.NORMAL)
        self.btn_disconnect.config(state=tk.DISABLED)
        self._update_button_states()
        self._log("已断开连接")

    def _update_button_states(self):
        """更新按钮状态"""
        state = tk.NORMAL if self.connected and self.models_loaded else tk.DISABLED

        # 预览按钮
        if not self.is_previewing:
            self.btn_start_preview.config(state=state)
        else:
            self.btn_start_preview.config(state=tk.DISABLED)

        # 货物检测按钮
        if not self.is_detecting_cargo:
            self.btn_start_cargo.config(state=state)
        else:
            self.btn_start_cargo.config(state=tk.DISABLED)

        # 计数器识别按钮
        if not self.is_recognizing_counter:
            self.btn_start_counter.config(state=state)
        else:
            self.btn_start_counter.config(state=tk.DISABLED)

        # 拍照按钮
        self.btn_capture.config(state=state)

    # ==================== 实时预览 ====================

    def _start_preview(self):
        """开始实时预览"""
        if not self.connected:
            messagebox.showwarning("警告", "请先连接OpenMV")
            return

        self.is_previewing = True
        self.preview_frame_count = 0
        self.btn_start_preview.config(state=tk.DISABLED)
        self.btn_stop_preview.config(state=tk.NORMAL)
        self._log("开始实时预览...")

        self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

    def _stop_preview(self):
        """停止实时预览"""
        self.is_previewing = False
        self.btn_start_preview.config(state=tk.NORMAL)
        self.btn_stop_preview.config(state=tk.DISABLED)
        self._log("停止实时预览")

    def _preview_loop(self):
        """实时预览循环 - 只显示图像，不进行识别"""
        self._log("预览线程已启动")

        while self.is_previewing:
            try:
                frame = self.receiver.receive_image()
                if frame is None:
                    time.sleep(0.1)
                    continue

                self.preview_frame_count += 1

                # 更新最新帧
                with self.frame_lock:
                    self.latest_frame = frame.copy()

                # 显示图像
                self.result_queue.put(("preview", frame))
                self.result_queue.put(("stats", f"预览帧数: {self.preview_frame_count}"))

                time.sleep(0.05)

            except Exception as e:
                self._log(f"预览错误: {e}")
                time.sleep(0.1)

        self._log("预览线程已停止")

    # ==================== 货物检测 ====================

    def _start_cargo_detect(self):
        """开始货物检测"""
        if not self.connected:
            messagebox.showwarning("警告", "请先连接OpenMV")
            return

        self.is_detecting_cargo = True
        self.cargo_detect_count = 0
        self.btn_start_cargo.config(state=tk.DISABLED)
        self.btn_stop_cargo.config(state=tk.NORMAL)
        self._log("开始货物检测...")

        self.cargo_thread = threading.Thread(target=self._cargo_detect_loop, daemon=True)
        self.cargo_thread.start()

    def _stop_cargo_detect(self):
        """停止货物检测"""
        self.is_detecting_cargo = False
        self.btn_start_cargo.config(state=tk.NORMAL)
        self.btn_stop_cargo.config(state=tk.DISABLED)
        self._log("停止货物检测")

    def _cargo_detect_loop(self):
        """货物检测循环"""
        self._log("货物检测线程已启动")

        while self.is_detecting_cargo:
            try:
                frame = self.receiver.receive_image()
                if frame is None:
                    time.sleep(0.1)
                    continue

                # 检测货物
                detections = self.cargo_detector.detect(frame)
                self.cargo_detect_count += len(detections)

                # 绘制检测结果
                annotated = self.cargo_detector.draw_detections(frame, detections)

                # 更新预览和结果
                self.result_queue.put(("preview", annotated))
                self.result_queue.put(("cargo_result", detections))

                # 保存带标注的图像
                if detections:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = self.save_dir / f"cargo_{timestamp}.jpg"
                    cv2.imwrite(str(save_path), annotated)

                time.sleep(0.1)

            except Exception as e:
                self._log(f"货物检测错误: {e}")
                time.sleep(0.1)

        self._log("货物检测线程已停止")

    # ==================== 计数器识别 ====================

    def _start_counter_recognize(self):
        """开始计数器识别"""
        if not self.connected:
            messagebox.showwarning("警告", "请先连接OpenMV")
            return

        self.is_recognizing_counter = True
        self.counter_recognize_count = 0
        self.btn_start_counter.config(state=tk.DISABLED)
        self.btn_stop_counter.config(state=tk.NORMAL)
        self._log("开始计数器识别...")

        self.counter_thread = threading.Thread(target=self._counter_recognize_loop, daemon=True)
        self.counter_thread.start()

    def _stop_counter_recognize(self):
        """停止计数器识别"""
        self.is_recognizing_counter = False
        self.btn_start_counter.config(state=tk.NORMAL)
        self.btn_stop_counter.config(state=tk.DISABLED)
        self._log("停止计数器识别")

    def _counter_recognize_loop(self):
        """计数器识别循环"""
        self._log("计数器识别线程已启动")

        while self.is_recognizing_counter:
            try:
                frame = self.receiver.receive_image()
                if frame is None:
                    time.sleep(0.1)
                    continue

                # 识别计数器
                results, annotated = self.counter_recognizer.recognize_counter(frame)
                self.counter_recognize_count += len(results)

                # 把识别结果上报给主后端 → SSE 推送到大屏前端
                # 取首个识别结果的 digits 字段作为当前面板读数
                if results:
                    digits = str(results[0].get('digits') or '').strip()
                    if digits:
                        self._post_counter_to_backend(digits)

                # 更新预览和结果
                self.result_queue.put(("preview", annotated))
                self.result_queue.put(("counter_result", results))

                # 保存带标注的图像
                if results:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = self.save_dir / f"counter_{timestamp}.jpg"
                    cv2.imwrite(str(save_path), annotated)

                time.sleep(0.2)

            except Exception as e:
                self._log(f"计数器识别错误: {e}")
                time.sleep(0.1)

        self._log("计数器识别线程已停止")

    # ==================== 其他功能 ====================

    def _capture_image(self):
        """拍照保存"""
        if not self.connected:
            messagebox.showwarning("警告", "请先连接OpenMV")
            return

        self._log("正在捕获图像...")
        frame = self.receiver.receive_image()
        if frame is None:
            self._log("捕获失败")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = self.save_dir / f"capture_{timestamp}.jpg"
        cv2.imwrite(str(save_path), frame)
        self._log(f"图像已保存: {save_path}")

        self._update_preview(frame)

    def _post_counter_to_backend(self, digits):
        """把识别到的计数器数字 POST 给主后端

        后端接口：POST /v1/vision/counter
        body: { device_id, digits, timestamp }
        失败只记日志（节流），不阻塞识别循环。
        """
        if not self.backend_base_url:
            return  # 没配置上报地址（独立运行模式）

        url = f"{self.backend_base_url}/v1/vision/counter"
        payload = json.dumps({
            'device_id': 'openmv_gui',
            'digits': str(digits),
            'timestamp': int(time.time() * 1000),
        }).encode('utf-8')

        req = urlrequest.Request(
            url,
            data=payload,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urlrequest.urlopen(req, timeout=1.5) as resp:
                resp.read(256)  # 读完即可，丢弃
        except (URLError, OSError, TimeoutError) as e:
            # 节流：失败时每 30s 才打一行，避免刷屏
            now = time.time()
            if now - self._last_post_log_at > 30:
                self._last_post_log_at = now
                self._log(f"上报后端失败: {e} （后续 30s 内不再提示）")

    # ==================== UI更新 ====================

    def _update_preview(self, frame):
        """更新预览"""
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            max_w, max_h = 640, 480
            scale = min(max_w / w, max_h / h, 1.0)
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w != w or new_h != h:
                rgb = cv2.resize(rgb, (new_w, new_h))

            im = Image.fromarray(rgb)
            photo = ImageTk.PhotoImage(image=im)

            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo

        except Exception as e:
            self._log(f"预览更新失败: {e}")

    def _set_result_text(self, text):
        """设置结果文本"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _append_result_text(self, text):
        """追加结果文本"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _log(self, msg):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _check_queue(self):
        """检查结果队列"""
        try:
            while True:
                msg_type, data = self.result_queue.get_nowait()

                if msg_type == "log":
                    self._log(data)
                    continue

                if msg_type == "models_loaded":
                    self.models_loaded = True
                    self.status_model.config(text="● 模型: 已加载", foreground='green')
                    self._update_button_states()

                elif msg_type == "connected":
                    if data:
                        self.connected = True
                        self.status_camera.config(text="● OpenMV: 已连接", foreground='green')
                        self.btn_connect.config(state=tk.DISABLED)
                        self.btn_disconnect.config(state=tk.NORMAL)
                        self._update_button_states()
                        self._log("OpenMV连接成功")
                    else:
                        self._log("OpenMV连接失败")
                        self.btn_connect.config(state=tk.NORMAL)

                elif msg_type == "preview":
                    self._update_preview(data)

                elif msg_type == "stats":
                    self.stats_label.config(text=data)

                elif msg_type == "cargo_result":
                    detections = data
                    result_text = f"=== 货物检测 ===\n"
                    result_text += f"检测到 {len(detections)} 个货物\n"
                    for i, det in enumerate(detections, 1):
                        result_text += f"{i}. {det['class_name']}: {det['confidence']:.2f}\n"
                    self._set_result_text(result_text)

                elif msg_type == "counter_result":
                    results = data
                    result_text = f"=== 计数器识别 ===\n"
                    result_text += f"识别到 {len(results)} 个计数器\n"
                    for i, res in enumerate(results, 1):
                        result_text += f"{i}. 数字: {res['digits']}\n"
                    self._set_result_text(result_text)

                elif msg_type == "error":
                    self._log(f"错误: {data}")
                    messagebox.showerror("错误", data)

        except queue.Empty:
            pass

        self.root.after(100, self._check_queue)

    def on_closing(self):
        """关闭窗口"""
        self.is_previewing = False
        self.is_detecting_cargo = False
        self.is_recognizing_counter = False
        if self.connected:
            self.receiver.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = OpenMVVisionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
