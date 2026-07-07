# AGENTS.md — 本项目 AI 编码代理指南

> 本文件面向 AI 编码代理（coding agent）。若你正在阅读此文件，说明你对本项目一无所知。以下信息均基于实际代码与配置文件，无假设与泛化。

---

## 1. 项目概述

本项目是一个基于 **ROS1 Noetic** 的机器人 SLAM 系统，核心硬件为：

- **LD-14P 激光雷达**（LDROBOT，USB 串口 CH343，波特率 230400，发布 `/scan`）
- **Yesense H30 IMU**（WHEELTEC，USB 串口 CH343，波特率 460800，发布 `/imu`）

系统使用 **Cartographer 2D** SLAM 后端：纯 2D scan matching，支持可选 IMU 辅助重力对齐和回环检测。

支持**纯雷达运行**（未检测到 IMU 时自动禁用 IMU 节点）。

项目采用 **Docker 容器化**运行，主机通过串口与硬件通信，容器内运行 ROS 节点。

---

## 2. 技术栈与构建系统

| 层级 | 技术 |
|------|------|
| 操作系统 | Ubuntu 20.04 (Focal)，ROS Noetic |
| 容器 | Docker (`osrf/ros:noetic-desktop`) |
| 构建工具 | `catkin` / `catkin_make` |
| 语言 | C++11（节点）、Python 3（脚本） |
| 编译配置 | `CMakeLists.txt` + `package.xml`（标准 ROS 包结构） |
| 依赖库 | `roscpp`, `sensor_msgs`, `serial`, `tf`, `pcl_ros`, `map_server`, `cartographer_ros` |

### 关键构建命令

```bash
# 在 Docker 容器内编译
cd /catkin_ws
source /opt/ros/noetic/setup.bash
catkin_make

# 单独编译某个包
catkin_make -DCATKIN_WHITELIST_PACKAGES="ldlidar"
```

### 一键启动（主机执行）

```bash
cd /home/tzb/lidar
sudo ./start_slam.sh          # Cartographer 2D SLAM
```

该脚本自动完成：
1. 动态检测 CH343 串口并识别 Lidar/IMU 身份
2. 如果只检测到雷达，以**纯雷达模式**启动；如果检测到 IMU，自动启用 IMU 融合
3. 创建 `/dev/wheeltec_lidar` 符号链接（IMU 存在时创建 `/dev/yesense_imu`）
4. 启动 Docker 容器（`ros_container`），只挂载实际存在的设备
5. 安装 apt/ros 依赖（首次）
6. 编译工作空间（首次）
7. 后台启动所有 ROS 节点

---

## 3. 代码组织与模块划分

