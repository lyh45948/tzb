"""摄像头抽象层"""
from app.vision.camera.base import BaseCamera
from app.vision.camera.usb_camera import USBCamera
from app.vision.camera.esp32_camera import ESP32Camera

__all__ = ['BaseCamera', 'USBCamera', 'ESP32Camera']
