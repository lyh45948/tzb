#!/usr/bin/env python3
"""
CRNN 集成测试：用训练集中的原图测试 recognize_counter，
并保存中间预处理结果用于目视排查。
"""
import os
import sys
from pathlib import Path
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISION_ONLY = PROJECT_ROOT / "vision_only"
if str(VISION_ONLY) not in sys.path:
    sys.path.insert(0, str(VISION_ONLY))
from src.utils.VL import ImageAnalyzer, _preprocess_for_crnn

IMG_DIR = str(PROJECT_ROOT / 'captured_images')
ANN_DIR = str(PROJECT_ROOT / 'annotations')
SAVE_DIR = str(Path(__file__).resolve().parent / 'test_crnn_debug')
os.makedirs(SAVE_DIR, exist_ok=True)

# 选几张有代表性的图
SAMPLES = [
    'esp32_capture_1780590408583',  # 0
    'esp32_capture_1780590444454',  # 10
    'esp32_capture_1780590551824',  # 50
    'esp32_capture_1780590685306',  # 100
    'esp32_capture_1780590895452',  # 200
]

analyzer = ImageAnalyzer()
analyzer.init()

for name in SAMPLES:
    img_path = os.path.join(IMG_DIR, name + '.jpg')
    ann_path = os.path.join(ANN_DIR, name + '.txt')
    img = cv2.imread(img_path)
    if img is None:
        print(f'[跳过] 无法读取 {img_path}')
        continue

    # 读取 YOLO 标注（GT bbox）
    with open(ann_path, 'r') as f:
        parts = f.readline().strip().split()
    gt_cls = int(parts[0])
    bbox = [float(p) for p in parts[1:]]

    # ---- 测试 1：用 HSV 自动定位面板（与实时推理一致）----
    pred_hsv, annotated_hsv = analyzer.recognize_counter(img.copy(), use_temporal=False)
    hsv_path = os.path.join(SAVE_DIR, f'{name}_hsv_{pred_hsv}.jpg')
    cv2.imwrite(hsv_path, annotated_hsv)

    # ---- 测试 2：用 YOLO 标注框精确裁剪（与训练时一致）----
    h, w = img.shape[:2]
    x_c, y_c, bw, bh = bbox
    x1 = int((x_c - bw / 2) * w)
    y1 = int((y_c - bh / 2) * h)
    x2 = int((x_c + bw / 2) * w)
    y2 = int((y_c + bh / 2) * h)
    roi_gt = img[y1:y2, x1:x2]

    proc = _preprocess_for_crnn(roi_gt, img_size=analyzer._crnn_img_size)
    # 反归一化保存可视化
    proc_vis = ((proc * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    proc_vis_large = cv2.resize(proc_vis, (320, 80), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(SAVE_DIR, f'{name}_proc_yolo.jpg'), proc_vis_large)

    # 手动推理（绕过 HSV 定位，直接送入精确 ROI）
    import torch
    img_tensor = torch.from_numpy(proc).unsqueeze(0).unsqueeze(0).to(analyzer.device)
    with torch.no_grad():
        outputs = analyzer.counter_crnn(img_tensor)
        preds = outputs.argmax(dim=2).cpu().numpy()
        from src.utils.VL import _ctc_decode
        pred_texts = _ctc_decode(preds)
        pred_yolo = pred_texts[0] if pred_texts else ""

    # 在 ROI 上画结果
    roi_annotated = roi_gt.copy()
    cv2.putText(roi_annotated, f'GT:{gt_cls} PRED:{pred_yolo}', (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite(os.path.join(SAVE_DIR, f'{name}_roi_yolo.jpg'), roi_annotated)

    print(f'{name}: GT={gt_cls:>3} | HSV_pred={pred_hsv:>6} | YOLO_pred={pred_yolo:>6}')

print(f'\n调试图像已保存到: {os.path.abspath(SAVE_DIR)}')