```
/home/tzb/lidar/
├── catkin_ws/                     # ROS1 工作空间（主运行目录）
│   ├── src/
│   │   ├── ldlidar/               # 激光雷达 ROS 驱动（ldlidar_ros1 的副本）
│   │   ├── yesense_imu/           # IMU ROS 驱动（yesense_imu 的副本）
│   │   ├── imu_tf_broadcaster/    # IMU TF 广播器（副本）
│   │   ├── cartographer/          # Cartographer 核心库（Plain CMake）
│   │   ├── cartographer_ros/      # Cartographer ROS 封装
│   │   ├── cartographer_ld06/     # 本项目 Cartographer 配置与 launch
│   │   ├── slam.rviz              # RViz 默认配置
│   │   └── save_map.sh            # 地图保存脚本
│   ├── build_isolated/            # Cartographer 隔离构建产物
│   ├── devel_isolated/            # Cartographer 隔离开发空间
│   └── map/                       # 保存的地图输出目录
│
├── ldlidar_ros1/                  # 激光雷达驱动源码（原始包）
│   ├── ldlidar/                   # ROS1 封装节点
│   │   ├── src/main.cpp           # 节点入口
│   │   ├── launch/*.launch        # 各型号雷达启动配置
│   │   └── rviz/                  # RViz 配置
│   └── ldlidar_driver/            # 无 ROS 依赖的核心驱动库
│       ├── include/core/          # 主 API: ldlidar_driver.h
│       ├── include/dataprocess/   # 数据包解析: lipkg.h
│       ├── include/filter/        # 噪声滤波: tofbf.h
│       └── src/                   # 串口/网口通信实现
│
├── yesense_imu/                   # IMU 驱动源码（原始包）
│   ├── src/
│   │   ├── yesense_node.cpp       # 节点入口
│   │   ├── yesense_driver.cpp/h   # 串口驱动与参数配置指令
│   │   └── analysis_data.cpp/h    # YIS 协议解析（0x59 0x53 帧头）
│   ├── msg/                       # 自定义消息类型（15 种）
│   ├── launch/yesense_ahrs.launch # IMU 节点启动配置
│   ├── cfg/Yesense.cfg            # dynamic_reconfigure 配置
│   └── yesense.md                 # 参数设置指令表（中文）
│
├── imu_tf_broadcaster/            # 简单 IMU TF 广播节点（Python）
│   ├── scripts/imu_tf_broadcaster.py
│   └── launch/imu_tf_broadcaster.launch
│
├── start_slam.sh                  # 一键启动脚本（核心运维入口）
├── build_lidar.sh                 # ROS2 编译脚本（Humble）
├── run_ros2_docker.sh             # ROS2 Docker 运行脚本
├── check_ports.py                 # 串口硬件诊断脚本
├── 启动指南.md                     # 硬件连接与启动指南
├── SLAM架构与优化分析.md           # SLAM 架构与调优分析
└── start_ros_slam.md              # ROS 节点手动启动文档
```

### 模块职责

| 包名 | 职责 |
|------|------|
| `ldlidar` | 读取串口激光数据 → 解析点云 → 发布 `sensor_msgs/LaserScan` (`/scan`) |
| `yesense_imu` | 读取串口 IMU 数据 → 解析 YIS 协议 → 发布 `sensor_msgs/Imu` (`/imu`) 及 15 种自定义消息 |
| `imu_tf_broadcaster` | 订阅 `/imu` → 广播 `imu_link` 相对于 `world` 的 TF 变换（演示用） |
| `cartographer_ld06` | 提供 Cartographer 的 Lua 配置与 launch 文件，支持 Lidar（+ 可选 IMU）|
| `rf2o_laser_odometry` | （已弃用，保留但不启动）2D 激光帧间里程计 |
| `robot_localization` | （已弃用，保留但不启动）EKF 融合激光里程计 + IMU |

---

## 4. 硬件与串口配置

### 设备映射

| 设备 | 芯片 | 实际设备 | 别名 | 波特率 |
|------|------|----------|------|--------|
| 激光雷达 | CH343 | `/dev/ttyCH343USB0/1` | `/dev/wheeltec_lidar` | 230400 |
| IMU | CH343 | `/dev/ttyCH343USB0/1` | `/dev/yesense_imu` | 460800 |

> 注意：两个 CH343 端口的编号可能因插拔顺序交换。`start_slam.sh` 内置自动检测逻辑（读取首字节判断 `0x59` 为 IMU，`0x54` 为 Lidar）。

### 手动排查串口

```bash
# 测试 IMU（应看到 59 53 帧头）
stty -F /dev/ttyCH343USB0 460800 raw
sudo docker exec ros_container bash -c "timeout 2 head -c 100 /dev/ttyCH343USB0 | od -A x -t x1z | grep '59 53'"

# 测试激光雷达（应看到 54 帧头）
stty -F /dev/ttyCH343USB1 230400 raw
sudo docker exec ros_container bash -c "timeout 2 head -c 100 /dev/ttyCH343USB1 | od -A x -t x1z | grep '54'"
```

---

## 5. 坐标系与 TF 树

### Cartographer 2D 模式（IMU 可选）

**有 IMU：**
```
map ──(cartographer)──→ odom ──→ base_link ──→ {laser, imu_link}
```

**无 IMU：**
```
map ──(cartographer)──→ odom ──→ base_link ──→ laser
```

