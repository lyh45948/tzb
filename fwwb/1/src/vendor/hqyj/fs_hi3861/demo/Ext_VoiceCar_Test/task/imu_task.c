/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * IMU 传感器读取任务实现 - H30 (Yesense YIS106)
 */

#include "imu_task.h"
#include "sys_config.h"
#include "hal_bsp_h30.h"
#include "cmsis_os2.h"
#include "ohos_init.h"
#include <stdio.h>
#include <unistd.h>

// 全局 IMU 数据（供 UDP 发送任务读取）
h30_imu_data_t g_imuData = {0};
uint8_t g_imuDataValid = 0;

// 帧序号计数器
static uint16_t s_imuFrameCount = 0;

/**
 * @brief IMU 传感器读取任务
 * @note  每 50ms 读取一次 H30 I2C 数据，解析后存入 g_imuData
 *        UDP 发送任务会在同一周期内将数据打包发送给后端
 */
void imu_task(void)
{
    printf("[IMU] imu_task started\r\n");

    while (1) {
        h30_imu_data_t imu = {0};
        int ret = H30_ReadData(&imu);

        if (ret == H30_PARSE_OK && imu.valid) {
            // 更新帧序号
            imu.tid = s_imuFrameCount++;

            // 存入全局变量（简单的赋值，Hi3861 单核无需复杂锁）
            g_imuData = imu;
            g_imuDataValid = 1;

            printf("[IMU] tid=%d accel(%.3f,%.3f,%.3f) gyro(%.3f,%.3f,%.3f) euler(%.1f,%.1f,%.1f)\r\n",
                   imu.tid,
                   imu.accel_x, imu.accel_y, imu.accel_z,
                   imu.gyro_x, imu.gyro_y, imu.gyro_z,
                   imu.pitch, imu.roll, imu.yaw);
        } else {
            g_imuDataValid = 0;
            if (ret == H30_I2C_ERROR) {
                printf("[IMU] I2C read error\r\n");
            } else {
                printf("[IMU] Parse error or invalid data\r\n");
            }
        }

        usleep(IMU_TASK_PERIOD_MS * 1000);  // 50ms
    }
}
