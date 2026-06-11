# 硬件数据格式手册 — H30 IMU & LD14P LiDAR

> 本文档面向 AI 编码代理与开发者，完整描述 Yesense H30 IMU 和 LDROBOT LD14P 激光雷达的串口协议、数据结构与 ROS 输出格式，便于跨终端开发与调试。

---

## 1. Yesense H30 IMU（WHEELTEC）

### 1.1 硬件接口

| 参数 | 值 |
|------|-----|
| 芯片 | YIS106（Yesense） |
| USB 转串口 | CH343 |
| 波特率 | **460800** |
| 设备路径 | `/dev/yesense_imu`（udev 符号链接） |
| 默认输出频率 | **100 Hz**（可配置 1~1000 Hz） |

### 1.2 串口输出协议（YIS 协议）

```
+--------+--------+--------+--------+--------+-----------+--------+--------+
| header1| header2|  tid   |  tid   |payload | payload   |  ck1   |  ck2   |
| 0x59   | 0x53   |  low   |  high  |  len   |  data     |        |        |
+--------+--------+--------+--------+--------+-----------+--------+--------+
   1B       1B       1B       1B       1B      N bytes      1B       1B
```

- **TID**：帧序号，范围 0~60000，用于检测丢帧
- **payload_len**：payload 数据长度，0~255 bytes
- **CRC**：校验范围从 TID 到 payload 最后一个字节
- 最小帧长：**7 bytes**（header ×2 + tid ×2 + len ×1 + ck ×2）

### 1.3 Payload Data ID 表

Payload 内部采用 TLV（Type-Length-Value）结构：

| Data ID | 内容 | 长度 | 单位 | 缩放因子 |
|---------|------|------|------|----------|
| `0x01` | IMU 温度 | 2 B | °C | `×0.01` |
| `0x10` | 加速度 (accel_x/y/z) | 12 B | m/s² | `×1e-6` |
| `0x20` | 角速度 (angle_x/y/z) | 12 B | °/s | `×1e-6` |
| `0x30` | 磁场（归一化） | 12 B | — | `×1e-6` |
| `0x31` | 原始磁场 (raw_mag_x/y/z) | 12 B | mGauss | `×1e-3` |
| `0x40` | 欧拉角 (pitch/roll/yaw) | 12 B | ° | `×1e-6` |
| `0x41` | 四元数 (q0/q1/q2/q3) | 16 B | — | `×1e-6` |
| `0x50` | UTC 时间 | 11 B | — | 年月日时分秒毫秒 |
| `0x51` | 采样时间戳 | 4 B | μs | 原始值 |
| `0x52` | 数据就绪时间戳 | 4 B | μs | 原始值 |
| `0x68` | 位置（高精度） | 20 B | 度/米 | 经纬度 `×1e-10`，高程 `×1e-3` |
| `0x70` | 速度 (vel_e/vel_n/vel_u) | 12 B | m/s | `×1e-3` |
| `0x80` | 融合状态 | 1 B | — | `fusion_status` |
| `0xC0` | GNSS 主天线完整数据 | 45 B | — | UTC+位置+误差+速度+状态+星数+PDOP |
| `0xF0` | GNSS 从天线 | 6 B | — | 双天线航向、误差、基线长度 |

### 1.4 串口输入协议（配置指令）

向 IMU 发送指令的格式：

```
+--------+--------+--------+--------+--------+-----------+--------+--------+
| header1| header2| class  |  id    |  len   | message   |  ck1   |  ck2   |
| 0x59   | 0x53   | 1B     |3bit    |13bit   |  N bytes  |        |        |
+--------+--------+--------+--------+--------+-----------+--------+--------+
```

| Class | 功能 |
|-------|------|
| `0x00` | 产品信息查询 |
| `0x02` | 波特率查询/设置 |
| `0x03` | 输出频率查询/设置 |
| `0x04` | 输出内容查询/设置 |
| `0x05` | 标准参数查询/设置（零偏等） |
| `0x4D` | 算法模式查询/设置 |

**id 字段**：bit0~bit2
- `0` = 查询
- `1` = 写入内存（掉电丢失）
- `2` = 写入 Flash（掉电保存）

### 1.5 ROS 话题输出

#### 标准消息

| 话题 | 类型 | 说明 |
|------|------|------|
| `/imu` | `sensor_msgs/Imu` | **主输出**。orientation（四元数）、angular_velocity、linear_acceleration，带协方差矩阵 |
| `imu/marker` | `visualization_msgs/Marker` | RViz 姿态箭头可视化 |

