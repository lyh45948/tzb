-- Cartographer configuration for LD-14P LiDAR + IMU + Wheel Odometry
-- LD-14P: 10Hz, 360deg, range 0.02~12m, USB serial
-- IMU:  Yesense H30, 200Hz, AHRS
-- Wheel Odometry: from Hi3861 via UDP 7799 (L_spd/R_spd)
-- Mode: 2D SLAM with IMU + external wheel odometry

include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "base_link",
  published_frame = "base_link",
  odom_frame = "odom",
  -- 外部轮速节点已提供 odom→base_link TF，Cartographer 不再提供
  provide_odom_frame = false,
  publish_frame_projected_to_2d = true,
  -- 使用外部轮速里程计作为辅助输入
  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.1,      -- 子图发布周期：0.3→0.1，加快可视化更新
  pose_publish_period_sec = 5e-3,
  trajectory_publish_period_sec = 30e-3,
  rangefinder_sampling_ratio = 1.0,
  odometry_sampling_ratio = 1.0,
  fixed_frame_pose_sampling_ratio = 1.0,
  imu_sampling_ratio = 1.0,
  landmarks_sampling_ratio = 1.0,
}

MAP_BUILDER.use_trajectory_builder_2d = true

-- ==================== 2D Trajectory Builder ====================

-- LD-14P 在极近距离噪点大，0.02→0.1 过滤掉不可靠的近场数据
TRAJECTORY_BUILDER_2D.min_range = 0.1
TRAJECTORY_BUILDER_2D.max_range = 12.0
-- 无回波射线长度：保持5.0m，适度清除空闲区域
-- 设太小(1.0)会导致已探索区域残留"幽灵障碍"，设太大(max_range)会错误清除远处墙壁
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 5.0

-- 启用 IMU：用于重力对齐和旋转约束
TRAJECTORY_BUILDER_2D.use_imu_data = true

-- 子图分辨率
TRAJECTORY_BUILDER_2D.submaps.grid_options_2d.resolution = 0.05
-- 每个子图包含的 scan 数：LD-14P 10Hz → 12帧 ≈ 1.2秒完成一个子图
-- Phase 2 优化：适度增大(10→12)，提高局部一致性，减少子图边界拼接误差
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 12
-- 提高命中概率，增强地图置信度（0.55→0.6）
TRAJECTORY_BUILDER_2D.submaps.range_data_inserter.probability_grid_range_data_inserter.hit_probability = 0.6

-- 运动滤波器：平衡插入频率与拼接质量
-- Phase 2 优化：适度增大阈值，避免子图过度碎片化
-- max_time 0.5s：即使位移不足，0.5秒也强制插入一帧
-- max_distance 0.08m：平衡更新频率与子图质量（原0.05m过碎）
-- max_angle 4°：适度捕获旋转
TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 0.5
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.08
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(4.0)

-- Ceres scan matcher：提高 scan-to-map 匹配权重，抑制漂移
-- Phase 2 优化：进一步增强匹配权重，减少轮速/IMU误差的影响
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.occupied_space_weight = 10.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 8.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.rotation_weight = 20.0
-- 增加迭代次数提升匹配精度（代价：CPU略增）
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.ceres_solver_options.max_num_iterations = 15

-- 实时相关扫描匹配器
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
-- 适度增大搜索窗口，容忍更大初始位姿误差
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window = 0.15
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.angular_search_window = math.rad(15.0)
-- translation_delta_cost_weight: 1.0 表示不过度惩罚位姿修正
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.translation_delta_cost_weight = 1.0
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.rotation_delta_cost_weight = 1e-1

-- ==================== Global SLAM (回环检测) ====================
-- Phase 2 优化：增强回环检测能力，降低漂移累积

-- 降低回环检测阈值，提高回环成功率（原0.65→0.55）
-- 代价：可能引入少量误回环，但全局优化会过滤
POSE_GRAPH.constraint_builder.min_score = 0.55
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.6

-- 全局优化频率：10→8，更快修正漂移
-- 10Hz LiDAR × 8帧 = 0.8秒优化一次
POSE_GRAPH.optimize_every_n_nodes = 8

-- 加快全局约束搜索频率（默认10秒→5秒）
POSE_GRAPH.global_constraint_search_after_n_seconds = 5.0

-- 增大回环搜索窗口，容忍更大漂移
POSE_GRAPH.constraint_builder.fast_correlative_scan_matcher.linear_search_window = 10.0
POSE_GRAPH.constraint_builder.fast_correlative_scan_matcher.angular_search_window = math.rad(45.0)
POSE_GRAPH.constraint_builder.fast_correlative_scan_matcher.branch_and_bound_depth = 7

-- 提高回环约束在全局优化中的权重
POSE_GRAPH.constraint_builder.loop_closure_translation_weight = 2.0e4
POSE_GRAPH.constraint_builder.loop_closure_rotation_weight = 2.0e5

-- 降低轮速里程计约束权重（轮速有打滑误差，不完全信任）
POSE_GRAPH.optimization_problem.odometry_translation_weight = 1e4
POSE_GRAPH.optimization_problem.odometry_rotation_weight = 1e4

return options
