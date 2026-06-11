"""
交互式 LED 数码管标注脚本
用法: 运行后逐张显示实拍图，输入看到的数字即可自动提取单字符ROI
"""
import os
import cv2
import numpy as np
from glob import glob

IMG_DIR = r"D:\挑战杯\1\captured_images"
OUT_DIR = r"D:\挑战杯\11\led_digit_cls"
PREVIEW_DIR = r"D:\挑战杯\1\captured_images\previews"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

# 创建 0-9 + blank 目录
for name in ['0','1','2','3','4','5','6','7','8','9','blank']:
    os.makedirs(os.path.join(OUT_DIR, name), exist_ok=True)

def locate_panel(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0, 60, 60]), np.array([15, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([155, 60, 60]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(m1, m2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    best = max(contours, key=cv2.contourArea)
    if cv2.contourArea(best) < 500:
        return None
    return cv2.boundingRect(best)

def draw_preview(img, panel):
    px, py, pw, ph = panel
    cell_w = pw / 6.0
    preview = img.copy()
    cv2.rectangle(preview, (px, py), (px+pw, py+ph), (0, 255, 0), 2)
    for i in range(7):
        xs = int(px + i * cell_w)
        cv2.line(preview, (xs, py), (xs, py+ph), (0, 255, 0), 1)
    for i in range(6):
        xs = int(px + i * cell_w)
        xe = int(px + (i + 1) * cell_w) if i < 5 else px + pw
        cx = (xs + xe) // 2
        cy = py + ph // 2
        cv2.putText(preview, str(i+1), (cx-5, py+20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(preview, "Input digits (right-aligned)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return preview

def save_roi(img, panel, fname, digits_str):
    px, py, pw, ph = panel
    cell_w = pw / 6.0
    
    # 右对齐到6位: 用户输入 "22" -> [blank, blank, blank, blank, '2', '2']
    aligned = ['blank'] * 6
    for i, ch in enumerate(reversed(digits_str)):
        if i >= 6:
            break
        aligned[5 - i] = ch
    
    saved = []
    for i, ch in enumerate(aligned):
        xs = int(px + i * cell_w)
        xe = int(px + (i + 1) * cell_w) if i < 5 else px + pw
        roi = img[py:py+ph, xs:xe]
        if roi.size == 0:
            continue
        roi_r = cv2.resize(roi, (64, 64), interpolation=cv2.INTER_AREA)
        out_path = os.path.join(OUT_DIR, ch, f"{fname}_{i}.png")
        _, buf = cv2.imencode('.png', roi_r)
        buf.tofile(out_path)
        saved.append(ch)
    return saved

def main():
    # 获取所有待标注的实拍图（排除已生成的预览/captcha/cv图）
    all_imgs = sorted(glob(os.path.join(IMG_DIR, "esp32_capture_*.jpg")))
    imgs = [p for p in all_imgs 
            if not os.path.basename(p).startswith("captcha_") 
            and not p.endswith("_cv.jpg")]
    
    # 过滤掉已经标注过的（检查输出目录中是否有该文件名前缀）
    def is_labeled(fname):
        base = os.path.splitext(fname)[0]
        for cls in ['0','1','2','3','4','5','6','7','8','9','blank']:
            d = os.path.join(OUT_DIR, cls)
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.startswith(base + "_"):
                        return True
        return False
    
    imgs = [p for p in imgs if not is_labeled(os.path.basename(p))]
    total = len(imgs)
    
    print(f"=" * 50)
    print(f"LED 数码管交互式标注工具")
    print(f"=" * 50)
    print(f"待标注图片: {total} 张")
    print(f"格子编号:  1   2   3   4   5   6")
    print(f"           [ ][ ][ ][ ][ ][ ]")
    print(f"你输入的数字会自动右对齐到格子 6,5,4...")
    print(f"例如输入 '22'  ->  [blank][blank][blank][blank]['2']['2']")
    print(f"输入 '123' ->  [blank][blank][blank]['1']['2']['3']")
    print(f"直接回车=跳过, q=退出")
    print(f"=" * 50)
    
    labeled_count = 0
    
    for idx, img_path in enumerate(imgs, 1):
        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        panel = locate_panel(img)
        if panel is None:
            print(f"[{idx}/{total}] {os.path.basename(img_path)}: 未检测到面板，跳过")
            continue
        
        preview = draw_preview(img, panel)
        fname = os.path.basename(img_path)
        
        # 保存预览图供参考
        preview_path = os.path.join(PREVIEW_DIR, f"preview_{fname}")
        _, buf = cv2.imencode('.jpg', preview)
        buf.tofile(preview_path)
        
        # 显示图片窗口
        cv2.imshow("LED Digit Labeler", preview)
        cv2.waitKey(1)
        
        print(f"\n[{idx}/{total}] {fname}")
        user_input = input("输入实际数字: ").strip()
        
        cv2.destroyWindow("LED Digit Labeler")
        
        if user_input.lower() == 'q':
            print("已退出")
            break
        if not user_input:
            print("  -> 跳过")
            continue
        if not user_input.isdigit():
            print("  -> 非法输入，跳过")
            continue
        
        saved = save_roi(img, panel, os.path.splitext(fname)[0], user_input)
        labeled_count += 1
        print(f"  -> 已保存: {saved}")
    
    print(f"\n标注完成！本次标注 {labeled_count} 张图")
    
    # 统计各类别数量
    print(f"\n当前各类别样本数:")
    for cls in ['0','1','2','3','4','5','6','7','8','9','blank']:
        d = os.path.join(OUT_DIR, cls)
        n = len([f for f in os.listdir(d) if f.endswith('.png')]) if os.path.exists(d) else 0
        print(f"  {cls}: {n}")

if __name__ == "__main__":
    main()
