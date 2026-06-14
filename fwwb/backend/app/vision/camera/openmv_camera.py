"""OpenMV 串口摄像头

OpenMV H7 通过 USB 虚拟串口（VCP）跟后端通信。OpenMV 板侧需运行
`tools/openmv/openmv_camera.py` 固件，等待 PC 端发送命令：

    capture\n      捕获并发送一帧 JPEG
    stream\n       视频流模式切换
    quality:X\n    设置 JPEG 质量

PC 端读到的串口字节序列里包含 JPEG 数据（FF D8 ... FF D9）。这里直接
扫描 SOI/EOI 标记取出 JPEG，然后用 cv2.imdecode 转成 BGR ndarray，
对接 BaseCamera 契约（capture_frame 返回 BGR ndarray）。

参考：tools/openmv/openmv_receiver.py 的 receive_image 协议实现。
为后端服务化做了：
- 抽掉 ultralytics/sys.path 等无关依赖
- 串口操作加锁，多线程安全（VisionService 同时跑 obstacle/counter 两条循环时不会撕裂数据）
- 自动扫描串口（描述含 USB / OpenMV / CDC）
- start() 失败不抛异常；OpenMV 没插也不会让整个 VisionService 崩
"""
import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

from app.vision.camera.base import BaseCamera

try:
    import serial
    import serial.tools.list_ports
    _HAS_SERIAL = True
except ImportError:  # pragma: no cover
    serial = None  # type: ignore
    _HAS_SERIAL = False

logger = logging.getLogger(__name__)


