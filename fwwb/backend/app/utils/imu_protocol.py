"""
IMU YIS 协议解析器
支持 Yesense H30 (YIS106) 的串口输出协议解析

帧格式:
    header1(0x59) + header2(0x53) + tid_low + tid_high + payload_len + payload + ck1 + ck2

Payload 内部采用 TLV (Type-Length-Value) 结构
"""
import struct
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable
from enum import IntEnum
from app.utils.logger import get_logger

logger = get_logger('imu_protocol')


class DataID(IntEnum):
    """YIS Payload Data ID 表"""
    TEMPERATURE = 0x01      # IMU 温度, 2B, °C, ×0.01
    ACCEL = 0x10            # 加速度 xyz, 12B, m/s², ×1e-6
    ANGLE_VEL = 0x20        # 角速度 xyz, 12B, °/s, ×1e-6
    MAG_NORMALIZED = 0x30   # 磁场（归一化）, 12B, ×1e-6
    MAG_RAW = 0x31          # 原始磁场 xyz, 12B, mGauss, ×1e-3
    EULER = 0x40            # 欧拉角 pitch/roll/yaw, 12B, °, ×1e-6
    QUATERNION = 0x41       # 四元数 q0/q1/q2/q3, 16B, ×1e-6
    UTC_TIME = 0x50         # UTC 时间, 11B
    SAMPLE_TIMESTAMP = 0x51 # 采样时间戳, 4B, μs
    READY_TIMESTAMP = 0x52  # 数据就绪时间戳, 4B, μs
    LOCATION = 0x68         # 位置（高精度）, 20B
    VELOCITY = 0x70         # 速度 vel_e/vel_n/vel_u, 12B, m/s, ×1e-3
    FUSION_STATUS = 0x80    # 融合状态, 1B
    GNSS_MAIN = 0xC0        # GNSS 主天线完整数据, 45B
    GNSS_SUB = 0xF0         # GNSS 从天线, 6B


@dataclass
class IMUData:
    """解析后的 IMU 数据结构"""
    tid: int = 0                          # 帧序号
    temperature: Optional[float] = None   # 温度 °C
    accel_x: Optional[float] = None       # 加速度 m/s²
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None        # 角速度 °/s
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    mag_x: Optional[float] = None         # 原始磁场 mGauss
    mag_y: Optional[float] = None
    mag_z: Optional[float] = None
    pitch: Optional[float] = None         # 欧拉角 °
    roll: Optional[float] = None
    yaw: Optional[float] = None
    q0: Optional[float] = None            # 四元数
    q1: Optional[float] = None
    q2: Optional[float] = None
    q3: Optional[float] = None
    fusion_status: Optional[int] = None   # 融合状态
    sample_timestamp: Optional[int] = None  # 采样时间戳 μs
    raw_payload: bytes = field(default_factory=bytes)  # 原始 payload

    def to_dict(self) -> Dict:
        """转换为字典，用于 JSON 序列化"""
        return {
            'tid': self.tid,
            'temperature': self.temperature,
            'accel': {
                'x': self.accel_x,
                'y': self.accel_y,
                'z': self.accel_z,
            } if any(v is not None for v in [self.accel_x, self.accel_y, self.accel_z]) else None,
            'gyro': {
                'x': self.gyro_x,
                'y': self.gyro_y,
                'z': self.gyro_z,
            } if any(v is not None for v in [self.gyro_x, self.gyro_y, self.gyro_z]) else None,
            'mag': {
                'x': self.mag_x,
                'y': self.mag_y,
                'z': self.mag_z,
            } if any(v is not None for v in [self.mag_x, self.mag_y, self.mag_z]) else None,
            'euler': {
                'pitch': self.pitch,
                'roll': self.roll,
                'yaw': self.yaw,
            } if any(v is not None for v in [self.pitch, self.roll, self.yaw]) else None,
            'quaternion': {
                'w': self.q0,
                'x': self.q1,
                'y': self.q2,
                'z': self.q3,
            } if any(v is not None for v in [self.q0, self.q1, self.q2, self.q3]) else None,
            'fusion_status': self.fusion_status,
            'sample_timestamp': self.sample_timestamp,
        }


