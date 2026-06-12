#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRNN + CTC 端到端数字序列识别训练脚本
======================================
用于识别数码管计数器图像中的数字序列（0~200）。
数据格式：YOLO 风格 .txt 标注（class_id x_center y_center width height）。

运行示例：
    python train_crnn.py --img_dir ../captured_images --ann_dir ../annotations
    python train_crnn.py --img_dir ../captured_images --ann_dir ../annotations --epochs 300 --batch_size 64
"""

import os
import sys
import argparse
import random
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SZSB_ROOT = Path(__file__).resolve().parent
import cv2
from typing import List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam
from torch.optim.lr_scheduler import StepLR

try:
    from tqdm import tqdm
except ImportError:
    # 若未安装 tqdm，使用简易占位符
    def tqdm(iterable, **kwargs):
        return iterable

# ==================== 全局常量 ====================
CHARS = '0123456789'
NUM_CLASSES = len(CHARS) + 1   # 10 个数字 + 1 个 CTC blank
BLANK_INDEX = len(CHARS)       # blank 索引固定为 10


# ==================== 工具函数 ====================
def set_seed(seed: int = 42):
    """固定随机种子，保证实验可复现。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        # 保证卷积等操作确定性
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def ctc_decode(preds: np.ndarray, blank: int = BLANK_INDEX) -> List[str]:
    """
    贪婪 CTC 解码：去 blank、去连续重复。
    :param preds: (T, B) 的 numpy 数组，每个元素为类别索引
    :return: 长度为 B 的字符串列表
    """
    T, B = preds.shape
    results = []
    for b in range(B):
        seq = preds[:, b].tolist()
        out = []
        prev = -1
        for s in seq:
            if s != blank and s != prev:
                out.append(str(s))
            prev = s
        results.append(''.join(out))
    return results


