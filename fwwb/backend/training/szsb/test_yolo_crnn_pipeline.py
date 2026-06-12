"""测试 YOLOv8s + CRNN 端到端流水线精度"""
import argparse
import os
import sys
from pathlib import Path

import cv2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISION_ONLY = PROJECT_ROOT / "vision_only"
if str(VISION_ONLY) not in sys.path:
    sys.path.insert(0, str(VISION_ONLY))

from src.utils.VL import ImageAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(description="测试 YOLOv8s + CRNN 端到端流水线精度")
    parser.add_argument('--img_dir', type=str, default=str(PROJECT_ROOT / 'captured_images'),
                        help='原始图像目录')
    parser.add_argument('--ann_dir', type=str, default=str(PROJECT_ROOT / 'annotations'),
                        help='YOLO 标注目录')
    parser.add_argument('--max_samples', type=int, default=0,
                        help='最多测试样本数，0 表示全部')
    return parser.parse_args()


def main():
    args = parse_args()
    img_dir = Path(args.img_dir).expanduser().resolve()
    ann_dir = Path(args.ann_dir).expanduser().resolve()

    if not ann_dir.is_dir():
        raise FileNotFoundError(f"标注目录不存在: {ann_dir}")
    if not img_dir.is_dir():
        raise FileNotFoundError(f"图像目录不存在: {img_dir}")

    analyzer = ImageAnalyzer.get_instance()
    analyzer.init()

    correct = 0
    total = 0
    errors = []

    ann_files = [p for p in sorted(ann_dir.iterdir()) if p.suffix == '.txt' and p.name != 'classes.txt']
    if args.max_samples > 0:
        ann_files = ann_files[:args.max_samples]

    for ann_path in ann_files:
        base = ann_path.stem
        img_path = None
        for ext in ('.jpg', '.jpeg', '.png', '.bmp'):
            candidate = img_dir / f"{base}{ext}"
            if candidate.exists():
                img_path = candidate
                break
        if img_path is None:
            continue

        # 读取标签
        with ann_path.open(encoding='utf-8') as fp:
            line = fp.readline().strip()
        gt = int(line.split()[0])

        # 推理
        img = cv2.imread(str(img_path))
        pred_str, _ = analyzer.recognize_counter(img, use_temporal=False)
        try:
            pred = int(pred_str)
        except ValueError:
            pred = -1

        total += 1
        if pred == gt:
            correct += 1
        else:
            errors.append((base, gt, pred_str))

    print(f"\n===== YOLO+CRNN 端到端测试 =====")
    if total == 0:
        print(f"未找到可测试样本，图像目录: {img_dir}，标注目录: {ann_dir}")
        return
    print(f"Total: {total}, Correct: {correct}, Accuracy: {correct/total*100:.1f}%")
    if errors:
        print(f"\n错误样本 (前20):")
        for base, gt, pred in errors[:20]:
            print(f"  {base}: GT={gt}, Pred={pred}")


if __name__ == '__main__':
    main()