class YISProtocolParser:
    """YIS 协议解析器（状态机）"""

    HEADER = bytes([0x59, 0x53])
    MIN_FRAME_LEN = 7  # header(2) + tid(2) + len(1) + ck(2)

    def __init__(self):
        self._buffer = bytearray()
        self._state = 'SYNC1'
        self._tid = 0
        self._payload_len = 0
        self._payload = bytearray()
        self.on_frame_parsed: Optional[Callable[[IMUData], None]] = None

    def reset(self):
        """重置状态机"""
        self._buffer.clear()
        self._state = 'SYNC1'
        self._tid = 0
        self._payload_len = 0
        self._payload.clear()

    def feed(self, data: bytes) -> List[IMUData]:
        """
        向解析器喂入原始字节流，返回解析出的所有完整帧
        :param data: 原始字节
        :return: IMUData 列表
        """
        self._buffer.extend(data)
        results = []
        while True:
            frame = self._try_parse_frame()
            if frame is None:
                break
            results.append(frame)
            if self.on_frame_parsed:
                try:
                    self.on_frame_parsed(frame)
                except Exception as e:
                    logger.error(f"帧解析回调异常: {e}")
        # 限制缓冲区大小，防止无限增长
        if len(self._buffer) > 4096:
            self._buffer = self._buffer[-2048:]
        return results

    def _try_parse_frame(self) -> Optional[IMUData]:
        """尝试从缓冲区解析一帧"""
        buf = self._buffer

        # 查找帧头 0x59 0x53
        idx = 0
        while idx + 1 < len(buf):
            if buf[idx] == 0x59 and buf[idx + 1] == 0x53:
                break
            idx += 1
        else:
            # 未找到完整帧头
            if len(buf) > 1:
                # 保留最后一个字节，可能是 0x59
                self._buffer = self._buffer[-1:]
            return None

        # 丢弃帧头前的垃圾数据
        if idx > 0:
            self._buffer = buf[idx:]
            buf = self._buffer
            idx = 0

        # 检查最小长度
        if len(buf) < self.MIN_FRAME_LEN:
            return None

        # 解析 tid 和 payload_len
        tid = struct.unpack_from('<H', buf, 2)[0]
        payload_len = buf[4]
        frame_len = self.MIN_FRAME_LEN + payload_len

        if len(buf) < frame_len:
            return None

        # 提取 payload 和 checksum
        payload = bytes(buf[5:5 + payload_len])
        ck1_recv = buf[5 + payload_len]
        ck2_recv = buf[6 + payload_len]

        # CRC 校验（范围：tid_low, tid_high, payload_len, payload...）
        check_data = bytes(buf[2:5 + payload_len])
        ck1_calc, ck2_calc = self._calc_checksum(check_data)

        if ck1_recv != ck1_calc or ck2_recv != ck2_calc:
            logger.debug(
                f"YIS CRC 校验失败: tid={tid}, "
                f"recv=({ck1_recv:02X},{ck2_recv:02X}), "
                f"calc=({ck1_calc:02X},{ck2_calc:02X})"
            )
            # 跳过当前帧头的一个字节，继续查找
            self._buffer = buf[1:]
            return None

        # 校验通过，消费这帧数据
        self._buffer = buf[frame_len:]

        # 解析 payload TLV
        imu_data = self._parse_payload(tid, payload)
        return imu_data

    @staticmethod
    def _calc_checksum(data: bytes) -> tuple:
        """
        计算 YIS 双字节校验和
        ck1: 累加和, ck2: ck1 的累加和 (Fletcher-8)
        """
        ck1 = 0
        ck2 = 0
        for b in data:
            ck1 = (ck1 + b) & 0xFF
            ck2 = (ck2 + ck1) & 0xFF
        return ck1, ck2

    @staticmethod
    def _parse_int32_le(data: bytes, offset: int) -> int:
        """解析小端 int32"""
        return struct.unpack_from('<i', data, offset)[0]

    def _parse_payload(self, tid: int, payload: bytes) -> IMUData:
        """解析 Payload TLV: [DataID(1B)] [DataLen(1B)] [Value(NB)] ..."""
        imu = IMUData(tid=tid, raw_payload=payload)
        offset = 0

        while offset + 1 < len(payload):
            data_id = payload[offset]
            data_len = payload[offset + 1]

            # 校验长度是否与预期一致（可选安全检查）
            expected_len = self._get_data_length(data_id)
            if expected_len and data_len != expected_len:
                logger.debug(f"DataID 0x{data_id:02X} 长度不匹配: got={data_len}, expected={expected_len}")

            if offset + 2 + data_len > len(payload):
                logger.warning(f"Payload 长度不足: id=0x{data_id:02X}, need={data_len}, remain={len(payload)-offset-2}")
                break

            value = payload[offset + 2:offset + 2 + data_len]
            self._decode_value(imu, data_id, value)
            offset += 2 + data_len

        return imu

    @staticmethod
    def _get_data_length(data_id: int) -> Optional[int]:
        """根据 DataID 获取数据长度"""
        length_map = {
            DataID.TEMPERATURE: 2,
            DataID.ACCEL: 12,
            DataID.ANGLE_VEL: 12,
            DataID.MAG_NORMALIZED: 12,
            DataID.MAG_RAW: 12,
            DataID.EULER: 12,
            DataID.QUATERNION: 16,
            DataID.UTC_TIME: 11,
            DataID.SAMPLE_TIMESTAMP: 4,
            DataID.READY_TIMESTAMP: 4,
            DataID.LOCATION: 20,
            DataID.VELOCITY: 12,
            DataID.FUSION_STATUS: 1,
            DataID.GNSS_MAIN: 45,
            DataID.GNSS_SUB: 6,
        }
        return length_map.get(data_id)

    def _decode_value(self, imu: IMUData, data_id: int, value: bytes):
        """解码单个 TLV 值"""
        try:
            if data_id == DataID.TEMPERATURE and len(value) >= 2:
                raw = struct.unpack_from('<h', value)[0]  # int16
                imu.temperature = raw * 0.01

            elif data_id == DataID.ACCEL and len(value) >= 12:
                imu.accel_x = self._parse_int32_le(value, 0) * 1e-6
                imu.accel_y = self._parse_int32_le(value, 4) * 1e-6
                imu.accel_z = self._parse_int32_le(value, 8) * 1e-6

            elif data_id == DataID.ANGLE_VEL and len(value) >= 12:
                imu.gyro_x = self._parse_int32_le(value, 0) * 1e-6
                imu.gyro_y = self._parse_int32_le(value, 4) * 1e-6
                imu.gyro_z = self._parse_int32_le(value, 8) * 1e-6

            elif data_id == DataID.MAG_RAW and len(value) >= 12:
                imu.mag_x = self._parse_int32_le(value, 0) * 1e-3
                imu.mag_y = self._parse_int32_le(value, 4) * 1e-3
                imu.mag_z = self._parse_int32_le(value, 8) * 1e-3

            elif data_id == DataID.EULER and len(value) >= 12:
                imu.pitch = self._parse_int32_le(value, 0) * 1e-6
                imu.roll = self._parse_int32_le(value, 4) * 1e-6
                imu.yaw = self._parse_int32_le(value, 8) * 1e-6

            elif data_id == DataID.QUATERNION and len(value) >= 16:
                imu.q0 = self._parse_int32_le(value, 0) * 1e-6
                imu.q1 = self._parse_int32_le(value, 4) * 1e-6
                imu.q2 = self._parse_int32_le(value, 8) * 1e-6
                imu.q3 = self._parse_int32_le(value, 12) * 1e-6

            elif data_id == DataID.SAMPLE_TIMESTAMP and len(value) >= 4:
                imu.sample_timestamp = struct.unpack_from('<I', value)[0]

            elif data_id == DataID.FUSION_STATUS and len(value) >= 1:
                imu.fusion_status = value[0]

        except struct.error as e:
            logger.warning(f"解码 DataID 0x{data_id:02X} 失败: {e}")


