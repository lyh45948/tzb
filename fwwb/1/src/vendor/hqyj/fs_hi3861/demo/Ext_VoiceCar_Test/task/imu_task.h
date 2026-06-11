/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * IMU 传感器读取任务 - H30 (Yesense YIS106)
 * 通过 I2C 读取姿态数据，存入全局变量供 UDP 发送任务使用
 */

#ifndef IMU_TASK_H
#define IMU_TASK_H

#include <stdint.h>
#include "hal_bsp_h30.h"

// IMU 读取周期 (ms)
#define IMU_TASK_PERIOD_MS  50   // 与 UDP 发送周期一致 (20Hz)

// 外部变量：供 UDP 发送任务读取
extern h30_imu_data_t g_imuData;
extern uint8_t g_imuDataValid;   // 1=数据有效, 0=无效

/**
 * @brief IMU 传感器读取任务
 * @note  循环读取 H30 I2C 数据，解析后存入全局变量 g_imuData
 */
void imu_task(void);

#endif // IMU_TASK_H
