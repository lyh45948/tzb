# Cartographer 2D SLAM 优化计划

> **本文件与 `~/.claude/plans/cheeky-spinning-seahorse.md` 同步更新**
>
> 每次新会话启动时，Claude 会自动检查本计划并继续推进。
> 如果上下文过长，会自动 compact 以保持高效。

## 项目背景

当前 `lidar/` 项目使用 Google Cartographer 2D SLAM，传感器组合为：
- **LD-14P** 2D LiDAR（10Hz，USB串口）
- **Yesense H30** IMU（200Hz，AHRS，USB串口）
- **Hi3861** 轮式里程计（UDP 7799，L_spd/R_spd）

**已知问题**：
- 长走廊/隧道场景位姿漂移
- 纯旋转时角度累积误差
- 快速运动时帧间匹配失败
- 长时间运行后累积漂移

---

## 执行阶段

### Phase 1: IMU 参数精标定（基于已有 Allan 方差数据）

**状态**: ✅ 已完成 (2026-06-09)

**成果**:
- 分析 `imu_calibration/allan_variance.csv`（8999个有效数据点，tau=0.1~899.9s）
- 提取关键噪声参数：
  - Gyro ARW: 4.0 deg/sqrt(hr) = 0.00116 rad/sqrt(s)
  - Gyro Bias Instability: 68.9 deg/hr（实测值，偏高但可接受）
  - Accel VRW: 0.28 m/s/sqrt(hr) = 0.00473 m/s/sqrt(s)
- 生成 `imu_calibration/imu_params.yaml`
- 更新 `yesense_ahrs.launch` 协方差参数：
  - orientation_stddev: 0.0011 → 0.0164 rad
  - angular_velocity_stddev: 0.0011 → 0.0164 rad/s
  - linear_acceleration_stddev: 0.004 → 0.0668 m/s²
- 更新 `imu_filter.launch` bias_alpha: 0.01 → 0.0075

利用已采集的 `imu_calibration/allan_variance.csv` 提取 ARW/VRW，更新 IMU 协方差参数。

**关键文件**:
- `imu_calibration/allan_variance.csv` — 已有数据
- `yesense_imu/launch/yesense_ahrs.launch` — 需更新协方差
- `cartographer_ld06/launch/imu_filter.launch` — 需更新 bias_alpha

---

### Phase 2: Cartographer 参数深度优化

**状态**: ✅ 已完成 (2026-06-09)

**成果**:
- 备份所有 4 个 `.lua` 配置文件
- 系统优化以下参数（所有配置一致）：

| 参数类别 | 参数 | 优化前 | 优化后 | 说明 |
|---------|------|--------|--------|------|
| **子图** | num_range_data | 10 | **12** | 提高局部一致性 |
| **子图** | hit_probability | 0.55 | **0.6** | 增强地图置信度 |
| **运动滤波** | max_distance | 0.05m | **0.08m** | 避免过度碎片化 |
| **运动滤波** | max_angle | 3°~5° | **4°** | 统一参数 |
| **Ceres匹配** | occupied_space_weight | 8.0 | **10.0** | 增强scan-to-map约束 |
| **Ceres匹配** | translation_weight | 5.0 | **8.0** | 增强平移约束 |
| **Ceres匹配** | rotation_weight | 15.0 | **20.0** | 增强旋转约束 |
| **Ceres匹配** | max_num_iterations | 12 | **15** | 提升匹配精度 |
| **回环检测** | min_score | 0.65 | **0.55** | 提高回环成功率 |
| **回环检测** | linear_search_window | 7.0m | **10.0m** | 容忍更大漂移 |
| **回环检测** | angular_search_window | 30° | **45°** | 容忍更大角度偏差 |
| **全局优化** | optimize_every_n_nodes | 10~20 | **8** | 更快修正漂移 |
| **全局优化** | global_constraint_search | 10s | **5s** | 更频繁搜索回环 |
| **全局优化** | loop_closure_translation_weight | 1.1e4 | **2.0e4** | 增强回环约束 |
| **全局优化** | loop_closure_rotation_weight | 1e5 | **2.0e5** | 增强回环约束 |
| **全局优化** | odometry_translation_weight | 1e5 | **1e4** | 降低轮速信任度 |
| **全局优化** | odometry_rotation_weight | 1e5 | **1e4** | 降低轮速信任度 |

针对退化场景系统性优化 Cartographer 配置，重点：
- 回环检测阈值降低（min_score 0.65→0.55）
- 搜索窗口增大（linear 7→10m, angular 30°→45°）
- Ceres 匹配权重增强（occupied_space 8→10, rotation 15→20）
- 全局优化频率提高（optimize_every_n_nodes 10→8）
- 回环约束权重增大（loop_closure_translation 1.1e4→2.0e4）
- odometry 约束权重降低（1e5→1e4，不完全信任轮速）

**关键文件**:
- `cartographer_ld06/configuration_files/ld14p_*.lua` — 4个配置文件

---

### Phase 3: 轮式里程计标定与增强

**状态**: ⏳ 待开始

- 精确标定 scale_factor 和 wheel_base
- wheel_odom_publisher 添加打滑检测（v4）

**关键文件**:
- `wheel_odom/scripts/wheel_odom_publisher.py`
- `wheel_odom/launch/wheel_odom.launch`

---

### Phase 4: 地图保存与加载

**状态**: ⏳ 待开始

- 新建 `save_map.sh` 脚本
- 新建 `cartographer_localization.launch` 纯定位模式
- `start_slam.sh` 添加 `--localization` 参数

---

### Phase 5: 退化场景测试与调优

**状态**: ⏳ 待开始

测试场景：
- A: 10m 长走廊往返
- B: 原地旋转 10 圈
- C: S 形路径 + 回环
- D: 混合场景（房间→走廊→房间）

使用 rosbag 记录 + evo 工具评估 ATE/RPE。

---

### Phase 6: 文档更新与回归测试

**状态**: ⏳ 待开始

- 更新 `SLAM参数对照表.md`
- 更新 `SLAM架构与优化分析.md`
- 新建 `OPTIMIZATION_LOG.md` 记录每次修改

---

## 验收指标

| 指标 | 优化前 | 优化后目标 |
|------|--------|-----------|
| 长走廊 10m 单程漂移 | ~10-15cm | < 5cm |
| 往返闭合误差 | ~5-8cm | < 3cm |
| 纯旋转 10 圈角度漂移 | ~5-10° | < 2° |
| 长时间运行（30min）漂移 | ~20-30cm | < 10cm |
| 地图保存/加载 | 不支持 | 支持 |

---

## 快速命令

```bash
# 启动 SLAM（全传感器模式）
cd /home/tzb/tzb/lidar && sudo ./start_slam.sh

# 查看日志
sudo docker exec ros_container tail -f /tmp/roslaunch.log

# 查看 TF
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rosrun tf tf_echo map base_link"

# 保存地图
sudo docker exec ros_container bash -c "source /catkin_ws/devel/setup.bash && rosrun map_server map_saver -f /catkin_ws/map/my_map"

# IMU 标定
sudo ./imu_calibration.sh record 30
sudo ./imu_calibration.sh analyze
```

---

*计划制定时间: 2026-06-09*
*最后更新: 2026-06-09*