- `base_link → laser`: `0 0 0.18 0 0 0`（z=0.18m）
- `base_link → imu_link`: `0 0.08 -0.05 0 0 0`（y=0.08m, z=-0.05m，仅 IMU 存在时发布）
- Cartographer 2D 发布 `map → odom → base_link`，`provide_odom_frame = true`
- 有 IMU 时：IMU 提供重力对齐和旋转约束，辅助 scan matching
- 无 IMU 时：纯 scan matching，Cartographer 自行估计位姿
- 子图分辨率 0.05m，支持回环检测和全局优化

---

## 6. 关键启动文件参数

### `yesense_imu/launch/yesense_ahrs.launch`

| 参数 | 值 |
|------|-----|
| `yesense_port` | `/dev/yesense_imu` |
| `yesense_baudrate` | `460800` |
| `frame_id` | `imu_link` |
| `imu_topic` | `imu` |

### `catkin_ws/src/ldlidar/launch/ld14p.launch`

| 参数 | 值 |
|------|-----|
| `port_name` | `/dev/wheeltec_lidar` |
| `port_baudrate` | `230400` |
| `frame_id` | `laser` |

### `catkin_ws/src/cartographer_ld06/launch/cartographer_ld06.launch`（Cartographer 配置）

| 参数 | 值 | 说明 |
|------|-----|------|
| `use_imu` | `false`（自动） | 是否启动 IMU 节点和 TF |
| `config_basename` | `ld14p` / `ld14p_imu` | 无 IMU 用 `ld14p.lua`，有 IMU 用 `ld14p_imu.lua` |

---

## 7. 开发规范

### 代码风格

- C++ 使用 **C++11** 标准（`CMakeLists.txt` 中显式设置 `-std=c++11`）
- 代码注释以 **中文** 为主
- ROS 包遵循标准 `catkin` 包结构：`CMakeLists.txt` + `package.xml` + `src/` + `launch/`
- Python 脚本需添加 shebang：`#!/usr/bin/env python3`

### 串口协议

- **IMU**：YIS 协议，帧头 `0x59 0x53`，CRC16 校验（和校验）。详见 `yesense_imu/src/analysis_data.cpp`
- **Lidar**：LDROBOT 私有协议，帧头 `0x54`，支持串口与网口两种模式

### 动态重配置

`yesense_imu` 支持 `dynamic_reconfigure`，配置文件为 `cfg/Yesense.cfg`，可在运行时通过 `rqt_reconfigure` 修改波特率、输出频率、输出内容等参数。

---

## 8. 测试与诊断

### 无单元测试框架

本项目未配置 gtest 或 nosetests（`CMakeLists.txt` 中测试部分被注释掉）。验证方式以**硬件在环测试**和**ROS 话题诊断**为主。

### 常用诊断命令

```bash
# 查看节点列表
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rosnode list"

# 查看话题列表
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rostopic list"

# 查看雷达数据频率
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rostopic hz /scan"

# 查看 IMU 数据频率
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rostopic hz /imu"

# 查看 TF 树
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rosrun tf2_tools view_frames.py"

# 查看日志
sudo docker exec ros_container bash -c "tail -f /tmp/roslaunch.log"
```

### RViz 可视化

```bash
xhost +local:root
sudo docker exec -it ros_container bash
source /catkin_ws/devel/setup.bash
rviz -d /catkin_ws/src/cartographer_ld06/rviz/cartographer.rviz
```

显示内容：
- 绿色点云：`/scan` (LaserScan)
- 灰色栅格地图：`/map` (Map)
- 轨迹：`/trajectory_node_list` (Trajectory)
- TF 坐标系：`/tf`

---

## 9. 地图保存与部署

### 保存地图

```bash
sudo ./catkin_ws/src/save_map.sh
```

输出到 `/catkin_ws/map/YYYYMMDD_HHMMSS.{pgm,yaml}`。

### 停止系统

```bash
sudo docker stop ros_container
```

### 容器生命周期

- 容器名固定为 `ros_container`
- `start_slam.sh` 会自动处理：创建、重启、设备映射过期重建
- 容器重启后符号链接会丢失，脚本会自动重新配置

