-- 智能小车数据库初始化脚本
-- 创建时间: 2024
-- 适配统信UOS系统运行

-- 创建数据库
CREATE DATABASE IF NOT EXISTS smart_car DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE smart_car;

-- 设备表
CREATE TABLE IF NOT EXISTS devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) UNIQUE NOT NULL COMMENT '设备ID',
    name VARCHAR(100) COMMENT '设备名称',
    ip_address VARCHAR(50) COMMENT '设备IP地址',
    port INT DEFAULT 7788 COMMENT '设备端口',
    last_seen DATETIME COMMENT '最后在线时间',
    status ENUM('online', 'offline') DEFAULT 'offline' COMMENT '在线状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备表';

-- 传感器数据表（旧版兼容）
CREATE TABLE IF NOT EXISTS sensor_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '采集时间',
    temperature DECIMAL(5,2) COMMENT '温度(℃)',
    humidity DECIMAL(5,2) COMMENT '湿度(%)',
    lux INT COMMENT '光照强度(lux)',
    proximity INT COMMENT '接近距离',
    ir_value INT COMMENT '人体检测值',
    co2 INT COMMENT 'CO2浓度(ppm)',
    soil_moisture DECIMAL(5,2) COMMENT '土壤湿度(%)',
    is_simulated TINYINT DEFAULT 0 COMMENT '是否模拟数据(0=实际,1=模拟)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp),
    INDEX idx_simulated (is_simulated)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='传感器数据表';

-- 小车状态表（旧版兼容）
CREATE TABLE IF NOT EXISTS car_status (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL,
    timestamp DATETIME(3) NOT NULL,
    car_status VARCHAR(20) COMMENT '小车状态',
    car_mode VARCHAR(20) COMMENT '运行模式',
    left_speed INT COMMENT '左电机速度',
    right_speed INT COMMENT '右电机速度',
    battery_voltage INT COMMENT '电池电压',
    distance INT COMMENT '障碍物距离(mm)',
    tvoc INT COMMENT 'TVOC有机挥发物(ppb)',
    gas_status INT COMMENT '燃气泄漏状态(0=正常,1=泄漏)',
    gas_mic INT COMMENT '燃气浓度数值',
    fan TINYINT COMMENT '风扇状态',
    led TINYINT COMMENT 'LED状态',
    buzzer TINYINT COMMENT '蜂鸣器状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小车状态表';

-- 控制命令日志表（旧版兼容）
CREATE TABLE IF NOT EXISTS control_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL,
    timestamp DATETIME(3) NOT NULL,
    command_type VARCHAR(50) COMMENT '命令类型',
    command_data JSON COMMENT '命令内容',
    source VARCHAR(20) COMMENT '来源(miniapp/system)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='控制命令日志表';

-- 指令记录表（新版）
CREATE TABLE IF NOT EXISTS control_commands (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '指令发送时间',
    command_type VARCHAR(50) NOT NULL COMMENT '指令类型',
    command_data JSON COMMENT '指令详细内容',
    source VARCHAR(20) DEFAULT 'miniapp' COMMENT '指令来源',
    is_simulated TINYINT DEFAULT 0 COMMENT '是否演示模式下发送',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_command_type (command_type),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指令记录表';

-- 模拟传感器数据表（新版）
CREATE TABLE IF NOT EXISTS simulated_sensor_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '模拟时间',
    temperature DECIMAL(5,2) COMMENT '模拟温度(℃)',
    humidity DECIMAL(5,2) COMMENT '模拟湿度(%)',
    lux INT COMMENT '模拟光照强度(lux)',
    co2 INT COMMENT '模拟CO2浓度(ppm)',
    time_period INT COMMENT '时间段(0-5)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟传感器数据表';

-- 小车实际传感器数据表（新版）
CREATE TABLE IF NOT EXISTS car_sensor_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '采集时间',
    temperature DECIMAL(5,2) COMMENT '实际温度(℃)',
    humidity DECIMAL(5,2) COMMENT '实际湿度(%)',
    lux INT COMMENT '实际光照强度(lux)',
    proximity INT COMMENT '接近距离',
    ir_value INT COMMENT '人体检测值',
    co2 INT COMMENT '模拟CO2浓度(ppm)',
    car_status VARCHAR(20) COMMENT '小车状态',
    car_mode VARCHAR(20) COMMENT '运行模式',
    left_speed INT COMMENT '左电机速度',
    right_speed INT COMMENT '右电机速度',
    battery_voltage INT COMMENT '电池电压',
    distance INT COMMENT '障碍物距离(mm)',
    tvoc INT COMMENT 'TVOC有机挥发物(ppb)',
    gas_status INT COMMENT '燃气泄漏状态(0=正常,1=泄漏)',
    gas_mic INT COMMENT '燃气浓度数值',
    fan TINYINT COMMENT '风扇状态',
    led TINYINT COMMENT 'LED状态',
    buzzer TINYINT COMMENT '蜂鸣器状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小车实际传感器数据表';

-- 插入默认设备
INSERT INTO devices (device_id, name, ip_address, port, status)
VALUES ('car_001', '智能小车1号', '192.168.1.100', 7788, 'offline')
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 显示创建结果
SHOW TABLES;
SELECT '数据库初始化完成!' AS message;
