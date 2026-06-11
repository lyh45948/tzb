"""
模拟数据服务
用于演示模式下生成模拟数据，以及非演示模式下推算CO2
"""
import math
import random
import threading
import time
from collections import deque
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger('simulation_service')


class DataSmoother:
    """
    数据平滑器 - 使用滑动窗口平均值减少数据波动
    """

    def __init__(self, window_size=10):
        """
        初始化平滑器
        :param window_size: 滑动窗口大小（保留最近N次采样）
        """
        self.window_size = window_size
        self.data_buffers = {}  # {data_key: deque}

    def add_and_get_average(self, key, value):
        """
        添加数据并获取平滑后的平均值
        :param key: 数据键名
        :param value: 新数据值
        :return: 平滑后的平均值
        """
        if key not in self.data_buffers:
            self.data_buffers[key] = deque(maxlen=self.window_size)

        self.data_buffers[key].append(value)

        # 计算平均值
        buffer = self.data_buffers[key]
        if len(buffer) == 0:
            return value

        avg = sum(buffer) / len(buffer)

        # 根据数据类型返回不同精度
        if isinstance(value, int):
            return int(round(avg))
        else:
            return round(avg, 1)

    def clear(self, key=None):
        """清除缓冲区"""
        if key:
            self.data_buffers.pop(key, None)
        else:
            self.data_buffers.clear()


