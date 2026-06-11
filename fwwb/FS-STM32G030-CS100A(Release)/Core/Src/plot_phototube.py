import serial
import struct
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import collections
import numpy as np
import csv
import time
from datetime import datetime

# --- 配置参数 ---
SERIAL_PORT = 'COM10'  # 请根据实际情况修改串口号 (例如 'COM3' 或 '/dev/ttyUSB0')
BAUD_RATE = 115200     # 需与 STM32 配置一致 (当前 STM32 USART1 为 115200)
CHANNEL_COUNT = 7      # 7路光电管
DATA_POINTS = 100      # 屏幕显示的采样点数
SAVE_FILENAME = f"adc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# 初始化数据结构
# 使用双端队列存储最近的 N 个采样值，用于滚动显示
data_history = [collections.deque([0] * DATA_POINTS, maxlen=DATA_POINTS) for _ in range(CHANNEL_COUNT)]

# 初始化 CSV 文件
try:
    log_file = open(SAVE_FILENAME, mode='w', newline='')
    csv_writer = csv.writer(log_file)
    # 写入表头
    header = ['Timestamp'] + [f'Sensor_{i}' for i in range(CHANNEL_COUNT)]
    csv_writer.writerow(header)
    print(f"数据将保存至: {SAVE_FILENAME}")
except Exception as e:
    print(f"无法创建日志文件: {e}")
    exit()

# 初始化串口
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"成功打开串口: {SERIAL_PORT}")
except Exception as e:
    print(f"无法打开串口: {e}")
    print("提示: 请检查串口号是否正确，以及是否有其他程序占用该串口。")
    exit()

# 创建画布
fig, ax = plt.subplots(figsize=(12, 7))
lines = []
# 使用新的 colormap 获取方式
colors = plt.colormaps['tab10'] 

for i in range(CHANNEL_COUNT):
    line, = ax.plot([], [], label=f'Sensor {i}', color=colors(i % 10), linewidth=1.5)
    lines.append(line)

ax.set_xlim(0, DATA_POINTS)
ax.set_ylim(-100, 4200)  # STM32 ADC 是 12 位，范围 0-4095
ax.set_title("7-Channel Phototube ADC Real-time Data Visualization", fontsize=14)
ax.set_xlabel("Time Samples", fontsize=12)
ax.set_ylabel("ADC Raw Value", fontsize=12)
ax.legend(loc='upper right', ncol=2)
ax.grid(True, linestyle='--', alpha=0.6)

def update(frame):
    """动画更新函数"""
    if ser.in_waiting > 0:
        # print(f"当前缓冲区字节数: {ser.in_waiting}")
        pass

    # 尽可能多地读取并处理缓冲区中的数据
    while ser.in_waiting > 0:
        # 搜索帧头 0xCC
        header = ser.read(1)
        if header == b'\xcc':
            # 找到了帧头，等待并读取后续 15 字节
            # 使用阻塞读取（带 timeout）来确保读到完整包
            payload = ser.read(15)
            if len(payload) == 15:
                # 校验数据
                checksum_received = payload[14]
                # 计算校验和 (0xCC + 前14个字节)
                checksum_calc = (0xCC + sum(payload[:14])) & 0xFF
                
                if checksum_received == checksum_calc:
                    # 解析 7 路 uint16 数据 (大端模式 '>HHHHHHH')
                    try:
                        raw_values = struct.unpack('>HHHHHHH', payload[:14])
                        # 更新数据队列
                        for i in range(CHANNEL_COUNT):
                            data_history[i].append(raw_values[i])
                        
                        # 保存数据到 CSV
                        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                        csv_writer.writerow([timestamp] + list(raw_values))
                    except struct.error:
                        pass
                else:
                    print(f"校验错误: 期望 {hex(checksum_calc)}, 收到 {hex(checksum_received)}")
            else:
                print(f"数据包长度不足: 收到 {len(payload)} 字节")
        else:
            # 不是帧头，继续搜索（跳过 0xFF 和 0xAA 数据包）
            pass

    # 更新绘图线条数据
    for i in range(CHANNEL_COUNT):
        lines[i].set_data(range(DATA_POINTS), list(data_history[i]))
    
    return lines

# 启动动画
# interval=20 表示约 50FPS，blit=True 提高渲染效率
ani = FuncAnimation(fig, update, interval=20, blit=True, cache_frame_data=False)

print("正在绘图... 按 Ctrl+C 退出。")

try:
    plt.tight_layout()
    plt.show()
except KeyboardInterrupt:
    print("\n用户中断程序。")
finally:
    if 'log_file' in locals():
        log_file.close()
        print(f"数据已保存至 {SAVE_FILENAME}")
    if ser.is_open:
        ser.close()
        print("串口已关闭。")

