"""
v3 模型综合验证：单字符 + 端到端
"""
import sys
import os
import re
import cv2
import numpy as np
import torch
import torch.nn as nn
from collections import defaultdict

sys.path.insert(0, r"D:\挑战杯\1\vision_only\src\utils")
from VL import ImageAnalyzer

DATA_ROOT = r"D:\挑战杯\11\led_digit_cls"
IMG_DIR = r"D:\挑战杯\1\captured_images"
MODEL_PATH = r"D:\挑战杯\1\szjs\led_digit_classifier\best.pth"
CLASS_NAMES = ['0','1','2','3','4','5','6','7','8','9','blank']

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(256*8*8, 512), nn.ReLU(), nn.Dropout(0.5), nn.Linear(512, 11)
        )
    def forward(self, x):
        return self.classifier(self.features(x))

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = Net().to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval()

def predict_roi(roi_bgr):
    roi = cv2.resize(roi_bgr, (64, 64), interpolation=cv2.INTER_AREA)
    roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
    roi = roi.astype(np.float32) / 255.0
    roi = (roi - 0.5) / 0.5
    roi = np.transpose(roi, (2, 0, 1))
    tensor = torch.from_numpy(roi).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
    conf, pred = probs.max(1)
    return CLASS_NAMES[pred.item()], conf.item()

# ===== 单字符验证 =====
print("=" * 60)
print("单字符验证（真实样本）")
print("=" * 60)
per_class = defaultdict(lambda: {'total':0, 'correct':0})
for class_name in CLASS_NAMES:
    class_dir = os.path.join(DATA_ROOT, class_name)
    if not os.path.isdir(class_dir):
        continue
    for fname in os.listdir(class_dir):
        if fname.startswith('syn_'):
            continue
        path = os.path.join(class_dir, fname)
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        pred, conf = predict_roi(img)
        per_class[class_name]['total'] += 1
        if pred == class_name:
            per_class[class_name]['correct'] += 1

total_correct = total_all = 0
for name in CLASS_NAMES:
    c = per_class[name]
    if c['total'] == 0:
        continue
    acc = c['correct'] / c['total']
    total_correct += c['correct']
    total_all += c['total']
    print(f"  {name:>5s}: {c['correct']:3d}/{c['total']:3d} = {acc:.1%}")
print(f"\n总准确率: {total_correct}/{total_all} = {total_correct/total_all:.1%}")

# ===== 端到端验证 =====
print("\n" + "=" * 60)
print("端到端验证（完整实拍图）")
print("=" * 60)

# 重建 GT
ground_truth = {}
pattern = re.compile(r"^(esp32_capture_\d+)_(\d)\.png$")
for class_name in os.listdir(DATA_ROOT):
    class_dir = os.path.join(DATA_ROOT, class_name)
    if not os.path.isdir(class_dir):
        continue
    for fname in os.listdir(class_dir):
        if fname.startswith('syn_'):
            continue
        m = pattern.match(fname)
        if not m:
            continue
        base_name = m.group(1) + ".jpg"
        pos = int(m.group(2))
        if base_name not in ground_truth:
            ground_truth[base_name] = ['?'] * 6
        ground_truth[base_name][pos] = class_name

# 使用修改后的 VL.py 逻辑（conf_thresh=0.3，无 bright_ratio）
analyzer = ImageAnalyzer()
analyzer.init()

correct = total = 0
errors = []
for fname in sorted(ground_truth.keys()):
    gt_digits = ground_truth[fname]
    gt_display = ''.join(gt_digits).replace('blank', '')
    
    path = os.path.join(IMG_DIR, fname)
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        continue
    
    pred_str, _ = analyzer.recognize_counter(img, use_temporal=False)
    total += 1
    if pred_str == gt_display:
        correct += 1
    else:
        errors.append((fname, gt_display, pred_str))

print(f"端到端准确率: {correct}/{total} = {correct/total:.1%}")
if errors:
    print(f"\n错误样本 ({len(errors)} 个):")
    for fname, gt, pred in errors[:15]:
        print(f"  {fname}: GT='{gt}' PRED='{pred}'")
