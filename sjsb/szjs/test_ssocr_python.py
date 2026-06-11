"""
简化版七段码规则匹配检测器 —— 纯 Python + OpenCV
原理：二值化 → 检测7个段亮灭 → 查表匹配数字
"""
import os
import cv2
import numpy as np
from collections import defaultdict

DATA_ROOT = r"D:\挑战杯\11\led_digit_cls"
CLASS_NAMES = ['0','1','2','3','4','5','6','7','8','9','blank']

# 七段码查表: (a,b,c,d,e,f,g) -> digit
# a=top, b=upper-right, c=lower-right, d=bottom, e=lower-left, f=upper-left, g=middle
DIGITS_LOOKUP = {
    (1,1,1,1,1,1,0): '0',
    (0,1,1,0,0,0,0): '1',
    (1,1,0,1,1,0,1): '2',
    (1,1,1,1,0,0,1): '3',
    (0,1,1,0,0,1,1): '4',
    (1,0,1,1,0,1,1): '5',
    (1,0,1,1,1,1,1): '6',
    (1,1,1,0,0,0,0): '7',
    (1,1,1,1,1,1,1): '8',
    (1,1,1,1,0,1,1): '9',
}

def detect_segments(img_bgr, debug=False):
    """
    检测七段码的7个段亮灭状态
    输入: BGR 图像 (64x64 或任意尺寸)
    返回: (digit_or_None, segments_tuple, is_blank)
    """
    h, w = img_bgr.shape[:2]
    
    # 1. 红色通道提取 + 灰度化（暗底红字，红色通道应显著高于其他通道）
    b, g, r = cv2.split(img_bgr)
    # 红色特征：R 高，G/B 低
    red_feature = cv2.subtract(r, cv2.max(g, b))
    
    # 2. 二值化（自适应阈值，处理过曝/欠曝）
    # 先高斯模糊去噪
    blurred = cv2.GaussianBlur(red_feature, (5, 5), 0)
    
    # 用 Otsu 自动找阈值
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 3. 定义7个检测区域（基于标准化坐标，适应不同尺寸）
    # 使用 ROI 的相对位置
    mx, my = w / 2, h / 2
    pad_x = w * 0.15
    pad_y = h * 0.12
    seg_w = w * 0.25
    seg_h = h * 0.15
    mid_y = h * 0.15
    
    regions = {
        'a': (int(mx - seg_w/2), int(pad_y), int(mx + seg_w/2), int(pad_y + mid_y)),           # top
        'b': (int(mx + seg_w/2 - pad_x), int(pad_y), int(w - pad_x), int(my - mid_y/2)),       # upper-right
        'c': (int(mx + seg_w/2 - pad_x), int(my + mid_y/2), int(w - pad_x), int(h - pad_y - mid_y)), # lower-right
        'd': (int(mx - seg_w/2), int(h - pad_y - mid_y), int(mx + seg_w/2), int(h - pad_y)),   # bottom
        'e': (int(pad_x), int(my + mid_y/2), int(mx - seg_w/2 + pad_x), int(h - pad_y - mid_y)), # lower-left
        'f': (int(pad_x), int(pad_y), int(mx - seg_w/2 + pad_x), int(my - mid_y/2)),           # upper-left
        'g': (int(mx - seg_w/2), int(my - mid_y/2), int(mx + seg_w/2), int(my + mid_y/2)),     # middle
    }
    
    # 4. 统计每个区域的亮像素比例
    segments = []
    seg_order = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    
    # 全图亮像素比例（用于判断 blank）
    total_ratio = np.sum(binary > 0) / (h * w)
    
    # 如果全图几乎全暗，认为是 blank
    if total_ratio < 0.02:
        return None, (0,0,0,0,0,0,0), True
    
    for seg_name in seg_order:
        x1, y1, x2, y2 = regions[seg_name]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            segments.append(0)
            continue
        
        roi = binary[y1:y2, x1:x2]
        ratio = np.sum(roi > 0) / (roi.shape[0] * roi.shape[1])
        # 阈值：区域中至少 15% 像素是亮的，认为该段点亮
        segments.append(1 if ratio > 0.15 else 0)
    
    seg_tuple = tuple(segments)
    digit = DIGITS_LOOKUP.get(seg_tuple)
    
    if debug:
        print(f"  total_ratio={total_ratio:.3f}, seg={seg_tuple}, digit={digit}")
    
    return digit, seg_tuple, False


# ===== 单字符验证（真实样本）=====
print("=" * 60)
print("七段码规则匹配 —— 单字符验证（真实样本）")
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
        
        pred, segs, is_blank = detect_segments(img)
        if class_name == 'blank':
            pred_label = 'blank' if is_blank else pred
        else:
            pred_label = pred
        
        per_class[class_name]['total'] += 1
        if pred_label == class_name:
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

# ===== 端到端验证（完整实拍图，使用 VL.py 的面板定位+6等分）=====
print("\n" + "=" * 60)
print("七段码规则匹配 —— 端到端验证（完整实拍图）")
print("=" * 60)

import sys
sys.path.insert(0, r"D:\挑战杯\1\vision_only\src\utils")
from VL import ImageAnalyzer

IMG_DIR = r"D:\挑战杯\1\captured_images"

def recognize_counter_ssocr(frame):
    """用规则匹配替换 CNN 分类"""
    analyzer = ImageAnalyzer()
    panel = analyzer._locate_counter_panel(frame)
    if panel is None:
        return "未检测到面板", frame
    
    px, py, pw, ph = panel
    cell_w = pw / 6.0
    
    results = []
    annotated = frame.copy()
    cv2.rectangle(annotated, (px, py), (px+pw, py+ph), (0, 255, 0), 2)
    
    for i in range(6):
        xs = int(px + i * cell_w)
        xe = int(px + (i + 1) * cell_w) if i < 5 else px + pw
        roi = frame[py:py+ph, xs:xe]
        if roi.size == 0:
            continue
        
        cv2.line(annotated, (xs, py), (xs, py+ph), (0, 255, 0), 1)
        
        pred, segs, is_blank = detect_segments(roi)
        if not is_blank and pred is not None:
            results.append(pred)
            cx = xs + (xe - xs) // 2
            cy = py + ph // 2
            cv2.putText(annotated, str(pred), (cx-8, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 255), 2)
    
    digit_str = ''.join(results) if results else "未检测到数字"
    cv2.putText(annotated, f"SSOCR: {digit_str}", (px, py-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    return digit_str, annotated

# 重建 GT
import re
pattern = re.compile(r"^(esp32_capture_\d+)_(\d)\.png$")
ground_truth = {}
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

correct = total = 0
errors = []
for fname in sorted(ground_truth.keys()):
    gt_digits = ground_truth[fname]
    gt_display = ''.join(gt_digits).replace('blank', '')
    
    path = os.path.join(IMG_DIR, fname)
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        continue
    
    pred_str, _ = recognize_counter_ssocr(img)
    total += 1
    if pred_str == gt_display:
        correct += 1
    else:
        errors.append((fname, gt_display, pred_str))

print(f"端到端准确率: {correct}/{total} = {correct/total:.1%}")
if errors:
    print(f"\n错误样本 ({len(errors)} 个):")
    for fname, gt, pred in errors[:20]:
        print(f"  {fname}: GT='{gt}' PRED='{pred}'")
