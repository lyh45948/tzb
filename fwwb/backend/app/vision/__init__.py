"""
视觉识别模块

将原 sjsb 项目的视觉能力整合为后端服务：
- engine: 推理引擎（障碍物检测、计数器识别、APF 避障）
- camera: 摄像头抽象层（USB / ESP32-CAM）
- vision_service: 编排器（摄像头 + 引擎 + WebSocket 广播 + 持久化）

依赖 torch / ultralytics / opencv-python，已在 requirements.txt 中声明为强制依赖。
"""