def preprocess_image(img: np.ndarray,
                     bbox: List[float],
                     img_size: Tuple[int, int] = (32, 128),
                     augment: bool = False) -> np.ndarray:
    """
    图像预处理：裁剪 ROI → resize → pad → 归一化。
    :param img: BGR 原图 (H, W, 3)
    :param bbox: YOLO 格式 [x_center, y_center, width, height]（归一化）
    :param img_size: (target_h, target_w)
    :param augment: 是否做训练增强
    :return: float32 数组 (target_h, target_w)，值域约 [-1, 1]
    """
    target_h, target_w = img_size
    img_h, img_w = img.shape[:2]

    # ---- 1. YOLO 归一化坐标 → 像素坐标 ----
    x_c, y_c, w, h = bbox
    x1 = int((x_c - w / 2) * img_w)
    y1 = int((y_c - h / 2) * img_h)
    x2 = int((x_c + w / 2) * img_w)
    y2 = int((y_c + h / 2) * img_h)

    # 轻微外扩 5%，防止数字边缘被裁掉
    margin_x = max(1, int((x2 - x1) * 0.05))
    margin_y = max(1, int((y2 - y1) * 0.05))
    x1 = max(0, x1 - margin_x)
    y1 = max(0, y1 - margin_y)
    x2 = min(img_w, x2 + margin_x)
    y2 = min(img_h, y2 + margin_y)

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        # 若出现退化，返回空白图
        return np.zeros((target_h, target_w), dtype=np.float32)

    # ---- 2. 灰度化 ----
    if len(roi.shape) == 3:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # ---- 3. 训练增强（在 uint8 阶段做，避免伪影）----
    if augment:
        # 随机亮度
        if random.random() < 0.5:
            beta = random.randint(-40, 40)
            roi = cv2.convertScaleAbs(roi, beta=beta)
        # 随机对比度
        if random.random() < 0.5:
            alpha = random.uniform(0.7, 1.3)
            roi = cv2.convertScaleAbs(roi, alpha=alpha)
        # 轻微高斯噪声
        if random.random() < 0.3:
            noise = np.random.normal(0, 3, roi.shape).astype(np.float32)
            roi = np.clip(roi.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # ---- 4. 保持宽高比 resize，高度固定 ----
    rh = target_h / roi.shape[0]
    new_w = int(roi.shape[1] * rh)
    # 若超出目标宽度，强行压到目标宽度（罕见，因 3 位数字 resize 后约 60 px）
    if new_w > target_w:
        new_w = target_w
    roi = cv2.resize(roi, (new_w, target_h), interpolation=cv2.INTER_AREA)

    # ---- 5. 居中 pad 到固定宽度 ----
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    start_x = (target_w - new_w) // 2
    canvas[:, start_x:start_x + new_w] = roi.astype(np.float32)

    # ---- 6. 归一化到 [-1, 1] ----
    canvas = (canvas / 255.0 - 0.5) / 0.5
    return canvas


# ==================== Dataset ====================
class DigitDataset(Dataset):
    def __init__(self,
                 img_dir: str,
                 ann_dir: str,
                 samples: List[dict],
                 img_size: Tuple[int, int] = (32, 128),
                 no_crop: bool = False,
                 augment: bool = False):
        super().__init__()
        self.img_dir = img_dir
        self.ann_dir = ann_dir
        self.samples = samples
        self.img_size = img_size
        self.no_crop = no_crop
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        sample = self.samples[idx]
        img_path = os.path.join(self.img_dir, sample['img'])
        ann_path = os.path.join(self.ann_dir, sample['ann'])

        img = cv2.imread(img_path)
        if img is None:
            raise RuntimeError(f"无法读取图像: {img_path}")

        # ---- 读取 YOLO 标注（支持多框，按 x_center 排序后拼接序列）----
        bboxes = []   # [(class_id, [x, y, w, h]), ...]
        with open(ann_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 5:
                    continue
                cls_id = int(parts[0])
                bbox = [float(p) for p in parts[1:]]
                bboxes.append((cls_id, bbox))

        # 按 x_center 从左到右排序（兼容未来多数字框场景）
        bboxes.sort(key=lambda x: x[1][0])

        # 构建序列标签：class_id 直接对应数值，如 200 → "200" → [2, 0, 0]
        label_str = ''.join(str(cls_id) for cls_id, _ in bboxes)
        label = [int(ch) for ch in label_str]

        # ---- 确定裁剪区域 ----
        if self.no_crop or not bboxes:
            roi_img = img
            bbox_for_preprocess = [0.5, 0.5, 1.0, 1.0]   # 整图
        else:
            # 当前数据每图一个框（框住整个数字序列），直接取该框
            if len(bboxes) == 1:
                _, bbox_for_preprocess = bboxes[0]
                roi_img = img
            else:
                # 若存在多框，取并集作为整体 ROI
                img_h, img_w = img.shape[:2]
                x1s, y1s, x2s, y2s = [], [], [], []
                for _, bbox in bboxes:
                    x_c, y_c, w, h = bbox
                    x1s.append(int((x_c - w / 2) * img_w))
                    y1s.append(int((y_c - h / 2) * img_h))
                    x2s.append(int((x_c + w / 2) * img_w))
                    y2s.append(int((y_c + h / 2) * img_h))
                x1 = max(0, min(x1s))
                y1 = max(0, min(y1s))
                x2 = min(img_w, max(x2s))
                y2 = min(img_h, max(y2s))
                roi_img = img[y1:y2, x1:x2]
                bbox_for_preprocess = [0.5, 0.5, 1.0, 1.0]

        # ---- 预处理 ----
        img_array = preprocess_image(roi_img, bbox_for_preprocess,
                                     img_size=self.img_size,
                                     augment=self.augment)
        img_tensor = torch.from_numpy(img_array).unsqueeze(0)  # (1, H, W)
        label_tensor = torch.tensor(label, dtype=torch.long)
        return img_tensor, label_tensor, len(label)


def collate_fn(batch):
    """自定义 collate：labels 拼接为 1D，用于 CTCLoss。"""
    images, labels, label_lengths = zip(*batch)
    images = torch.stack(images, dim=0)          # (B, 1, H, W)
    targets = torch.cat(labels, dim=0)           # (sum_len,)
    target_lengths = torch.tensor(label_lengths, dtype=torch.long)
    return images, targets, target_lengths


# ==================== CRNN 模型 ====================
class CRNN(nn.Module):
    """
    标准 CRNN（CNN + BiLSTM + CTC）。
    输入: (B, 1, H=32, W)
    输出: (T, B, num_classes)  其中 T ≈ W / 4
    """
    def __init__(self, num_classes: int = NUM_CLASSES, hidden_size: int = 256):
        super(CRNN, self).__init__()

        self.cnn = nn.Sequential(
            # (B, 1, 32, W)
            nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),                       # (32, 16, W/2)

            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),                       # (64, 8, W/4)

            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            # 仅高度方向下采样，宽度方向 stride=1，保持更多时序分辨率
            nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1)),  # (128, 4, W/4+1)

            nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1)),  # (256, 2, ~W/4)

            nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1)),  # (512, 1, ~W/4)
        )

        self.rnn = nn.LSTM(input_size=512,
                           hidden_size=hidden_size,
                           num_layers=2,
                           bidirectional=True,
                           batch_first=False)

        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, 1, H, W)
        x = self.cnn(x)              # (B, 512, 1, T)
        x = x.squeeze(2)             # (B, 512, T)
        x = x.permute(2, 0, 1)       # (T, B, 512)  时序维度放第一，符合 LSTM 要求
        x, _ = self.rnn(x)           # (T, B, 512)
        x = self.fc(x)               # (T, B, num_classes)
        return x


