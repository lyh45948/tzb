# AGENTS.md

> 本文件为 AI 编程代理提供项目上下文。所有修改过本文件所提及的架构、风格、配置、工作流的开发者，都有义务同步更新此文件。

## 项目概述

本项目是**智慧工厂安全监测控制平台**（Smart Factory Safety Monitoring & Control Platform），基于 Hi3861（OpenHarmony / LiteOS-M）开发，服务于"挑战杯"揭榜挂帅擂台赛（赛题编号 XA-202606）。

平台核心功能：
1. 温湿度智能监控 — SHT20 传感器采集，每秒入库
2. 红外感应照明 — AP3216C 环境光 + PIR 人体检测，分时段自动调光
3. 危气监测 — SGP30（CO2/TVOC）、MQ-2（烟雾）、MQ-7（CO）多级告警
4. AGV 避障系统 — HC-SR04 超声波测距，自动停车或绕行
5. 货物感应计数 — PCF8574 P6 脉冲计数（红外对管 E3F-DS30C）

系统架构采用"微信小程序 → Python 后端 → Hi3861 → 双 STM32"五级链路，数据以 JSON 为主、关键电机通信采用二进制协议以降低延迟。

## 技术栈与关键配置

| 层级 | 技术栈 | 关键配置文件 |
|------|--------|-------------|
| 后端 | Python 3.8+、Flask 3.0、Flask-SQLAlchemy 3.1、PyMySQL 1.1 | `backend/requirements.txt`、`backend/config.py`、`.env` |
| 数据库 | MySQL 5.7+ | `backend/sql/init.sql`、`backend/migrate_tables.py` |
| 小程序 | 微信小程序原生框架 + Vant Weapp UI | `微信小程序端/smart_car_udp/app.json`、`project.config.json` |
| 主控固件 | OpenHarmony 1.0（LiteOS-M）、C、FreeRTOS 任务 | `1/src/vendor/hqyj/fs_hi3861/config.json`、`BUILD.gn` |
| 电机驱动 | STM32G030、HAL 库、Keil MDK-ARM | `FS-Hi3861-Motor-Driver(Release)/*.ioc` |
| 传感器板 | STM32G030、HAL 库、Keil MDK-ARM | `FS-STM32G030-CS100A(Release)/*.ioc` |
| 工具脚本 | Node.js（图标生成、MySQL 连接测试） | `package.json`、`icons/package.json` |

### 环境变量（后端）

复制 `backend/.env.example` 为 `backend/.env`，关键字段：
- `MYSQL_HOST/MYSQL_PORT/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE` — 数据库连接
- `TCP_HOST/TCP_PORT` — 小程序 UDP 服务监听地址（默认 `0.0.0.0:8888`）
- `UDP_PORT` — Hi3861 UDP 通信端口（默认 `7788`）
- `HTTP_PORT` — Flask REST API 端口（默认 `5000`）
- `HI3861_IP` — 可选，后端启动时自动连接的小车 IP

## 目录结构与模块划分