---

## 10. 安全与注意事项

1. **权限**：`start_slam.sh` 需要 `sudo` 执行（串口设备访问 + Docker 管理）
2. **硬件损伤风险**：
   - 激光雷达不要放在桌面上（会遮挡下方 180° 视野）
   - 避免阳光直射激光雷达窗口
   - 避免全黑/高反光表面
3. **软件稳定性**：
   - **Cartographer 2D**：纯 scan matching，可选 IMU 辅助。`use_imu_data` 在 `ld14p_imu.lua` 中为 `true`，在 `ld14p.lua`（纯雷达）中为 `false`
4. **Docker 镜像**：使用清华 apt 镜像源加速依赖安装，首次启动需 3~5 分钟

---

## 11. 修改项目时的 checklist

- [ ] 修改 `launch` 文件后无需重新编译，直接重新 `roslaunch` 即可
- [ ] 修改 C++ 源码后需在容器内重新执行 `catkin_make`
- [ ] 若修改了 Cartographer 的 `*.lua` 配置，需同步到 `install_isolated/share/cartographer_ld06/configuration_files/`
- [ ] 若修改了 Cartographer 的核心 C++ 代码，需使用 `catkin_make_isolated` 重新编译
- [ ] 修改串口参数（波特率、设备名）时，需同步更新 `launch` 文件与 `start_slam.sh` 中的检测逻辑
- [ ] 新增 ROS 包时，需将其放入 `catkin_ws/src/` 并重新编译
- [ ] 所有路径硬编码为 `/home/tzb/lidar/`，若迁移项目需全局替换

---

## 12. Git 工作流（铁律）

> 本子项目遵循工作空间统一的 **GitHub Flow**（详见根目录 `AGENTS.md` 第 8 节）。此处给出本子项目适用的完整规则。

### 铁律

- `main` 分支**始终保持可运行**，**严禁直接在其上提交任何代码改动**（C++ 驱动、Python 脚本、launch、lua 配置、shell 脚本等一律开分支）。
- 任何代码改动必须先从最新 `main` 拉出独立分支，完成后再合并回 `main`。
- **例外**：仅修改 `AGENTS.md` / `CLAUDE.md` / `*.md` / 注释这类**无代码逻辑**的改动，允许直接在 `main` 提交（仍鼓励开分支）。

### 标准流程（每次改动）

```bash
# 1. 基于最新 main 起步
git checkout main && git pull

# 2. 新建分支
git checkout -b <type>/<scope>-<简述>

# 3. 在分支上开发、按 Conventional Commits 提交
git commit -m "<type>(<scope>): <subject>"

# 4. 自检：C++/lua/launch 改动后按第 11 节 checklist 决定是否重编译；复查差异
git diff main

# 5. 合并回 main（--no-ff 保留分支记录）
git checkout main && git merge --no-ff <分支名>

# 6. 合并后删除分支
git branch -d <分支名>
```

### 分支命名规范

- **type**：`feat`（新功能）、`fix`（缺陷修复）、`docs`（文档）、`refactor`（重构）、`chore`（构建/杂务）
- **scope**：`slam`（SLAM 整体）、`ldlidar`（激光雷达驱动）、`yesense`（IMU 驱动）、`cartographer`（SLAM 配置）、`docker`（容器/部署）、`docs`、`config`
- 示例：`fix/ldlidar-frame-parse`、`feat/cartographer-imu-tune`、`chore/docker-resource-limit`

### 提交格式
```
<type>(<scope>): <subject>
```

### 同步义务

凡改动影响到本文件或 `CLAUDE.md` 描述的**坐标系与 TF 树、串口设备映射、Cartographer 参数、launch 配置、分支模型**等内容，**必须同步更新对应说明文件**，并在同一分支一并提交。说明文件与代码不一致是技术债，禁止留下。

### 工作区卫生

- 开新分支前 `git status` 应干净；未提交改动先 `git stash` 或提交，**不要把无关改动混入新分支**。
