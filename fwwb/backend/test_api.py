#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后端 REST API 测试脚本（小车在线版）

用法:
    cd backend
    bash run.sh        # 先启动后端（后台运行）
    python test_api.py # 再运行测试

说明:
    本脚本会自动检测在线设备，并向其发送请求验证数据完整性。
"""

import os
import sys

# 自动切换到虚拟环境（如果当前不在 venv 中且 .venv 存在）
VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv', 'bin', 'python3')
if sys.prefix == sys.base_prefix and os.path.exists(VENV_PYTHON):
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import requests
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:5000"
online_device_id = None


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_get(url, params=None):
    full_url = f"{BASE_URL}{url}"
    print(f"\n[GET] {full_url}")
    if params:
        print(f"  Params: {params}")
    try:
        resp = requests.get(full_url, params=params, timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {data}")
        return data
    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] 无法连接到后端，请确认服务已启动: {BASE_URL}")
        sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def main():
    global online_device_id
    print("后端 API 测试脚本启动（小车在线检测模式）")
    print(f"目标地址: {BASE_URL}")

    # 1. 设备列表
    print_section("1. 获取设备列表 /v1/devices")
    test_get("/v1/devices")

    # 2. 当前传感器数据（默认车辆）
    print_section("2. 获取默认车辆当前数据 /v1/sensors/current")
    r = test_get("/v1/sensors/current")
    env = (r or {}).get('data', {}).get('env', {})
    print(f"  >> 当前温度: {env.get('temp')}℃, 湿度: {env.get('humi')}%, "
          f"CO2: {env.get('co2')}, TVOC: {env.get('tvoc')}, "
          f"燃气状态: {env.get('gasStatus')}, 燃气浓度: {env.get('gasMic')}")

    # 3. 字段筛选
    print_section("3. 字段筛选 /v1/sensors/current?fields=temp,humi")
    test_get("/v1/sensors/current", params={"fields": "temp,humi"})

    # 4. 所有车辆当前数据（检测在线设备）
    print_section("4. 获取所有车辆当前数据 /v1/sensors/current/all")
    r = test_get("/v1/sensors/current/all")
    all_data = (r or {}).get('data', {})
    for dev_id, dev_info in all_data.items():
        if dev_info.get('online'):
            online_device_id = dev_id
            print(f"  >> 发现在线设备: {dev_id}")
            print(f"     温度={dev_info.get('env', {}).get('temp')}, "
                  f"CO2={dev_info.get('env', {}).get('co2')}, "
                  f"TVOC={dev_info.get('env', {}).get('tvoc')}, "
                  f"gasStatus={dev_info.get('env', {}).get('gasStatus')}, "
                  f"gasMic={dev_info.get('env', {}).get('gasMic')}")

    if not online_device_id:
        print("\n[!] 未检测到在线设备，后续测试将使用 demo_car / car1")
        online_device_id = 'car1'

    # 5. 指定车辆当前数据（在线设备）
    print_section(f"5. 获取指定车辆当前数据 /v1/sensors/current/{online_device_id}")
    r = test_get(f"/v1/sensors/current/{online_device_id}")
    env = (r or {}).get('data', {}).get('env', {})
    print(f"  >> 温度: {env.get('temp')}, CO2: {env.get('co2')}, "
          f"TVOC: {env.get('tvoc')}, gasStatus: {env.get('gasStatus')}, gasMic: {env.get('gasMic')}")

    # 6. 指定车辆字段筛选（危气传感器）
    print_section(f"6. 指定车辆字段筛选 /v1/sensors/current/{online_device_id}?fields=co2,tvoc,gasStatus")
    r = test_get(f"/v1/sensors/current/{online_device_id}", params={"fields": "co2,tvoc,gasStatus"})
    env = (r or {}).get('data', {}).get('env', {})
    print(f"  >> 筛选结果: CO2={env.get('co2')}, TVOC={env.get('tvoc')}, gasStatus={env.get('gasStatus')}")

    # 7. 历史数据查询（在线设备）
    print_section(f"7. 历史数据查询 /v1/sensors/history/{online_device_id}")
    end = datetime.now()
    start = end - timedelta(days=1)
    r = test_get(f"/v1/sensors/history/{online_device_id}", params={
        "startTime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "endTime": end.strftime("%Y-%m-%d %H:%M:%S"),
        "interval": 60
    })
    history = (r or {}).get('data', [])
    print(f"  >> 历史记录数: {len(history)}")
    if history:
        print(f"  >> 最新一条: {history[0]}")

    # 8. 视觉分析（占位接口）
    print_section("8. 视觉分析（占位）/v1/vision/analyze")
    test_get("/v1/vision/analyze", params={"image_url": "http://example.com/image.jpg"})

    # 9. 电量预测（占位接口）
    print_section("9. 电量预测（占位）/v1/device/battery/predict")
    test_get("/v1/device/battery/predict", params={"device_id": online_device_id})

    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
