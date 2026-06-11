-- 为sensor_data表添加CO2、土壤湿度和模拟数据标记字段
-- 执行此脚本前请先备份数据

USE smart_car;

-- 添加CO2字段（如果不存在）
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'smart_car' AND TABLE_NAME = 'sensor_data' AND COLUMN_NAME = 'co2');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE sensor_data ADD COLUMN co2 INT COMMENT ''CO2浓度(ppm)'' AFTER ir_value',
    'SELECT ''Column co2 already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加土壤湿度字段（如果不存在）
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'smart_car' AND TABLE_NAME = 'sensor_data' AND COLUMN_NAME = 'soil_moisture');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE sensor_data ADD COLUMN soil_moisture DECIMAL(5,2) COMMENT ''土壤湿度(%)'' AFTER co2',
    'SELECT ''Column soil_moisture already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 添加模拟数据标记字段（如果不存在）
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'smart_car' AND TABLE_NAME = 'sensor_data' AND COLUMN_NAME = 'is_simulated');
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE sensor_data ADD COLUMN is_simulated TINYINT DEFAULT 0 COMMENT ''是否模拟数据(0=实际,1=模拟)'' AFTER soil_moisture',
    'SELECT ''Column is_simulated already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 显示修改结果
DESCRIBE sensor_data;

SELECT '数据库字段添加完成!' AS message;
