"""USB / V4L2 本地摄像头

由 OpenCV `cv2.VideoCapture` 后台线程持续抓帧，主线程通过 capture_frame
取最新副本。从 sjsb/vision_only/src/utils/Camera.py 改造：
- 去除单例与 ConfigManager 依赖（参数由构造注入）
- 去除 cv2.imshow / waitKey（服务端 headless）
- 重命名 start_camera/stop_camera 为 start/stop，符合 BaseCamera
"""
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from app.vision.camera.base import BaseCamera

logger = logging.getLogger(__name__)


class USBCamera(BaseCamera):
    """本地 USB / V4L2 摄像头，OpenCV VideoCapture 实现"""

    def __init__(self, camera_index: int = 0, frame_width: int = 320,
                 frame_height: int = 240, fps: int = 1):
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps

        self.cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

    def _open_cap(self) -> bool:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            logger.warning(f"USB 摄像头索引 {self.camera_index} 打开失败，尝试 0/1 备选")
            for alt in (0, 1):
                if alt == self.camera_index:
                    continue
                self.cap = cv2.VideoCapture(alt)
                if self.cap.isOpened():
                    self.camera_index = alt
                    logger.info(f"USB 摄像头切换到索引 {alt}")
                    break
        if not self.cap.isOpened():
            logger.error("USB 摄像头无法打开任何索引")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        # 测试一帧
        ret, _ = self.cap.read()
        if not ret:
            logger.error("USB 摄像头打开成功但无法读取首帧")
            return False
        return True

    def _capture_loop(self):
        if not self._open_cap():
            self._running = False
            return

        logger.info(f"USB 摄像头采集线程已启动: idx={self.camera_index} "
                    f"{self.frame_width}x{self.frame_height}@{self.fps}fps")

        failed = 0
        max_failed = 5
        sleep_interval = max(1.0 / max(self.fps, 1), 0.0)

        while self._running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    failed += 1
                    logger.warning(f"USB 读取失败 {failed}/{max_failed}")
                    if failed >= max_failed:
                        logger.error("USB 连续失败，重新初始化")
                        if not self._open_cap():
                            self._running = False
                            break
                        failed = 0
                    time.sleep(0.1)
                    continue
                failed = 0
                with self._frame_lock:
                    self._latest_frame = frame
                if sleep_interval > 0:
                    time.sleep(sleep_interval)
            except Exception as e:
                logger.error(f"USB 采集异常: {e}")
                failed += 1
                if failed >= max_failed:
                    self._running = False
                    break

        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("USB 摄像头采集线程已结束")

    def start(self) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.debug("USB 摄像头线程已在运行")
                return self._running
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True,
                                            name='USBCameraThread')
            self._thread.start()
            # 等待首帧
            for _ in range(30):
                if self._latest_frame is not None:
                    return True
                time.sleep(0.1)
            logger.warning("USB 摄像头启动 3s 内未拿到首帧")
            return self._running

    def stop(self) -> bool:
        with self._lock:
            self._running = False
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._thread = None
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            return True

    def capture_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()
