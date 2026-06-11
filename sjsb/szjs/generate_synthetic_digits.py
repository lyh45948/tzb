"""
生成合成七段码训练数据，补充真实 LED 样本
关键改进：模拟真实拍摄中的低分辨率+放大过程
"""
import os
import cv2
import numpy as np

OUT_DIR = r"D:\挑战杯\11\led_digit_cls"

def draw_7seg(img, digit, color, offset=(0,0)):
    """在图像上绘制七段码数字"""
    h, w = img.shape[:2]
    pad = 4
    t = max(3, min(h, w) // 8)  # 段厚度
    ox, oy = offset
    
    # 关键点坐标
    x0, x1, x2 = ox + pad, ox + w//2, ox + w - pad
    y0, y1, y2 = oy + pad, oy + h//2, oy + h - pad
    
    # 7个段定义: (x1,y1,x2,y2) 矩形
    segs = [
        (x0+t, y0, x2-t, y0+t),      # 0 top
        (x2-t, y0+t, x2, y1-t),       # 1 upper-right
        (x2-t, y1+t, x2, y2-t),       # 2 lower-right
        (x0+t, y2-t, x2-t, y2),       # 3 bottom
        (x0, y1+t, x0+t, y2-t),       # 4 lower-left
        (x0, y0+t, x0+t, y1-t),       # 5 upper-left
        (x0+t, y1-t//2, x2-t, y1+t//2), # 6 middle
    ]
    
    digits_map = {
        '0': [0,1,2,3,4,5], '1': [1,2], '2': [0,1,6,4,3],
        '3': [0,1,6,2,3], '4': [5,6,1,2], '5': [0,5,6,2,3],
        '6': [0,5,6,4,2,3], '7': [0,1,2], '8': [0,1,2,3,4,5,6],
        '9': [0,1,2,3,5,6],
    }
    
    for seg_id in digits_map.get(str(digit), []):
        x1, y1, x2, y2 = segs[seg_id]
        cv2.rectangle(img, (x1, y1), (x2, y2), color, -1, cv2.LINE_AA)

def generate_digit(digit, size=(64, 64)):
    """生成单张合成数字图（模拟低分辨率实拍效果）"""
    # 先生成高分辨率图，再缩小模拟低分辨率，最后放大回64x64
    # 这样可以让模型学习从模糊/块状图像中识别数字
    
    # 1. 生成清晰的高分辨率图（128x128）
    hires = np.full((128, 128, 3), np.random.randint(15, 50), dtype=np.uint8)
    
    r = np.random.randint(160, 255)
    g = np.random.randint(0, 80)
    b = np.random.randint(0, 50)
    color = (b, g, r)
    
    offset_x = np.random.randint(-8, 9)
    offset_y = np.random.randint(-8, 9)
    draw_7seg(hires, digit, color, offset=(offset_x, offset_y))
    
    # 2. 随机缩小到 20-50px（模拟真实拍摄中的低分辨率面板）
    small_w = np.random.randint(20, 55)
    small_h = np.random.randint(30, 70)
    small = cv2.resize(hires, (small_w, small_h), interpolation=cv2.INTER_AREA)
    
    # 3. 强模糊（模拟摄像头光学模糊 + 低分辨率）
    k = np.random.choice([3, 5, 7, 9])
    small = cv2.GaussianBlur(small, (k, k), np.random.uniform(0.5, 3.0))
    
    # 4. resize 回 64x64（模拟从完整图裁剪后的放大）
    img = cv2.resize(small, size, interpolation=cv2.INTER_AREA)
    
    # 5. 强噪声（模拟 sensor 噪声）
    noise = np.random.normal(0, np.random.uniform(5, 35), img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # 6. 随机亮度/对比度（模拟过曝和欠曝）
    alpha = np.random.uniform(0.5, 1.8)
    beta = np.random.uniform(-30, 30)
    img = np.clip(img.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
    
    # 7. 随机压缩 artifacts（模拟 JPEG 压缩）
    if np.random.rand() > 0.3:
        quality = np.random.randint(30, 80)
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    
    return img

def generate_blank(size=(64, 64)):
    """生成 blank 样本（暗背景 + 少量噪声）"""
    bg = np.random.randint(5, 30)
    img = np.full((*size, 3), bg, dtype=np.uint8)
    noise = np.random.normal(0, np.random.uniform(2, 12), img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return img

if __name__ == "__main__":
    N_PER_CLASS = 400  # 每类生成400个
    
    for digit in range(10):
        cls_dir = os.path.join(OUT_DIR, str(digit))
        os.makedirs(cls_dir, exist_ok=True)
        # 删除旧的合成数据，重新生成
        for f in os.listdir(cls_dir):
            if f.startswith('syn_'):
                os.remove(os.path.join(cls_dir, f))
        for i in range(N_PER_CLASS):
            img = generate_digit(digit)
            path = os.path.join(cls_dir, f"syn_{i:04d}.png")
            _, buf = cv2.imencode('.png', img)
            buf.tofile(path)
        print(f"  {digit}: generated {N_PER_CLASS} synthetic")
    
    # blank
    cls_dir = os.path.join(OUT_DIR, 'blank')
    os.makedirs(cls_dir, exist_ok=True)
    for f in os.listdir(cls_dir):
        if f.startswith('syn_'):
            os.remove(os.path.join(cls_dir, f))
    for i in range(N_PER_CLASS):
        img = generate_blank()
        path = os.path.join(cls_dir, f"syn_{i:04d}.png")
        _, buf = cv2.imencode('.png', img)
        buf.tofile(path)
    print(f"  blank: generated {N_PER_CLASS} synthetic")
    
    print("\n合成数据生成完成!")