```
.
├── backend/                    # Python 后端
│   ├── main.py                 # 服务入口：Flask REST API + UDP 小程序服务 + UDP 小车服务
│   ├── config.py               # 多环境配置（development/production/testing/default）
│   ├── migrate_tables.py       # 数据库迁移脚本（创建 control_commands / simulated_sensor_data / car_sensor_data）
│   ├── run.sh                  # 启动脚本
│   ├── sql/init.sql            # 数据库初始化（devices / sensor_data / car_status / smart_light_status / control_logs / irrigation_history / irrigation_config）
│   └── app/
│       ├── __init__.py         # Flask app 工厂 + SQLAlchemy db 初始化
│       ├── models/             # ORM 模型（device, car_status, sensor_data, smart_light_status, control_command, simulated_sensor_data, car_sensor_data, irrigation_config, irrigation_history）
│       ├── routes/             # REST API 蓝图（sensor_routes, device_routes, agent_routes），前缀 /v1
│       ├── services/           # 业务服务层
│       │   ├── udp_service.py          # UDP 与 Hi3861 通信（端口 7788）
│       │   ├── udp_miniapp_service.py  # UDP 与小程序通信（端口 8888）
│       │   ├── data_service.py         # 数据持久化与查询
│       │   ├── simulation_service.py   # 演示模式数据生成 / 实际数据 CO2 推算
│       │   ├── smart_light_service.py  # 智能光照逻辑
│       │   └── registry.py             # 服务实例注册表（供 REST API 调用）
│       └── utils/              # 工具模块
│           ├── logger.py       # 日志配置
│           └── protocol.py     # JSON 协议解析 / 消息构造
│
├── 微信小程序端/
│   └── smart_car_udp/          # 微信小程序（主项目）
│       ├── app.js              # 全局逻辑：演示模式、传感器数据缓存、阈值告警、自动控制
│       ├── app.json            # 页面路由与 Vant Weapp 组件注册
│       ├── app.wxss            # 全局样式
│       ├── pages/              # 页面目录
│       │   ├── home/           # 首页
│       │   ├── control/        # 小车遥控（摇杆、模式切换）
│       │   ├── environment/    # 环境监测
│       │   ├── factory_dashboard/   # 数字可视化大屏
│       │   ├── alert_center/   # 多级告警中心
│       │   ├── equipment_control/   # 设备控制（风扇、蜂鸣器、LED）
│       │   ├── smart_light/    # 智能照明
│       │   ├── backend_connect/# 后端连接配置
│       │   ├── agriculture/    # 农业安防
│       │   ├── monitor/        # 监控
│       │   └── ...
│       ├── components/         # 自定义组件
│       │   └── sensor-gauge/   # 传感器仪表盘
│       └── utils/              # 网络管理、UDP 后端管理、配置管理、错误处理
│   └── smart_agriculture/      # 旧版农业小程序（已融合进 smart_car_udp）
│
├── 1/src/                      # OpenHarmony 源码（完整 SDK）
│   └── vendor/hqyj/fs_hi3861/  # 项目固件源码
│       ├── config.json         # 产品配置（hi3861_sdk）
│       ├── common/bsp/         # 板级驱动（SHT20、AP3216C、SSD1306、PCF8574、AW2013、SGP30、NFC、WiFi）
│       └── demo/Ext_VoiceCar_Test/
│           ├── voicecar_demo.c         # 入口：外设初始化、WiFi/NFC 联网、创建 FreeRTOS 任务
│           ├── function/sys_config.h   # 全局结构体 system_value_t、枚举、阈值宏
│           ├── task/                   # FreeRTOS 任务
│           │   ├── udp_recv_task.c     # UDP 接收（端口 7788，事件驱动）
│           │   ├── udp_send_task.c     # UDP 发送（50ms 周期）
│           │   ├── uart_recv_task.c    # UART2 接收 STM32 数据
│           │   ├── oled_show_task.c    # OLED 刷新（100ms）
│           │   ├── auto_avoid_task.c   # 自动避障（5ms）
│           │   ├── smart_light_task.c  # 智能光照（100ms）
│           │   └── agriculture/agriculture_sensor_task.c  # SGP30 采集
│           └── agriculture/            # PWM RGB 控制
│
├── FS-Hi3861-Motor-Driver(Release)/    # STM32 电机驱动板
│   ├── Core/Src/main.c                 # 主循环：UART1 接收 JSON、UART2 发送超声波触发、100ms 遥测打包
│   ├── Core/Src/app_motor.c            # 电机控制、PID、编码器
│   └── Core/Src/system_cfg.h           # 系统状态结构体
│
├── FS-STM32G030-CS100A(Release)/       # STM32 传感器板
│   ├── Core/Src/main.c                 # 主循环：定时器任务调度（5ms 基准）
│   ├── Core/Src/user_app.c             # 超声波测距、光电管巡线、RGB 灯带、串口输出
│   └── Core/Src/adc.c                  # 7 通道 ADC（光敏、火焰、气体等）
│
├── fig/                        # 架构图、时序图、流程图（PNG + Markdown）
├── icons/                      # SVG 图标与 PNG 生成脚本
├── lidar/                      # LD-STL-19P 激光雷达文档
├── ref/                        # 参考项目（智慧农业、智能测距仪等）
└── doc/ 与各 .md 文件           # 接口说明、算法设计、通信协议汇总、外设控制代码汇总
```

## 构建与运行命令

