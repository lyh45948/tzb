#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRNN + CTC 端到端数字序列识别训练脚本 v2
=============================================
修复 v1 中的训练不收敛问题：
  1. 图像改为左对齐（代替居中 pad），更符合 CTC 从左到右的时序假设
  2. 学习率降至 1e-4，并加入 Warmup + CosineAnnealing
  3. 增加训练过程监控（每 batch 打印 loss，保存 loss 曲线图）
  4. 数据增强加入随机左右平移，帮助模型学习位置不变性
  5. 优化器改为 AdamW，增加权重衰减防止过拟合

运行示例：
    python train_crnn_v2.py
    python train_crnn_v2.py --epochs 300 --batch_size 64 --lr 1e-4
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
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

# ==================== 全局常量 ====================
CHARS = '0123456789'
NUM_CLASSES = len(CHARS) + 1   # 10 个数字 + 1 个 CTC blank
BLANK_INDEX = len(CHARS)       # blank 索引固定为 10


# ==================== 工具函数 ====================
def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def ctc_decode(preds: np.ndarray, blank: int = BLANK_INDEX) -> List[str]:
    """贪婪 CTC 解码：去 blank、去连续重复。"""
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


def get_warmup_cosine_schedule(optimizer, warmup_epochs, total_epochs):
    """Warmup + CosineAnnealing 学习率调度。"""
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return (epoch + 1) / warmup_epochs
        else:
            progress = (epoch - warmup_epochs) / (total_epochs - warmup_epochs)
            return 0.5 * (1 + np.cos(np.pi * progress))
    return LambdaLR(optimizer, lr_lambda)


def preprocess_image(img: np.ndarray,
                     bbox: List[float],
                     img_size: Tuple[int, int] = (32, 128),
                     augment: bool = False) -> np.ndarray:
    """
    图像预处理：裁剪 ROI → resize → **左对齐 pad** → 归一化。
    左对齐比居中更符合 CTC 时序扫描习惯，显著降低学习难度。
    """
    target_h, target_w = img_size
    img_h, img_w = img.shape[:2]

    x_c, y_c, w, h = bbox
    x1 = int((x_c - w / 2) * img_w)
    y1 = int((y_c - h / 2) * img_h)
    x2 = int((x_c + w / 2) * img_w)
    y2 = int((y_c + h / 2) * img_h)

    margin_x = max(1, int((x2 - x1) * 0.05))
    margin_y = max(1, int((y2 - y1) * 0.05))
    x1 = max(0, x1 - margin_x)
    y1 = max(0, y1 - margin_y)
    x2 = min(img_w, x2 + margin_x)
    y2 = min(img_h, y2 + margin_y)

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return np.zeros((target_h, target_w), dtype=np.float32)

    if len(roi.shape) == 3:
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # ---- 训练增强（uint8 阶段）----
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
        # 随机左右平移（帮助 CTC 学习位置不变性）
        if random.random() < 0.5:
            shift_x = random.randint(-5, 5)
            M = np.float32([[1, 0, shift_x], [0, 1, 0]])
            roi = cv2.warpAffine(roi, M, (roi.shape[1], roi.shape[0]),
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    # ---- 保持宽高比 resize ----
    rh = target_h / roi.shape[0]
    new_w = int(roi.shape[1] * rh)
    if new_w > target_w:
        new_w = target_w
    roi = cv2.resize(roi, (new_w, target_h), interpolation=cv2.INTER_AREA)

    # ---- 左对齐 pad 到固定宽度（关键修复）----
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    canvas[:, :new_w] = roi.astype(np.float32)

    # 归一化到 [-1, 1]
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

        bboxes = []
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

        bboxes.sort(key=lambda x: x[1][0])

        label_str = ''.join(str(cls_id) for cls_id, _ in bboxes)
        label = [int(ch) for ch in label_str]

        if self.no_crop or not bboxes:
            roi_img = img
            bbox_for_preprocess = [0.5, 0.5, 1.0, 1.0]
        else:
            if len(bboxes) == 1:
                _, bbox_for_preprocess = bboxes[0]
                roi_img = img
            else:
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

        img_array = preprocess_image(roi_img, bbox_for_preprocess,
                                     img_size=self.img_size,
                                     augment=self.augment)
        img_tensor = torch.from_numpy(img_array).unsqueeze(0)
        label_tensor = torch.tensor(label, dtype=torch.long)
        return img_tensor, label_tensor, len(label)


def collate_fn(batch):
    images, labels, label_lengths = zip(*batch)
    images = torch.stack(images, dim=0)
    targets = torch.cat(labels, dim=0)
    target_lengths = torch.tensor(label_lengths, dtype=torch.long)
    return images, targets, target_lengths


# ==================== CRNN 模型（稍作加宽）====================
class CRNN(nn.Module):
    def __init__(self, num_classes: int = NUM_CLASSES, hidden_size: int = 256):
        super(CRNN, self).__init__()

        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, 3, 1, 1), nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),                       # (64, 16, W/2)

            nn.Conv2d(64, 128, 3, 1, 1), nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),                       # (128, 8, W/4)

            nn.Conv2d(128, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),  # (256, 4, W/4+1)

            nn.Conv2d(256, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),  # (512, 2, ~W/4)

            nn.Conv2d(512, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),  # (512, 1, ~W/4)
        )

        self.rnn = nn.LSTM(512, hidden_size, num_layers=2,
                           bidirectional=True, batch_first=False)
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x):
        x = self.cnn(x)              # (B, 512, 1, T)
        x = x.squeeze(2)             # (B, 512, T)
        x = x.permute(2, 0, 1)       # (T, B, 512)
        x, _ = self.rnn(x)           # (T, B, 512)
        x = self.fc(x)               # (T, B, num_classes)
        return x


