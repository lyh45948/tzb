# 当前 SLAM 系统架构与优化分析

## 一、整体架构

### 1.1 Cartographer 2D 模式

```
┌─────────────────────────────────────────────────────────────────┐
│                        传感器层 (Sensor Layer)                   │
├─────────────────────────┬───────────────────────────────────────┤
│  LD-14P 激光雷达        │  Yesense IMU (可选)                  │
│  - 设备: /dev/wheeltec_lidar │  - 设备: /dev/yesense_imu       │
│  - 话题: /scan          │  - 话题: /imu                        │
│  - 频率: 10 Hz          │  - 频率: ~200 Hz                     │
└─────────────────────────┴───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        TF 坐标变换层 (TF Layer)                  │
├─────────────────────────────────────────────────────────────────┤
│  static_transform_publisher                                     │
│    base_link ──(z=0.18)──→ laser                               │
│    base_link ──(y=0.08, z=-0.05)──→ imu_link (可选)            │
│                                                                 │
│  cartographer_node 动态发布:                                     │
│    map ──(scan matching + submap)──→ odom ──→ base_link        │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SLAM 层                                   │
├─────────────────────────────────────────────────────────────────┤
│  cartographer_node (Cartographer 2D)                             │
│    - 算法: Ceres scan matching + 子图优化 + 回环检测              │
│    - 输入: /scan + 可选 /imu + TF                               │
│    - 输出: /map + /submap_list + /tf(map→odom→base_link)       │
│                                                                 │
│  cartographer_occupancy_grid_node                                │
│    - 将子图转换为 2D 占据栅格地图，发布 /map                     │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        可视化层 (RViz)                           │
├─────────────────────────────────────────────────────────────────┤
│  - LaserScan (/scan)     绿色点云                                │
│  - Map (/map)            灰色占据栅格                            │
│  - TF                    坐标系树                                 │
│  - Trajectory            轨迹节点列表                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、SLAM 地图建模原理（参考）

### 2.1 核心思想

纯激光雷达的 2D SLAM（如 Hector、Cartographer 等）核心特点是：
- **不使用外部里程计**（无 wheel odometry）
- **不使用粒子滤波**（对比 Gmapping）
- **直接 scan-to-map 匹配**估计位姿

### 2.2 占据栅格地图 (Occupancy Grid Map)

SLAM 系统将环境表示为二维栅格地图，每个格子存储一个概率值：

| 值 | 含义 |
|---|------|
| `-1` (0) | 未知区域 (unknown) |
| `0` | 确定空闲 (free) |
| `100` | 确定占据 (occupied) |
| `1~99` | 概率过渡区域 |

**地图参数（当前配置）**：
```yaml
map_resolution: 0.10    # 每个栅格 10cm x 10cm
map_size: 2048          # 2048 x 2048 栅格
map_start_x: 0.5        # 初始位置在地图中心 (0.5 * 2048 * 0.1 = 102.4m)
map_start_y: 0.5
```

**物理尺寸**：204.8m x 204.8m，以地图中心为原点。

### 2.3 Scan-to-Map 匹配流程

SLAM 系统每收到一帧 `/scan`，执行以下步骤：

```
Step 1: 坐标变换
  将 laser 坐标系下的 scan 点通过 TF 转换到 base_link 坐标系
  
Step 2: 初始位姿猜测
  使用上一帧的位姿作为初始猜测
  （或使用多分辨率金字塔从粗到细匹配）

Step 3: 高斯牛顿优化 (Gauss-Newton)
  目标: 找到位姿变换 T，使得 scan 点在地图上的占用概率最大
  
  优化变量: [x, y, theta]
  
  残差: 每个 scan 点投影到地图上对应的栅格值
  
  迭代更新: T_new = T_old + (J^T * J)^(-1) * J^T * r
  
Step 4: 多分辨率金字塔
  先在粗分辨率 (0.4m) 快速收敛
  再到中分辨率 (0.2m) 细化
  最后在细分辨率 (0.1m) 精修

Step 5: 地图更新 (条件触发)
  if 位移 > 0.4m OR 旋转 > 0.06 rad:
      将当前 scan 投影到地图上，更新栅格值
      发布 /map
```

### 2.4 地图更新机制

SLAM 系统使用**对数几率 (Log-Odds)** 更新栅格：

```
log_odds_new = log_odds_old + update_factor

