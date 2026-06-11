"""
实时计数器识别诊断脚本 v2 —— CRNN + CTC 端到端
用法: cd szjs && python debug_counter_realtime.py
"""
import os
import sys
import cv2
import numpy as np
import time

sys.path.insert(0, r"D:\挑战杯\1\vision_only\src\utils")
from VL import ImageAnalyzer, _preprocess_for_crnn

CAPTURE_URL = "http://192.168.137.167/capture"
SAVE_DIR = r"D:\挑战杯\1\szjs\debug_frames"
os.makedirs(SAVE_DIR, exist_ok=True)

import requests


def capture_frame():
    try:
        resp = requests.get(CAPTURE_URL, timeout=10)
        if resp.status_code == 200:
            img = cv2.imdecode(np.frombuffer(resp.content, dtype=np.uint8), cv2.IMREAD_COLOR)
            return img
    except Exception as e:
        print(f"捕获失败: {e}")
    return None


def debug_recognize(frame, analyzer, save_prefix="frame"):
    """详细诊断：保存面板定位、CRNN 预处理图、推理结果"""
    if frame is None:
        return

    ts = int(time.time() * 1000)
    raw_path = os.path.join(SAVE_DIR, f"{save_prefix}_{ts}_raw.jpg")
    cv2.imwrite(raw_path, frame)

    # 面板定位
    panel = analyzer._locate_counter_panel(frame)
    if panel is None:
        print("  [FAIL] 未检测到面板")
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([15, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([155, 60, 60]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(mask1, mask2)
        cv2.imwrite(os.path.join(SAVE_DIR, f"{save_prefix}_{ts}_redmask.jpg"), red_mask)
        return

    px, py, pw, ph = panel
    print(f"  面板: ({px},{py},{pw},{ph}), 面积={pw*ph}")

    # 保存面板图
    debug_img = frame.copy()
    cv2.rectangle(debug_img, (px, py), (px+pw, py+ph), (0, 255, 0), 2)
    cv2.imwrite(os.path.join(SAVE_DIR, f"{save_prefix}_{ts}_panel.jpg"), debug_img)

    # CRNN 端到端推理（直接复用 analyzer 的接口）
    pred_str, annotated = analyzer.recognize_counter(frame, use_temporal=False)
    cv2.imwrite(os.path.join(SAVE_DIR, f"{save_prefix}_{ts}_result.jpg"), annotated)

    # 额外保存 CRNN 预处理后的输入图（反归一化到 0-255 便于查看）
    roi = frame[py:py+ph, px:px+pw]
    if roi.size > 0:
        proc = _preprocess_for_crnn(roi, img_size=analyzer._crnn_img_size)
        proc_vis = ((proc * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
        proc_vis = cv2.resize(proc_vis, (320, 80), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(os.path.join(SAVE_DIR, f"{save_prefix}_{ts}_crnn_input.jpg"), proc_vis)

    print(f"  CRNN 识别结果: '{pred_str}'")


if __name__ == "__main__":
    analyzer = ImageAnalyzer()
    analyzer.init()

    print("诊断脚本启动 (CRNN v2)，按 Ctrl+C 停止")
    print(f"诊断帧将保存到: {SAVE_DIR}")
    print("-" * 50)

    try:
        while True:
            frame = capture_frame()
            if frame is not None:
                print(f"\n捕获帧: {frame.shape[1]}x{frame.shape[0]}")
                debug_recognize(frame, analyzer)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n已停止")