# ==================== 训练 / 验证 / 推理 ====================
def train_one_epoch(model: nn.Module,
                    dataloader: DataLoader,
                    criterion: nn.Module,
                    optimizer: torch.optim.Optimizer,
                    device: torch.device) -> float:
    model.train()
    total_loss = 0.0
    count = 0

    for images, targets, target_lengths in tqdm(dataloader, desc='Train', file=sys.stdout):
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        target_lengths = target_lengths.to(device, non_blocking=True)

        outputs = model(images)              # (T, B, C)
        T, B, C = outputs.shape
        log_probs = F.log_softmax(outputs, dim=2)
        input_lengths = torch.full((B,), T, dtype=torch.long, device=device)

        loss = criterion(log_probs, targets, input_lengths, target_lengths)

        optimizer.zero_grad()
        loss.backward()
        # 梯度裁剪，防止 RNN 爆炸
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()

        total_loss += loss.item()
        count += 1

    return total_loss / max(count, 1)


@torch.no_grad()
def validate(model: nn.Module,
             dataloader: DataLoader,
             criterion: nn.Module,
             device: torch.device) -> Tuple[float, float, float]:
    model.eval()
    total_loss = 0.0
    count = 0

    total_samples = 0
    exact_correct = 0
    char_correct = 0
    char_total = 0

    for images, targets, target_lengths in tqdm(dataloader, desc='Val  ', file=sys.stdout):
        images = images.to(device, non_blocking=True)
        targets_dev = targets.to(device, non_blocking=True)
        target_lengths_dev = target_lengths.to(device, non_blocking=True)

        outputs = model(images)              # (T, B, C)
        T, B, C = outputs.shape
        log_probs = F.log_softmax(outputs, dim=2)
        input_lengths = torch.full((B,), T, dtype=torch.long, device=device)

        loss = criterion(log_probs, targets_dev, input_lengths, target_lengths_dev)
        total_loss += loss.item()
        count += 1

        # ---- 解码 ----
        preds = outputs.argmax(dim=2).cpu().numpy()  # (T, B)
        pred_texts = ctc_decode(preds)

        # ---- 解析真实标签 ----
        targets_np = targets.numpy()
        target_lengths_np = target_lengths.numpy()
        ptr = 0
        for i in range(B):
            gt_len = target_lengths_np[i]
            gt_label = targets_np[ptr:ptr + gt_len]
            gt_text = ''.join(str(x) for x in gt_label)
            ptr += gt_len

            pred_text = pred_texts[i]
            if pred_text == gt_text:
                exact_correct += 1
            total_samples += 1

            # 字符级准确率（按最小长度对齐比较）
            for j in range(min(len(pred_text), len(gt_text))):
                if pred_text[j] == gt_text[j]:
                    char_correct += 1
            char_total += len(gt_text)

    avg_loss = total_loss / max(count, 1)
    exact_acc = exact_correct / max(total_samples, 1)
    char_acc = char_correct / max(char_total, 1)
    return avg_loss, exact_acc, char_acc


