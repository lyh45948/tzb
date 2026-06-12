# backend/training — 视觉模型训练代码

整合自原 `sjsb/szsb` 与 `sjsb/szjs`。仅保留训练脚本与最小目录结构，**不包含训练数据集、模型权重和日志**（已在 `.gitignore` 中排除）。

## 目录

| 子目录 | 说明 |
|--------|------|
| `szsb/` | CRNN(CNN+BiLSTM+CTC) + YOLO 数字面板检测训练（生产线路） |
| `szjs/` | 早期单字符 CNN 分类方法（已被 CRNN 取代，归档保留） |

## szsb 训练流程

1. **采集训练样本** — 使用 `backend/tools/esp32_viewer/` 抓取计数器图像到 `datasets/digit_panel/images/`。
2. **YOLOv8s 数字面板检测训练**：
   ```bash
   cd backend/training/szsb
   yolo detect train data=datasets/digit_panel/data.yaml model=yolov8s.pt epochs=100 imgsz=320
   ```
   产物 `runs/detect/.../weights/best.pt` 重命名为 `digit_panel_yolov8s.pt`，复制到 `backend/models/`。

3. **CRNN v2 训练（推荐）**：
   ```bash
   python train_crnn_v2.py
   ```
   产物 `checkpoints_v2/best_crnn.pth` 复制到 `backend/models/best_crnn.pth`。

4. **验证流水线**：
   ```bash
   python test_yolo_crnn_pipeline.py
   ```

CRNN v3 使用固定 ROI 而非 YOLO bbox，适配固定机位场景，保留供研究。

## szjs 归档说明

`szjs/` 是早期把数字面板分割为 6 个单元格、每个单元格用 11 类 CNN 分类的方法，端到端准确率不如 CRNN。脚本仍可运行，但生产环境使用 szsb/CRNN 路线。

## 输出与生产环境的衔接

- 训练得到的 `*.pt` / `*.pth` **复制**到 `backend/models/`
- 路径在 `backend/.env` 中配置：`VISION_OBSTACLE_MODEL` / `VISION_DIGIT_PANEL_MODEL` / `VISION_CRNN_MODEL`
- 重启 backend 后，`VisionService` 通过 `ImageAnalyzer` 加载新模型
