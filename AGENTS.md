# AGENTS.md — 工作空间 AI 编码代理指南

> 本文件面向 AI 编码代理（coding agent）。当前路径 `/home/tzb/tzb` 是一个**工作空间根目录**，内部包含两个相互独立但在硬件上有关联的子项目。若你正在阅读此文件，说明你对本工作空间一无所知。以下信息均基于实际目录结构与配置文件，无假设与泛化。

---

## 1. 工作空间概述

本工作空间包含两个子目录：

| 目录 | 项目名称 | 性质 |
|------|----------|------|
| `fwwb/` | 智慧工厂安全监测控制平台 | 物联网监测 + AGV 控制 + 微信小程序 |
| `lidar/` | ROS1 SLAM 建图系统 | 激光雷达 + IMU 定位建图 |

**关键事实**：
- 根目录**没有任何**构建配置文件（如 `pyproject.toml`、`package.json`、`Cargo.toml`、`CMakeLists.txt` 等）。
- 两个子项目使用**完全不同的技术栈**，拥有**独立的构建系统**和**独立的运行环境**。
- 两个子项目共享同一套硬件（LD-14P / LD-STL-19P 激光雷达、Yesense H30 IMU），但各自通过不同的接口读取数据，**软件层面无直接耦合**。
- 每个子目录内部均已存在独立的 `AGENTS.md` 和 `CLAUDE.md`，记录了该子项目的详细架构与规范。

---

## 2. 目录结构与模块划分

```
/home/tzb/tzb/
├── fwwb/                    # 智慧工厂安全监测控制平台（详见 fwwb/AGENTS.md）
│   ├── backend/             # Python Flask 后端（REST API + UDP 通信）
│   ├── 微信小程序端/         # 微信小程序（smart_car_udp 为主项目）
│   ├── 1/src/               # OpenHarmony Hi3861 固件源码
│   ├── FS-Hi3861-Motor-Driver(Release)/   # STM32 电机驱动（Keil MDK）
│   ├── FS-STM32G030-CS100A(Release)/      # STM32 传感器板（Keil MDK）
│   ├── lidar/               # LD-STL-19P 激光雷达文档（仅文档，无驱动代码）
│   ├── fig/                 # 架构图、时序图
│   ├── doc/ 及各 .md 文件    # 接口说明、算法设计、通信协议汇总
│   ├── AGENTS.md            # ← fwwb 子项目详细指南
│   └── CLAUDE.md            # ← 硬件参数、FreeRTOS 任务表等
│
└── lidar/                   # ROS1 Noetic SLAM 系统（详见 lidar/AGENTS.md）
    ├── catkin_ws/           # ROS1 工作空间（catkin_make 编译）
    ├── ldlidar_ros1/        # 激光雷达驱动源码
    ├── yesense_imu/         # IMU 驱动源码
    ├── imu_tf_broadcaster/  # IMU TF 广播节点
    ├── start_slam.sh        # 一键启动脚本（核心运维入口）
    ├── build_lidar.sh       # ROS2 编译脚本（Humble，备用）
    ├── run_ros2_docker.sh   # ROS2 Docker 运行脚本（备用）
    ├── check_ports.py       # 串口硬件诊断脚本
    ├── AGENTS.md            # ← lidar 子项目详细指南
    └── CLAUDE.md            # ← 更详细的硬件参数与调优
```

---

## 3. 子项目详解与关联

### 3.1 fwwb/ — 智慧工厂安全监测控制平台

**目标**：服务于"挑战杯"揭榜挂帅擂台赛（赛题编号 XA-202606），基于国产操作系统 OpenHarmony Hi3861 实现工厂环境监测、危气报警、AGV 避障、货物计数。

**五级通信链路**：
```
微信小程序 → Python 后端 → Hi3861 → STM32 电机板 ↔ STM32 传感器板
```

**与激光雷达/IMU 的关系**：
- Hi3861 固件通过 **UART** 直接连接 LD-STL-19P 激光雷达模块，解析其私有协议（帧头 `0x54`），并将点云数据打包为 JSON 通过 UDP 上报给后端。
- Hi3861 固件通过 **I2C/UART** 读取 Yesense H30 IMU 数据，同样以 JSON 形式 UDP 透传至后端。
- 后端 `backend/app/services/imu_service.py` 支持三种 IMU 接入模式：`tcp`（网口版直连）、`serial`（USB 串口版直连）、`udp_passive`（Hi3861 JSON 透传）。
- **注意**：`fwwb/lidar/` 目录下**仅有雷达开发手册 PDF 和协议文档**，没有 ROS 驱动代码；实际的雷达 ROS 驱动位于根目录 `lidar/` 中。

**构建入口**：
- 后端：`cd fwwb/backend && pip install -r requirements.txt && python main.py`
- 固件：DevEco Device Tool 或 `hb build`
- STM32：Keil MDK-ARM
- 小程序：微信开发者工具导入 `fwwb/微信小程序端/smart_car_udp/`

> **详细构建命令、通信协议、代码规范、测试策略请阅读 `fwwb/AGENTS.md`。**

### 3.2 lidar/ — ROS1 Noetic SLAM 系统

**目标**：基于 LD-14P 激光雷达（或 LD-STL-19P）与 Yesense H30 IMU，使用 Hector SLAM 或 Cartographer 实现 2D 栅格地图构建与定位。

