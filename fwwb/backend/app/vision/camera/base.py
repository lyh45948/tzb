"""摄像头抽象基类

定义统一接口供 VisionService 调用，屏蔽 USB / ESP32-CAM 等差异。
"""
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class BaseCamera(ABC):
    """摄像头抽象基类

    所有具体实现需保证：
    - start/stop 线程安全、可幂等调用
    - capture_frame 返回最新一帧的副本（None 表示当前不可用）
    """

    @abstractmethod
    def start(self) -> bool:
        """启动摄像头采集（同步等待初始化完成）"""

    @abstractmethod
    def stop(self) -> bool:
        """停止采集，释放资源"""

    @abstractmethod
    def capture_frame(self) -> Optional[np.ndarray]:
        """获取当前最新一帧的副本(BGR ndarray)，未就绪返回 None"""

    @abstractmethod
    def is_running(self) -> bool:
        """是否正在采集"""

    def on_demand_capture(self) -> Optional[np.ndarray]:
        """按需同步抓取一帧。默认实现回退到 capture_frame；
        ESP32 等支持单帧 HTTP 抓取的实现可重写以绕过后台循环。
        """
        return self.capture_frame()
