"""
数据库表迁移脚本
执行 redesign_tables.sql 创建新的3表结构
"""
import pymysql
from config import Config


def run_migration():
    """运行数据库迁移"""
    try:
        # 连接MySQL（不指定数据库）
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            charset='utf8mb4'
        )

        cursor = connection.cursor()

        # 先确保数据库存在
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS smart_car CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE smart_car")

        print("=== 创建 control_commands 表 ===")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_commands (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                device_id VARCHAR(50) NOT NULL COMMENT '设备ID',
                timestamp DATETIME(3) NOT NULL COMMENT '指令发送时间',
                command_type VARCHAR(50) NOT NULL COMMENT '指令类型',
                command_data JSON COMMENT '指令详细内容',
                source VARCHAR(20) DEFAULT 'miniapp' COMMENT '指令来源',
                is_simulated TINYINT DEFAULT 0 COMMENT '是否在演示模式下发送',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_device_time (device_id, timestamp),
                INDEX idx_command_type (command_type),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指令记录表'
        """)
        print("control_commands 表创建成功")

        print("\n=== 创建 simulated_sensor_data 表 ===")
        cursor.execute("""
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟传感器数据表'
        """)
        print("simulated_sensor_data 表创建成功")

        print("\n=== 创建 car_sensor_data 表 ===")
        cursor.execute("""
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
                tvoc INT COMMENT 'TVOC有机挥发物(ppb)',
                gas_status INT COMMENT '燃气泄漏状态(0=正常,1=泄漏)',
                gas_mic INT COMMENT '燃气浓度数值',

                -- 外设状态
                fan TINYINT COMMENT '风扇状态',
                led TINYINT COMMENT 'LED状态',
                buzzer TINYINT COMMENT '蜂鸣器状态',

                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_device_time (device_id, timestamp),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='小车实际传感器数据表'
        """)
        print("car_sensor_data 表创建成功")

        connection.commit()

        # 显示所有表
        print("\n=== 当前数据库表 ===")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")

        cursor.close()
        connection.close()

        print("\n数据库迁移完成!")
        return True

    except Exception as e:
        print(f"迁移失败: {e}")
        return False


if __name__ == '__main__':
    run_migration()
