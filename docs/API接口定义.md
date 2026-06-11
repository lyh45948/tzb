# 后端接口说明文档

本文档说明如何接入本后端服务、获取工厂环境传感器数据。适合 AI 智能体（Agent）和数字孪生平台开发使用。

**阅读前提：** 具备 HTTP 请求和 JSON 基本知识即可，无需了解任何硬件或嵌入式系统知识。

---

## 1. 基本信息

| 项目 | 值 |
|------|-----|
| 协议 | HTTP |
| 端口 | 5000 |
| 数据格式 | JSON |
| 编码 | UTF-8 |

---

## 2. HTTP REST API 端点一览

### 2.1 传感器数据

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/sensors/current` | GET | 获取当前默认车辆的最新数据 |
| `/v1/sensors/current/all` | GET | 获取所有车辆的最新数据 |
| `/v1/sensors/current/<device_id>` | GET | 获取指定车辆的最新数据 |
| `/v1/sensors/history` | GET | 查询默认车辆的历史数据 |
| `/v1/sensors/history/<device_id>` | GET | 查询指定车辆的历史数据 |

### 2.2 设备管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/devices` | GET | 获取所有注册车辆列表 |

### 2.3 智能体功能（占位）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/vision/analyze` | GET | 视觉分析（功能待实现） |
| `/v1/device/battery/predict` | GET | 电量预测告警（功能待实现） |

---

## 3. 传感器数据接口

### 3.1 获取当前数据

#### 获取所有车辆最新数据

```
GET http://后端IP:5000/v1/sensors/current/all
GET http://后端IP:5000/v1/sensors/current/all?fields=temp,humi
```

**返回示例：**

```json
{
    "code": 0,
    "data": {
        "car1": {
            "env": {
                "temp": 25.5,
                "humi": 60.2,
                "lux": 350,
                "co2": 450,
                "tvoc": 120,
                "gasStatus": 0,
                "gasMic": 180
            },
            "timestamp": 1700000000000,
            "online": true
        },
        "car2": {
            "env": {
                "temp": 26.1,
                "humi": 58.8,
                "lux": 320,
                "co2": 420,
                "tvoc": 110,
                "gasStatus": 0,
                "gasMic": 160
            },
            "timestamp": 1700000000100,
            "online": false
        }
    }
}
```

#### 获取指定车辆最新数据

```
GET http://后端IP:5000/v1/sensors/current/car1
GET http://后端IP:5000/v1/sensors/current/car1?fields=temp
```

**返回示例：**