class IMUJSONParser:
    """
    IMU JSON 数据解析器
    用于解析通过 UDP/JSON 传来的 IMU 数据（如 Hi3861 转发）
    """

    @staticmethod
    def parse(json_data: dict) -> Optional[IMUData]:
        """
        从 JSON dict 解析 IMU 数据
        期望格式:
        {
            "imu": {
                "tid": 123,
                "temperature": 25.5,
                "accel": {"x": 0.0, "y": 0.0, "z": 9.8},
                "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
                "euler": {"pitch": 0.0, "roll": 0.0, "yaw": 0.0},
                "quaternion": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
                "fusion_status": 1
            }
        }
        """
        imu_json = json_data.get('imu')
        if not isinstance(imu_json, dict):
            return None

        imu = IMUData()
        imu.tid = imu_json.get('tid', 0)
        imu.temperature = imu_json.get('temperature')
        imu.fusion_status = imu_json.get('fusion_status')
        imu.sample_timestamp = imu_json.get('sample_timestamp')

        accel = imu_json.get('accel')
        if isinstance(accel, dict):
            imu.accel_x = accel.get('x')
            imu.accel_y = accel.get('y')
            imu.accel_z = accel.get('z')

        gyro = imu_json.get('gyro')
        if isinstance(gyro, dict):
            imu.gyro_x = gyro.get('x')
            imu.gyro_y = gyro.get('y')
            imu.gyro_z = gyro.get('z')

        mag = imu_json.get('mag')
        if isinstance(mag, dict):
            imu.mag_x = mag.get('x')
            imu.mag_y = mag.get('y')
            imu.mag_z = mag.get('z')

        euler = imu_json.get('euler')
        if isinstance(euler, dict):
            imu.pitch = euler.get('pitch')
            imu.roll = euler.get('roll')
            imu.yaw = euler.get('yaw')

        quat = imu_json.get('quaternion')
        if isinstance(quat, dict):
            imu.q0 = quat.get('w')
            imu.q1 = quat.get('x')
            imu.q2 = quat.get('y')
            imu.q3 = quat.get('z')

        return imu
