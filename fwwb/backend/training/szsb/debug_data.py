#!/usr/bin/env python3
"""
快速检查数据预处理是否正确：
可视化裁剪后的 ROI 和最终送入网络的图像。
"""
import os
import sys
from pathlib import Path
import cv2
import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 把 train_crnn.py 中的函数直接复制过来使用
import random

def preprocess_image(img, bbox, img_size=(32, 128), augment=False):
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
    start_x = (target_w - new_w) // 2
    canvas[:, start_x:start_x + new_w] = roi.astype(np.float32)
    canvas = (canvas / 255.0 - 0.5) / 0.5
    return canvas


def main():
    img_dir = str(PROJECT_ROOT / 'captured_images')
    ann_dir = str(PROJECT_ROOT / 'annotations')
    samples = [
        'esp32_capture_1780590408583',  # class 0
        'esp32_capture_1780590444454',  # class 10
        'esp32_capture_1780590551824',  # class 50
        'esp32_capture_1780590685306',  # class 100
        'esp32_capture_1780590895452',  # class 200
    ]

    os.makedirs('./debug_vis', exist_ok=True)
    for name in samples:
        img_path = os.path.join(img_dir, name + '.jpg')
        ann_path = os.path.join(ann_dir, name + '.txt')
        img = cv2.imread(img_path)
        with open(ann_path, 'r') as f:
            line = f.readline().strip()
        parts = line.split()
        cls_id = int(parts[0])
        bbox = [float(p) for p in parts[1:]]

        # 原始图 + 画框
        img_vis = img.copy()
        h, w = img.shape[:2]
        x1 = int((bbox[0] - bbox[2]/2) * w)
        y1 = int((bbox[1] - bbox[3]/2) * h)
        x2 = int((bbox[0] + bbox[2]/2) * w)
        y2 = int((bbox[1] + bbox[3]/2) * h)
        cv2.rectangle(img_vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_vis, f'cls={cls_id}', (x1, max(y1-5, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 预处理后的图（反归一化到 0-255 以便可视化）
        proc = preprocess_image(img, bbox, img_size=(32, 128), augment=False)
        proc_vis = ((proc * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
        proc_vis = cv2.resize(proc_vis, (320, 80), interpolation=cv2.INTER_NEAREST)

        # 保存
        cv2.imwrite(f'./debug_vis/{name}_orig.jpg', img_vis)
        cv2.imwrite(f'./debug_vis/{name}_proc.jpg', proc_vis)
        print(f'{name}: cls={cls_id}, proc shape={proc.shape}, min={proc.min():.2f}, max={proc.max():.2f}, mean={proc.mean():.2f}')

    print('可视化结果已保存到 ./debug_vis/')


if __name__ == '__main__':
    main()
