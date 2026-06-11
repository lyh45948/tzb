#!/usr/bin/env python3
import termios, fcntl, os, sys, time

def read_port(path, baud, label):
    print(f"\n--- Testing {path} at {baud} ({label}) ---")
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
        attrs = termios.tcgetattr(fd)
        
        baud_const = {
            230400: termios.B230400,
            460800: termios.B460800,
        }.get(baud, termios.B230400)
        
        attrs[4] = baud_const
        attrs[5] = baud_const
        attrs[2] = attrs[2] & ~termios.PARENB & ~termios.CSTOPB & ~termios.CSIZE | termios.CS8
        attrs[2] = attrs[2] | termios.CLOCAL | termios.CREAD
        attrs[0] = attrs[0] & ~termios.ICRNL & ~termios.INLCR & ~termios.IGNCR
        attrs[1] = 0
        attrs[3] = attrs[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ECHOE & ~termios.ISIG
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 1
        
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
        termios.tcflush(fd, termios.TCIOFLUSH)
        
        time.sleep(0.3)
        
        data = b''
        start = time.time()
        while time.time() - start < 1.0:
            try:
                chunk = os.read(fd, 256)
                if chunk:
                    data += chunk
            except BlockingIOError:
                time.sleep(0.05)
        
        os.close(fd)
        
        if len(data) == 0:
            print("  No data received (0 bytes)")
            return False
        else:
            print(f"  Received {len(data)} bytes")
            hex_str = " ".join(f"{b:02x}" for b in data[:32])
            print(f"  First 32 bytes (hex): {hex_str}")
            if data[0] == 0x54:
                print("  >>> Possible LD06 lidar (header 0x54)")
            if data[0] == 0x5a:
                print("  >>> Possible Yesense IMU (header 0x5a)")
            return True
            
    except Exception as e:
        print(f"  Error: {e}")
        return False

results = {}
for port, baud, label in [
    ("/dev/ttyCH343USB0", 230400, "lidar_baud"),
    ("/dev/ttyCH343USB0", 460800, "imu_baud"),
    ("/dev/ttyCH343USB1", 230400, "lidar_baud"),
    ("/dev/ttyCH343USB1", 460800, "imu_baud"),
]:
    has_data = read_port(port, baud, label)
    results[(port, baud)] = has_data

print("\n=== Summary ===")
for (port, baud), has_data in results.items():
    status = "DATA" if has_data else "NO DATA"
    print(f"{port} @ {baud}: {status}")