@torch.no_grad()
def inference(model: nn.Module,
              dataloader: DataLoader,
              device: torch.device,
              save_path: str,
              max_print: int = 30):
    """在验证集上进行推理，保存结果并打印前 max_print 条。"""
    model.eval()
    lines = []
    lines.append(f'{"GroundTruth":>12} | {"Prediction":>12} | Match')
    lines.append('-' * 40)

    for images, targets, target_lengths in dataloader:
        images = images.to(device, non_blocking=True)
        outputs = model(images)
        preds = outputs.argmax(dim=2).cpu().numpy()
        pred_texts = ctc_decode(preds)

        targets_np = targets.numpy()
        target_lengths_np = target_lengths.numpy()
        ptr = 0
        for i in range(images.size(0)):
            gt_len = target_lengths_np[i]
            gt_label = targets_np[ptr:ptr + gt_len]
            gt_text = ''.join(str(x) for x in gt_label)
            ptr += gt_len

            pred_text = pred_texts[i]
            match = '✓' if pred_text == gt_text else '✗'
            lines.append(f'{gt_text:>12} | {pred_text:>12} | {match}')

    # 保存到文件
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    # 终端打印
    print(f'\n推理结果（前 {max_print} 条）：')
    for line in lines[:max_print + 2]:
        print(line)
    print(f'...\n完整结果已保存至: {save_path}')


# ==================== 主函数 ====================
def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='CRNN+CTC 端到端数字序列识别训练')
    parser.add_argument('--img_dir', type=str, default=str(PROJECT_ROOT / 'captured_images'),
                        help='原始图像目录（默认: 项目根目录/captured_images）')
    parser.add_argument('--ann_dir', type=str, default=str(PROJECT_ROOT / 'annotations'),
                        help='YOLO 标注目录（默认: 项目根目录/annotations）')
    parser.add_argument('--save_dir', type=str, default=str(SZSB_ROOT / 'checkpoints'),
                        help='模型与日志保存目录')
    parser.add_argument('--img_h', type=int, default=32,
                        help='输入图像高度（默认 32）')
    parser.add_argument('--img_w', type=int, default=128,
                        help='输入图像宽度（默认 128）')
    parser.add_argument('--hidden_size', type=int, default=256,
                        help='BiLSTM 隐藏层维度（默认 256）')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='批次大小（默认 32）')
    parser.add_argument('--epochs', type=int, default=200,
                        help='训练轮数（默认 200）')
    parser.add_argument('--lr', type=float, default=1e-3,
                        help='初始学习率（默认 1e-3）')
    parser.add_argument('--val_ratio', type=float, default=0.2,
                        help='验证集划分比例（默认 0.2）')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子（默认 42）')
    parser.add_argument('--num_workers', type=int, default=0,
                        help='DataLoader 线程数（Windows 建议 0，默认 0）')
    parser.add_argument('--no_crop', action='store_true',
                        help='不使用 YOLO 框裁剪，直接输入整图（通常不推荐）')
    parser.add_argument('--resume', type=str, default='',
                        help='从指定 checkpoint 恢复训练（可选）')
    return parser