#### 自定义消息（`yesense_imu/*`）

| 话题 | 类型 | 关键字段 |
|------|------|---------|
| `yesense/sensor_data` | `YesenseImuSensorData` | temperature, accel, quaternion, eulerAngle, location |
| `yesense/inertial_data` | `YesenseImuInertialData` | 惯性导航解算数据 |
| `yesense/nav_data` | `YesenseImuNavData` | tid, location(经纬度高程), utc_time, status |
| `yesense/gnss_data` | `YesenseImuGnssData` | UTC, location, error, ground_speed, yaw, status, star_cnt, p_dop |
| `yesense/gps_data` | `YesenseImuGpsData` | GPS NMEA 原始数据 |
| `yesense/imu_status` | `YesenseImuStatus` | `fusion_status`, `gnss_status` |
| `yesense/command_resp` | `YesenseImuCmdResp` | 配置指令执行结果 |

### 1.6 sensor_msgs/Imu 字段映射

```yaml
header:
  frame_id: "imu_link"
orientation:           # 四元数，来自硬件 q0/q1/q2/q3
  x: q1
  y: q2
  z: q3
  w: q0
orientation_covariance: [0.05, 0, 0, 0, 0.05, 0, 0, 0, 0.05]
angular_velocity:      # 角速度，来自硬件 angle_x/y/z (°/s → rad/s 转换在驱动内完成)
  x: ...
  y: ...
  z: ...
angular_velocity_covariance: [0.02, 0, 0, 0, 0.02, 0, 0, 0, 0.02]
linear_acceleration:   # 加速度，来自硬件 accel_x/y/z
  x: ...
  y: ...
  z: ...
linear_acceleration_covariance: [0.1, 0, 0, 0, 0.1, 0, 0, 0, 0.1]
```

### 1.7 配置参数（Launch）

```xml
<param name="yesense_port"     value="/dev/yesense_imu"/>
<param name="yesense_baudrate" value="460800"/>
<param name="frame_id"         value="imu_link"/>
<param name="imu_topic"        value="imu"/>
<param name="orientation_stddev"         value="0.05"/>
<param name="angular_velocity_stddev"    value="0.02"/>
<param name="linear_acceleration_stddev" value="0.1"/>
```

---

## 2. LDROBOT LD14P 2D LiDAR

### 2.1 硬件接口

| 参数 | 值 |
|------|-----|
| 型号 | LD14P（LDROBOT） |
| USB 转串口 | CH343 |
| 波特率 | **230400** |
| 设备路径 | `/dev/wheeltec_lidar`（udev 符号链接） |
| 帧率 | ~**8 Hz** |
| 点频 | **4000 Hz** |

### 2.2 串口数据协议

单帧数据结构（`LiDARFrameTypeDef`，**47 bytes**，小端序）：

```
Offset  Size    Field           Description
------  ----    -----           -----------
0       1B      header          帧头，固定 0x54
1       1B      ver_len         版本+长度，固定 0x2C
2       2B      speed           转速，单位 0.1°/s
4       2B      start_angle     起始角度，单位 0.01°
6       3B × 12 point[0..11]    12 个测量点
    6+3i   2B    distance      距离，单位 mm
    8+3i   1B    intensity     信号强度，0~255
42      2B      end_angle       终止角度，单位 0.01°
44      2B      timestamp       时间戳，单位 ms
46      1B      crc8            CRC8 校验
```

#### 单点结构（`LidarPointStructDef`，3 bytes）

```c
typedef struct __attribute__((packed)) {
  uint16_t distance;    // 距离，mm
  uint8_t  intensity;   // 信号强度
} LidarPointStructDef;
```

### 2.3 数据解析流程

```
串口字节流
  ↓
状态机解析 [HEADER → VER_LEN → DATA]
  ↓
CRC8 校验（查表法，覆盖 header 到 timestamp）
  ↓
提取 12 个点，在 start_angle 和 end_angle 间线性插值
  ↓
累积到缓冲区 frame_tmp_
  ↓
检测角度跨过 0°/360° 分界线 → 凑齐一圈
  ↓
SlTransform: 左手系 → 右手系坐标变换
  ↓
LD14P 跳过近点滤波（LD14 有 Slbf::NearFilter）
  ↓
按角度从小到大排序
  ↓
生成 sensor_msgs/LaserScan 发布
```

#### 角度插值公式

```cpp
uint32_t diff = (end_angle + 36000 - start_angle) % 36000;  // 单位：0.01°
float step = diff / (POINT_PER_PACK - 1) / 100.0;           // 每点角度步长，单位 °
float start = start_angle / 100.0;
for (i = 0; i < 12; i++) {
    angle = start + i * step;  // 第 i 个点的角度
}
```

