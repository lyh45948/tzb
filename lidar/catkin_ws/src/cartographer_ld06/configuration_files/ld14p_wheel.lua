-- Cartographer configuration for LD-14P LiDAR + Wheel Odometry (no IMU)
-- 优化目标：加快地图绘制速度，减少漂移，提升建图清晰度
--
-- LD-14P: 10Hz, 360deg, range 0.02~12m, USB serial
-- Wheel Odometry: from Hi3861 via UDP 7799 (L_spd/R_spd)

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
  submap_publish_period_sec = 0.1,      -- 子图发布加快
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
-- 无回波射线长度：1.0→5.0，适度清除空闲区域
-- 设太小(1.0)导致已探索区域残留"幽灵障碍"
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 5.0

-- 无 IMU：禁用 IMU，依赖 scan matching + 轮速
TRAJECTORY_BUILDER_2D.use_imu_data = false

-- 子图参数：LD-14P 10Hz → 12帧 ≈ 1.2秒完成一个子图
-- Phase 2 优化：适度增大(10→12)，提高局部一致性
TRAJECTORY_BUILDER_2D.submaps.grid_options_2d.resolution = 0.05
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 12
-- 提高命中概率，增强地图置信度（0.55→0.6）
TRAJECTORY_BUILDER_2D.submaps.range_data_inserter.probability_grid_range_data_inserter.hit_probability = 0.6

-- 运动滤波器：平衡插入频率与拼接质量
-- Phase 2 优化：适度增大阈值，避免子图过度碎片化
TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 0.5
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.08
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(4.0)

-- 插值体素滤波器：降采样去噪
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.02

-- Ceres scan matcher：加大观测权重，减少对轮速初值的依赖
-- Phase 2 优化：进一步增强匹配权重，统一参数
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.occupied_space_weight = 10.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.translation_weight = 8.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.rotation_weight = 20.0
TRAJECTORY_BUILDER_2D.ceres_scan_matcher.ceres_solver_options.max_num_iterations = 15

-- 实时相关扫描匹配器
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.linear_search_window = 0.2
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.angular_search_window = math.rad(20.0)
-- 不过度信任初始位姿
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.translation_delta_cost_weight = 1.0
TRAJECTORY_BUILDER_2D.real_time_correlative_scan_matcher.rotation_delta_cost_weight = 1e-1

-- ==================== Global SLAM (回环检测) ====================
-- Phase 2 优化：增强回环检测能力，降低漂移累积

POSE_GRAPH.constraint_builder.min_score = 0.55
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.6
POSE_GRAPH.optimize_every_n_nodes = 8
POSE_GRAPH.global_constraint_search_after_n_seconds = 5.0

POSE_GRAPH.constraint_builder.fast_correlative_scan_matcher.linear_search_window = 10.0
POSE_GRAPH.constraint_builder.fast_correlative_scan_matcher.angular_search_window = math.rad(45.0)
POSE_GRAPH.constraint_builder.fast_correlative_scan_matcher.branch_and_bound_depth = 7

-- 提高回环约束权重，降低轮速约束权重（轮速有打滑误差）
POSE_GRAPH.constraint_builder.loop_closure_translation_weight = 2.0e4
POSE_GRAPH.constraint_builder.loop_closure_rotation_weight = 2.0e5
POSE_GRAPH.optimization_problem.odometry_translation_weight = 1e4
POSE_GRAPH.optimization_problem.odometry_rotation_weight = 1e4

return options
