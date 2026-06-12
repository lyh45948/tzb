# OpenMV摄像头拍照并通过USB串口发送到电脑
# 用于货物识别和计数器识别

import sensor
import image
import time
import pyb
import ustruct

# 初始化摄像头
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)  # 320x240
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# 初始化USB虚拟串口
usb = pyb.USB_VCP()

# LED指示灯
led_red = pyb.LED(1)
led_green = pyb.LED(2)

# 初始化时钟
clock = time.clock()

# 图像质量（压缩用）
JPEG_QUALITY = 70

print("OpenMV货物识别摄像头已启动")
print("等待电脑端命令...")
print("命令格式:")
print("  'capture' - 拍照并发送")
print("  'stream' - 开始/停止视频流")
print("  'quality:X' - 设置JPEG质量(1-100)")

streaming = False
last_cmd_time = time.ticks_ms()

def send_image(img):
    """发送图像到电脑"""
    # 压缩为JPEG
    jpeg = img.compress(quality=JPEG_QUALITY)

    # 发送图像大小（4字节）
    size = len(jpeg)
    usb.write(ustruct.pack('<I', size))

    # 发送JPEG数据
    usb.write(jpeg)

    # 发送校验和
    checksum = sum(jpeg) & 0xFF
    usb.write(bytes([checksum]))

    return size

def process_command(cmd):
    """处理命令"""
    global streaming, JPEG_QUALITY

    if cmd == "capture":
        led_red.on()
        img = sensor.snapshot()
        size = send_image(img)
        led_red.off()
        print(f"图像已发送: {size} 字节")
        return True

    elif cmd == "stream":
        streaming = not streaming
        state = "开启" if streaming else "关闭"
        print(f"视频流: {state}")
        return True

    elif cmd.startswith("quality:"):
        try:
            q = int(cmd.split(":")[1])
            if 1 <= q <= 100:
                JPEG_QUALITY = q
                print(f"JPEG质量已设置为: {q}")
            else:
                print("质量范围: 1-100")
        except:
            print("无效的质量值")
        return True

    elif cmd == "ping":
        usb.write(b"PONG\n")
        return True

    elif cmd == "info":
        info = f"RES:{sensor.width()}x{sensor.height()}\n"
        info += f"QUALITY:{JPEG_QUALITY}\n"
        usb.write(info.encode())
        return True

    return False

# 主循环
while True:
    clock.tick()

    # 检查USB命令
    if usb.any():
        try:
            cmd = usb.readline().decode().strip()
            if cmd:
                last_cmd_time = time.ticks_ms()
                process_command(cmd)
        except Exception as e:
            print(f"命令处理错误: {e}")

    # 视频流模式
    if streaming:
        led_green.on()
        img = sensor.snapshot()
        send_image(img)
        led_green.off()
        time.sleep_ms(50)  # 约20fps

    # 空闲时闪烁LED表示就绪
    if time.ticks_diff(time.ticks_ms(), last_cmd_time) > 3000:
        if time.ticks_ms() % 2000 < 100:
            led_green.on()
        else:
            led_green.off()

    time.sleep_ms(10)
