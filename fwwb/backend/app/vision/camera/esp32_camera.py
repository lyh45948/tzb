"""ESP32-CAM HTTP 摄像头

后台线程定时调用 ESP32-CAM 的 /capture 端点，缓存最新帧。
从 sjsb/esp32_viewer/capture_still.py 的 ESP32CameraStream 改造：
- 去除单例
- 改为构造参数注入 IP/path/fps/timeout
- 提供 on_demand_capture（同步 GET，不依赖后台线程）
"""
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np
import requests

from app.vision.camera.base import BaseCamera

logger = logging.getLogger(__name__)


class ESP32Camera(BaseCamera):
    """ESP32-CAM HTTP /capture 抓取实现"""

    def __init__(self, esp32_ip: str = '192.168.137.213',
                 capture_path: str = '/capture',
                 fps: int = 1,
                 timeout: float = 3.0):
        self.esp32_ip = esp32_ip
        self.capture_path = capture_path
        self.fps = max(1, int(fps))
        self.timeout = timeout

        self._url = f"http://{esp32_ip}{capture_path}"
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

    def _fetch_one(self) -> Optional[np.ndarray]:
        try:
            resp = requests.get(self._url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"ESP32 /capture 返回 {resp.status_code}")
                return None
            arr = np.frombuffer(resp.content, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return img
        except requests.exceptions.Timeout:
            logger.warning("ESP32 /capture 超时")
        except Exception as e:
            logger.warning(f"ESP32 /capture 失败: {e}")
        return None

    def _capture_loop(self):
        logger.info(f"ESP32 摄像头采集线程启动: {self._url} @{self.fps}fps")
        consecutive_errors = 0
        max_consecutive_errors = 10
        sleep_interval = 1.0 / self.fps
        while self._running:
            img = self._fetch_one()
            if img is None:
                consecutive_errors += 1
                if consecutive_errors > max_consecutive_errors:
                    logger.error("ESP32 连续失败，停止采集线程")
                    self._running = False
                    break
            else:
                consecutive_errors = 0
                with self._frame_lock:
                    self._latest_frame = img
            time.sleep(sleep_interval)
        logger.info("ESP32 摄像头采集线程已退出")

    def start(self) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self._running
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True,
                                            name='ESP32CameraThread')
            self._thread.start()
            # 同步等首帧（最多 timeout * 2）
            deadline = time.time() + max(self.timeout * 2, 5.0)
            while time.time() < deadline:
                if self._latest_frame is not None:
                    return True
                time.sleep(0.1)
                if not self._running:
                    return False
            logger.warning("ESP32 摄像头启动后未在超时内拿到首帧，将继续后台尝试")
            return self._running

    def stop(self) -> bool:
        with self._lock:
            self._running = False
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=3.0)
            self._thread = None
            return True

    def capture_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def on_demand_capture(self) -> Optional[np.ndarray]:
        """同步 GET 一次。即使后台线程没启动也能用。"""
        img = self._fetch_one()
        if img is not None:
            with self._frame_lock:
                self._latest_frame = img
            return img.copy()
        return None

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()