class OpenMVCamera(BaseCamera):
    """OpenMV USB 串口摄像头"""

    # JPEG 单帧大小上限（防止串口异常时无界累积）
    _MAX_JPEG_SIZE = 500_000
    # 抓帧之间的最小等待，避免占满串口
    _MIN_FRAME_INTERVAL = 0.05

    def __init__(self, port: Optional[str] = None,
                 baudrate: int = 115200,
                 capture_timeout: float = 3.0,
                 fps: int = 1):
        self.port = port  # None → 自动扫描
        self.baudrate = int(baudrate)
        self.capture_timeout = float(capture_timeout)
        self.fps = max(int(fps), 1)

        self._serial: Optional["serial.Serial"] = None
        self._serial_lock = threading.Lock()  # 保护串口读写
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lifecycle_lock = threading.Lock()
        # 日志节流（避免无板时按 1Hz 刷屏）
        self._last_no_port_log = 0.0
        self._last_open_fail_log = 0.0

    # ─── BaseCamera 接口 ───

    def start(self) -> bool:
        with self._lifecycle_lock:
            if not _HAS_SERIAL:
                logger.error("未安装 pyserial，OpenMV 摄像头无法启动")
                return False
            if self._thread is not None and self._thread.is_alive():
                logger.debug("OpenMV 摄像头线程已在运行")
                return self._running

            if not self._open_serial():
                return False

            self._running = True
            self._thread = threading.Thread(
                target=self._capture_loop, daemon=True, name='OpenMVCameraThread')
            self._thread.start()

            # 等待首帧（最多 capture_timeout + 1s）
            deadline = time.time() + self.capture_timeout + 1.0
            while time.time() < deadline:
                with self._frame_lock:
                    if self._latest_frame is not None:
                        return True
                time.sleep(0.1)
            logger.warning(f"OpenMV 启动 {self.capture_timeout + 1}s 内未拿到首帧（板上是否运行 openmv_camera.py？）")
            # 即使首帧没拿到，线程仍在跑，下一次 capture 仍可能成功
            return self._running

    def stop(self) -> bool:
        with self._lifecycle_lock:
            self._running = False
            if self._thread is not None and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._thread = None
            self._close_serial()
            return True

    def capture_frame(self) -> Optional[np.ndarray]:
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def on_demand_capture(self) -> Optional[np.ndarray]:
        """同步抓一帧。后台线程未跑时 VisionService 会调这个，
        所以这里也要能在不依赖 capture_loop 的情况下工作。"""
        if self._serial is None or not self._serial.is_open:
            if not self._open_serial():
                return None
        frame = self._capture_one()
        if frame is not None:
            with self._frame_lock:
                self._latest_frame = frame.copy()
        return frame

    # ─── 内部 ───

    def _find_port(self) -> Optional[str]:
        """扫描串口，返回第一个像 OpenMV 的"""
        if not _HAS_SERIAL:
            return None
        try:
            ports = list(serial.tools.list_ports.comports())
        except Exception as e:
            logger.error(f"枚举串口失败: {e}")
            return None
        for p in ports:
            desc = (p.description or '') + ' ' + (p.hwid or '')
            if any(key in desc for key in ('USB', 'OpenMV', 'CDC', 'ACM')):
                return p.device
        return None

    def _open_serial(self) -> bool:
        if self.port is None:
            self.port = self._find_port()
            if self.port is None:
                # 节流：避免 capture 循环 1Hz 反复打 ERROR 刷屏
                now = time.time()
                if now - self._last_no_port_log > 30:
                    logger.error("未找到 OpenMV 串口设备（描述需包含 USB/OpenMV/CDC/ACM）")
                    self._last_no_port_log = now
                return False

        try:
            self._serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.capture_timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            time.sleep(2.0)  # OpenMV 复位后需要时间稳定
            logger.info(f"OpenMV 已连接: port={self.port} baud={self.baudrate}")
            return True
        except Exception as e:
            now = time.time()
            if now - self._last_open_fail_log > 30:
                logger.error(f"打开串口 {self.port} 失败: {e}")
                self._last_open_fail_log = now
            self._serial = None
            return False

    def _close_serial(self):
        with self._serial_lock:
            try:
                if self._serial is not None and self._serial.is_open:
                    self._serial.close()
            except Exception as e:
                logger.warning(f"关闭串口异常: {e}")
            finally:
                self._serial = None

    def _capture_loop(self):
        sleep_interval = max(1.0 / self.fps, self._MIN_FRAME_INTERVAL)
        consecutive_fail = 0
        while self._running:
            t0 = time.time()
            try:
                frame = self._capture_one()
                if frame is not None:
                    consecutive_fail = 0
                    with self._frame_lock:
                        self._latest_frame = frame
                else:
                    consecutive_fail += 1
                    if consecutive_fail % 5 == 0:
                        logger.warning(f"OpenMV 连续 {consecutive_fail} 次抓帧失败")
            except Exception as e:
                consecutive_fail += 1
                logger.error(f"OpenMV 采集异常: {e}")

            elapsed = time.time() - t0
            remain = sleep_interval - elapsed
            if remain > 0:
                time.sleep(remain)
        logger.info("OpenMV 摄像头采集线程已结束")

    def _capture_one(self) -> Optional[np.ndarray]:
        """同步抓一帧并解码为 BGR ndarray。失败返回 None。"""
        with self._serial_lock:
            ser = self._serial
            if ser is None or not ser.is_open:
                return None
            try:
                # 清空缓冲，避免读到上一次的残留
                if ser.in_waiting:
                    ser.read(ser.in_waiting)
                ser.write(b"capture\n")
                ser.flush()
            except Exception as e:
                logger.error(f"串口写入失败: {e}")
                return None

            # 等 OpenMV 把图像写到串口
            time.sleep(0.3)

            all_data = bytearray()
            start_time = time.time()
            try:
                while time.time() - start_time < self.capture_timeout:
                    waiting = ser.in_waiting
                    if waiting:
                        all_data.extend(ser.read(waiting))
                        time.sleep(0.05)
                    else:
                        if all_data:
                            break
                        time.sleep(0.01)
            except Exception as e:
                logger.error(f"串口读取失败: {e}")
                return None

        # 串口锁释放后再做 CPU 密集的解码，让其它线程有机会调度
        if not all_data:
            return None
        return self._decode_jpeg(bytes(all_data))

    @classmethod
    def _decode_jpeg(cls, data: bytes) -> Optional[np.ndarray]:
        # 扫描 JPEG SOI(FF D8) 与 EOI(FF D9)
        soi = data.find(b'\xff\xd8')
        if soi < 0:
            # 大概率板侧 openmv_camera.py 没运行，串口回了文字
            try:
                text = data[:128].decode('utf-8', errors='ignore').strip()
                if text:
                    logger.warning(f"OpenMV 返回非图像数据：{text!r}")
            except Exception:
                pass
            return None
        eoi = data.find(b'\xff\xd9', soi + 2)
        if eoi < 0:
            logger.warning(f"JPEG 不完整，已收到 {len(data) - soi} 字节，未见 EOI")
            return None
        jpeg = data[soi:eoi + 2]
        if len(jpeg) > cls._MAX_JPEG_SIZE:
            logger.warning(f"JPEG 过大 ({len(jpeg)} 字节)，丢弃")
            return None
        arr = np.frombuffer(jpeg, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("cv2.imdecode 解码失败")
        return frame
