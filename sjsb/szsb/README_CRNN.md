# CRNN + CTC 端到端数字序列识别

## 文件说明

| 文件 | 说明 |
|------|------|
| `train_crnn.py` | 完整训练脚本（数据读取、预处理、CRNN模型、CTC训练循环、推理测试） |

## 依赖安装

```bash
pip install torch torchvision opencv-python numpy tqdm
```

> 本脚本默认使用 GPU（CUDA），若未安装 CUDA 会自动回退到 CPU。

## 数据路径

- 原始图片：`/home/tzb/tzb/sjsb/captured_images`（或通过 `--img_dir` 指定）
- YOLO 标注：`/home/tzb/tzb/sjsb/annotations`（或通过 `--ann_dir` 指定）

标注格式：`class_id x_center y_center width height`（每行一个框，脚本支持多框并按 x_center 排序拼接序列）。

## 运行命令

```bash
cd /home/tzb/tzb/sjsb/szsb

# 基础训练（默认参数）
python train_crnn.py

# 自定义训练（更多轮数、更大batch）
python train_crnn.py --epochs 300 --batch_size 64 --lr 5e-4

# 从 checkpoint 恢复训练
python train_crnn.py --resume ./checkpoints/last_crnn.pth
```

## 主要参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--img_dir` | `/home/tzb/tzb/sjsb/captured_images` | 图像目录 |
| `--ann_dir` | `/home/tzb/tzb/sjsb/annotations` | 标注目录 |
| `--save_dir` | `./checkpoints` | 模型保存目录 |
| `--img_h` | 32 | 输入图像高度 |
| `--img_w` | 128 | 输入图像宽度 |
| `--hidden_size` | 256 | BiLSTM 隐藏层维度 |
| `--batch_size` | 32 | 批次大小 |
| `--epochs` | 200 | 训练轮数 |
| `--lr` | 1e-3 | 初始学习率 |
| `--val_ratio` | 0.2 | 验证集比例 |
| `--num_workers` | 0 | 数据加载线程数（Windows 建议保持 0） |

## 输出文件

训练结束后会在 `--save_dir` 目录生成：

- `best_crnn.pth`：验证准确率最高的模型权重
- `last_crnn.pth`：每 20 epoch 保存的进度快照
- `inference_results.txt`：验证集全部推理结果（GT vs Pred）