# ==================== 训练 / 验证 / 推理 ====================
def train_one_epoch(model, dataloader, criterion, optimizer, device, epoch):
    model.train()
    total_loss = 0.0
    count = 0

    pbar = tqdm(dataloader, desc=f'Train E{epoch}', file=sys.stdout)
    for images, targets, target_lengths in pbar:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        target_lengths = target_lengths.to(device, non_blocking=True)

        outputs = model(images)
        T, B, C = outputs.shape
        log_probs = F.log_softmax(outputs, dim=2)
        input_lengths = torch.full((B,), T, dtype=torch.long, device=device)

        loss = criterion(log_probs, targets, input_lengths, target_lengths)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()

        total_loss += loss.item()
        count += 1
        pbar.set_postfix({'loss': f'{loss.item():.4f}'})

    return total_loss / max(count, 1)


@torch.no_grad()
def validate(model, dataloader, criterion, device):
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

        outputs = model(images)
        T, B, C = outputs.shape
        log_probs = F.log_softmax(outputs, dim=2)
        input_lengths = torch.full((B,), T, dtype=torch.long, device=device)

        loss = criterion(log_probs, targets_dev, input_lengths, target_lengths_dev)
        total_loss += loss.item()
        count += 1

        preds = outputs.argmax(dim=2).cpu().numpy()
        pred_texts = ctc_decode(preds)

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

            for j in range(min(len(pred_text), len(gt_text))):
                if pred_text[j] == gt_text[j]:
                    char_correct += 1
            char_total += len(gt_text)

    avg_loss = total_loss / max(count, 1)
    exact_acc = exact_correct / max(total_samples, 1)
    char_acc = char_correct / max(char_total, 1)
    return avg_loss, exact_acc, char_acc


@torch.no_grad()
def inference(model, dataloader, device, save_path, max_print=30):
    model.eval()
    lines = [f'{"GroundTruth":>12} | {"Prediction":>12} | Match', '-' * 40]

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

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'\n推理结果（前 {max_print} 条）：')
    for line in lines[:max_print + 2]:
        print(line)
    print(f'...\n完整结果已保存至: {save_path}')


