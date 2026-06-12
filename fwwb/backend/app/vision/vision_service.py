"""
视觉识别服务

整合自原 sjsb 项目，作为 backend 的后台服务运行：
- 管理摄像头（USB / ESP32-CAM / none）
- 持有唯一的 ImageAnalyzer 实例（YOLO 障碍物 + YOLO 数字面板 + CRNN 计数器）
- 后台循环按间隔捕帧、推理、更新内存缓存、WebSocket 广播、限流持久化

所有外部访问路径（routes / dashboard）通过 registry.get_service('vision_service') 获得。
"""
import base64
import os
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from app.utils.logger import get_logger
from app.vision.camera.base import BaseCamera
from app.vision.camera.esp32_camera import ESP32Camera
from app.vision.camera.usb_camera import USBCamera
from app.vision.engine.image_analyzer import ImageAnalyzer

logger = get_logger('vision_service')


class VisionService:
    """视觉识别服务 —— 编排摄像头 + 引擎 + 缓存 + 广播 + 持久化"""

    CAMERA_NONE = 'none'
    CAMERA_USB = 'usb'
    CAMERA_ESP32 = 'esp32'

    def __init__(self, app, config, websocket_service=None, data_service=None):
        self.app = app
        self.config = config
        self.websocket_service = websocket_service
        self.data_service = data_service

        # 配置
        self.enabled = getattr(config, 'VISION_ENABLED', False)
        self.camera_type = getattr(config, 'VISION_CAMERA_TYPE', self.CAMERA_NONE).lower()
        self.device_id = 'vision_backend'  # 后端自身视觉数据的设备标识

        # 模型路径解析
        models_dir = getattr(config, 'VISION_MODELS_DIR', None)
        self.obstacle_model_path = self._resolve_model(
            getattr(config, 'VISION_OBSTACLE_MODEL', 'yolo11s.pt'), models_dir)
        self.digit_panel_model_path = self._resolve_model(
            getattr(config, 'VISION_DIGIT_PANEL_MODEL', 'digit_panel_yolov8s.pt'), models_dir)
        self.crnn_model_path = self._resolve_model(
            getattr(config, 'VISION_CRNN_MODEL', 'best_crnn.pth'), models_dir)

        # 推理与摄像头参数
        self.device_pref = getattr(config, 'VISION_DEVICE', 'auto')
        self.obstacle_conf = float(getattr(config, 'VISION_OBSTACLE_CONF', 0.05))
        self.counter_conf = float(getattr(config, 'VISION_COUNTER_CONF', 0.3))
        self.frame_width = int(getattr(config, 'VISION_FRAME_WIDTH', 320))
        self.frame_height = int(getattr(config, 'VISION_FRAME_HEIGHT', 240))
        self.fps = int(getattr(config, 'VISION_FPS', 1))
        self.esp32_ip = getattr(config, 'VISION_ESP32_IP', '192.168.137.213')
        self.esp32_path = getattr(config, 'VISION_ESP32_CAPTURE_PATH', '/capture')
        self.esp32_timeout = float(getattr(config, 'VISION_ESP32_TIMEOUT', 3.0))
        self.camera_index = int(getattr(config, 'VISION_CAMERA_INDEX', 0))
        self.obstacle_interval = float(getattr(config, 'VISION_OBSTACLE_INTERVAL', 1.0))
        self.counter_interval = float(getattr(config, 'VISION_COUNTER_INTERVAL', 1.0))
        self.persist_interval = float(getattr(config, 'VISION_PERSIST_INTERVAL', 5.0))
        self.persist_image = bool(getattr(config, 'VISION_PERSIST_IMAGE', False))

        # 运行时状态
        self.analyzer: Optional[ImageAnalyzer] = None
        self.camera: Optional[BaseCamera] = None
        self._obstacle_thread: Optional[threading.Thread] = None
        self._counter_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # 最新结果缓存
        self._obstacles_cache: Optional[Dict] = None
        self._counter_cache: Optional[Dict] = None
        self._cache_lock = threading.Lock()

        # 持久化限流
        self._last_persist_obstacle = 0.0
        self._last_persist_counter = 0.0

        # 模型可用性
        self._models_loaded = False

    # ------------ 初始化与生命周期 ------------

    def _resolve_model(self, name: Optional[str], models_dir: Optional[str]) -> Optional[str]:
        if not name:
            return None
        if os.path.isabs(name):
            return name
        if models_dir:
            return os.path.join(models_dir, name)
        return name

    def _build_camera(self) -> Optional[BaseCamera]:
        if self.camera_type == self.CAMERA_NONE:
            logger.info("视觉摄像头类型 = none，仅作为外部数据接收端运行")
            return None
        if self.camera_type == self.CAMERA_USB:
            return USBCamera(
                camera_index=self.camera_index,
                frame_width=self.frame_width,
                frame_height=self.frame_height,
                fps=self.fps,
            )
        if self.camera_type == self.CAMERA_ESP32:
            return ESP32Camera(
                esp32_ip=self.esp32_ip,
                capture_path=self.esp32_path,
                fps=self.fps,
                timeout=self.esp32_timeout,
            )
        logger.warning(f"未知的 VISION_CAMERA_TYPE={self.camera_type}，按 none 处理")
        return None

    def init(self) -> bool:
        """加载模型、构建摄像头。失败不会抛异常，返回 False"""
        if not self.enabled:
            logger.info("VisionService 未启用 (VISION_ENABLED=false)")
            return False

        logger.info("加载视觉模型...")
        self.analyzer = ImageAnalyzer(
            obstacle_model_path=self.obstacle_model_path,
            digit_panel_model_path=self.digit_panel_model_path,
            crnn_model_path=self.crnn_model_path,
            device=self.device_pref,
            obstacle_conf=self.obstacle_conf,
            counter_conf=self.counter_conf,
        )
        self._models_loaded = self.analyzer.init()
        if not self._models_loaded:
            logger.warning("视觉模型全部加载失败，VisionService 将仅支持外部 POST 数据转发")

        try:
            self.camera = self._build_camera()
        except Exception as e:
            logger.error(f"摄像头构建失败: {e}")
            self.camera = None
        return True

    def start(self) -> bool:
        if not self.enabled:
            return False
        with self._lock:
            if self._running:
                return True
            self._running = True

            # 启动摄像头
            if self.camera is not None:
                ok = self.camera.start()
                if not ok:
                    logger.warning("摄像头启动失败，后台采集循环将以按需模式运行")

            # 仅当模型加载且摄像头存在时才启动后台循环
            if self._models_loaded and self.camera is not None:
                if self.obstacle_interval > 0 and self.analyzer.obstacle_detector is not None:
                    self._obstacle_thread = threading.Thread(
                        target=self._obstacle_loop, daemon=True, name='VisionObstacleLoop')
                    self._obstacle_thread.start()
                    logger.info(f"障碍物检测后台循环已启动 (间隔 {self.obstacle_interval}s)")
                if self.counter_interval > 0 and self.analyzer.counter_crnn is not None:
                    self._counter_thread = threading.Thread(
                        target=self._counter_loop, daemon=True, name='VisionCounterLoop')
                    self._counter_thread.start()
                    logger.info(f"计数器识别后台循环已启动 (间隔 {self.counter_interval}s)")
        return True

    def stop(self) -> bool:
        with self._lock:
            self._running = False
            if self.camera is not None:
                try:
                    self.camera.stop()
                except Exception as e:
                    logger.warning(f"摄像头停止异常: {e}")
            for t in (self._obstacle_thread, self._counter_thread):
                if t is not None and t.is_alive():
                    t.join(timeout=2.0)
            self._obstacle_thread = None
            self._counter_thread = None
        return True

    # ------------ 后台循环 ------------

    def _obstacle_loop(self):
        while self._running:
            t0 = time.time()
            try:
                self.capture_and_detect_obstacles()
            except Exception as e:
                logger.error(f"障碍物循环异常: {e}")
            elapsed = time.time() - t0
            sleep_left = max(0.0, self.obstacle_interval - elapsed)
            time.sleep(sleep_left)

    def _counter_loop(self):
        while self._running:
            t0 = time.time()
            try:
                self.capture_and_recognize_counter()
            except Exception as e:
                logger.error(f"计数器循环异常: {e}")
            elapsed = time.time() - t0
            sleep_left = max(0.0, self.counter_interval - elapsed)
            time.sleep(sleep_left)

    # ------------ 一次性推理（路由直接调用） ------------

    def capture_and_detect_obstacles(self, frame_override: Optional[np.ndarray] = None
                                     ) -> Dict:
        """捕一帧 + 障碍物检测 + APF + 缓存 + 广播 + 限流写库"""
        if self.analyzer is None or self.analyzer.obstacle_detector is None:
            return {'success': False, 'message': '障碍物模型未加载'}

        frame = frame_override
        if frame is None:
            frame = self._grab_frame()
        if frame is None:
            return {'success': False, 'message': '无可用帧'}

        obstacles, annotated = self.analyzer.detect_obstacles_from_frame(frame)
        apf = self.analyzer.compute_apf_avoidance(
            obstacles, frame_width=frame.shape[1], frame_height=frame.shape[0])

        annotated_b64 = self._encode_jpg_b64(annotated)
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        payload = {
            'device_id': self.device_id,
            'obstacles': self._serialize_obstacles(obstacles),
            'count': len(obstacles),
            'apf': self._serialize_apf(apf),
            'annotated_image': annotated_b64,
            'timestamp': timestamp_ms,
        }

        with self._cache_lock:
            self._obstacles_cache = payload

        self._broadcast('obstacles', payload)
        self._maybe_persist_obstacle(payload)
        return {'success': True, 'data': payload}

    def capture_and_recognize_counter(self, frame_override: Optional[np.ndarray] = None
                                      ) -> Dict:
        if self.analyzer is None or self.analyzer.counter_crnn is None:
            return {'success': False, 'message': '计数器模型未加载'}

        frame = frame_override
        if frame is None:
            frame = self._grab_frame()
        if frame is None:
            return {'success': False, 'message': '无可用帧'}

        digits, annotated, meta = self.analyzer.recognize_counter(frame)
        annotated_b64 = self._encode_jpg_b64(annotated)
        timestamp_ms = int(datetime.now().timestamp() * 1000)
        payload = {
            'device_id': self.device_id,
            'digits': digits,
            'raw': meta.get('raw'),
            'smooth_status': meta.get('smooth_status'),
            'panel_bbox': meta.get('panel_bbox'),
            'annotated_image': annotated_b64,
            'timestamp': timestamp_ms,
        }

        with self._cache_lock:
            self._counter_cache = payload

        self._broadcast('counter', payload)
        self._maybe_persist_counter(payload)
        return {'success': True, 'data': payload}

    # ------------ 外部 POST 接收 ------------

    def receive_external_obstacles(self, data: Dict) -> None:
        """vision_routes /vision/obstacles POST 入口直接更新缓存并广播"""
        with self._cache_lock:
            self._obstacles_cache = data
        self._broadcast('obstacles', data)

    def receive_external_counter(self, data: Dict) -> None:
        with self._cache_lock:
            self._counter_cache = data
        self._broadcast('counter', data)

    # ------------ 状态/查询 ------------

    def get_latest_obstacles(self) -> Optional[Dict]:
        with self._cache_lock:
            return self._obstacles_cache

    def get_latest_counter(self) -> Optional[Dict]:
        with self._cache_lock:
            return self._counter_cache

    def get_status(self) -> Dict:
        return {
            'enabled': self.enabled,
            'cameraType': self.camera_type,
            'cameraRunning': self.camera.is_running() if self.camera is not None else False,
            'modelsLoaded': self._models_loaded,
            'obstacleModel': bool(self.analyzer and self.analyzer.obstacle_detector),
            'panelModel': bool(self.analyzer and self.analyzer.yolo_panel_detector),
            'counterModel': bool(self.analyzer and self.analyzer.counter_crnn),
            'obstacleLooping': self._obstacle_thread is not None and self._obstacle_thread.is_alive(),
            'counterLooping': self._counter_thread is not None and self._counter_thread.is_alive(),
            'paths': {
                'obstacle': self.obstacle_model_path,
                'panel': self.digit_panel_model_path,
                'crnn': self.crnn_model_path,
            },
        }

    # ------------ 工具方法 ------------

    def _grab_frame(self) -> Optional[np.ndarray]:
        if self.camera is None:
            return None
        frame = self.camera.capture_frame()
        if frame is None:
            # 后台循环未启动时回退到同步抓取
            frame = self.camera.on_demand_capture()
        return frame

    @staticmethod
    def _encode_jpg_b64(frame: np.ndarray) -> Optional[str]:
        try:
            ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                return None
            return base64.b64encode(buf).decode('utf-8')
        except Exception as e:
            logger.warning(f"JPG 编码失败: {e}")
            return None

    @staticmethod
    def _serialize_obstacles(obstacles):
        out = []
        for obs in obstacles:
            out.append({
                'class': obs.get('class'),
                'class_id': obs.get('class_id'),
                'confidence': float(obs.get('confidence') or 0.0),
                'bbox': obs.get('bbox'),
                'distance': obs.get('distance'),
                'dangerous': bool(obs.get('dangerous', False)),
            })
        return out

    @staticmethod
    def _serialize_apf(apf: Dict) -> Dict:
        # APF 内部含 tuple 等不可 JSON 化字段，做一次清洗
        return {
            'recommendation': apf.get('recommendation'),
            'danger_level': apf.get('danger_level'),
            'nearest_distance': apf.get('nearest_distance'),
            'nearest_class': apf.get('nearest_class'),
            'nearest_position': apf.get('nearest_position'),
            'steer_angle': apf.get('steer_angle'),
            'speed_ratio': apf.get('speed_ratio'),
            'target_heading': apf.get('target_heading'),
            'obstacle_count': apf.get('obstacle_count'),
        }

    def _broadcast(self, vision_type: str, data: Dict) -> None:
        if self.websocket_service is None:
            return
        try:
            # 广播时去掉大字段避免 ws 包过大
            slim = {k: v for k, v in data.items() if k != 'annotated_image'}
            self.websocket_service.broadcast_vision_data(vision_type, slim)
        except Exception as e:
            logger.debug(f"广播视觉数据失败: {e}")

    # ------------ 持久化（限流） ------------

    def _maybe_persist_obstacle(self, payload: Dict):
        if self.persist_interval <= 0:
            return
        now = time.time()
        if now - self._last_persist_obstacle < self.persist_interval:
            return
        self._last_persist_obstacle = now
        self._save_vision_result('obstacle', payload)

    def _maybe_persist_counter(self, payload: Dict):
        if self.persist_interval <= 0:
            return
        now = time.time()
        if now - self._last_persist_counter < self.persist_interval:
            return
        self._last_persist_counter = now
        self._save_vision_result('counter', payload)

    def _save_vision_result(self, result_type: str, payload: Dict):
        try:
            from app import db
            from app.models.vision_result import VisionResult
        except Exception as e:
            logger.debug(f"持久化模块不可用: {e}")
            return
        try:
            with self.app.app_context():
                ts_ms = payload.get('timestamp') or int(datetime.now().timestamp() * 1000)
                ts = datetime.fromtimestamp(ts_ms / 1000)
                row = VisionResult(
                    device_id=payload.get('device_id', self.device_id),
                    timestamp=ts,
                    result_type=result_type,
                    annotated_image=payload.get('annotated_image') if self.persist_image else None,
                )
                if result_type == 'obstacle':
                    apf = payload.get('apf') or {}
                    row.obstacles = payload.get('obstacles')
                    row.obstacle_count = payload.get('count')
                    row.nearest_distance = apf.get('nearest_distance')
                    row.nearest_class = apf.get('nearest_class')
                    row.danger_level = apf.get('danger_level')
                    row.steer_angle = apf.get('steer_angle')
                    row.speed_ratio = apf.get('speed_ratio')
                else:
                    row.counter_digits = payload.get('digits')
                    row.counter_raw = payload.get('raw')
                    row.counter_smooth_status = payload.get('smooth_status')
                db.session.add(row)
                db.session.commit()
        except Exception as e:
            logger.warning(f"保存视觉结果失败 ({result_type}): {e}")
