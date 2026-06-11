"""
调试七段码规则匹配 —— 可视化二值化和段检测区域
"""
import os
import cv2
import numpy as np

DATA_ROOT = r"D:\挑战杯\11\led_digit_cls"

# 从每类取1张真实样本做调试
samples = []
for class_name in ['0','1','2','5','8','blank']:
    class_dir = os.path.join(DATA_ROOT, class_name)
    for fname in os.listdir(class_dir):
        if not fname.startswith('syn_'):
            samples.append((class_name, os.path.join(class_dir, fname)))
            break

def visualize_detection(img_bgr, class_name):
    h, w = img_bgr.shape[:2]
    
    # 红色特征
    b, g, r = cv2.split(img_bgr)
    red_feature = cv2.subtract(r, cv2.max(g, b))
    
    # 高斯模糊 + Otsu
    blurred = cv2.GaussianBlur(red_feature, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 检测区域
    mx, my = w / 2, h / 2
    pad_x, pad_y = w * 0.15, h * 0.12
    seg_w, seg_h = w * 0.25, h * 0.15
    mid_y = h * 0.15
    
    regions = {
        'a': (int(mx - seg_w/2), int(pad_y), int(mx + seg_w/2), int(pad_y + mid_y)),
        'b': (int(mx + seg_w/2 - pad_x), int(pad_y), int(w - pad_x), int(my - mid_y/2)),
        'c': (int(mx + seg_w/2 - pad_x), int(my + mid_y/2), int(w - pad_x), int(h - pad_y - mid_y)),
        'd': (int(mx - seg_w/2), int(h - pad_y - mid_y), int(mx + seg_w/2), int(h - pad_y)),
        'e': (int(pad_x), int(my + mid_y/2), int(mx - seg_w/2 + pad_x), int(h - pad_y - mid_y)),
        'f': (int(pad_x), int(pad_y), int(mx - seg_w/2 + pad_x), int(my - mid_y/2)),
        'g': (int(mx - seg_w/2), int(my - mid_y/2), int(mx + seg_w/2), int(my + mid_y/2)),
    }
    
    # 统计
    total_ratio = np.sum(binary > 0) / (h * w)
    seg_order = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    segments = []
    
    vis = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    colors = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(255,0,255),(0,255,255),(128,128,255)]
    
    for i, seg_name in enumerate(seg_order):
        x1, y1, x2, y2 = regions[seg_name]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        roi = binary[y1:y2, x1:x2]
        ratio = np.sum(roi > 0) / (roi.shape[0] * roi.shape[1]) if roi.size > 0 else 0
        on = ratio > 0.15
        segments.append(1 if on else 0)
        
        cv2.rectangle(vis, (x1, y1), (x2, y2), colors[i], 1)
        cv2.putText(vis, f"{seg_name}:{ratio:.2f}", (x1+2, y1+12), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, colors[i], 1)
    
    print(f"\n{class_name}: total_ratio={total_ratio:.3f}, seg={tuple(segments)}")
    
    # 拼合显示
    red_vis = cv2.resize(red_feature, (128, 128))
    bin_vis = cv2.resize(binary, (128, 128))
    bin_vis = cv2.cvtColor(bin_vis, cv2.COLOR_GRAY2BGR)
    
    # 在原图上画区域
    orig_vis = img_bgr.copy()
    for i, seg_name in enumerate(seg_order):
        x1, y1, x2, y2 = regions[seg_name]
        cv2.rectangle(orig_vis, (x1, y1), (x2, y2), colors[i], 1)
    
    orig_vis = cv2.resize(orig_vis, (128, 128))
    
    combined = np.hstack([orig_vis, bin_vis])
    return combined

# 生成调试图
rows = []
for class_name, path in samples:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        continue
    vis = visualize_detection(img, class_name)
    rows.append(vis)

if rows:
    final = np.vstack(rows)
    cv2.imwrite(r"D:\挑战杯\1\szjs\ssocr_debug.png", final)
    print(f"\n调试图已保存: szjs/ssocr_debug.png")
