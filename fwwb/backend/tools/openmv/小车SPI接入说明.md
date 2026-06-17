# WT OpenMV 经小车 SPI 接入说明

## 目标

OpenMV 在设备端完成视觉识别，只把紧凑结果交给 Hi3861。Hi3861 作为 SPI 主机读取 OpenMV 当前结果帧，并将结果放入 UDP 遥测 JSON 的 `vision` 字段，后端自动写入 `VisionService` 缓存，数字孪生大屏复用已有障碍物/计数器显示链路。

不建议通过 SPI 传输图片。当前链路只传输 46 字节识别结果帧，适合小车 50ms 遥测周期。

## 接线

- OpenMV VIN → 5V，GND → Hi3861 GND，推荐电源电流 ≥ 250mA。
- 必须共地。
- OpenMV I/O 为 3.3V；SPI 信号不要上拉/接入 5V。
- Hi3861 使用 SPI1，避免 SPI0 与 UART1 语音模块 GPIO5/GPIO6 冲突。

默认 Hi3861 SPI1 接线：

| Hi3861 | 功能 | OpenMV |
| --- | --- | --- |
| GPIO0 | SPI1_CK | SCK |
| GPIO1 | SPI1_RXD / MISO | MISO / SDO |
| GPIO2 | SPI1_TXD / MOSI | MOSI / SDI |
| GPIO3 | SPI1_CSN | CS / NSS |
| GND | GND | GND |

## 默认 SPI 参数

- Hi3861：SPI 主机。
- OpenMV：SPI 从机。
- 模式：Motorola SPI mode 0，CPOL=0，CPHA=0。
- 数据位宽：8bit。
- 频率：默认 1MHz，联调稳定后可提高。
- 每次事务长度：固定 46 字节。
- Hi3861 发送 dummy 字节 `0xFF` 产生时钟，OpenMV 在同一次全双工事务中返回当前结果帧。

## 结果帧格式

| 偏移 | 长度 | 字段 | 说明 |
| --- | --- | --- | --- |
| 0 | 2 | magic | 固定 `5A A5` |
| 2 | 1 | version | 当前为 `1` |
| 3 | 1 | flags | bit0=结果有效 |
| 4 | 1 | obstacle_count | 最大 4 |
| 5 | 8×4 | obstacles | `class_id, confidence, x, y, w, h, distance_le16` |
| 37 | 6 | counter_digits | ASCII 数字，不足补 0 |
| 43 | 2 | frame_counter | 小端自增帧号 |
| 45 | 1 | crc8 | 多项式 `0x07`，覆盖前 45 字节 |

UDP JSON 示例：

```json
{
  "vision": {
    "source": "openmv_spi",
    "valid": 1,
    "frame": 123,
    "flags": 1,
    "obstacleCount": 1,
    "obstacles": [
      {"class_id": 1, "confidence": 86, "x": 120, "y": 80, "w": 40, "h": 30, "distance": 350}
    ],
    "counter": "000123"
  }
}
```

## OpenMV 脚本

示例脚本：`openmv_spi_result_slave.py`。

先使用脚本内置的固定假数据打通链路：

1. 保存为 OpenMV 板载 `main.py`。
2. 按 SPI1 表格连接 SCK/MISO/MOSI/CS/GND 和供电。
3. 烧录/运行 Hi3861 固件。
4. 后端查看 `/v1/vision/latest`，应出现 `obstacles` 或 `counter`。

注意：不同 OpenMV/MicroPython 固件对 `pyb.SPI` 从机模式和 `send_recv` 的支持可能不同。如果 OpenMV IDE 报 `SPI.SLAVE` 或 `send_recv` 相关错误，需要按当前固件 API 调整 OpenMV 端脚本；Hi3861 和后端仍保持同一 46 字节帧格式。

## 验证

```bash
curl http://127.0.0.1:5000/v1/vision/latest
curl http://127.0.0.1:5000/v1/dashboard/snapshot
```

期望：

- `/v1/vision/latest` 的 `counter` 或 `obstacles` 不再是 `null`。
- 大屏快照的 `counterDigits/goodsCount` 随 OpenMV `counter` 变化。
- 若障碍物带 `distance`，大屏 `minDistance` 会用更近的视觉距离补充超声波距离。

## 故障定位

- `[OpenMV] SPI read error`：SPI 事务失败，优先检查 CS/SCK/MISO/MOSI、OpenMV 是否运行 SPI 从机脚本、SPI bus 是否选对。
- `[OpenMV] invalid result frame`：SPI 读到了数据但 magic/CRC/长度不匹配，检查 CPOL/CPHA、帧长度、CRC8、OpenMV 是否正在发送 46 字节结果帧。
- WebSocket 中 `vision.valid=0`：Hi3861 没拿到有效视觉结果，后端不会写入 `VisionService` 缓存。