### 2.4 ROS 输出: sensor_msgs/LaserScan

| 字段 | 值 | 说明 |
|------|-----|------|
| topic | `/scan` | |
| frame_id | `laser` | launch 中可配置 |
| angle_min | `0` | 0 rad |
| angle_max | `2π` | 360° |
| angle_increment | `2π / (beam_size - 1)` | 约 0.00628 rad (~0.36°) |
| range_min | `0.02` | 0.02 m |
| range_max | `12.0` | 12 m |
| ranges[] | `distance / 1000.0` | 单位 m，无效值填 NaN |
| intensities[] | `intensity` | 0~255，无效值填 NaN |
| scan_time | 相邻帧时间差 | ~0.125 s (@ 8Hz) |
| time_increment | `scan_time / (beam_size - 1)` | 相邻点时间差 |

#### 一圈参数估算

| 参数 | 值 |
|------|-----|
| 每包点数 | 12 |
| 点频 | 4000 Hz |
| 转速 | ~8 Hz (~2880 °/s) |
| 每圈总点数 | ~1000 点（取决于实际转速） |
| 角度分辨率 | ~0.36° |

### 2.5 特殊处理

| 场景 | 处理方式 |
|------|---------|
| `distance == 0 && intensity == 0` | 视为无效点，`range = NaN` |
| 角度裁剪 (`enable_angle_crop_func`) | 指定角度范围内 `range = NaN` |
| 分段屏蔽 (`flag_parted`) | 指定角度范围 `range = infinity` |
| 同一角度多包覆盖 | 保留距离更短的点 |

### 2.6 Launch 配置参数

```xml
<param name="product_name"   value="LDLiDAR_LD14P"/>
<param name="port_name"      value="/dev/wheeltec_lidar"/>
<param name="topic_name"     value="scan"/>
<param name="frame_id"       value="laser"/>
<param name="laser_scan_dir" value="true"/>   <!-- true=逆时针 -->
<param name="enable_angle_crop_func" value="false"/>
<param name="angle_crop_min" value="0.0"/>
<param name="angle_crop_max" value="0.0"/>
```

---

## 3. 快速参考对照表

### 3.1 串口帧头对比

| 设备 | 帧头 Byte 1 | 帧头 Byte 2 | 波特率 | 最小帧长 |
|------|------------|------------|--------|---------|
| H30 IMU | `0x59` | `0x53` | 460800 | 7 B |
| LD14P LiDAR | `0x54` | `0x2C` (ver_len) | 230400 | 47 B |

### 3.2 启动脚本自动识别逻辑

```python
# start_slam.sh 中的检测逻辑
# 读取端口首字节：
#   0x59 → IMU（YIS 协议帧头）
#   0x54 → LiDAR（LDROBOT 帧头）
```

### 3.3 TF 树中的坐标系

```
# Hector SLAM 模式
map → base_link → laser
map → base_link → imu_link

# Cartographer 模式（IMU 启用时）
map → odom → base_link → laser
map → odom → base_link → imu_link
```

| 变换 | 参数 (x y z yaw pitch roll) |
|------|---------------------------|
| base_link → laser | `0 0 0.18 0 0 0` |
| base_link → imu_link | `0 0.08 -0.05 0 0 0` |

---

## 4. 开发注意事项

1. **IMU 协方差非零**：`robot_pose_ekf` 和 Cartographer 要求 IMU 的协方差矩阵对角线元素非零，否则会被忽略。当前配置已设置 `orientation_stddev=0.05`。

2. **LiDAR 数据丢包**：如果 `speed <= 0` 或帧组装超时，驱动会清空缓冲区并报错退出。确保串口稳定，避免 USB 供电不足。

3. **时间戳问题**：LiDAR 的 `timestamp` 字段是硬件时间戳（ms），但 ROS 消息中 `header.stamp` 使用的是 `ros::Time::now()`。Cartographer 内部通过消息到达时间做排序，不要求硬件时间戳绝对精确。

4. **H30 数据输出内容**：默认输出包含加速度、角速度、磁场、欧拉角、四元数。如需 GNSS 位置/速度，必须给 H30 外接 GNSS 天线，并确保输出内容配置包含位置速度（`output_content_setting: 0x02`）。

5. **CRC 校验**：
   - IMU：双字节和校验（ck1 累加和，ck2 是 ck1 的累加和）
   - LiDAR：CRC8 查表校验（覆盖 header 到 timestamp）
