# Cartographer 2D SLAM 参数对照表

> 更新日期：2026-06-08
> 目标：提高地图更新频率，适配小车边走边建图场景

---

## 一、地图更新频率相关参数（本次重点调整）

### 1.1 运动滤波器 motion_filter

控制 scan 是否插入当前子图。三个条件满足**任一**即插入。

| 参数 | 含义 | ld14p 修改前 | ld14p 修改后 | ld14p_imu 修改前 | ld14p_imu 修改后 | ld14p_wheel 修改前 | ld14p_wheel 修改后 | ld14p_imu_wheel 修改前 | ld14p_imu_wheel 修改后 |
|------|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `max_time_seconds` | 最大时间间隔(s)，超时强制插入 | 1.0 | **0.5** | 1.0 | **0.5** | 2.0 | **0.5** | 2.0 | **0.5** |
| `max_distance_meters` | 最小位移(m)，达到即插入 | 0.1 | **0.05** | 0.1 | **0.05** | 0.1 | **0.05** | 0.1 | **0.05** |
| `max_angle_radians` | 最小转角(°)，达到即插入 | 5° | **3°** | 5° | **3°** | 10° | **5°** | 10° | **5°** |

**调参指南：**
- 地图更新太慢 → 减小这三个值（更多 scan 被插入）
- 地图出现重影/拖影 → 增大 `max_angle_radians`（旋转时少插入）
- CPU 占用过高 → 增大 `max_time_seconds`（减少插入频率）

### 1.2 子图大小 submaps.num_range_data

每个子图包含的 scan 帧数。子图完成 = 2 × num_range_data 帧插入。

| 参数 | ld14p 修改前 | ld14p 修改后 | ld14p_imu 修改前 | ld14p_imu 修改后 | ld14p_wheel 修改前 | ld14p_wheel 修改后 | ld14p_imu_wheel 修改前 | ld14p_imu_wheel 修改后 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `num_range_data` | 15 | **10** | 15 | **10** | 10 | 10 | 15 | **10** |

**调参指南：**
- LD-14P 10Hz，num_range_data=10 → 子图约 1 秒完成
- 值越小 → 子图越快完成 → 地图更新越频繁 → 但子图边界增多可能影响拼接质量
- 值越大 → 子图越大 → 拼接更平滑 → 但更新延迟增大

### 1.3 Occupancy Grid 发布周期（launch 文件）

| 参数 | 含义 | 修改前 | 修改后 | 位置 |
|------|------|:---:|:---:|------|
| `-publish_period_sec` | /map 话题发布周期 | 1.0s（默认值） | **0.3s** | `cartographer_ld06.launch` 第 47 行 |
| `-resolution` | 栅格分辨率(m) | 0.05 | 0.05（未改） | 同上 |

**调参指南：**
- 值越小 → RViz 地图刷新越快 → 但 CPU 开销增大
- 该节点只是"渲染"，不影响 Cartographer 内部建图质量

### 1.4 子图发布周期 submap_publish_period_sec

| 参数 | 含义 | 所有配置当前值 |
|------|------|:---:|
| `submap_publish_period_sec` | 子图列表发布到 ROS 的周期 | 0.1s |

已从早期的 0.3s 优化到 0.1s，当前值合理，未修改。

---

## 二、扫描匹配参数（影响位姿精度）

### 2.1 Ceres 扫描匹配器

| 参数 | 含义 | ld14p | ld14p_imu | ld14p_wheel | ld14p_imu_wheel |
|------|------|:---:|:---:|:---:|:---:|
| `occupied_space_weight` | 占据空间匹配权重 | 8.0 | 8.0 | **10.0** | 8.0 |
| `translation_weight` | 平移约束权重 | 5.0 | 5.0 | 5.0 | 5.0 |
| `rotation_weight` | 旋转约束权重 | 15.0 | 15.0 | **20.0** | 15.0 |
| `max_num_iterations` | 最大迭代次数 | 12 | 12 | **15** | 12 |

