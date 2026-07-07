# -*- coding: utf-8 -*-
"""
车辆环境监测智能体 - 输出通过 API 传输版本
所有数据从后端获取，所有输出通过 API 发送到后端
"""

import requests
import ollama
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ==================== 配置区域 ====================
API_BASE_URL = "http://127.0.0.1:18080"  # 后端地址
DEVICE_ID = "car1"  # 要监控的车辆ID
CHECK_INTERVAL = 30  # 数据采集间隔（秒）
PREDICTION_INTERVAL = 60  # 预测分析间隔（秒）

# 定时报告配置
DAILY_REPORT_HOUR = 20  # 每天20点生成日报
WEEKLY_REPORT_DAY = 6  # 周日生成周报（周一=0，周日=6）
WEEKLY_REPORT_HOUR = 20  # 晚上20点生成周报

# 告警阈值配置
CO_WARNING = 10    # CO 警告阈值（ppm）
CO_CRITICAL = 30   # CO 严重阈值（ppm）
TEMP_MIN = 15      # 温度最低值（℃）
TEMP_MAX = 35      # 温度最高值（℃）
TVOC_WARNING = 300 # TVOC 警告阈值（ppb）


# ==================== API 交互模块 ====================
class SensorAPI:
    """传感器 API 交互类"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def get_current_data(self, device_id: str = None, fields: List[str] = None) -> Optional[Dict]:
        """获取当前传感器数据"""
        if device_id:
            url = f"{self.base_url}/v1/sensors/current/{device_id}"
        else:
            url = f"{self.base_url}/v1/sensors/current/all"
        
        if fields:
            url += f"?fields={','.join(fields)}"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data")
            return None
        except Exception as e:
            print(f"获取数据失败: {e}")
            return None
    
    def get_history_data(self, device_id: str, start_time: str, end_time: str,
                         interval: int = None) -> List[Dict]:
        """获取历史数据"""
        url = f"{self.base_url}/v1/sensors/history/{device_id}"
        params = {
            "startTime": start_time,
            "endTime": end_time
        }
        if interval:
            params["interval"] = interval
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data", [])
            return []
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return []


class AgentOutputAPI:
    """智能体输出 API 交互类 - 所有输出通过接口传输"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def _post(self, endpoint: str, data: Dict) -> bool:
        """通用 POST 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, json=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"发送数据到 {endpoint} 失败: {e}")
            return False
    
    def send_sensor_record(self, device_id: str, temp: float, co: int, 
                           humi: float, tvoc: int, gasStatus: int,
                           timestamp: str = None) -> bool:
        """发送传感器历史记录"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        data = {
            "device_id": device_id,
            "timestamp": timestamp,
            "temp": temp,
            "co": co,
            "humi": humi,
            "tvoc": tvoc,
            "gasStatus": gasStatus
        }
        return self._post("/v1/agent/sensor_record", data)
    
    def send_event(self, event_type: str, description: str, device_id: str,
                   severity: str, co_value: float = None, temp_value: float = None) -> bool:
        """发送报警/异常事件"""
        data = {
            "event_type": event_type,
            "description": description,
            "device_id": device_id,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        if co_value is not None:
            data["co_value"] = co_value
        if temp_value is not None:
            data["temp_value"] = temp_value
        return self._post("/v1/agent/event", data)
    
    def send_analysis_result(self, device_id: str, result_type: str,
                             content: str, has_anomaly: bool = False) -> bool:
        """发送AI分析结果"""
        data = {
            "device_id": device_id,
            "result_type": result_type,
            "content": content,
            "has_anomaly": has_anomaly,
            "timestamp": datetime.now().isoformat()
        }
        return self._post("/v1/agent/analysis", data)
    
    def send_report(self, device_id: str, report_type: str, date: str,
                    summary: str, avg_temp: float, max_co: float,
                    alert_count: int, full_report: str) -> bool:
        """发送报告（日报/周报）"""
        data = {
            "device_id": device_id,
            "report_type": report_type,
            "date": date,
            "summary": summary,
            "avg_temp": avg_temp,
            "max_co": max_co,
            "alert_count": alert_count,
            "full_report": full_report,
            "created_at": datetime.now().isoformat()
        }
        return self._post("/v1/agent/report", data)
    
    def send_status(self, device_id: str, status: str, temp: float = None,
                    co: int = None, gas_status: int = None) -> bool:
        """发送智能体状态"""
        data = {
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        if temp is not None:
            data["temp"] = temp
        if co is not None:
            data["co"] = co
        if gas_status is not None:
            data["gas_status"] = gas_status
        return self._post("/v1/agent/status", data)
    
    def send_alert(self, device_id: str, alert_level: str, alert_type: str,
                   message: str, co_value: float = None, temp_value: float = None) -> bool:
        """发送实时警报"""
        data = {
            "device_id": device_id,
            "alert_level": alert_level,
            "alert_type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if co_value is not None:
            data["co_value"] = co_value
        if temp_value is not None:
            data["temp_value"] = temp_value
        return self._post("/v1/agent/alert", data)
    
    def send_prediction(self, device_id: str, field: str, trend: str,
                        current_value: float, next_prediction: float,
                        risk_level: str, message: str) -> bool:
        """发送风险预测"""
        data = {
            "device_id": device_id,
            "field": field,
            "trend": trend,
            "current_value": current_value,
            "next_prediction": next_prediction,
            "risk_level": risk_level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        return self._post("/v1/agent/prediction", data)


# ==================== 预测分析模块 ====================
class EnvironmentPredictor:
    """环境预测器"""
    
    @staticmethod
    def calculate_trend(data: List[Dict], field: str) -> Dict:
        """计算数据趋势"""
        if len(data) < 3:
            return {"trend": "数据不足", "change_rate": 0}
        
        values = [d.get(field) for d in data if d.get(field) is not None]
        if len(values) < 3:
            return {"trend": "数据不足", "change_rate": 0}
        
        x = list(range(len(values)))
        n = len(values)
        slope = (n * sum(x[i] * values[i] for i in range(n)) - sum(x) * sum(values)) / \
                (n * sum(i*i for i in x) - sum(x)**2)
        
        change_rate = slope / (values[-1] + 1e-6) * 100
        if slope > 0.01:
            trend = "上升"
        elif slope < -0.01:
            trend = "下降"
        else:
            trend = "平稳"
        
        next_value = values[-1] + slope
        return {
            "trend": trend,
            "change_rate": round(change_rate, 2),
            "current": values[-1],
            "next_prediction": round(next_value, 2),
            "confidence": min(0.9, 0.7 + len(values) / 100)
        }
    
    @staticmethod
    def check_anomaly(current: Dict) -> tuple:
        """检测异常"""
        anomalies = []
        alert_level = "normal"
        co_value = None
        temp_value = None
        
        # 一氧化碳检测
        if "co" in current and current["co"] is not None:
            co_value = current["co"]
            if co_value > CO_WARNING:
                anomalies.append(f"⚠️ 一氧化碳浓度过高: {co_value}ppm！")
                if co_value > CO_CRITICAL:
                    anomalies.append("🚨 紧急：立即撤离该区域！")
                alert_level = "critical"
        
        # 燃气泄漏检测
        if current.get("gasStatus") == 1:
            anomalies.append("⚠️ 燃气泄漏！请立即检查！")
            alert_level = "critical"
        
        # 温度检测
        if "temp" in current and current["temp"] is not None:
            temp_value = current["temp"]
            if temp_value < TEMP_MIN:
                anomalies.append(f"温度过低: {temp_value}°C")
                alert_level = "warning" if alert_level != "critical" else alert_level
            elif temp_value > TEMP_MAX:
                anomalies.append(f"温度过高: {temp_value}°C")
                alert_level = "warning" if alert_level != "critical" else alert_level
        
        # TVOC检测
        if "tvoc" in current and current["tvoc"] is not None:
            if current["tvoc"] > TVOC_WARNING:
                anomalies.append(f"TVOC超标: {current['tvoc']}ppb")
                alert_level = "warning" if alert_level != "critical" else alert_level
        
        # 生成建议
        recommendations = []
        for anomaly in anomalies:
            if "一氧化碳" in anomaly:
                if "紧急" in anomaly:
                    recommendations.append("🚨 立即撤离！拨打急救电话！")
                else:
                    recommendations.append("立即开窗通风，检查燃气设备")
            elif "燃气" in anomaly:
                recommendations.append("立即关闭燃气阀门，开窗通风，不要使用电器")
            elif "温度" in anomaly:
                recommendations.append("检查空调系统或通风")
            elif "TVOC" in anomaly:
                recommendations.append("开启空气净化器，检查装修材料")
        
        return (len(anomalies) > 0, alert_level, anomalies, recommendations, co_value, temp_value)


# ==================== AI 智能体核心 ====================
class VehicleEnvAgent:
    """车辆环境智能体"""
    
    def __init__(self, base_url: str, device_id: str):
        self.sensor_api = SensorAPI(base_url)
        self.output_api = AgentOutputAPI(base_url)
        self.predictor = EnvironmentPredictor()
        self.device_id = device_id
        self.last_prediction_time = 0
        self.alert_triggered = False
        self.history_data = []
    
    def check_and_alert(self, current_data: Dict) -> bool:
        """检查问题并报警"""
        env = current_data.get("env", {})
        has_anomaly, alert_level, anomalies, recommendations, co_value, temp_value = self.predictor.check_anomaly(env)
        
        if has_anomaly:
            # 发送警报到接口
            alert_message = " | ".join(anomalies)
            self.output_api.send_alert(
                self.device_id, alert_level, "sensor_anomaly",
                alert_message, co_value, temp_value
            )
            
            if not self.alert_triggered:
                # 打印报警
                print("\n" + "="*60)
                print("🚨 🚨 🚨 警 报 🚨 🚨 🚨")
                print("="*60)
                
                for anomaly in anomalies:
                    print(f"❌ {anomaly}")
                print("\n📋 建议措施：")
                for rec in recommendations:
                    print(f"   • {rec}")
                
                # 调用 AI 给出紧急指导
                prompt = self.build_problem_prompt(current_data, anomalies, recommendations)
                try:
                    response = ollama.chat(
                        model="deepseek-r1:7b",
                        messages=[{"role": "user", "content": prompt}],
                        stream=False
                    )
                    ai_guide = response["message"]["content"]
                    print("\n🤖 AI 应急指导：")
                    print(ai_guide)
                    
                    # 发送AI指导到接口
                    self.output_api.send_analysis_result(
                        self.device_id, "emergency_guide", ai_guide, True
                    )
                except Exception as e:
                    print(f"\n🤖 AI 指导获取失败: {e}")
                
                print("="*60 + "\n")
                self.alert_triggered = True
                
                # 发送事件到接口
                for anomaly in anomalies:
                    self.output_api.send_event(
                        "报警", anomaly, self.device_id, alert_level, co_value, temp_value
                    )
            
            return True
        else:
            self.alert_triggered = False
            return False
    
    def build_problem_prompt(self, current_data: Dict, anomalies: List[str], recommendations: List[str]) -> str:
        """构建问题报警提示词"""
        env = current_data.get("env", {})
        
        prompt = f"""
【紧急警报】车辆「{self.device_id}」检测到异常！

## 当前数据
- 温度: {env.get('temp', 'N/A')} °C
- 一氧化碳: {env.get('co', 'N/A')} ppm
- TVOC: {env.get('tvoc', 'N/A')} ppb
- 燃气状态: {'泄漏' if env.get('gasStatus') == 1 else '正常'}

## 检测到的问题
{chr(10).join(f'- {a}' for a in anomalies)}

## 紧急建议
{chr(10).join(f'- {r}' for r in recommendations)}

请给出简要的应急处理指导（50字以内）：
"""
        return prompt
    
    def analyze_with_ai(self, current_data: Dict, history: List[Dict]) -> Optional[str]:
        """正常AI分析"""
        env = current_data.get("env", {})
        
        # 计算趋势
        trends = {}
        for field in ["temp", "humi", "co"]:
            if len(history) >= 5:
                trends[field] = self.predictor.calculate_trend(history[-20:], field)
        
        # 检测是否有预测风险
        for field, trend in trends.items():
            if trend.get("trend") == "上升" and trend.get("change_rate", 0) > 5:
                if field == "co" and trend.get("next_prediction", 0) > CO_WARNING:
                    self.output_api.send_prediction(
                        self.device_id, field, trend.get("trend"),
                        trend.get("current", 0), trend.get("next_prediction", 0),
                        "warning", f"预测一氧化碳将持续上升，可能达到{trend.get('next_prediction')}ppm"
                    )
                    print(f"\n⚠️ 风险预测：预测一氧化碳将持续上升，可能达到{trend.get('next_prediction')}ppm")
                elif field == "temp" and trend.get("next_prediction", 0) > TEMP_MAX:
                    self.output_api.send_prediction(
                        self.device_id, field, trend.get("trend"),
                        trend.get("current", 0), trend.get("next_prediction", 0),
                        "warning", f"预测温度将持续上升，可能超过{TEMP_MAX}°C"
                    )
                    print(f"\n⚠️ 风险预测：预测温度将持续上升，可能超过{TEMP_MAX}°C")
        
        prompt = f"""
分析以下传感器数据，给出简要评估（50字以内）：

温度: {env.get('temp')}°C
一氧化碳: {env.get('co')} ppm
湿度: {env.get('humi')} %
TVOC: {env.get('tvoc')} ppb
燃气状态: {'泄漏' if env.get('gasStatus') == 1 else '正常'}

趋势: {json.dumps(trends, ensure_ascii=False)}

注意：一氧化碳(CO)超过10ppm即有风险，超过30ppm需立即撤离。

只需回答：环境状态（正常/注意/危险）和1句话建议。
"""
        
        try:
            response = ollama.chat(
                model="deepseek-r1:7b",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            result = response["message"]["content"]
            
            # 发送分析结果到接口
            has_anomaly = "注意" in result or "危险" in result
            self.output_api.send_analysis_result(
                self.device_id, "routine_analysis", result, has_anomaly
            )
            
            return result
        except Exception as e:
            return f"分析失败: {e}"
    
    def generate_daily_report(self):
        """生成日报"""
        print("\n📊 正在生成日报...")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 从接口获取今日历史数据
        start_time = f"{today} 00:00:00"
        end_time = f"{today} 23:59:59"
        history = self.sensor_api.get_history_data(self.device_id, start_time, end_time)
        
        if not history:
            print("今日无数据，跳过日报生成\n")
            return
        
        # 统计数据
        temps = [d.get("temperature", d.get("temp")) for d in history if d.get("temperature") is not None or d.get("temp") is not None]
        cos = [d.get("co") for d in history if d.get("co") is not None]
        alerts = [d for d in history if d.get("gasStatus") == 1 or (d.get("co", 0) > CO_WARNING)]
        
        avg_temp = sum(temps) / len(temps) if temps else 0
        max_temp = max(temps) if temps else 0
        min_temp = min(temps) if temps else 0
        max_co = max(cos) if cos else 0
        alert_count = len(alerts)
        
        # 找出一条最严重的事件
        critical_event = None
        for d in history:
            if d.get("gasStatus") == 1:
                critical_event = f"燃气泄漏 发生在 {d.get('timestamp', '未知时间')}"
                break
            elif d.get("co", 0) > CO_CRITICAL:
                critical_event = f"一氧化碳严重超标 ({d['co']}ppm) 发生在 {d.get('timestamp', '未知时间')}"
                break
            elif d.get("co", 0) > CO_WARNING:
                critical_event = f"一氧化碳超标 ({d['co']}ppm) 发生在 {d.get('timestamp', '未知时间')}"
                break
        
        prompt = f"""
请根据以下日报数据生成一份简洁的报告。

## 数据统计
- 数据条数: {len(history)}
- 平均温度: {avg_temp:.1f}°C (最高{max_temp:.1f}°C / 最低{min_temp:.1f}°C)
- 最高一氧化碳: {max_co:.1f} ppm
- 异常事件次数: {alert_count} 次

## 关键事件
{critical_event if critical_event else '无重大异常事件'}

## 要求
1. 评估整体环境状况
2. 指出主要风险点
3. 给出改进建议
4. 控制在150字以内

请生成报告：
"""
        
        try:
            response = ollama.chat(
                model="deepseek-r1:7b",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            report = response["message"]["content"]
            
            # 发送报告到接口
            self.output_api.send_report(
                self.device_id, "daily", today, report[:200],
                avg_temp, max_co, alert_count, report
            )
            
            print("\n" + "="*60)
            print(f"📋 日报 {today}")
            print("="*60)
            print(report)
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"日报生成失败: {e}\n")
    
    def generate_weekly_report(self):
        """生成周报"""
        print("\n📊 正在生成周报...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_time = start_date.strftime("%Y-%m-%d 00:00:00")
        end_time = end_date.strftime("%Y-%m-%d 23:59:59")
        
        history = self.sensor_api.get_history_data(self.device_id, start_time, end_time)
        
        if not history:
            print("本周无数据，跳过周报生成\n")
            return
        
        # 统计数据
        temps = [d.get("temperature", d.get("temp")) for d in history if d.get("temperature") is not None or d.get("temp") is not None]
        cos = [d.get("co") for d in history if d.get("co") is not None]
        alerts = [d for d in history if d.get("gasStatus") == 1 or (d.get("co", 0) > CO_WARNING)]
        
        avg_temp = sum(temps) / len(temps) if temps else 0
        max_temp = max(temps) if temps else 0
        min_temp = min(temps) if temps else 0
        max_co = max(cos) if cos else 0
        alert_count = len(alerts)
        
        # 统计每日平均温度
        daily_avg = {}
        for d in history:
            ts = d.get("timestamp", "")
            date = ts[:10] if len(ts) >= 10 else ts
            temp_val = d.get("temperature", d.get("temp"))
            if date and temp_val:
                if date not in daily_avg:
                    daily_avg[date] = []
                daily_avg[date].append(temp_val)
        
        trend_desc = ""
        if len(daily_avg) >= 2:
            first_week_avg = sum(list(daily_avg.values())[:3]) / 3 if len(daily_avg) >= 3 else sum(daily_avg.values()) / len(daily_avg)
            last_week_avg = sum(list(daily_avg.values())[-3:]) / 3 if len(daily_avg) >= 3 else sum(daily_avg.values()) / len(daily_avg)
            if last_week_avg > first_week_avg + 1:
                trend_desc = "本周温度呈上升趋势"
            elif last_week_avg < first_week_avg - 1:
                trend_desc = "本周温度呈下降趋势"
            else:
                trend_desc = "本周温度基本平稳"
        
        prompt = f"""
请根据以下周报数据生成一份简洁的周报。

## 数据统计
- 数据条数: {len(history)}
- 平均温度: {avg_temp:.1f}°C (最高{max_temp:.1f}°C / 最低{min_temp:.1f}°C)
- 最高一氧化碳: {max_co:.1f} ppm
- 异常事件总次数: {alert_count} 次
- 温度趋势: {trend_desc}

## 要求
1. 评估本周整体环境状况
2. 指出主要风险点和趋势
3. 给出下周改进建议
4. 控制在200字以内

请生成周报：
"""
        
        try:
            response = ollama.chat(
                model="deepseek-r1:7b",
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            report = response["message"]["content"]
            
            # 发送报告到接口
            self.output_api.send_report(
                self.device_id, "weekly",
                f"{start_date.strftime('%Y-%m-%d')}~{end_date.strftime('%Y-%m-%d')}",
                report[:200], avg_temp, max_co, alert_count, report
            )
            
            print("\n" + "="*60)
            print(f"📋 周报 ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})")
            print("="*60)
            print(report)
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"周报生成失败: {e}\n")
    
    def run_continuous(self):
        """持续运行模式"""
        print("\n🚗 车辆环境监测智能体已启动（输出通过 API 传输）")
        print(f"📡 监控设备: {self.device_id}")
        print(f"📡 后端地址: {API_BASE_URL}")
        print(f"⏱️  数据采集间隔: {CHECK_INTERVAL}秒")
        print(f"🔮 预测分析间隔: {PREDICTION_INTERVAL}秒")
        print(f"📊 日报时间: 每天 {DAILY_REPORT_HOUR}:00")
        print(f"📊 周报时间: 每周六 {WEEKLY_REPORT_HOUR}:00")
        print("="*60)
        print("\n⚠️ 告警阈值：一氧化碳 > 10ppm 警告，> 30ppm 紧急撤离")
        print("💡 提示：所有数据将通过 API 传输到后端\n")
        
        # 发送启动状态
        self.output_api.send_status(self.device_id, "running")
        
        last_prediction = 0
        last_daily_report_date = None
        last_weekly_report_week = None
        
        while True:
            try:
                current_time = time.time()
                now = datetime.now()
                
                # 定时生成日报
                if now.hour == DAILY_REPORT_HOUR and last_daily_report_date != now.date():
                    self.generate_daily_report()
                    last_daily_report_date = now.date()
                
                # 定时生成周报
                if now.weekday() == WEEKLY_REPORT_DAY and now.hour == WEEKLY_REPORT_HOUR:
                    current_week = now.strftime("%Y-%W")
                    if last_weekly_report_week != current_week:
                        self.generate_weekly_report()
                        last_weekly_report_week = current_week
                
                # 获取当前数据
                current_data = self.sensor_api.get_current_data(self.device_id)
                if current_data:
                    env = current_data.get("env", {})
                    
                    # 发送传感器记录到接口
                    self.output_api.send_sensor_record(
                        self.device_id,
                        env.get("temp"),
                        env.get("co"),
                        env.get("humi"),
                        env.get("tvoc"),
                        env.get("gasStatus", 0)
                    )
                    
                    # 更新本地历史缓存
                    record = {
                        "timestamp": datetime.now().isoformat(),
                        "temp": env.get("temp"),
                        "co": env.get("co"),
                        "humi": env.get("humi"),
                        "tvoc": env.get("tvoc"),
                        "gasStatus": env.get("gasStatus")
                    }
                    self.history_data.append(record)
                    if len(self.history_data) > 100:
                        self.history_data = self.history_data[-100:]
                    
                    # 检查问题并报警
                    has_problem = self.check_and_alert(current_data)
                    
                    # 发送状态到接口
                    status = "alert" if has_problem else "normal"
                    self.output_api.send_status(
                        self.device_id, status,
                        env.get("temp"), env.get("co"), env.get("gasStatus")
                    )
                    
                    # 定期AI分析
                    if current_time - last_prediction >= PREDICTION_INTERVAL:
                        print(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] 智能体正在分析...")
                        
                        # 获取历史数据
                        end_time = datetime.now()
                        start_time = end_time - timedelta(minutes=30)
                        history = self.sensor_api.get_history_data(
                            self.device_id,
                            start_time.strftime("%Y-%m-%d %H:%M:%S"),
                            end_time.strftime("%Y-%m-%d %H:%M:%S"),
                            60
                        )
                        if not history and len(self.history_data) > 0:
                            history = self.history_data
                        
                        # 静默分析
                        analysis = self.analyze_with_ai(current_data, history)
                        print(f"✅ 分析完成: {analysis if analysis else '正常'}")
                        
                        last_prediction = current_time
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\n👋 智能体已停止")
                self.output_api.send_status(self.device_id, "stopped")
                break
            except Exception as e:
                print(f"\n❌ 运行时错误: {e}")
                time.sleep(CHECK_INTERVAL)


# ==================== 主程序 ====================
def main():
    agent = VehicleEnvAgent(
        base_url=API_BASE_URL,
        device_id=DEVICE_ID
    )
    agent.run_continuous()


if __name__ == "__main__":
    main()