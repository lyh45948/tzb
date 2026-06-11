#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 摄像头 AI 视觉辅助系统 - 图形化界面
基于 tkinter，无需额外安装 GUI 依赖
功能：实时预览、障碍物检测、场景分析、拍照保存、焦距标定、调试模式
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import queue
import time
import logging
import base64
import os
import sys
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageTk

# ---------- 路径设置 ----------
# vision_only
vision_only_path = Path(__file__).parent.parent / "vision_only"
if str(vision_only_path) not in sys.path:
    sys.path.insert(0, str(vision_only_path))

# esp32_viewer (同级目录，用于导入 capture_still)
esp32_viewer_path = Path(__file__).parent
if str(esp32_viewer_path) not in sys.path:
    sys.path.insert(0, str(esp32_viewer_path))

# ---------- 导入核心模块 ----------
try:
    from capture_still import (
        ESP32CameraStream, CAPTURE_URL, CAPTURE_DIR, ESP32_IP,
        encode_frame_to_base64, save_temp_image, delete_temp_image,
        set_esp32_resolution, set_esp32_quality, CAMERA_CONFIG,
        OBSTACLE_YOLO_PATH
    )
except Exception as e:
    print(f"警告: 无法从 capture_still.py 导入: {e}")
    ESP32CameraStream = None
    CAPTURE_URL = "http://192.168.137.213/capture"
    CAPTURE_DIR = str(Path(__file__).resolve().parents[1] / "captured_images")
    ESP32_IP = "192.168.137.213"
    OBSTACLE_YOLO_PATH = Path(__file__).resolve().parents[1] / "yolo11s.pt"

try:
    from src.utils.VL import ImageAnalyzer
    from src.utils.config_manager import ConfigManager
except Exception as e:
    print(f"错误: 无法导入 vision_only 模块: {e}")
    sys.exit(1)

# ---------- 日志配置 ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ESP32VisionGUI")

# ---------- 全局常量 ----------
# 预览窗口最大尺寸
PREVIEW_MAX_WIDTH = 640
PREVIEW_MAX_HEIGHT = 480