class SimulationService:
    """模拟数据服务"""

    def __init__(self, data_service, udp_miniapp_service, udp_car_service):
        self.data_service = data_service
        self.udp_miniapp_service = udp_miniapp_service
        self.udp_car_service = udp_car_service
        print(f"[SimulationService] 初始化完成: data_service={data_service is not None}, udp_miniapp_service={udp_miniapp_service is not None}")

        # 演示模式状态
        self.demo_mode = False
        self.simulation_thread = None
        self.running = False

        # 模拟数据生成间隔
        self.simulation_interval = 0.5  # 每0.5秒更新一次

        # 数据保存计时器
        self.last_save_time = 0
        self.save_interval = 1.0  # 每秒保存一次

        # 设备ID
        self.device_id = 'demo_car'

        # 数据平滑器 - 使用10次采样的滑动窗口（约5秒的数据）
        self.smoother = DataSmoother(window_size=10)

        # 平滑数据更新间隔（每5秒更新一次显示值）
        self.smooth_update_interval = 5.0
        self.last_smooth_update_time = 0

        # 缓存最新模拟数据（用于REST API拉取）
        self._latest_snapshot = None

    def generate_single_data(self):
        """生成一次模拟数据（不启动循环，用于REST API拉取）"""
        return self._generate_simulated_data()

    def get_latest_simulated_data(self):
        """获取缓存的最新模拟数据"""
        if self._latest_snapshot is None:
            self._latest_snapshot = self._generate_simulated_data()
        return self._latest_snapshot

    def set_demo_mode(self, enabled, device_id=None):
        """
        切换演示模式
        :param enabled: 是否启用
        :param device_id: 设备ID
        """
        logger.info(f"设置演示模式: {enabled}, 当前状态: demo_mode={self.demo_mode}, running={self.running}")

        self.demo_mode = enabled
        if device_id:
            self.device_id = device_id

        if enabled:
            self._start_simulation()
        else:
            self._stop_simulation()

        return True, f"演示模式已{'开启' if enabled else '关闭'}"

    def _start_simulation(self):
        """启动模拟数据生成"""
        if self.running:
            return

        self.running = True
        self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.simulation_thread.start()
        logger.info("模拟数据生成器已启动")

    def _stop_simulation(self):
        """停止模拟数据生成"""
        logger.info(f"停止模拟数据生成: running={self.running}, demo_mode={self.demo_mode}")
        self.running = False
        self.demo_mode = False  # 确保状态同步
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=2)
        logger.info("模拟数据生成器已停止")

    def _simulation_loop(self):
        """模拟数据生成循环"""
        print("[SimulationService] 模拟数据生成循环开始运行")
        logger.info("模拟数据生成循环开始运行")
        loop_count = 0
        while self.running and self.demo_mode:  # 同时检查两个条件
            try:
                loop_count += 1
                # 生成模拟数据
                simulated_data = self._generate_simulated_data()

                # 推送给小程序
                if self.udp_miniapp_service:
                    self.udp_miniapp_service.broadcast_simulated_data(simulated_data)
                    if loop_count % 20 == 0:  # 每1秒打印一次（20*50ms=1s）
                        print(f"[SimulationService] 已生成 {loop_count} 次模拟数据")
                else:
                    print("[SimulationService] udp_miniapp_service 为 None，无法广播数据")
                    logger.warning("udp_miniapp_service 为 None，无法广播数据")

                # 每秒保存一次到数据库
                current_time = time.time()
                if current_time - self.last_save_time >= self.save_interval:
                    self.last_save_time = current_time
                    print(f"[SimulationService] 保存模拟数据: temp={simulated_data.get('env', {}).get('temp')}")
                    logger.info(f"保存模拟数据")
                    if self.data_service:
                        now = datetime.now()
                        hour = now.hour + now.minute / 60.0
                        time_period = self._get_time_period(hour)
                        result = self.data_service.save_simulated_data(
                            self.device_id,
                            simulated_data,
                            time_period=time_period
                        )
                        print(f"[SimulationService] 模拟数据保存结果: {result}")
                        logger.info(f"模拟数据保存结果: {result}")
                    else:
                        print("[SimulationService] data_service 为 None，无法保存数据")
                        logger.warning("data_service 为 None，无法保存数据")

                time.sleep(self.simulation_interval)

            except Exception as e:
                print(f"[SimulationService] 模拟数据生成错误: {e}")
                logger.error(f"模拟数据生成错误: {e}")

        print(f"[SimulationService] 模拟数据生成循环退出: running={self.running}, demo_mode={self.demo_mode}")
        logger.info(f"模拟数据生成循环退出: running={self.running}, demo_mode={self.demo_mode}")

    def _generate_simulated_data(self):
        """
        生成完整模拟数据
        :return: dict 模拟数据
        """
        now = datetime.now()
        hour = now.hour + now.minute / 60.0  # 精确到分钟

        # 生成传感器数据
        temperature = self._simulate_temperature(hour)
        humidity = self._simulate_humidity(hour, temperature)
        lux = self._simulate_light(hour)

        # 原始值（带噪声）
        raw_co2 = self._simulate_co2(hour, temperature, humidity, lux)

        # 使用滑动窗口平均平滑CO2
        smoothed_co2 = self.smoother.add_and_get_average('co2', raw_co2)

        # 构建完整数据包（模拟Hi3861格式）
        return {
            "carStatus": "on",
            "carMode": "manual",
            "L_spd": 0,
            "R_spd": 0,
            "carPower": 85,
            "distance": 200,
            "env": {
                "temp": temperature,
                "humi": humidity,
                "lux": lux,
                "ps": 100,
                "ir": 0,
                "fan": 0,
                "led": 0,
                "buzzer": 0,
                "co2": smoothed_co2
            }
        }

    def _simulate_temperature(self, hour):
        """
        模拟温度
        - 基础温度: 22℃
        - 时间因子: +8℃ * sin((hour-6) * π/12)  // 6点最低，18点最高
        - 随机噪声: ±2℃ (增大波动范围，让变化更明显)
        - 范围: 15℃ ~ 35℃
        """
        base_temp = 22
        # 使用正弦波模拟日变化，6点最低，18点最高
        time_factor = 8 * math.sin((hour - 6) * math.pi / 12)
        # 增大噪声范围，让温度变化更明显
        noise = random.uniform(-2, 2)
        temperature = base_temp + time_factor + noise
        return round(max(15, min(35, temperature)), 1)

    def _simulate_humidity(self, hour, temperature):
        """
        模拟湿度
        - 基础湿度: 60%
        - 时间因子: -15% * sin((hour-6) * π/12)  // 与温度反相
        - 温度影响: -0.5% per ℃ above 25℃
        - 随机噪声: ±3%
        - 范围: 30% ~ 90%
        """
        base_humidity = 60
        # 与温度反相
        time_factor = -15 * math.sin((hour - 6) * math.pi / 12)
        # 温度影响
        temp_factor = -0.5 * max(0, temperature - 25)
        noise = random.uniform(-3, 3)
        humidity = base_humidity + time_factor + temp_factor + noise
        return round(max(30, min(90, humidity)), 1)

    def _simulate_light(self, hour):
        """
        模拟光照强度 - 改进版本
        - 日出时间: 06:00, 日落时间: 18:30
        - 夜间也提供微弱光照用于演示（避免显示"无"）
        - 白天计算: sin((hour-6) * π/12.5) for 06:00-18:30
        - 基础光照: 100 lux (夜间演示), 800 lux (白天基础)
        - 峰值光照: 1200 lux (正午)
        - 天气模拟: 随机cloud_factor (0.6-1.0)
        - 范围: 50 ~ 1500 lux
        """
        sunrise = 6.0
        sunset = 18.5

        if hour < sunrise or hour > sunset:
            # 夜间也提供微弱光照用于演示（避免显示"黑暗"）
            # 根据时间段提供不同强度的基础光照
            if 23 <= hour or hour < 5:
                # 深夜：最暗，但仍可见
                return int(random.uniform(80, 120))
            else:
                # 黎明前/黄昏后：稍亮一些
                return int(random.uniform(100, 200))

        # 白天光照计算
        day_progress = (hour - sunrise) / (sunset - sunrise)
        # 正弦曲线，正午最高
        light_factor = math.sin(day_progress * math.pi)

        # 基础光照 + 峰值
        base_light = 800
        peak_light = 1200

        # 天气因子（云层遮挡）
        cloud_factor = random.uniform(0.6, 1.0)

        lux = base_light + (peak_light - base_light) * light_factor * cloud_factor
        return int(max(100, min(1500, lux)))  # 最低100 lux，避免显示"黑暗"

    def _simulate_co2(self, hour, temperature, humidity, lux):
        """
        模拟CO2浓度（修复版）
        - 基础CO2: 450 ppm（提高基础值避免触及下限）
        - 时间因子: 白天-30ppm, 夜晚+80ppm（减小波动幅度）
        - 温度影响: +1 ppm per ℃ above 22℃
        - 湿度影响: -0.3 ppm per % above 60%
        - 光照影响: -0.01 ppm per lux（大幅减小系数，避免白天过低）
        - 随机噪声: ±50 ppm（增大波动范围）
        - 范围: 400 ~ 1000 ppm（调整范围）
        """
        base_co2 = 450

        # 时间因子（减小波动幅度）
        if 6 <= hour <= 18:  # 白天
            time_factor = -30
        else:  # 夜晚
            time_factor = 80

        # 温度影响
        temp_factor = 1 * max(0, temperature - 22)

        # 湿度影响
        humi_factor = -0.3 * max(0, humidity - 60)

        # 光照影响（大幅减小系数）
        light_factor = -0.01 * lux

        # 增大随机噪声
        noise = random.uniform(-50, 50)

        co2 = base_co2 + time_factor + temp_factor + humi_factor + light_factor + noise
        return int(max(400, min(1000, co2)))

    def _get_time_period(self, hour):
        """获取时间段"""
        if 5 <= hour < 7:
            return 0  # 黎明
        elif 7 <= hour < 12:
            return 1  # 上午
        elif 12 <= hour < 17:
            return 2  # 下午
        elif 17 <= hour < 19:
            return 3  # 黄昏
        elif 19 <= hour < 23:
            return 4  # 夜晚
        else:
            return 5  # 深夜

    def enrich_real_data(self, real_data):
        """
        为实际数据添加CO2（使用平滑处理）
        :param real_data: 实际传感器数据
        :return: 增强后的数据
        """
        try:
            now = datetime.now()
            hour = now.hour + now.minute / 60.0

            env = real_data.get('env', {})

            # 保留agri原始数据（包含co2, tvoc, gasMic等真实传感器数据）
            agri_data = env.get('agri')

            # 获取实际传感器数据
            temp = env.get('temp', 25)
            humi = env.get('humi', 60)
            lux = env.get('lux', 500)

            # 处理agri真实传感器数据（将字段提升到env顶层）
            if agri_data:
                if agri_data.get('co2') is not None:
                    env['co2'] = agri_data['co2']
                if agri_data.get('tvoc') is not None:
                    env['tvoc'] = agri_data['tvoc']
                if agri_data.get('gasStatus') is not None:
                    env['gasStatus'] = agri_data['gasStatus']
                if agri_data.get('gasMic') is not None:
                    env['gasMic'] = agri_data['gasMic']

            # 推算CO2（仅在没有真实CO2数据时）
            if env.get('co2') is None:
                raw_co2 = self._calculate_co2(temp, humi, lux, hour)
                smoothed_co2 = self.smoother.add_and_get_average('real_co2', raw_co2)
                env['co2'] = smoothed_co2

            real_data['env'] = env
            return real_data

        except Exception as e:
            logger.error(f"增强实际数据失败: {e}")
            return real_data

    def _calculate_co2(self, temp, humi, lux, hour):
        """
        基于实际数据推算CO2（修复版）
        :param temp: 温度
        :param humi: 湿度
        :param lux: 光照
        :param hour: 小时
        :return: CO2浓度
        """
        base_co2 = 450

        # 时间因子（减小波动幅度）
        if 6 <= hour <= 18:
            time_factor = -30
        else:
            time_factor = 80

        # 温度影响
        temp_factor = 1 * max(0, temp - 22)

        # 湿度影响
        humi_factor = -0.3 * max(0, humi - 60)

        # 光照影响（大幅减小系数）
        light_factor = -0.01 * lux

        # 增大随机噪声
        noise = random.uniform(-50, 50)

        co2 = base_co2 + time_factor + temp_factor + humi_factor + light_factor + noise
        return int(max(400, min(1000, co2)))

    def get_status(self):
        """获取模拟服务状态"""
        return {
            'demo_mode': self.demo_mode,
            'running': self.running,
            'device_id': self.device_id
        }

    def stop(self):
        """停止服务"""
        logger.info("停止模拟服务...")
        self._stop_simulation()