**运行方式**：
- 采用 **Docker 容器化**部署，基础镜像 `osrf/ros:noetic-desktop`
- 一键启动脚本 `start_slam.sh`（需 `sudo`）：自动检测 CH343 串口、创建设备别名、启动容器、编译工作空间、后台运行 ROS 节点
- 支持**纯雷达模式**（未检测到 IMU 时自动禁用 IMU 节点）

**与 fwwb/ 的关系**：
- 使用**完全相同**的 LD-14P / LD-STL-19P 激光雷达和 Yesense H30 IMU 硬件。
- 但 `lidar/` 项目通过 **USB 串口**直接在主机/容器内读取原始数据，不经过 Hi3861 转发。
- `lidar/` 与 `fwwb/` **无代码共享、无网络协议交互、无数据库共享**。
- 两者可以在同一台主机上同时运行，但需确保串口设备不被占用（或使用不同的硬件实例）。

**构建入口**：
```bash
cd /home/tzb/lidar
sudo ./start_slam.sh              # Hector SLAM 模式
sudo ./start_slam.sh --cartographer  # Cartographer 模式
```

> **详细坐标系定义、TF 树、诊断命令、地图保存方法请阅读 `lidar/AGENTS.md`。**

---

## 4. 共享硬件与端口协调

两个子项目涉及相同的物理硬件，若在同一台主机上运行，需注意资源冲突：

| 硬件 | 接口芯片 | 默认设备路径 | fwwb 使用方式 | lidar 使用方式 |
|------|----------|--------------|---------------|----------------|
| LD-14P / LD-STL-19P 激光雷达 | CH343 | `/dev/ttyCH343USB0` 或 `1` | Hi3861 UART 直连（fwwb 后端仅接收 JSON） | `lidar/` 容器内串口直连（ROS `ldlidar` 节点） |
| Yesense H30 IMU | CH343 | `/dev/ttyCH343USB0` 或 `1` | Hi3861 I2C/UART 读取后 UDP 透传 | `lidar/` 容器内串口直连（ROS `yesense_imu` 节点） |

**协调建议**：
- 若 `fwwb` 的 Hi3861 已通过 UART 占用雷达/IMU，则同一套硬件无法同时被 `lidar/` 的 ROS 节点读取。
- `lidar/` 的 `start_slam.sh` 会自动检测 CH343 端口并识别设备身份（`0x59` 为 IMU，`0x54` 为雷达），若检测不到会按纯雷达模式启动。
- `fwwb` 后端也可以通过配置 `.env` 中的 `IMU_MODE=serial` 直接占用 USB 串口版 IMU，此时会与 `lidar/` 冲突。

---

## 5. 代码风格与语言约定

- **工作语言**：两个子项目的注释、文档、日志、变量命名均以**中文为主**，英文为辅。
- **fwwb/**：Python 使用 Flask 蓝图 + 服务层注册表；C 固件使用 FreeRTOS 任务；小程序使用 Vant Weapp。
- **lidar/**：C++ 使用 C++11 标准；ROS 包遵循标准 `catkin` 结构；Python 脚本需加 `#!/usr/bin/env python3` shebang。

---

## 6. 测试策略

- **根工作空间无统一的自动化测试框架**。
- **fwwb/**：业务代码（后端、小程序、固件）目前无单元测试；验证依赖手动测试（`test-mysql.js`、微信开发者工具模拟器、串口日志）。
- **lidar/**：未配置 gtest 或 nosetests；验证以**硬件在环测试**和**ROS 话题诊断**（`rostopic hz`、`rosnode list`、`rviz`）为主。

---

## 7. 安全注意事项

综合两个子项目的安全风险：

1. **硬编码凭证**：`fwwb/1/src/.../voicecar_demo.c` 中硬编码了默认 WiFi SSID 与密码，生产环境必须替换。
2. **数据库明文密码**：`fwwb/backend/.env` 与 `test-mysql.js` 包含明文数据库凭证，已加入 `.gitignore`，但需确保不泄露。
3. **无身份鉴权**：`fwwb` 后端 REST API 与 UDP 服务均未实现登录鉴权，任何可达客户端均可发送控制命令。
4. **通信未加密**：`fwwb` 的小程序 ↔ 后端 ↔ Hi3861 全程明文 UDP；`lidar/` 的 ROS 话题也明文传输。
5. **权限风险**：`lidar/start_slam.sh` 需要 `sudo` 执行（串口设备 + Docker 管理）。
6. **硬件损伤风险**：激光雷达避免桌面遮挡、阳光直射、全黑/高反光表面。

---

## 8. 相关文档索引

| 文档路径 | 内容 |
|----------|------|
| `fwwb/AGENTS.md` | 智慧工厂平台详细架构、构建命令、通信协议、代码规范 |
| `fwwb/CLAUDE.md` | 硬件参数、FreeRTOS 任务表、PCF8574 I/O 定义、Vant 图标列表 |
| `fwwb/接口说明文档.md` | 后端 API 接口详细说明 |
| `fwwb/算法设计文档.md` | 智能光照、灌溉、告警算法 |
| `fwwb/4层通信协议汇总.md` | 完整协议定义（实际为 5 层） |
| `fwwb/HARDWARE_DATA_FORMAT.md` | Yesense H30 IMU 与 LD14P 激光雷达的串口协议、数据结构 |
| `lidar/AGENTS.md` | ROS1 SLAM 系统详细架构、构建命令、坐标系与 TF 树、诊断命令 |
| `lidar/CLAUDE.md` | Hector SLAM 原理与调优、Cartographer 配置说明 |
| `lidar/启动指南.md` | 硬件连接与启动指南 |
| `lidar/SLAM架构与优化分析.md` | Hector SLAM 原理与调优 |
