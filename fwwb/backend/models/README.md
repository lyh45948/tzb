# 视觉模型存放目录

此目录存放视觉识别模型权重文件。**所有 `*.pt` / `*.pth` / `*.onnx` / `*.whl` 不入版本控制**（已在 `.gitignore` 中排除）。

## 必备模型

| 文件名 | 用途 | 默认路径(env 变量) |
|--------|------|--------------------|
| `yolo11s.pt` | 障碍物检测（YOLOv11s, COCO 80 类） | `VISION_OBSTACLE_MODEL` |
| `digit_panel_yolov8s.pt` | 数字面板检测（YOLOv8s 微调） | `VISION_DIGIT_PANEL_MODEL` |
| `best_crnn.pth` | 数字序列识别（CRNN+CTC，对应 sjsb v2 训练产物） | `VISION_CRNN_MODEL` |

## 来源

这些模型由 `backend/training/` 下的训练脚本产生：
- `training/szsb/train_crnn_v2.py` → `best_crnn.pth`
- `training/szsb/datasets/digit_panel/` 的 YOLOv8s 训练 → `digit_panel_yolov8s.pt`
- `yolo11s.pt` 来自 ultralytics 官方权重

## 路径解析规则

`config.py` 中的 `VISION_*_MODEL` 默认是相对路径，相对于 `VISION_MODELS_DIR`（默认 `backend/models/`）。
配置绝对路径会原样使用。模型文件不存在时仅打印 warning 并禁用对应能力，**不会阻塞 backend 启动**。

## 启用视觉服务

```bash
# 在 .env 中添加
VISION_ENABLED=true
VISION_CAMERA_TYPE=esp32          # none / usb / esp32
VISION_ESP32_IP=192.168.137.213
VISION_OBSTACLE_MODEL=yolo11s.pt
VISION_DIGIT_PANEL_MODEL=digit_panel_yolov8s.pt
VISION_CRNN_MODEL=best_crnn.pth
```
