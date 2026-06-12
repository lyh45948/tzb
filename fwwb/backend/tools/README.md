# backend/tools — 视觉调试与采集工具

整合自原 `sjsb` 项目，作为本地调试工具保留，**不属于 backend 运行时**。

## 目录

| 子目录 | 说明 |
|--------|------|
| `esp32_viewer/` | ESP32-CAM 图像查看器（CLI + Tkinter GUI），用于本机预览 + 标定 + 抓样 |
| `openmv/` | OpenMV H7 摄像头工具（USB 串口替代 WiFi 路线） |
| `legacy_vision_only/` | 原 `vision_only/` 整体备份，保留 `main.py` / `download_model.py` 等独立入口供对照参考 |

## 注意

- `esp32_viewer/capture_still.py` 和 `gui.py` 原本依赖 `vision_only.src.utils.VL.ImageAnalyzer`。整合到 backend 后，等价能力已在 `backend/app/vision/engine/image_analyzer.py` 提供。如需直接运行原脚本，请保留 `legacy_vision_only/` 中的 `src/utils/` 即可（这些工具走独立 `sys.path`）。
- `openmv/openmv_camera.py` 是运行在 OpenMV 微控制器上的固件脚本，不在 PC 端 Python 中运行。
- 这些工具不会随 `python main.py` 启动，仅在开发/调试阶段手动运行。