**调参指南：**
- `occupied_space_weight` 越大 → scan-to-map 匹配越强 → 漂移越小 → 但计算量增大
- `translation_weight` / `rotation_weight` 越大 → 越信任上一帧位姿 → 运动平滑但响应变慢
- `max_num_iterations` 越大 → 匹配越精确 → 但耗时增大（影响实时性）

### 2.2 实时相关扫描匹配器（在线暴力搜索）

| 参数 | 含义 | ld14p | ld14p_imu | ld14p_wheel | ld14p_imu_wheel |
|------|------|:---:|:---:|:---:|:---:|
| `use_online_correlative_scan_matching` | 启用在线暴力匹配 | true | true | true | true |
| `linear_search_window` | 平移搜索窗口(m) | 0.2 | 0.2 | 0.2 | 0.15 |
| `angular_search_window` | 角度搜索窗口(°) | 20° | 20° | 20° | 15° |
| `translation_delta_cost_weight` | 平移偏差惩罚 | 10.0 | 10.0 | 0.1 | **1.0** |
| `rotation_delta_cost_weight` | 旋转偏差惩罚 | 0.1 | 0.1 | 0.1 | 0.1 |

**调参指南：**
- 搜索窗口越大 → 容忍更大位姿误差 → 但 CPU 开销呈平方增长
- `translation_delta_cost_weight` 越大 → 越信任初始位姿（不敢大幅修正）
- 有轮速里程计时可适当减小搜索窗口（轮速提供较好的初值）

---

## 三、传感器与范围参数

| 参数 | 含义 | ld14p | ld14p_imu | ld14p_wheel | ld14p_imu_wheel |
|------|------|:---:|:---:|:---:|:---:|
| `min_range` | 最小有效距离(m) | **0.1** | **0.1** | **0.1** | **0.1** |
| `max_range` | 最大有效距离(m) | **8.0** | **8.0** | 12.0 | 12.0 |
| `missing_data_ray_length` | 无回波射线长度(m) | **3.0** | **3.0** | **5.0** | **5.0** |
| `use_imu_data` | 使用 IMU | false | **true** | false | **true** |
| `use_odometry` | 使用轮速里程计 | true | true | true | true |
| `provide_odom_frame` | Cartographer 提供 odom TF | true | true | **false** | **false** |

**调参指南：**
- `min_range`：LD-14P 近距离噪点大，纯雷达模式可从 0.02 提高到 0.1 过滤近场噪声
- `missing_data_ray_length`：太小 → 已探索区域残留"幽灵障碍"；太大 → 错误清除远处墙壁
- `provide_odom_frame`：使用外部轮速里程计时设为 false（轮速节点已发布 odom TF）

---

## 四、全局 SLAM（回环检测与位姿图优化）

| 参数 | 含义 | ld14p | ld14p_imu | ld14p_wheel | ld14p_imu_wheel |
|------|------|:---:|:---:|:---:|:---:|
| `optimize_every_n_nodes` | 每 N 个节点做一次全局优化 | 20 | 20 | **10** | **10** |
| `min_score` | 回环约束最小匹配分 | 0.65 | 0.65 | **0.55** | 0.65 |
| `global_localization_min_score` | 全局定位最小匹配分 | 0.7 | 0.7 | **0.6** | 0.7 |
| `linear_search_window` | 回环平移搜索窗口(m) | 7.0 | 7.0 | 7.0 | 7.0 |
| `angular_search_window` | 回环角度搜索窗口(°) | 30° | 30° | 30° | 30° |
| `branch_and_bound_depth` | 分支定界深度 | 7 | 7 | 7 | 7 |

**调参指南：**
- `optimize_every_n_nodes` 越小 → 全局优化越频繁 → 漂移修正越及时 → CPU 开销增大
- `min_score` 越低 → 更容易接受回环约束 → 可能引入错误回环
- 10Hz LiDAR + optimize_every_n_nodes=10 → 约每 1 秒全局优化一次

---

## 五、发布频率参数

