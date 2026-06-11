"""
设置固定 ROI 脚本 —— 摄像头固定安装时使用
用法: cd szjs && python set_fixed_roi.py
"""
import os
import sys
import cv2
import numpy as np
import requests

sys.path.insert(0, r"D:\挑战杯\1\vision_only\src\utils")
from VL import ImageAnalyzer

CAPTURE_URL = "http://192.168.137.167/capture"

def capture():
    try:
        resp = requests.get(CAPTURE_URL, timeout=10)
        if resp.status_code == 200:
            return cv2.imdecode(np.frombuffer(resp.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"捕获失败: {e}")
    return None

print("固定 ROI 设置工具")
print("请确保摄像头已对准计数器面板，按 Enter 捕获，按 q 退出")
print("-" * 50)

analyzer = ImageAnalyzer()
analyzer.init()

cv2.namedWindow("Set Fixed ROI", cv2.WINDOW_NORMAL)

while True:
    frame = capture()
    if frame is None:
        print("无法获取图像，请检查 ESP32 连接")
        input("按 Enter 重试...")
        continue
    
    # 用当前算法定位面板
    panel = analyzer._locate_counter_panel(frame)
    display = frame.copy()
    
    if panel:
        px, py, pw, ph = panel
        cv2.rectangle(display, (px, py), (px+pw, py+ph), (0, 255, 0), 2)
        cv2.putText(display, f"Panel: ({px},{py},{pw},{ph})", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        print(f"当前面板位置: ({px}, {py}, {pw}, {ph})")
    else:
        cv2.putText(display, "Panel not found", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        print("未检测到面板")
    
    cv2.imshow("Set Fixed ROI", display)
    key = cv2.waitKey(500) & 0xFF
    
    if key == ord('q'):
        break
    elif key == ord('s') and panel:
        # 保存固定 ROI
        roi_code = f"({px}, {py}, {pw}, {ph})"
        print(f"\n>>> 固定 ROI 已保存: {roi_code}")
        print(f">>> 请将此值写入 VL.py 中 ImageAnalyzer.__init__ 的 self._fixed_roi")
        print(f">>> 或运行: analyzer._fixed_roi = {roi_code}")
        # 测试一次
        analyzer._fixed_roi = panel
        test_panel = analyzer._locate_counter_panel(frame)
        print(f">>> 测试定位结果: {test_panel}")
        break

cv2.destroyAllWindows()
print("已退出")
