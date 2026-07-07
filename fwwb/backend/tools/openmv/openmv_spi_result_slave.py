# WT OpenMV SPI 结果帧示例脚本
#
# 运行位置：OpenMV IDE 中保存为 OpenMV 板载 main.py。
# 作用：在 OpenMV 本地完成识别，通过 SPI 从机模式把紧凑结果帧交给 Hi3861。
# 注意：不同 OpenMV/MicroPython 固件对 SPI 从机 API 支持不同；如果运行时报
# SPI.SLAVE/send_recv 相关错误，请在 OpenMV IDE 中按当前固件 API 调整 SPI 初始化。

import sensor
import time
import struct
from pyb import LED, SPI

SPI_BUS = 2
MAX_OBSTACLES = 4
COUNTER_LEN = 6
OBSTACLE_SIZE = 8
HEADER_SIZE = 13
PAYLOAD_SIZE = HEADER_SIZE + MAX_OBSTACLES * OBSTACLE_SIZE
FRAME_SIZE = PAYLOAD_SIZE + 1


led = LED(1)


def crc8(data):
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def build_frame(frame_counter, obstacles=None, counter="000000", valid=True):
    obstacles = obstacles or []
    buf = bytearray(FRAME_SIZE)
    buf[0] = 0x5A
    buf[1] = 0xA5
    buf[2] = 1
    buf[3] = 0x01 if valid else 0x00
    buf[4] = min(len(obstacles), MAX_OBSTACLES)

    for index, obs in enumerate(obstacles[:MAX_OBSTACLES]):
        offset = 5 + index * OBSTACLE_SIZE
        distance = int(obs.get("distance", 0))
        buf[offset] = int(obs.get("class_id", 0)) & 0xFF
        buf[offset + 1] = int(obs.get("confidence", 0)) & 0xFF
        buf[offset + 2] = int(obs.get("x", 0)) & 0xFF
        buf[offset + 3] = int(obs.get("y", 0)) & 0xFF
        buf[offset + 4] = int(obs.get("w", 0)) & 0xFF
        buf[offset + 5] = int(obs.get("h", 0)) & 0xFF
        struct.pack_into("<H", buf, offset + 6, max(0, min(distance, 65535)))

    counter_offset = 5 + MAX_OBSTACLES * OBSTACLE_SIZE
    digits = (str(counter)[:COUNTER_LEN]).encode("ascii", "ignore")
    for index in range(COUNTER_LEN):
        buf[counter_offset + index] = digits[index] if index < len(digits) else 0
    struct.pack_into("<H", buf, counter_offset + COUNTER_LEN, frame_counter & 0xFFFF)
    buf[PAYLOAD_SIZE] = crc8(buf[:PAYLOAD_SIZE])
    return buf


def detect_result(img, frame_counter):
    # TODO: 在这里替换成真实识别逻辑，例如颜色块、二维码、AprilTag、数字识别等。
    # 当前示例返回固定障碍物和递增计数，便于先打通 Hi3861/后端链路。
    return [
        {
            "class_id": 1,
            "confidence": 86,
            "x": 120,
            "y": 80,
            "w": 40,
            "h": 30,
            "distance": 350,
        }
    ], "%06d" % (frame_counter % 1000000)


def init_camera():
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)
    sensor.set_framesize(sensor.QVGA)
    sensor.skip_frames(time=2000)


def init_spi():
    # Hi3861 当前配置为 SPI mode 0：CPOL=0, CPHA=0, 8bit。
    # OpenMV H7 常见 SPI(2) 引脚需按实际板卡丝印/说明书连接到 Hi3861 SPI1。
    return SPI(SPI_BUS, SPI.SLAVE, polarity=0, phase=0)


init_camera()
spi = init_spi()
frame_counter = 0
result_frame = build_frame(frame_counter, [], "000000", valid=False)
rx_dummy = bytearray(FRAME_SIZE)
clock = time.clock()
last_led_tick = time.ticks_ms()

while True:
    clock.tick()
    img = sensor.snapshot()
    obstacles, counter = detect_result(img, frame_counter)
    result_frame = build_frame(frame_counter, obstacles, counter, valid=True)
    frame_counter = (frame_counter + 1) & 0xFFFF

    # Hi3861 为 SPI 主机，会发送 FRAME_SIZE 个 dummy 字节产生时钟；
    # OpenMV 在同一次全双工事务中把 result_frame 从 MISO 发出。
    try:
        spi.send_recv(result_frame, rx_dummy, timeout=2)
    except OSError:
        pass

    now = time.ticks_ms()
    if time.ticks_diff(now, last_led_tick) > 500:
        led.toggle()
        last_led_tick = now

    time.sleep_ms(10)