| 参数 | 含义 | 所有配置当前值 | 对应话题 |
|------|------|:---:|------|
| `pose_publish_period_sec` | TF (map→odom) 发布周期 | 0.005s (200Hz) | /tf |
| `trajectory_publish_period_sec` | 轨迹标记发布周期 | 0.03s (~33Hz) | /trajectory_marker_list |
| `submap_publish_period_sec` | 子图列表发布周期 | 0.1s (10Hz) | /submap_list |
| `publish_period_sec` (occupancy_grid) | 栅格地图发布周期 | **0.3s** (~3Hz) | /map |

---

## 六、各配置文件差异速查表

| 参数类别 | 参数 | ld14p (纯雷达) | ld14p_imu (+IMU) | ld14p_wheel (+轮速) | ld14p_imu_wheel (全传感器) |
|----------|------|:-:|:-:|:-:|:-:|
| **IMU** | use_imu_data | ❌ | ✅ | ❌ | ✅ |
| **odom来源** | provide_odom_frame | Cartographer | Cartographer | 外部轮速 | 外部轮速 |
| **近场过滤** | min_range | 0.1 | 0.1 | 0.1 | 0.1 |
| **远场截断** | max_range | 8.0 | 8.0 | 12.0 | 12.0 |
| **空闲清除** | missing_data_ray_length | 3.0 | 3.0 | 5.0 | 5.0 |
| **子图大小** | num_range_data | 10 | 10 | 10 | 10 |
| **运动滤波** | max_time / dist / angle | 0.5s/0.05m/3° | 0.5s/0.05m/3° | 0.5s/0.05m/5° | 0.5s/0.05m/5° |
| **Ceres迭代** | max_num_iterations | 12 | 12 | 15 | 12 |
| **占据权重** | occupied_space_weight | 8.0 | 8.0 | 10.0 | 8.0 |
| **旋转权重** | rotation_weight | 15.0 | 15.0 | 20.0 | 15.0 |
| **搜索窗口** | linear/angular | 0.2m/20° | 0.2m/20° | 0.2m/20° | 0.15m/15° |
| **全局优化** | optimize_every_n_nodes | 20 | 20 | 10 | 10 |
| **回环分数** | min_score | 0.65 | 0.65 | 0.55 | 0.65 |

---

## 七、常见问题调参速查

### 地图更新太慢
```
motion_filter.max_time_seconds → 减小（如 0.3）
motion_filter.max_distance_meters → 减小（如 0.03）
submaps.num_range_data → 减小（如 8）
occupancy_grid publish_period_sec → 减小（如 0.2）
```

### 地图出现重影/拖影
```
motion_filter.max_angle_radians → 增大（如 10°~15°）
ceres_scan_matcher.rotation_weight → 增大
real_time_correlative_scan_matcher.angular_search_window → 增大
```

### 地图有"幽灵障碍"（已走过区域残留障碍物）
```
missing_data_ray_length → 增大（如 3.0~5.0m，但不能超过 max_range）
max_range → 减小（如 8.0m，过滤远距离不可靠数据）
min_range → 增大（如 0.1m，过滤近场噪声）
```

### 漂移严重
```
ceres_scan_matcher.occupied_space_weight → 增大
POSE_GRAPH.optimize_every_n_nodes → 减小
use_online_correlative_scan_matching = true
real_time_correlative_scan_matcher.linear_search_window → 增大
```

### CPU 占用过高
```
ceres_scan_matcher.max_num_iterations → 减小
use_online_correlative_scan_matching = false（关闭暴力搜索）
POSE_GRAPH.optimize_every_n_nodes → 增大
motion_filter.max_time_seconds → 增大
```

### 回环检测失败
```
POSE_GRAPH.constraint_builder.min_score → 减小
fast_correlative_scan_matcher.linear_search_window → 增大
fast_correlative_scan_matcher.angular_search_window → 增大
global_constraint_search_after_n_seconds → 减小
```

---

## 八、Cartographer 默认值参考

以下为 Cartographer 官方默认值，供回退参考：

