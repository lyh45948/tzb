-- 视觉识别结果表
-- 由 VisionService 按 VISION_PERSIST_INTERVAL 限流写入，避免每秒一行。
-- 实时数据通过 WebSocket 广播 + 内存缓存提供，本表仅用于历史回溯。

CREATE TABLE IF NOT EXISTS `vision_results` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `device_id` VARCHAR(50) NOT NULL COMMENT '设备ID',
    `timestamp` DATETIME(3) NOT NULL COMMENT '采集时间',
    `result_type` VARCHAR(20) NOT NULL COMMENT '结果类型: obstacle/counter',

    -- 障碍物检测字段
    `obstacles` JSON DEFAULT NULL COMMENT '障碍物列表',
    `obstacle_count` INT DEFAULT NULL COMMENT '障碍物数量',
    `nearest_distance` DECIMAL(6,2) DEFAULT NULL COMMENT '最近障碍物距离(米)',
    `nearest_class` VARCHAR(50) DEFAULT NULL COMMENT '最近障碍物类别',
    `danger_level` VARCHAR(20) DEFAULT NULL COMMENT '危险等级',
    `steer_angle` DECIMAL(6,2) DEFAULT NULL COMMENT 'APF推荐转向角(度)',
    `speed_ratio` DECIMAL(4,2) DEFAULT NULL COMMENT 'APF推荐速度比例',

    -- 计数器识别字段
    `counter_digits` VARCHAR(20) DEFAULT NULL COMMENT '平滑后计数器数字',
    `counter_raw` VARCHAR(20) DEFAULT NULL COMMENT '原始识别值',
    `counter_smooth_status` VARCHAR(30) DEFAULT NULL COMMENT '时序平滑状态',

    -- 通用字段
    `annotated_image` TEXT DEFAULT NULL COMMENT '标注图像 base64',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`id`),
    KEY `idx_vision_device_time` (`device_id`, `timestamp`),
    KEY `idx_vision_type_time` (`result_type`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视觉识别结果表';
