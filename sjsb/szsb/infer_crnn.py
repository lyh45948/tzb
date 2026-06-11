#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CRNN 推理脚本：加载已训练模型，对验证集进行推理并输出结果。
用法：
    python infer_crnn.py --ckpt ./checkpoints_v2/best_crnn.pth
"""

import os
import sys
import argparse
import random
from pathlib import Path
import numpy as np
import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SZSB_ROOT = Path(__file__).resolve().parent

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# 从 train_crnn_v2 中复制必要定义
CHARS = '0123456789'
NUM_CLASSES = len(CHARS) + 1
BLANK_INDEX = len(CHARS)


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def ctc_decode(preds, blank=BLANK_INDEX):
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


def preprocess_image(img, bbox, img_size=(32, 128)):
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
    rh = target_h / roi.shape[0]
    new_w = int(roi.shape[1] * rh)
    if new_w > target_w:
        new_w = target_w
    roi = cv2.resize(roi, (new_w, target_h), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((target_h, target_w), dtype=np.float32)
    canvas[:, :new_w] = roi.astype(np.float32)
    canvas = (canvas / 255.0 - 0.5) / 0.5
    return canvas


class DigitDataset(Dataset):
    def __init__(self, img_dir, ann_dir, samples, img_size=(32, 128), no_crop=False):
        self.img_dir = img_dir
        self.ann_dir = ann_dir
        self.samples = samples
        self.img_size = img_size
        self.no_crop = no_crop

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
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

        img_array = preprocess_image(roi_img, bbox_for_preprocess, img_size=self.img_size)
        img_tensor = torch.from_numpy(img_array).unsqueeze(0)
        label_tensor = torch.tensor(label, dtype=torch.long)
        return img_tensor, label_tensor, len(label), sample['img']


def collate_fn(batch):
    images, labels, label_lengths, img_names = zip(*batch)
    images = torch.stack(images, dim=0)
    targets = torch.cat(labels, dim=0)
    target_lengths = torch.tensor(label_lengths, dtype=torch.long)
    return images, targets, target_lengths, img_names


class CRNN(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES, hidden_size=256):
        super(CRNN, self).__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 64, 3, 1, 1), nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, 1, 1), nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, 1, 1), nn.BatchNorm2d(256), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),
            nn.Conv2d(256, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),
            nn.Conv2d(512, 512, 3, 1, 1), nn.BatchNorm2d(512), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), stride=(2, 1), padding=(0, 1)),
        )
        self.rnn = nn.LSTM(512, hidden_size, num_layers=2, bidirectional=True, batch_first=False)
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x):
        x = self.cnn(x)
        x = x.squeeze(2)
        x = x.permute(2, 0, 1)
        x, _ = self.rnn(x)
        x = self.fc(x)
        return x


@torch.no_grad()
def run_inference(model, dataloader, device, save_path, max_print=40):
    model.eval()
    lines = [f'{"Image":>30} | {"GT":>6} | {"Pred":>6} | Match', '-' * 60]
    total = correct = 0

    for images, targets, target_lengths, img_names in dataloader:
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
            if pred_text == gt_text:
                correct += 1
            total += 1
            lines.append(f'{img_names[i]:>30} | {gt_text:>6} | {pred_text:>6} | {match}')

    lines.append('-' * 60)
    lines.append(f'总计: {total} | 正确: {correct} | 准确率: {correct/total:.4f}')

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print('\n'.join(lines[:max_print + 2]))
    if len(lines) > max_print + 2:
        print('...')
    print(f'\n完整结果已保存至: {save_path}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ckpt', type=str, default=str(SZSB_ROOT / 'checkpoints_v2' / 'best_crnn.pth'))
    parser.add_argument('--img_dir', type=str, default=str(PROJECT_ROOT / 'captured_images'))
    parser.add_argument('--ann_dir', type=str, default=str(PROJECT_ROOT / 'annotations'))
    parser.add_argument('--img_h', type=int, default=32)
    parser.add_argument('--img_w', type=int, default=128)
    parser.add_argument('--hidden_size', type=int, default=256)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--num_workers', type=int, default=0)
    parser.add_argument('--val_ratio', type=float, default=0.2)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--no_crop', action='store_true')
    args = parser.parse_args()
    args.ckpt = str(Path(args.ckpt).expanduser().resolve())
    args.img_dir = str(Path(args.img_dir).expanduser().resolve())
    args.ann_dir = str(Path(args.ann_dir).expanduser().resolve())

    set_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'设备: {device}')

    if not os.path.isfile(args.ckpt):
        raise FileNotFoundError(f'Checkpoint 不存在: {args.ckpt}')

    # 加载 checkpoint
    ckpt = torch.load(args.ckpt, map_location=device, weights_only=False)
    saved_args = ckpt.get('args', {})
    hidden_size = saved_args.get('hidden_size', args.hidden_size)
    img_h = saved_args.get('img_h', args.img_h)
    img_w = saved_args.get('img_w', args.img_w)
    img_size = (img_h, img_w)

    # 扫描样本（与训练时相同划分）
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

    random.shuffle(all_samples)
    val_size = max(1, int(len(all_samples) * args.val_ratio))
    val_samples = all_samples[:val_size]
    print(f'验证集样本数: {len(val_samples)}')

    dataset = DigitDataset(args.img_dir, args.ann_dir, val_samples,
                           img_size=img_size, no_crop=args.no_crop)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.num_workers, collate_fn=collate_fn)

    model = CRNN(num_classes=NUM_CLASSES, hidden_size=hidden_size).to(device)
    model.load_state_dict(ckpt['model_state_dict'])

    save_path = os.path.join(os.path.dirname(args.ckpt), 'inference_results.txt')
    run_inference(model, dataloader, device, save_path)


if __name__ == '__main__':
    main()