```json
{
    "code": 0,
    "data": {
        "device_id": "car1",
        "env": {
            "temp": 25.5,
            "humi": 60.2,
            "lux": 350,
            "co2": 450,
            "tvoc": 120,
            "gasStatus": 0,
            "gasMic": 180
        },
        "timestamp": 1700000000000,
        "online": true
    }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 0=成功，1=失败 |
| data.env.temp | float | 温度（℃） |
| data.env.humi | float | 湿度（%） |
| data.env.lux | int | 光照强度（lux） |
| data.env.co2 | int | CO2浓度（ppm），400=室外正常值，>800 人会闷 |
| data.env.tvoc | int | 有机挥发物（ppb），越低越好 |
| data.env.gasStatus | int | 燃气状态，0=正常，1=检测到燃气泄漏 |
| data.env.gasMic | int | 燃气浓度，越高越危险 |
| data.timestamp | int | 服务器时间戳（毫秒） |
| data.online | bool | 车辆是否在线 |
| data.device_id | string | 车辆标识符 |

---

### 3.2 字段筛选

所有传感器接口均支持 `fields` 参数，指定返回哪些字段，减少数据传输量。

```
GET /v1/sensors/current/car1?fields=temp
GET /v1/sensors/current/car1?fields=temp,humi,co2
GET /v1/sensors/current/all?fields=temp
```

**可用字段名：** `temp`, `humi`, `lux`, `co2`, `tvoc`, `gasStatus`, `gasMic`

**返回示例（fields=temp）：**

```json
{
    "code": 0,
    "data": {
        "device_id": "car1",
        "env": {
            "temp": 25.5
        },
        "timestamp": 1700000000000,
        "online": true
    }
}
```

---

### 3.3 查询历史数据

```
GET http://后端IP:5000/v1/sensors/history/car1?startTime=2026-05-01 00:00:00&endTime=2026-05-02 00:00:00
GET http://后端IP:5000/v1/sensors/history/car1?startTime=2026-05-01 00:00:00&endTime=2026-05-02 00:00:00&interval=60
GET http://后端IP:5000/v1/sensors/history/car1?startTime=2026-05-01 00:00:00&endTime=2026-05-02 00:00:00&fields=temp,co2
```

**Query 参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| startTime | ✅ | 开始时间，格式 `YYYY-MM-DD HH:MM:SS` |
| endTime | ✅ | 结束时间，格式 `YYYY-MM-DD HH:MM:SS` |
| interval | ❌ | 采样间隔（秒），不填则返回全部原始数据 |
| fields | ❌ | 字段筛选，如 `fields=temp,humi` |

**返回示例：**

```json
{
    "code": 0,
    "data": [
        {"timestamp": "2026-05-01 00:00:00", "temperature": 25.5, "humidity": 60.2, "lux": 350, "co2": 450},
        {"timestamp": "2026-05-01 00:01:00", "temperature": 25.6, "humidity": 60.1, "lux": 348, "co2": 452}
    ]
}
```

**错误返回（缺少参数）：**

```json
{"code": 1, "message": "缺少 startTime 或 endTime 参数"}
```

**错误返回（设备不存在）：**

```json
{"code": 1, "message": "设备 car1 不存在或无数据"}
```

---

## 4. 设备注册列表

```
GET http://后端IP:5000/v1/devices
```

**返回示例：**

```json
{
    "code": 0,
    "data": [
        {
            "device_id": "car1",
            "name": "小车1号",
            "ip_address": "192.168.1.100",
            "port": 7788,
            "last_seen": "2026-05-24T10:00:00",
            "status": "online"
        },
        {
            "device_id": "car2",
            "name": "小车2号",
            "ip_address": "192.168.1.101",
            "port": 7788,
            "last_seen": "2026-05-24T09:30:00",
            "status": "offline"
        }
    ]
}
```

---

## 5. 智能体占位接口

以下接口尚在规划中，当前返回"功能待实现"，供智能体开发阶段预留对接。

### 5.1 视觉分析

```
GET http://后端IP:5000/v1/vision/analyze?image_url=http://example.com/image.jpg
```

**返回：**

```json
{"code": 1, "message": "功能待实现", "data": null}
```

### 5.2 电量预测告警

```
GET http://后端IP:5000/v1/device/battery/predict?device_id=car1
```

**返回：**

```json
{"code": 1, "message": "功能待实现", "data": null, "device_id": "car1"}
```

---

## 6. 推荐报警阈值

| 指标 | 警告 | 危险 |
|------|------|------|
| 温度 | > 30℃ | > 35℃ |
| 湿度 | > 75% | > 80% |
| CO2 | > 800 ppm | > 1000 ppm |
| TVOC | > 220 ppb | > 500 ppb |
| 燃气浓度 gasMic | > 300 | > 500 |
| 燃气泄漏 gasStatus | 1 | - |

---

## 7. 常见问题

**Q: HTTP 请求返回 `Connection refused`**
A: 后端服务未启动，或端口填写错误。HTTP API 端口为 **5000**。

**Q: 请求返回 `设备 xxx 不存在或无数据`**
A: 该车辆尚未连接后端，或尚无数据上报。可先调用 `/v1/devices` 查看已注册车辆。

**Q: `fields` 参数大小写敏感吗？**
A: 不敏感，`temp`、`TEMP`、`Temp` 均可识别。

**Q: `online` 字段含义？**
A: `true` 表示车辆当前与后端保持 UDP 连接；`false` 表示车辆离线，数据来自数据库历史记录。

---

*文档版本：v1.2*
*最后更新：2026-05-24*