occupied_cell:  +0.9  (增加占据概率)
free_cell:      -0.4  (降低占据概率，射线上的格子)
```

**关键参数**：
```yaml
p_update_factor_occupied: 0.9   # 击中格子 +0.9
p_update_factor_free: 0.4       # 射线空闲格子 -0.4
map_update_distance_thresh: 0.05 # 移动 0.05m 就更新地图
map_update_angle_thresh: 0.03   # 旋转 1.7° 就更新地图
```

---

## 三、当前系统的瓶颈分析

### 3.1 数据层瓶颈

| 问题 | 影响 | 根因 |
|------|------|------|
| 有效点太少 (30~200/666) | scan matching 失败 → 位姿跳变 | 环境空旷 / 雷达性能 |
| 帧率过低 (10Hz) | 快速运动时帧间位移大 | 已通过更换 LD-14P 解决 |
| 大量 nan 值 | 匹配不稳定 | 低反射率表面 / 强光干扰 |

### 3.2 算法层瓶颈

| 问题 | 影响 | 根因 |
|------|------|------|
| 纯 scan matching 无约束 | 抖动时容易丢失定位 | 无 odometry 辅助 |
| 高斯牛顿对初值敏感 | 帧间位移大时陷入局部最优 | 5Hz 帧率低 |
| 无回环检测 | 长时间运行后累积漂移 | 纯 scan-to-map 设计 |

### 3.3 工程层问题

| 问题 | 影响 |
|------|------|
| Cartographer 内存占用过高 | 长时间建图可能 OOM |
| 无地图保存机制 | 每次重启从零开始 |

---

## 四、优化方向与建议

### 4.1 传感器数据优化（最关键）

#### ① 增加有效点数量
```bash
# 检查当前有效点
rostopic echo /scan | grep ranges
```

**改善方法**：
- ✅ 将设备放在**障碍物丰富的环境**（四周 0.5~2m 有墙壁/家具）
- ✅ 避免阳光直射激光雷达窗口
- ✅ 避免全黑/高反光表面

#### ② LD06 参数调优
```xml
<!-- ld06.launch -->
<param name="min_range" value="0.02"/>   <!-- 当前 0.3，可能过滤了近处点 -->
<param name="max_range" value="12.0"/>   <!-- 当前 20.0，远处点噪声大 -->
```

### 4.2 SLAM 参数优化

#### ① 降低地图分辨率（提高鲁棒性）
```xml
<param name="map_resolution" value="0.20"/>  <!-- 0.10 → 0.20 -->
```
**效果**：栅格变大，对噪声更不敏感，匹配更容易收敛。

#### ② 降低地图更新阈值（更频繁更新）
```xml
<param name="map_update_distance_thresh" value="0.1"/>  <!-- 0.4 → 0.1 -->
<param name="map_update_angle_thresh" value="0.03"/>     <!-- 0.06 → 0.03 -->
```
**效果**：轻微移动就更新地图，避免位姿漂移后再更新导致错误累积。

#### ③ 增大 scan 队列
```xml
<param name="scan_subscriber_queue_size" value="20"/>  <!-- 10 → 20 -->
```
**效果**：防止 5Hz 雷达在系统繁忙时丢帧。

#### ④ 调整匹配搜索范围
```yaml
# SLAM 内部参数（需改源码或动态配置）
map_update_loop_closing_distance: 0.1    # 回环检测距离
map_update_loop_closing_angle: 0.05     # 回环检测角度
```

### 4.3 系统架构优化

#### ① 添加 IMU 辅助（方案 A：轻量级）
用 IMU 的 orientation 提供初始 yaw 猜测：
```xml
<!-- 使用 imu_filter_madgwick 融合 IMU -->
<node pkg="imu_filter_madgwick" type="imu_filter_node" name="imu_filter">
  <param name="use_mag" value="false"/>
  <param name="publish_tf" value="false"/>
  <remap from="/imu/data_raw" to="/imu"/>
</node>
```

#### ② 添加轮式里程计（方案 B：最佳）
如果有底盘电机编码器，提供 `odom → base_link` TF：
```xml
<param name="odom_frame" value="odom"/>  <!-- SLAM 使用 odom 辅助 -->
```

#### ③ 使用 Gmapping（备选方案）
```bash
sudo apt-get install ros-noetic-slam-gmapping
```
Gmapping 使用**粒子滤波**，对稀疏点云更鲁棒，但需要 odometry。

#### ④ 使用 Cartographer（当前方案）
已配置好，支持：
- 纯雷达运行（无 IMU 时自动降级为 scan matching）
- 可选 IMU 辅助（重力对齐和旋转约束）
- 回环检测
- 子图优化
- 子图分辨率 0.05m

启动方式：
```bash
sudo ./start_slam.sh
```

### 4.4 工程优化

#### ① 添加地图保存
```bash
# 保存地图
rosrun map_server map_saver -f /catkin_ws/map/my_map
```

#### ③ 自动重启后加载地图
```xml
<node name="map_server" pkg="map_server" type="map_server" 
      args="/catkin_ws/map/my_map.yaml"/>
```

---

## 五、推荐优化优先级

| 优先级 | 优化项 | 预期效果 | 工作量 |
|--------|--------|---------|--------|
| P0 | **确保障碍物丰富的环境** | 有效点 200+ → 400+ | 无 |
| P1 | **调整 Cartographer 子图参数** | 匹配精度 ↑ | 改 Lua |
| P1 | **调整运动滤波器阈值** | 地图实时性 ↑ | 改 Lua |
| P2 | **添加地图保存/加载** | 避免重复建图 | 加脚本 |
| P0 | **Cartographer 2D** | 子图优化 + 回环检测 | 已启用 |
| P3 | **连接 IMU（可选）** | 重力对齐辅助 scan matching | 即插即用 |
| P3 | **添加 imu_filter_madgwick** | 提供初始姿态 | 安装+配置 |

---

## 六、当前配置快速参考

```xml
<!-- cartographer_ld06.launch (Cartographer 关键参数) -->
<node name="cartographer_node" pkg="cartographer_ros" type="cartographer_node"
      args="-configuration_directory $(find cartographer_ld06)/configuration_files
            -configuration_basename ld14p.lua">  <!-- 有 IMU 时用 ld14p_imu.lua -->
  <remap from="scan" to="scan"/>
</node>
<node name="cartographer_occupancy_grid_node" pkg="cartographer_ros"
      type="cartographer_occupancy_grid_node" args="-resolution 0.05"/>
```