### Python 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 配置 MYSQL_*/TCP_*/UDP_*
mysql -u root -p < sql/init.sql
python main.py
```

- REST API 运行在 `HTTP_PORT`（默认 5000）
- 小程序 UDP 服务在 `TCP_PORT`（默认 8888）
- 小车 UDP 服务在 `UDP_PORT`（默认 7788）
- 若设置了 `HI3861_IP`，启动后会自动向 Hi3861 发送初始化命令

### Hi3861 固件（DevEco Device Tool）

1. VSCode 安装 DevEco Device Tool 插件
2. 导入项目目录 `1/src`
3. SOC 选择 HI3861，Board 选择 hi3861
4. 点击 Build

输出固件：`1/src/out/hispark_pegasus/wifiiot_hispark_pegasus/Hi3861_wifiiot_app_allinone.bin`

### Hi3861 固件（命令行）

```bash
cd 1/src
hb set
hb build
```

### 烧录 Hi3861

使用 HiBurn 工具：Baud 2000000，Loader 选择 `Hi3861_loader_signed.bin`。

### STM32 项目

- **电机驱动**：Keil MDK-ARM 打开 `FS-Hi3861-Motor-Driver(Release)/MDK-ARM/*.uvprojx`
- **传感器板**：Keil MDK-ARM 打开 `FS-STM32G030-CS100A(Release)/MDK-ARM/*.uvprojx`

### 微信小程序

使用微信开发者工具导入 `微信小程序端/smart_car_udp/`，在 `miniprogram/` 目录下如需重新构建 npm：

```bash
cd 微信小程序端/smart_car_udp/miniprogram
npm install
```

## 通信协议与数据流

### 五级通信链路

| 层级 | 两端 | 介质 | 格式 | 端口/波特率 |
|------|------|------|------|------------|
| 1 | 小程序 ↔ 后端 | WiFi UDP | JSON | 8888 |
| 2 | 后端 ↔ Hi3861 | WiFi UDP | JSON | 7788 |
| 3 | Hi3861 ↔ STM32 Motor | UART | JSON | 115200 |
| 4 | STM32 Motor ↔ STM32 Sensor | UART | 二进制 | 115200 |
| 5 | 语音模块 → Hi3861 | UART | Hex | 115200 |

### 小程序 ↔ 后端 JSON 协议示例

```json
// 小程序 → 后端：连接小车
{"type":"connect","carIp":"192.168.1.100","carPort":7788}

// 小程序 → 后端：控制命令
{"type":"control","command":{"carStatus":"run"}}
{"type":"control","command":{"carMode":"avoid"}}
{"type":"control","command":{"joyX":50,"joyY":-30}}
{"type":"control","command":{"smartLight":{"mode":"auto","brightness":80}}}

// 后端 → 小程序：实时数据推送
{"type":"realtime","data":{"carStatus":"on","env":{"temp":28.5,"humi":65,"lux":400,"co2":450}},"timestamp":...}

// 演示模式切换
{"type":"demo_mode","enabled":true,"deviceId":"demo_car"}
```

### STM32 电机 ↔ 传感器 二进制协议

**同步包**（Motor → Sensor）：
`0xBB` + `L_spd(2B)` + `R_spd(2B)` + `Status(1B)` + `Mode(1B)` + `Sum(1B)`

**传感器包**（Sensor → Motor）：
- 避障：`0xFF` + `Dist_H(1B)` + `Dist_L(1B)` + `Sum(1B)`
- 巡线/按键：`0xAA` + `LineOut(1B)` + `ModeByte(1B)` + `Sum(1B)`

ModeByte：`0x00` 遥控、`0xD0` 避障、`0xF0` 巡线、`0xE0` 规划路径

## 关键业务规则与阈值

### 环境告警阈值

| 指标 | 警告阈值 | 危险阈值 |
|------|---------|---------|
| 温度 | 30°C | 35°C |
| 湿度 | 75% | 80% |
| CO2 | 800 ppm | 1000 ppm |
| 烟雾 | 300 | 500 |
| CO | 35 ppm | 50 ppm |
| 超声波避障 | 30 cm | 15 cm |

### 速度档位

- Low：500 mm/s
- Middle：800 mm/s
- High：1100 mm/s

### 时序参数

- UDP 数据发送间隔：50 ms
- 数据库存储间隔：1 s
- 摇杆报告最小间隔：≥ 50 ms
- 模式切换锁定时长：500 ms
- UART 超时自动复位：50 ms
- 90 度转向脉冲数：920
- 最小启动 PWM：150（15%）

## 代码风格与约定

### 语言
- 所有注释、文档、日志、变量命名以**中文为主**，英文为辅。
- 后端代码中的类名、函数名采用英文蛇形命名或驼峰命名；注释使用中文。

### Python 后端
- 使用 Flask 蓝图组织路由，前缀 `/v1`
- 服务层通过 `registry.py` 注册单例，避免循环导入
- 数据库操作必须在 `app.app_context()` 内进行
- 日志使用 `app.utils.logger` 模块，格式：`%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- 环境配置通过 `python-dotenv` 加载 `.env`

### Hi3861 C 固件
- FreeRTOS 任务使用 `osThreadNew` 创建
- 全局状态通过 `system_value_t systemValue` 共享（无显式锁，依赖原子赋值与优先级调度）
- 外设驱动统一放在 `common/bsp/src/`，头文件在 `common/bsp/include/`
- I2C 设备地址：
  - PCF8574：0x43
  - SHT20 / SGP30：0x80
  - AW2013：0x8A
  - AP3216C：0x3C
  - SSD1306：0x78
- UART1：GPIO_5(RX) / GPIO_6(TX) — 语音模块
- UART2：GPIO_12(RX) / GPIO_11(TX) — STM32 电机板
- I2C：GPIO_9(SCL) / GPIO_10(SDA)，100 kHz

### 微信小程序
- 使用 Vant Weapp 组件库，`van-icon` 必须显式指定 `color` 属性
- 网络通信优先通过 `udpBackendManager`（后端中转），未连接后端时可直接 UDP 连接小车
- 全局数据与状态管理写在 `app.js` 的 `globalData` 中
- 演示模式（demo_mode）在本地生成模拟数据，不与数据库同步；如需同步请通过 `backend_connect` 页面连接后端

## 测试策略

> **现状**：项目目前没有针对自定义业务代码的自动化测试套件。OpenHarmony SDK 内部包含大量单元测试（`1/src/**/test/`），但项目业务代码（后端、小程序、固件）均未编写单元测试或集成测试。

### 建议的测试方式

1. **后端手动验证**：
   - 启动后端后，使用 `test-mysql.js`（Node.js + mysql2）验证数据库连通性
   - 通过 REST API `GET /v1/sensors/current` 检查服务状态
   - 使用微信小程序或 `nc -u` 发送 UDP 命令测试链路

2. **固件调试验证**：
   - Hi3861 通过串口打印日志（`printf` 重定向到 UART）
   - STM32 电机板 `fputc` 已注释（禁用调试打印，确保 UART1 纯 JSON 通信）

3. **小程序验证**：
   - 微信开发者工具打开"真机调试"或"模拟器"
   - `backend_connect` 页面输入后端 IP 与端口测试连通性
   - 开启"演示模式"可脱离硬件验证 UI 逻辑

## 安全注意事项

1. **硬编码凭证**：`voicecar_demo.c` 中硬编码了默认 WiFi SSID 与密码（`DEFAULT_WIFI_SSID`、`DEFAULT_WIFI_PASSWORD`），生产环境必须替换。
2. **数据库密码**：`backend/.env` 与 `test-mysql.js` 包含明文数据库凭证，勿提交到版本控制（已加入 `.gitignore`）。
3. **无身份鉴权**：后端 REST API 与 UDP 服务均未实现登录鉴权，任何可达网络的客户端均可发送控制命令。
4. **通信未加密**：小程序 ↔ 后端 ↔ Hi3861 全程明文 UDP/TCP，存在中间人攻击与重放攻击风险。
5. **SQL 注入防护**：后端使用 Flask-SQLAlchemy ORM，基本避免 SQL 注入；但手写原生 SQL 时需谨慎。

## Git 分支与提交规范

### 分支管理
- `main` — 生产分支，始终保持可运行
- `develop` — 开发分支
- `feature/*` — 新功能
- `bugfix/*` — Bug 修复
- `release/*` — 发布准备

### 提交格式
```
<type>(<scope>): <subject>
```

**type**：feat, fix, docs, style, refactor, test, chore
**scope**：backend, miniapp, hi3861, stm32, docs, config

## 常见问题排查

| 现象 | 排查方向 |
|------|---------|
| 后端启动报错端口占用 | `lsof -i :8888` / `lsof -i :7788`，检查是否有残留进程 |
| 小程序无法收到数据 | 确认手机与后端在同一局域网；检查 `backend_connect` 中 IP/端口；查看后端日志 `UDP小程序服务已启动` |
| Hi3861 编译报错 | 确认 DevEco / hb 工具链版本；检查 `config.json` 中 subsystem 配置 |
| STM32 电机不转 | 检查 INA219 电源检测是否初始化；确认 PWM 定时器已启动；查看 UART JSON 是否包含 `carStatus:on` |
| OLED 不显示 | 确认 I2C 地址 0x78；检查 SSD1306_Init 是否成功 |
| 数据库表缺失 | 运行 `mysql -u root -p < backend/sql/init.sql`，再执行 `python backend/migrate_tables.py` |

## 相关文档索引

- `CLAUDE.md` — 更详细的硬件参数、FreeRTOS 任务表、PCF8574 I/O 定义、Vant 图标列表
- `4层通信协议汇总.md` — 完整协议定义（实际为 5 层）
- `接口说明文档.md` — 后端 API 接口详细说明
- `算法设计文档.md` — 智能光照、灌溉、告警算法
- `外设控制代码汇总.md` — 各外设寄存器与操作代码
- `语音接口说明.md` — 语音模块通信协议
- `智慧工厂安全监测控制平台.md` — 项目总体设计文档
- `微信小程序端/更新说明.md` — 小程序版本更新记录
- `微信小程序端/演示模式说明.md` — 演示模式使用说明