| 参数 | 官方默认值 | 当前 ld14p 值 |
|------|:---:|:---:|
| submaps.num_range_data | 90 | 10 |
| motion_filter.max_time_seconds | 5.0 | 0.5 |
| motion_filter.max_distance_meters | 0.2 | 0.05 |
| motion_filter.max_angle_radians | 1° | 3° |
| ceres_scan_matcher.occupied_space_weight | 2.0 | 8.0 |
| ceres_scan_matcher.max_num_iterations | 20 | 12 |
| optimize_every_n_nodes | 90 | 20 |
| use_online_correlative_scan_matching | false | true |

---

## 九、IMU 滤波器参数（imu_complementary_filter）

> 配置文件：`cartographer_ld06/launch/imu_filter.launch`

| 参数 | 含义 | 当前值 | 调参方向 |
|------|------|:---:|------|
| `use_mag` | 使用磁力计 | false | Yesense H30 无可靠磁力计，保持 false |
| `do_bias_estimation` | 在线陀螺仪偏置估计 | **true** | 核心功能，保持 true |
| `bias_alpha` | 偏置估计平滑系数 | 0.01 | 越小越稳定但收敛慢，越大收敛快但可能抖动 |
| `do_adaptive_gain` | 自适应增益 | true | 静止时信任加速度计，运动时信任陀螺仪 |
| `remove_gravity_vector` | 移除重力 | false | Cartographer 需要重力信息，保持 false |

**数据流：** `/imu_raw` → imu_complementary_filter → `/imu`

**滤波器特性：**
- 不修改 `angular_velocity` 和 `linear_acceleration` 字段（保持原始数据）
- 只修正 `orientation`（四元数）
- 在线估计并减去陀螺仪零偏

---

## 十、轮速/IMU 互补滤波参数（wheel_odom v3）

> 配置文件：`wheel_odom/launch/wheel_odom.launch`

| 参数 | 含义 | 当前值 | 调参方向 |
|------|------|:---:|------|
| `alpha_static` | 静止时轮速权重 | 0.3 | 越小越信任 IMU（静止时推荐 0.2~0.4） |
| `alpha_moving` | 运动时轮速权重 | 0.7 | 越大越信任轮速（运动时推荐 0.6~0.8） |
| `speed_threshold` | 静止判定阈值 (m/s) | 0.05 | 低于此值视为静止 |

**互补滤波逻辑：**
```
if speed < speed_threshold:
    alpha = alpha_static    # 静止：30%轮速 + 70%IMU
else:
    alpha = alpha_moving    # 运动：70%轮速 + 30%IMU

theta = alpha * theta_wheel_pred + (1-alpha) * theta_imu
w_fused = alpha * w_wheel + (1-alpha) * w_imu
```

**调参指南：**
- 原地旋转时角度不准 → 减小 `alpha_static`（更信任 IMU）
- 直行时角度抖动 → 增大 `alpha_moving`（更信任轮速）
- IMU 漂移严重 → 增大两个 alpha（更信任轮速）
- 轮速噪声大 → 减小两个 alpha（更信任 IMU）

---

## 十一、IMU 协方差参数（待校准）

> 配置文件：`yesense_imu/launch/yesense_ahrs.launch`
> 校准工具：`./imu_calibration.sh record 30 && ./imu_calibration.sh analyze`

| 参数 | 含义 | 当前默认值 | 校准后应填入 |
|------|------|:---:|------|
| `orientation_stddev` | 方向标准差 | 0.05 | ARW × π/180 / 60 |
| `angular_velocity_stddev` | 角速度标准差 | 0.02 | ARW × π/180 / 60 |
| `linear_acceleration_stddev` | 加速度标准差 | 0.1 | VRW / 60 |

**校准流程：**
1. 小车静止放在平面上
2. `sudo ./imu_calibration.sh record 30`（录制 30 分钟）
3. `sudo ./imu_calibration.sh analyze`（分析 Allan 方差）
4. 用输出的 ARW/VRW 值更新 launch 文件中的 stddev
