-- =============================================
-- 智能小车物联网系统数据库初始化脚本
-- 版本: V1.0
-- 创建日期: 2025-12-31
-- =============================================

CREATE DATABASE IF NOT EXISTS smart_car DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE smart_car;

-- =============================================
-- 表1: 设备表 (devices)
-- 功能: 设备注册表
-- =============================================
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

-- =============================================
-- 表2: 传感器数据表 (sensor_data)
-- 功能: 存储环境传感器采集的数据
-- =============================================
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

-- =============================================
-- 表3: 小车状态表 (car_status)
-- 功能: 记录小车的运行状态
-- =============================================
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
    fan TINYINT COMMENT '风扇状态',
    led TINYINT COMMENT 'LED状态',
    buzzer TINYINT COMMENT '蜂鸣器状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小车状态表';

-- =============================================
-- 表4: 智能光照状态表 (smart_light_status)
-- 功能: 记录智能照明系统的状态
-- =============================================
CREATE TABLE IF NOT EXISTS smart_light_status (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL,
    timestamp DATETIME(3) NOT NULL,
    mode TINYINT COMMENT '模式(1=auto, 0=manual)',
    brightness INT COMMENT '当前亮度(0-100)',
    target_brightness INT COMMENT '目标亮度',
    time_period INT COMMENT '时间段',
    light_level INT COMMENT '光照等级',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='智能光照状态表';

-- =============================================
-- 表5: 灌溉配置表 (irrigation_config)
-- 功能: 存储智能灌溉系统的配置
-- =============================================
CREATE TABLE IF NOT EXISTS irrigation_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) UNIQUE NOT NULL COMMENT '设备ID',
    base_water_amount FLOAT DEFAULT 500 COMMENT '基础灌溉水量(ml)',
    soil_moisture_threshold FLOAT DEFAULT 30 COMMENT '土壤湿度阈值(%)',
    auto_irrigation_enabled TINYINT DEFAULT 0 COMMENT '是否启用自动灌溉',
    scheduled_time TIME COMMENT '定时灌溉时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='灌溉配置表';

-- =============================================
-- 表6: 灌溉历史表 (irrigation_history)
-- 功能: 记录每次灌溉事件
-- =============================================
CREATE TABLE IF NOT EXISTS irrigation_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    start_time DATETIME NOT NULL COMMENT '灌溉开始时间',
    end_time DATETIME COMMENT '灌溉结束时间',
    water_amount FLOAT NOT NULL COMMENT '灌溉水量(ml)',
    duration INT COMMENT '灌溉时长(秒)',
    status ENUM('pending','running','completed','failed') DEFAULT 'pending' COMMENT '灌溉状态',
    trigger_type ENUM('manual','auto','scheduled') DEFAULT 'manual' COMMENT '触发类型',
    sensor_data JSON COMMENT '灌溉时的传感器数据快照',
    algorithm_factors JSON COMMENT '算法各因子数值',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, start_time),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='灌溉历史表';

-- =============================================
-- 表7: 控制命令日志表 (control_logs)
-- 功能: 记录所有控制指令
-- =============================================
CREATE TABLE IF NOT EXISTS control_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL,
    timestamp DATETIME(3) NOT NULL,
    command_type VARCHAR(50) COMMENT '命令类型',
    command_data JSON COMMENT '命令内容',
    source VARCHAR(20) COMMENT '来源(miniapp/hap/system)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='控制命令日志表';

-- =============================================
-- 表8: 指令记录表 (control_commands)
-- 功能: 重新设计的统一指令记录表
-- =============================================
CREATE TABLE IF NOT EXISTS control_commands (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '指令发送时间',
    command_type VARCHAR(50) NOT NULL COMMENT '指令类型',
    command_data JSON COMMENT '指令详细内容',
    source VARCHAR(20) DEFAULT 'miniapp' COMMENT '指令来源(miniapp/hap/system)',
    is_simulated TINYINT DEFAULT 0 COMMENT '是否在演示模式下发送',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_command_type (command_type),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指令记录表';

-- =============================================
-- 表9: 模拟传感器数据表 (simulated_sensor_data)
-- 功能: 存储演示模式下的模拟传感器数据
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
-- 表10: 小车传感器数据表 (car_sensor_data)
-- 功能: 存储小车实际传感器数据
-- =============================================
CREATE TABLE IF NOT EXISTS car_sensor_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
    timestamp DATETIME(3) NOT NULL COMMENT '采集时间',
    temperature DECIMAL(5,2) COMMENT '实际温度(℃)',
    humidity DECIMAL(5,2) COMMENT '实际湿度(%)',
    lux INT COMMENT '实际光照强度(lux)',
    proximity INT COMMENT '接近距离',
    ir_value INT COMMENT '红外传感器值',
    co2 INT COMMENT '推算CO2浓度(ppm)',
    soil_moisture DECIMAL(5,2) COMMENT '推算土壤湿度(%)',
    car_status VARCHAR(20) COMMENT '小车状态',
    car_mode VARCHAR(20) COMMENT '运行模式',
    left_speed INT COMMENT '左电机速度(mm/s)',
    right_speed INT COMMENT '右电机速度(mm/s)',
    battery_voltage INT COMMENT '电池电压(mV)',
    distance INT COMMENT '障碍物距离(mm)',
    fan TINYINT COMMENT '风扇状态',
    led TINYINT COMMENT 'LED状态',
    buzzer TINYINT COMMENT '蜂鸣器状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, timestamp),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小车传感器数据表';

-- =============================================
-- 初始化数据
-- =============================================

-- 插入默认设备
INSERT INTO devices (device_id, name, ip_address, port, status) VALUES
('car_001', '智能小车1号', '192.168.1.100', 7788, 'offline')
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- 插入灌溉配置
INSERT INTO irrigation_config (device_id, base_water_amount, soil_moisture_threshold) VALUES
('car_001', 500, 30)
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- =============================================
-- 创建视图: 设备状态概览
-- =============================================
CREATE OR REPLACE VIEW device_status_overview AS
SELECT
    d.device_id,
    d.name,
    d.ip_address,
    d.status,
    d.last_seen,
    cs.car_status,
    cs.car_mode,
    cs.battery_voltage,
    cs.distance,
    sd.temperature,
    sd.humidity,
    sd.lux,
    sl.mode as light_mode,
    sl.brightness as light_brightness
FROM devices d
LEFT JOIN (
    SELECT device_id, car_status, car_mode, battery_voltage, distance, timestamp
    FROM car_status cs1
    WHERE timestamp = (SELECT MAX(timestamp) FROM car_status cs2 WHERE cs1.device_id = cs2.device_id)
) cs ON d.device_id = cs.device_id
LEFT JOIN (
    SELECT device_id, temperature, humidity, lux, timestamp
    FROM sensor_data sd1
    WHERE timestamp = (SELECT MAX(timestamp) FROM sensor_data sd2 WHERE sd1.device_id = sd2.device_id)
) sd ON d.device_id = sd.device_id
LEFT JOIN (
    SELECT device_id, mode, brightness, timestamp
    FROM smart_light_status sls1
    WHERE timestamp = (SELECT MAX(timestamp) FROM smart_light_status sls2 WHERE sls1.device_id = sls2.device_id)
) sl ON d.device_id = sl.device_id;

-- =============================================
-- 显示创建结果
-- =============================================
SHOW TABLES;
SELECT '智能小车物联网系统数据库初始化完成!' AS message;
