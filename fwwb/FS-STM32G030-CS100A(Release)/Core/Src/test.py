import serial
import time

# --- 配置参数 ---
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200 

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    print(f"正在监听 {SERIAL_PORT} @ {BAUD_RATE}...")
    print("将显示原始数据的十六进制 (HEX) 和尝试解码的文本:\n")
    
    while True:
        if ser.in_waiting > 0:
            # 读取当前缓冲区所有数据
            raw_data = ser.read(ser.in_waiting)
            
            # 显示十六进制
            hex_str = ' '.join([f'{b:02X}' for b in raw_data])
            # 尝试解码为 ASCII
            ascii_str = raw_data.decode('ascii', errors='replace').replace('\n', '\\n').replace('\r', '\\r')
            
            print(f"[HEX]: {hex_str}")
            print(f"[TXT]: {ascii_str}")
            print("-" * 20)
            
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n停止监听。")
except Exception as e:
    print(f"错误: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()