def main():
    args = get_parser().parse_args()
    args.img_dir = str(Path(args.img_dir).expanduser().resolve())
    args.ann_dir = str(Path(args.ann_dir).expanduser().resolve())
    args.save_dir = str(Path(args.save_dir).expanduser().resolve())
    set_seed(args.seed)

    # ---- 设备 ----
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'设备: {device}')
    if device.type == 'cuda':
        print(f'GPU: {torch.cuda.get_device_name(0)}')

    # ---- 扫描样本 ----
    if not os.path.isdir(args.img_dir):
        raise FileNotFoundError(f'图像目录不存在: {args.img_dir}')
    if not os.path.isdir(args.ann_dir):
        raise FileNotFoundError(f'标注目录不存在: {args.ann_dir}')

    all_samples = []
    for ann_file in sorted(os.listdir(args.ann_dir)):
        if not ann_file.lower().endswith('.txt') or ann_file.lower() == 'classes.txt':
            continue
        base_name = os.path.splitext(ann_file)[0]
        # 匹配常见图像后缀
        img_file = None
        for ext in ('.jpg', '.jpeg', '.png', '.bmp'):
            candidate = base_name + ext
            if os.path.exists(os.path.join(args.img_dir, candidate)):
                img_file = candidate
                break
        if img_file:
            all_samples.append({'img': img_file, 'ann': ann_file})

    if len(all_samples) == 0:
        raise RuntimeError('未找到任何匹配的图像-标注对，请检查路径。')
    print(f'共扫描到 {len(all_samples)} 条样本。')

    # ---- 划分训练/验证集 ----
    random.shuffle(all_samples)
    val_size = max(1, int(len(all_samples) * args.val_ratio))
    val_samples = all_samples[:val_size]
    train_samples = all_samples[val_size:]
    print(f'训练集: {len(train_samples)} | 验证集: {len(val_samples)}')

    # ---- 构建 DataLoader ----
    img_size = (args.img_h, args.img_w)
    train_dataset = DigitDataset(args.img_dir, args.ann_dir, train_samples,
                                 img_size=img_size, no_crop=args.no_crop, augment=True)
    val_dataset = DigitDataset(args.img_dir, args.ann_dir, val_samples,
                               img_size=img_size, no_crop=args.no_crop, augment=False)

    train_loader = DataLoader(train_dataset,
                              batch_size=args.batch_size,
                              shuffle=True,
                              num_workers=args.num_workers,
                              collate_fn=collate_fn,
                              pin_memory=True if device.type == 'cuda' else False)
    val_loader = DataLoader(val_dataset,
                            batch_size=args.batch_size,
                            shuffle=False,
                            num_workers=args.num_workers,
                            collate_fn=collate_fn,
                            pin_memory=True if device.type == 'cuda' else False)

    # ---- 模型、损失、优化器 ----
    model = CRNN(num_classes=NUM_CLASSES, hidden_size=args.hidden_size).to(device)
    criterion = nn.CTCLoss(blank=BLANK_INDEX, reduction='mean', zero_infinity=True)
    optimizer = Adam(model.parameters(), lr=args.lr)
    scheduler = StepLR(optimizer, step_size=50, gamma=0.5)

    start_epoch = 1
    best_acc = -1.0

    # ---- 恢复训练 ----
    if args.resume and os.path.isfile(args.resume):
        print(f'从 checkpoint 恢复: {args.resume}')
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_epoch = ckpt.get('epoch', 1) + 1
        best_acc = ckpt.get('val_acc', -1.0)
        print(f'恢复至 epoch {start_epoch - 1}, 历史最佳 acc={best_acc:.4f}')

    os.makedirs(args.save_dir, exist_ok=True)

    # ---- 训练循环 ----
    print('\n开始训练...')
    for epoch in range(start_epoch, args.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_char_acc = validate(model, val_loader, criterion, device)
        scheduler.step()

        lr = optimizer.param_groups[0]['lr']
        print(f'Epoch [{epoch:03d}/{args.epochs}]  '
              f'LR:{lr:.1e}  '
              f'TrainLoss:{train_loss:.4f}  '
              f'ValLoss:{val_loss:.4f}  '
              f'ValAcc:{val_acc:.4f}  '
              f'ValCharAcc:{val_char_acc:.4f}')

        # 保存最佳模型
        if val_acc > best_acc:
            best_acc = val_acc
            best_path = os.path.join(args.save_dir, 'best_crnn.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'val_char_acc': val_char_acc,
                'args': vars(args)
            }, best_path)
            print(f'  >>> 最佳模型已更新并保存至: {best_path} (acc={val_acc:.4f})')

        # 每 20 epoch 保存一次最新模型（防止意外中断）
        if epoch % 20 == 0:
            last_path = os.path.join(args.save_dir, 'last_crnn.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'args': vars(args)
            }, last_path)

    print(f'\n训练结束。最佳验证准确率: {best_acc:.4f}')

    # ---- 最终推理测试 ----
    print('\n加载最佳模型并在验证集上推理...')
    best_ckpt = torch.load(os.path.join(args.save_dir, 'best_crnn.pth'), map_location=device)
    model.load_state_dict(best_ckpt['model_state_dict'])
    result_path = os.path.join(args.save_dir, 'inference_results.txt')
    inference(model, val_loader, device, save_path=result_path, max_print=30)


if __name__ == '__main__':
    main()
