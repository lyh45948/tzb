-- 重新设计数据库表结构
-- 分为：指令表格、模拟数据表格、小车实际数据表格

USE smart_car;

-- =============================================
-- 1. 指令表格 (control_commands)
-- 记录微信小程序向小车发送的所有指令
-- =============================================
CREATE TABLE IF NOT EXISTS control_commands (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '指令发送时间',
    command_type VARCHAR(50) NOT NULL COMMENT '指令类型(fan/led/car_control等)',
    command_data JSON COMMENT '指令详细内容',
    source VARCHAR(20) DEFAULT 'miniapp' COMMENT '指令来源(miniapp/system)',
    is_simulated TINYINT DEFAULT 0 COMMENT '是否在演示模式下发送',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_command_type (command_type),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指令记录表';

-- =============================================
-- 2. 模拟数据表格 (simulated_sensor_data)
-- 存储演示模式下的模拟传感器数据
-- =============================================
CREATE TABLE IF NOT EXISTS simulated_sensor_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '模拟时间',
    temperature DECIMAL(5,2) COMMENT '模拟温度(℃)',
    humidity DECIMAL(5,2) COMMENT '模拟湿度(%)',
    lux INT COMMENT '模拟光照强度(lux)',
    co2 INT COMMENT '模拟CO2浓度(ppm)',
    soil_moisture DECIMAL(5,2) COMMENT '模拟土壤湿度(%)',
    time_period INT COMMENT '时间段(0-5)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟传感器数据表';

-- =============================================
-- 3. 小车实际数据表格 (car_sensor_data)
-- 存储非演示模式下的小车实际数据
-- 包含实际传感器数据 + 模拟的CO2和土壤湿度
-- =============================================
CREATE TABLE IF NOT EXISTS car_sensor_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '采集时间',

    -- 实际传感器数据
    temperature DECIMAL(5,2) COMMENT '实际温度(℃)',
    humidity DECIMAL(5,2) COMMENT '实际湿度(%)',
    lux INT COMMENT '实际光照强度(lux)',
    proximity INT COMMENT '接近距离',
    ir_value INT COMMENT '人体检测值',

    -- 模拟数据（基于实际数据推算）
    co2 INT COMMENT '模拟CO2浓度(ppm)',
    soil_moisture DECIMAL(5,2) COMMENT '模拟土壤湿度(%)',

    -- 小车状态
    car_status VARCHAR(20) COMMENT '小车状态',
    car_mode VARCHAR(20) COMMENT '运行模式',
    left_speed INT COMMENT '左电机速度',
    right_speed INT COMMENT '右电机速度',
    battery_voltage INT COMMENT '电池电压',
    distance INT COMMENT '障碍物距离(mm)',

    -- 外设状态
    fan TINYINT COMMENT '风扇状态',
    led TINYINT COMMENT 'LED状态',
    buzzer TINYINT COMMENT '蜂鸣器状态',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小车实际传感器数据表';

-- 显示创建结果
SHOW TABLES;
SELECT '数据库表重构完成!' AS message;