# ==================== 主函数 ====================
def get_parser():
    parser = argparse.ArgumentParser(description='CRNN+CTC 端到端数字序列识别训练 v2')
    parser.add_argument('--img_dir', type=str, default=str(PROJECT_ROOT / 'captured_images'))
    parser.add_argument('--ann_dir', type=str, default=str(PROJECT_ROOT / 'annotations'))
    parser.add_argument('--save_dir', type=str, default=str(SZSB_ROOT / 'checkpoints_v2'))
    parser.add_argument('--img_h', type=int, default=32)
    parser.add_argument('--img_w', type=int, default=128)
    parser.add_argument('--hidden_size', type=int, default=256)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--epochs', type=int, default=200)
    parser.add_argument('--lr', type=float, default=1e-4, help='初始学习率（v2 默认 1e-4）')
    parser.add_argument('--warmup', type=int, default=10, help='Warmup epoch 数')
    parser.add_argument('--weight_decay', type=float, default=1e-4, help='AdamW 权重衰减')
    parser.add_argument('--val_ratio', type=float, default=0.2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--num_workers', type=int, default=0)
    parser.add_argument('--no_crop', action='store_true')
    parser.add_argument('--resume', type=str, default='')
    return parser


def main():
    args = get_parser().parse_args()
    args.img_dir = str(Path(args.img_dir).expanduser().resolve())
    args.ann_dir = str(Path(args.ann_dir).expanduser().resolve())
    args.save_dir = str(Path(args.save_dir).expanduser().resolve())
    set_seed(args.seed)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'设备: {device}')
    if device.type == 'cuda':
        print(f'GPU: {torch.cuda.get_device_name(0)}')

    if not os.path.isdir(args.img_dir):
        raise FileNotFoundError(f'图像目录不存在: {args.img_dir}')
    if not os.path.isdir(args.ann_dir):
        raise FileNotFoundError(f'标注目录不存在: {args.ann_dir}')

    all_samples = []
    for ann_file in sorted(os.listdir(args.ann_dir)):
        if not ann_file.lower().endswith('.txt') or ann_file.lower() == 'classes.txt':
            continue
        base_name = os.path.splitext(ann_file)[0]
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

    random.shuffle(all_samples)
    val_size = max(1, int(len(all_samples) * args.val_ratio))
    val_samples = all_samples[:val_size]
    train_samples = all_samples[val_size:]
    print(f'训练集: {len(train_samples)} | 验证集: {len(val_samples)}')

    img_size = (args.img_h, args.img_w)
    train_dataset = DigitDataset(args.img_dir, args.ann_dir, train_samples,
                                 img_size=img_size, no_crop=args.no_crop, augment=True)
    val_dataset = DigitDataset(args.img_dir, args.ann_dir, val_samples,
                               img_size=img_size, no_crop=args.no_crop, augment=False)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size,
                              shuffle=True, num_workers=args.num_workers,
                              collate_fn=collate_fn,
                              pin_memory=True if device.type == 'cuda' else False)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size,
                            shuffle=False, num_workers=args.num_workers,
                            collate_fn=collate_fn,
                            pin_memory=True if device.type == 'cuda' else False)

    model = CRNN(num_classes=NUM_CLASSES, hidden_size=args.hidden_size).to(device)
    criterion = nn.CTCLoss(blank=BLANK_INDEX, reduction='mean', zero_infinity=True)
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = get_warmup_cosine_schedule(optimizer, args.warmup, args.epochs)

    start_epoch = 1
    best_acc = -1.0

    if args.resume and os.path.isfile(args.resume):
        print(f'从 checkpoint 恢复: {args.resume}')
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_epoch = ckpt.get('epoch', 1) + 1
        best_acc = ckpt.get('val_acc', -1.0)
        print(f'恢复至 epoch {start_epoch - 1}, 历史最佳 acc={best_acc:.4f}')

    os.makedirs(args.save_dir, exist_ok=True)

    # 记录训练历史
    history = {'train_loss': [], 'val_loss': [], 'val_acc': [], 'val_char_acc': []}

    print('\n开始训练...')
    for epoch in range(start_epoch, args.epochs + 1):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device, epoch)
        val_loss, val_acc, val_char_acc = validate(model, val_loader, criterion, device)
        scheduler.step()

        lr = optimizer.param_groups[0]['lr']
        print(f'Epoch [{epoch:03d}/{args.epochs}]  '
              f'LR:{lr:.2e}  '
              f'TrainLoss:{train_loss:.4f}  '
              f'ValLoss:{val_loss:.4f}  '
              f'ValAcc:{val_acc:.4f}  '
              f'ValCharAcc:{val_char_acc:.4f}')

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        history['val_char_acc'].append(val_char_acc)

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
            print(f'  >>> 最佳模型已更新: {best_path} (acc={val_acc:.4f})')

        if epoch % 20 == 0:
            last_path = os.path.join(args.save_dir, 'last_crnn.pth')
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'args': vars(args)
            }, last_path)

    # 保存训练曲线（纯文本 CSV）
    csv_path = os.path.join(args.save_dir, 'training_log.csv')
    with open(csv_path, 'w') as f:
        f.write('epoch,train_loss,val_loss,val_acc,val_char_acc\n')
        for i in range(len(history['train_loss'])):
            f.write(f"{i+1},{history['train_loss'][i]:.6f},"
                    f"{history['val_loss'][i]:.6f},"
                    f"{history['val_acc'][i]:.6f},"
                    f"{history['val_char_acc'][i]:.6f}\n")
    print(f'\n训练曲线已保存至: {csv_path}')
    print(f'训练结束。最佳验证准确率: {best_acc:.4f}')

    # 推理
    print('\n加载最佳模型并在验证集上推理...')
    best_ckpt = torch.load(os.path.join(args.save_dir, 'best_crnn.pth'), map_location=device, weights_only=False)
    model.load_state_dict(best_ckpt['model_state_dict'])
    result_path = os.path.join(args.save_dir, 'inference_results.txt')
    inference(model, val_loader, device, save_path=result_path, max_print=30)


if __name__ == '__main__':
    main()