class ESP32VisionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 AI 视觉辅助系统")
        self.root.geometry("1200x780")
        self.root.minsize(1000, 700)
        self.root.configure(bg='#2b2b2b')

        # 样式
        self.font_family = self._choose_font_family()
        self._setup_styles()

        # 核心组件
        self.camera = None
        self.analyzer = None
        self.config = ConfigManager.get_instance()

        # 线程与通信
        self.result_queue = queue.Queue(maxsize=3)
        self.preview_active = False
        self.preview_thread = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()

        # 状态
        self.esp32_connected = False
        self.model_loaded = False
        self.current_focal_length = 600.0

        # 障碍物实时检测
        self.obstacle_detecting = False
        self.obstacle_thread = None

        # 计数器数字识别
        self.counter_recognizing = False
        self.counter_thread = None

        # 图像旋转角度 (0, 90, 180, 270)
        self.rotation_angle = 0

        # 保持 PhotoImage 引用防止 GC
        self._current_photo = None

        # 构建UI
        self._build_ui()

        # 延迟初始化（让UI先渲染出来）
        self.root.after(100, self._delayed_init)

        # 启动队列检查循环
        self._check_queue()

    def _choose_font_family(self):
        """选择 Linux/Windows 都可用的中文字体"""
        candidates = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans', 'Microsoft YaHei']
        try:
            available = set(tkfont.families(self.root))
            for name in candidates:
                if name in available:
                    return name
        except Exception:
            pass
        return 'DejaVu Sans'

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        ui_font = (self.font_family, 10)
        header_font = (self.font_family, 14, 'bold')
        status_font = (self.font_family, 9)
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='#e0e0e0', font=ui_font)
        style.configure('TButton', font=ui_font, padding=6)
        style.configure('Header.TLabel', font=header_font, foreground='#4fc3f7')
        style.configure('Status.TLabel', font=status_font, foreground='#aaaaaa')
        style.configure('Success.TLabel', foreground='#81c784')
        style.configure('Error.TLabel', foreground='#e57373')
        style.configure('Warning.TLabel', foreground='#ffb74d')
        style.configure('TCheckbutton', background='#2b2b2b', foreground='#e0e0e0', font=ui_font)
        style.map('TButton',
                  background=[('active', '#4a4a4a'), ('pressed', '#3a3a3a')],
                  foreground=[('active', '#ffffff')])

    def _build_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 顶部状态栏 ==========
        self._build_status_bar(main_frame)

        # ========== 中部左右分栏 ==========
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        # 左侧：预览 + 结果
        left_frame = ttk.Frame(content_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.rowconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)
        self._build_left_panel(left_frame)

        # 右侧：控制按钮 + 日志
        right_frame = ttk.Frame(content_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        self._build_right_panel(right_frame)

    def _build_status_bar(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(bar, text="ESP32 AI 视觉辅助系统", style='Header.TLabel').pack(side=tk.LEFT)

        self.status_esp32 = ttk.Label(bar, text="● ESP32: 未连接", style='Error.TLabel')
        self.status_esp32.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_model = ttk.Label(bar, text="● 模型: 未加载", style='Error.TLabel')
        self.status_model.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_focal = ttk.Label(bar, text="焦距: 600px", style='Status.TLabel')
        self.status_focal.pack(side=tk.RIGHT, padx=(10, 0))

        self.status_counter = ttk.Label(bar, text="🔢 计数器: --", style='Status.TLabel')
        self.status_counter.pack(side=tk.RIGHT, padx=(10, 0))

    def _build_left_panel(self, parent):
        # 预览区域
        preview_frame = ttk.LabelFrame(parent, text="实时预览", padding=5)
        preview_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_label = tk.Label(
            preview_frame, bg='#1a1a1a', text="等待启动...",
            fg='#666666', font=(self.font_family, 14)
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        # 结果区域
        result_frame = ttk.LabelFrame(parent, text="分析结果", padding=5)
        result_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        self.result_text = scrolledtext.ScrolledText(
            result_frame, wrap=tk.WORD, font=(self.font_family, 11),
            bg='#1e1e1e', fg='#e0e0e0', insertbackground='#e0e0e0',
            state=tk.DISABLED
        )
        self.result_text.grid(row=0, column=0, sticky="nsew")

    def _build_right_panel(self, parent):
        # 控制按钮区
        ctrl_frame = ttk.LabelFrame(parent, text="操作控制", padding=10)
        ctrl_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # 预览控制
        preview_ctrl = ttk.Frame(ctrl_frame)
        preview_ctrl.pack(fill=tk.X, pady=(0, 10))
        self.btn_start_preview = ttk.Button(preview_ctrl, text="▶ 开始预览", command=self._start_preview)
        self.btn_start_preview.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.btn_stop_preview = ttk.Button(preview_ctrl, text="⏹ 停止预览", command=self._stop_preview, state=tk.DISABLED)
        self.btn_stop_preview.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # 功能按钮
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        # 障碍物检测控制（开始/停止）
        obstacle_ctrl = ttk.Frame(btn_frame)
        obstacle_ctrl.pack(fill=tk.X, pady=3)
        self.btn_start_obstacle = ttk.Button(obstacle_ctrl, text="🔍 开始障碍物检测", command=self._start_obstacle_detect)
        self.btn_start_obstacle.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.btn_stop_obstacle = ttk.Button(obstacle_ctrl, text="⏹ 停止障碍物检测", command=self._stop_obstacle_detect, state=tk.DISABLED)
        self.btn_stop_obstacle.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        self.btn_capture = ttk.Button(btn_frame, text="📷 拍照保存", command=self._on_capture)
        self.btn_capture.pack(fill=tk.X, pady=3)

        self.btn_calibrate = ttk.Button(btn_frame, text="⚙ 焦距标定", command=self._on_calibrate)
        self.btn_calibrate.pack(fill=tk.X, pady=3)

        self.btn_debug = ttk.Button(btn_frame, text="🐞 调试模式", command=self._on_debug)
        self.btn_debug.pack(fill=tk.X, pady=3)

        # 计数器识别控制（开始/停止）
        counter_ctrl = ttk.Frame(btn_frame)
        counter_ctrl.pack(fill=tk.X, pady=3)
        self.btn_start_counter = ttk.Button(counter_ctrl, text="🔢 开始计数器识别", command=self._start_counter_recognize)
        self.btn_start_counter.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self.btn_stop_counter = ttk.Button(counter_ctrl, text="⏹ 停止计数器识别", command=self._stop_counter_recognize, state=tk.DISABLED)
        self.btn_stop_counter.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        # 图像旋转控制
        rotation_frame = ttk.Frame(ctrl_frame)
        rotation_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(rotation_frame, text="🔄 图像旋转:").pack(side=tk.LEFT)
        self.rotation_combo = ttk.Combobox(
            rotation_frame, values=["0°", "90°", "180°", "270°"],
            state="readonly", width=8
        )
        self.rotation_combo.set("0°")
        self.rotation_combo.pack(side=tk.LEFT, padx=(5, 0))
        self.rotation_combo.bind("<<ComboboxSelected>>", self._on_rotation_change)

        # 功能开关区域
        # 日志区
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding=5)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, font=('Consolas', 9),
            bg='#1e1e1e', fg='#aaaaaa', insertbackground='#aaaaaa',
            height=10, state=tk.DISABLED
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

    def _delayed_init(self):
        """延迟初始化（模型加载等耗时操作）"""
        self._log("=" * 50)
        self._log("系统启动中...")
        self._log(f"ESP32 地址: {CAPTURE_URL}")
        self._log("正在初始化视觉模型，请稍候...")
        self._set_buttons_state(tk.DISABLED)
        self.btn_start_preview.config(state=tk.DISABLED)
        self.btn_stop_preview.config(state=tk.DISABLED)

        # 在新线程中加载模型，避免阻塞UI
        threading.Thread(target=self._init_model_thread, daemon=True).start()

    def _init_model_thread(self):
        try:
            self.analyzer = ImageAnalyzer.get_instance()
            self.analyzer.init()
            self.result_queue.put(("model_loaded", True, "视觉模型加载完成（障碍物 YOLO / 数字区域 YOLO / CRNN）"))
        except Exception as e:
            self.result_queue.put(("model_loaded", False, str(e)))

    def _start_camera(self):
        if ESP32CameraStream is None:
            self._log("错误: ESP32CameraStream 未导入")
            return False
        if self.camera is None:
            self.camera = ESP32CameraStream()
        try:
            success = self.camera.start()
        except Exception as e:
            self._log(f"启动摄像头失败: {e}")
            success = False

        if success:
            self.esp32_connected = True
            self.status_esp32.config(text="● ESP32: 已连接", style='Success.TLabel')
            self._log("ESP32 摄像头连接成功")
            # 确认摄像头分辨率（ESP32 固件固定 320x240，/control 接口无法改变）
            w, h = CAMERA_CONFIG["frame_width"], CAMERA_CONFIG["frame_height"]
            self._log(f"摄像头分辨率: {w}x{h} (ESP32 固件固定输出)")
        else:
            self.esp32_connected = False
            self.status_esp32.config(text="● ESP32: 连接失败", style='Error.TLabel')
            self._log("ESP32 摄像头连接失败，请检查IP地址和网络")
        return success

    def _rotate_frame(self, frame):
        """根据 rotation_angle 旋转图像帧"""
        if self.rotation_angle == 0 or frame is None:
            return frame
        elif self.rotation_angle == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_angle == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif self.rotation_angle == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    def _on_rotation_change(self, event=None):
        """旋转角度切换回调"""
        val = self.rotation_combo.get().replace("°", "")
        try:
            self.rotation_angle = int(val)
            self._log(f"图像旋转已设置为 {self.rotation_angle}°")
        except ValueError:
            self.rotation_angle = 0
            self.rotation_combo.set("0°")

    def _start_counter_recognize(self):
        if not self._ensure_ready():
            return
        self._log("启动计数器数字识别...")
        self.counter_recognizing = True

        # 重置时序平滑器 + 面板定位平滑（避免旧值锁死）
        if hasattr(self.analyzer, 'counter_smoother') and self.analyzer.counter_smoother:
            self.analyzer.counter_smoother.reset()
            self._log("时序平滑器已重置")
        if hasattr(self.analyzer, '_panel_smooth'):
            self.analyzer._panel_smooth = None
            self._log("面板定位平滑已重置")

        self.btn_start_counter.config(state=tk.DISABLED)
        self.btn_stop_counter.config(state=tk.NORMAL)
        # 计数器识别可与预览共存，不禁用其他按钮

        self.counter_thread = threading.Thread(target=self._counter_recognize_loop, daemon=True)
        self.counter_thread.start()

    def _stop_counter_recognize(self):
        self._log("停止计数器数字识别")
        self.counter_recognizing = False
        # 停止时重置平滑器 + 面板定位，下次启动时从零开始
        if hasattr(self.analyzer, 'counter_smoother') and self.analyzer.counter_smoother:
            self.analyzer.counter_smoother.reset()
        if hasattr(self.analyzer, '_panel_smooth'):
            self.analyzer._panel_smooth = None
        self.btn_start_counter.config(state=tk.NORMAL)
        self.btn_stop_counter.config(state=tk.DISABLED)

    def _counter_recognize_loop(self):
        """计数器数字识别后台循环，约1秒识别一次"""
        self._log("计数器识别线程已启动")
        while self.counter_recognizing:
            try:
                frame = self._get_frame_for_analysis()
                if frame is None:
                    self.result_queue.put(("counter_error", "无法获取图像", None))
                    break

                self._log(f"[Counter] 获取帧: {frame.shape[1]}x{frame.shape[0]}")
                digits, annotated_frame = self.analyzer.recognize_counter(frame)
                self._log(f"[Counter] 识别返回: {digits}")
                self.result_queue.put(("counter_result", digits, annotated_frame))
            except Exception as e:
                logger.exception("计数器识别失败")
                self.result_queue.put(("counter_error", f"识别失败: {e}", None))

            for _ in range(10):
                if not self.counter_recognizing:
                    break
                time.sleep(0.1)
        self._log("计数器识别线程已停止")

    def _start_preview(self):
        # 防止重复启动
        if self.preview_active and self.preview_thread and self.preview_thread.is_alive():
            self._log("预览已在运行中")
            return

        if not self.esp32_connected:
            if not self._start_camera():
                messagebox.showerror(
                    "连接失败",
                    "无法连接到 ESP32 摄像头，请检查:\n"
                    "1. ESP32 是否已上电\n"
                    "2. 电脑与 ESP32 是否在同一网络\n"
                    f"3. IP 地址是否正确 (当前: {CAPTURE_URL})"
                )
                return

        self.preview_active = True
        self.btn_start_preview.config(state=tk.DISABLED)
        self.btn_stop_preview.config(state=tk.NORMAL)
        self._log("开始实时预览...")

        self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

    def _stop_preview(self):
        self.preview_active = False
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=1.5)
        self.preview_thread = None
        self.btn_start_preview.config(state=tk.NORMAL)
        self.btn_stop_preview.config(state=tk.DISABLED)
        self._log("停止实时预览")

    def _preview_loop(self):
        """预览循环 - 优先使用MJPEG流（低延迟），回退到HTTP捕获"""
        stream_urls = [
            f"http://{ESP32_IP}:81/stream",
            f"http://{ESP32_IP}/stream",
        ]
        cap = None
        for url in stream_urls:
            test_cap = cv2.VideoCapture(url)
            if test_cap.isOpened():
                cap = test_cap
                self._log(f"已连接 MJPEG 流（低延迟）: {url}")
                break
            test_cap.release()

        if cap is not None:
            frame_counter = 0
            while self.preview_active:
                ret, frame = cap.read()
                if ret and frame is not None:
                    frame = self._rotate_frame(frame)
                    with self.frame_lock:
                        self.latest_frame = frame
                    # 限频推送到UI：每2帧推送1次，减轻主线程压力
                    frame_counter += 1
                    if frame_counter % 2 == 0:
                        try:
                            self.result_queue.put_nowait(("preview_frame", frame, None))
                        except queue.Full:
                            pass
                else:
                    time.sleep(0.01)
            cap.release()
        else:
            self._log("MJPEG 流不可用，回退到 HTTP 捕获模式（延迟较高）")
            frame_counter = 0
            while self.preview_active:
                try:
                    frame = self.camera.on_demand_capture()
                    if frame is not None:
                        frame = self._rotate_frame(frame)
                        with self.frame_lock:
                            self.latest_frame = frame
                        frame_counter += 1
                        if frame_counter % 2 == 0:
                            try:
                                self.result_queue.put_nowait(("preview_frame", frame, None))
                            except queue.Full:
                                pass
                except Exception as e:
                    logger.error(f"预览循环错误: {e}")
                time.sleep(0.15)

    def _start_obstacle_detect(self):
        if not self._ensure_ready():
            return
        self._log("启动实时障碍物检测...")
        self.obstacle_detecting = True

        # 禁用其他功能按钮，保留停止按钮可用
        for btn in [self.btn_capture, self.btn_calibrate, self.btn_debug]:
            btn.config(state=tk.DISABLED)
        self.btn_start_obstacle.config(state=tk.DISABLED)
        self.btn_stop_obstacle.config(state=tk.NORMAL)
        self.btn_start_preview.config(state=tk.DISABLED)

        self.obstacle_thread = threading.Thread(target=self._obstacle_detect_loop, daemon=True)
        self.obstacle_thread.start()

    def _stop_obstacle_detect(self):
        self._log("停止实时障碍物检测")
        self.obstacle_detecting = False
        self.btn_start_obstacle.config(state=tk.NORMAL)
        self.btn_stop_obstacle.config(state=tk.DISABLED)
        # 恢复其他功能按钮
        for btn in [self.btn_capture, self.btn_calibrate, self.btn_debug]:
            btn.config(state=tk.NORMAL)
        if not self.preview_active:
            self.btn_start_preview.config(state=tk.NORMAL)

    def _obstacle_detect_loop(self):
        """实时障碍物检测后台循环，约1秒检测一次"""
        while self.obstacle_detecting:
            try:
                frame = self._get_frame_for_analysis()
                if frame is None:
                    self.result_queue.put(("error_live", "无法获取图像，请检查ESP32连接", None))
                    break

                base64_img = encode_frame_to_base64(frame)
                if not base64_img:
                    self.result_queue.put(("error_live", "图像编码失败", None))
                    break

                obstacles, annotated_b64 = self.analyzer.detect_obstacles(base64_img)
                report = self.analyzer.analyze_obstacles(obstacles)

                # 解码标注图像用于显示
                annotated_frame = None
                if annotated_b64:
                    img_bytes = base64.b64decode(annotated_b64)
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    annotated_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                self.result_queue.put(("obstacle_result_live", report, annotated_frame))
            except Exception as e:
                logger.exception("实时障碍物检测失败")
                self.result_queue.put(("error_live", f"检测失败: {e}", None))

            # 1秒检测一次，同时支持快速响应停止指令
            for _ in range(10):
                if not self.obstacle_detecting:
                    break
                time.sleep(0.1)

    def _on_capture(self):
        frame = self._get_frame_for_analysis()
        if frame is None:
            messagebox.showwarning("拍照失败", "无法获取图像，请检查ESP32连接")
            return

        path = save_temp_image(frame, save_to_captured=True)
        if path:
            self._log(f"照片已保存: {path}")
            self._set_result_text(f"📷 照片已保存至:\n{path}")
            # 拍照成功，不弹窗，结果已显示在界面和日志中
        else:
            messagebox.showerror("保存失败", "无法保存图片")

    def _on_calibrate(self):
        if not self._ensure_ready():
            return

        known_dist = simpledialog.askfloat(
            "焦距标定", "请输入参考物体到摄像头的实际距离（米）:",
            minvalue=0.01, initialvalue=1.0
        )
        if known_dist is None:
            return
        known_width = simpledialog.askfloat(
            "焦距标定", "请输入参考物体的实际宽度（米）:",
            minvalue=0.01, initialvalue=0.21
        )
        if known_width is None:
            return

        self._log(f"开始标定: 距离={known_dist}m, 宽度={known_width}m")
        self._set_buttons_state(tk.DISABLED)

        def task():
            try:
                frame = self._get_frame_for_analysis()
                if frame is None:
                    self.result_queue.put(("error", "无法获取图像", None))
                    return

                base64_img = encode_frame_to_base64(frame)
                obstacles, _ = self.analyzer.detect_obstacles(base64_img)

                if obstacles and len(obstacles) > 0:
                    first = obstacles[0]
                    x1, y1, x2, y2 = first['bbox']
                    measured_width = x2 - x1

                    new_focal = (measured_width * known_dist) / known_width
                    old_focal = self.analyzer.obstacle_detector.focal_length
                    self.analyzer.obstacle_detector.focal_length = new_focal
                    self.current_focal_length = new_focal

                    msg = (
                        f"标定完成！\n"
                        f"参考物体: {first['class']}\n"
                        f"检测框宽度: {measured_width} 像素\n"
                        f"新焦距: {new_focal:.2f} 像素\n"
                        f"原焦距: {old_focal:.2f} 像素\n\n"
                        f"距离估算已更新，将更加准确。"
                    )
                    self.result_queue.put(("calibrate_result", msg, None))
                else:
                    self.result_queue.put(("error", "未检测到物体，请确保画面中有明显物体", None))
            except Exception as e:
                logger.exception("标定失败")
                self.result_queue.put(("error", f"标定失败: {e}", None))

        threading.Thread(target=task, daemon=True).start()

    def _on_debug(self):
        frame = self._get_frame_for_analysis()
        if frame is None:
            messagebox.showwarning("调试失败", "无法获取图像，请检查ESP32连接")
            return

        info = (
            f"🐞 调试信息:\n"
            f"图像尺寸: {frame.shape[1]} x {frame.shape[0]}\n"
            f"通道数: {frame.shape[2]}\n"
            f"平均亮度: {frame.mean():.1f}\n"
            f"像素值范围: {frame.min()} - {frame.max()}"
        )
        self._log(info.replace("🐞 ", ""))
        self._set_result_text(info)

        # 保存调试图像
        path = save_temp_image(frame, save_to_captured=True)
        if path:
            self._log(f"调试图像已保存: {path}")

        # 异步测试多阈值检测
        self._set_buttons_state(tk.DISABLED)

        def task():
            try:
                from ultralytics import YOLO
                model = YOLO(str(OBSTACLE_YOLO_PATH))
                lines = ["\n不同阈值YOLO检测结果:"]
                for conf in [0.05, 0.1, 0.15, 0.2, 0.25, 0.3]:
                    results = model(frame, conf=conf, verbose=False)[0]
                    count = len(results.boxes)
                    lines.append(f"  阈值 {conf}: {count} 个物体")
                    if count > 0 and conf == 0.05:
                        lines.append("    检测到的物体:")
                        for box in results.boxes:
                            cls_name = results.names[int(box.cls.cpu().numpy()[0])]
                            conf_val = float(box.conf.cpu().numpy()[0])
                            lines.append(f"      - {cls_name}: {conf_val:.3f}")
                self.result_queue.put(("debug_result", "\n".join(lines), None))
            except Exception as e:
                self.result_queue.put(("error", f"调试检测失败: {e}", None))

        threading.Thread(target=task, daemon=True).start()

    def _get_frame_for_analysis(self):
        """获取用于分析的一帧图像"""
        # 优先使用最新预览帧
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()

        # 否则直接获取
        if self.camera:
            frame = self.camera.on_demand_capture()
            if frame is not None:
                return self._rotate_frame(frame)
            frame = self.camera.capture_frame()
            if frame is not None:
                return self._rotate_frame(frame)
        return None

    def _ensure_ready(self):
        if not self.esp32_connected:
            self._log("尝试连接 ESP32...")
            if not self._start_camera():
                messagebox.showerror("连接失败", "无法连接到 ESP32 摄像头")
                return False
        return True

    def _set_buttons_state(self, state):
        if self.obstacle_detecting and state == tk.NORMAL:
            # 实时检测中，不自动恢复被禁用的功能按钮
            return
        for btn in [self.btn_capture,
                    self.btn_calibrate, self.btn_debug]:
            btn.config(state=state)

    def _check_queue(self):
        """主线程定时检查队列，处理后台线程结果（线程安全更新UI）"""
        try:
            while True:
                msg_type, data, extra = self.result_queue.get_nowait()

                if msg_type == "model_loaded":
                    success, info = data, extra
                    self.model_loaded = success
                    if success:
                        self.status_model.config(text="● 模型: 已加载", style='Success.TLabel')
                        self._log(info)
                        # 尝试自动连接ESP32
                        self._start_camera()
                        self.btn_start_preview.config(state=tk.NORMAL)
                    else:
                        self.status_model.config(text="● 模型: 加载失败", style='Error.TLabel')
                        self._log(f"视觉模型加载失败: {info}")
                        messagebox.showwarning(
                            "模型加载失败",
                            f"YOLOv8 加载失败: {info}\n\n"
                            "请检查 ultralytics 是否已安装。"
                        )
                        self.btn_start_preview.config(state=tk.NORMAL)
                    self._set_buttons_state(tk.NORMAL)

                elif msg_type == "preview_frame":
                    # 丢弃队列中所有堆积的旧预览帧，只保留最新的一帧
                    while True:
                        try:
                            nt, nd, ne = self.result_queue.get_nowait()
                            if nt == "preview_frame":
                                data = nd  # 用更新的帧覆盖
                            else:
                                self.result_queue.put((nt, nd, ne))  # 非预览帧放回去
                                break
                        except queue.Empty:
                            break
                    self._update_preview(data)

                elif msg_type == "obstacle_result_live":
                    report, annotated_frame = data, extra
                    self._set_result_text(f"🔍 实时障碍物检测:\n\n{report}")
                    if annotated_frame is not None:
                        self._update_preview(annotated_frame)
                    self._log("实时检测更新")

                elif msg_type == "error_live":
                    self._log(f"实时检测错误: {data}")

                elif msg_type == "counter_result":
                    digits, annotated_frame = data, extra
                    self.status_counter.config(text=f"🔢 计数器: {digits}")
                    self._set_result_text(f"🔢 计数器识别结果: {digits}")
                    if annotated_frame is not None:
                        self._update_preview(annotated_frame)
                    self._log(f"计数器识别: {digits}")

                elif msg_type == "counter_error":
                    self._log(f"计数器识别错误: {data}")

                elif msg_type == "calibrate_result":
                    self._set_result_text(f"⚙ 标定结果:\n\n{data}")
                    self.status_focal.config(text=f"焦距: {self.current_focal_length:.1f}px")
                    self._set_buttons_state(tk.NORMAL)
                    self._log(data.replace("\n", " | "))

                elif msg_type == "debug_result":
                    current = self.result_text.get(1.0, tk.END).strip()
                    self._set_result_text(f"{current}\n{data}")
                    self._set_buttons_state(tk.NORMAL)

                elif msg_type == "error":
                    self._log(f"错误: {data}")
                    self._set_result_text(f"❌ 错误:\n\n{data}")
                    self._set_buttons_state(tk.NORMAL)

        except queue.Empty:
            pass

        self.root.after(100, self._check_queue)

    def _update_preview(self, frame):
        """将 OpenCV 帧更新到预览区"""
        try:
            # BGR -> RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # 等比例缩放
            h, w = rgb.shape[:2]
            scale = min(PREVIEW_MAX_WIDTH / w, PREVIEW_MAX_HEIGHT / h, 1.0)
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w != w or new_h != h:
                rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

            im = Image.fromarray(rgb)
            self._current_photo = ImageTk.PhotoImage(image=im)
            self.preview_label.config(image=self._current_photo, text="")
        except Exception as e:
            logger.error(f"更新预览失败: {e}")

    def _set_result_text(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        logger.info(msg)

    def on_closing(self):
        """窗口关闭时的清理"""
        self.preview_active = False
        self.obstacle_detecting = False
        self.counter_recognizing = False
        if self.obstacle_thread and self.obstacle_thread.is_alive():
            self.obstacle_thread.join(timeout=2.0)
        if self.counter_thread and self.counter_thread.is_alive():
            self.counter_thread.join(timeout=2.0)
        if self.camera:
            try:
                self.camera.stop()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ESP32VisionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
