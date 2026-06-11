/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * H30 (Yesense YIS106) IMU 传感器 I2C 驱动头文件
 * 通过 I2C 接口读取加速度、角速度、欧拉角、四元数等姿态数据
 */

#ifndef HAL_BSP_H30_H
#define HAL_BSP_H30_H

#include <stdint.h>

// ============================================
// H30 I2C 配置（根据实际硬件数据手册调整）
// ============================================
#define H30_I2C_ADDR       (0x50)   // YIS106 默认 7-bit I2C 地址（8-bit 写地址 = 0xA0）
#define H30_I2C_IDX        0        // 使用 I2C0（与 SHT20/AP3216C/PCF8574 共享总线）
#define H30_I2C_SPEED      100000   // I2C 速率 100KHz（可尝试 400KHz）

// 数据读取配置（需要根据 H30 I2C 数据手册修改）
#define H30_DATA_REG_ADDR  0x00     // 假设数据起始寄存器地址
#define H30_DATA_BUF_SIZE  72       // 数据缓冲区大小（需 >= 实际数据包长度）

// 解析状态
#define H30_PARSE_OK       0
#define H30_PARSE_ERROR    1
#define H30_I2C_ERROR      2

// ============================================
// H30 解析后的数据结构
// ============================================
typedef struct _h30_imu_data {
    uint16_t tid;           // 帧序号
    
    // 加速度 (m/s²)
    float accel_x;
    float accel_y;
    float accel_z;
    
    // 角速度 (°/s)
    float gyro_x;
    float gyro_y;
    float gyro_z;
    
    // 欧拉角 (°)
    float pitch;
    float roll;
    float yaw;
    
    // 四元数
    float q0;  // w
    float q1;  // x
    float q2;  // y
    float q3;  // z
    
    // 温度 (°C)
    float temperature;
    
    // 融合状态
    uint8_t fusion_status;
    
    // 数据有效标志
    uint8_t valid;  // 1=有效, 0=无效
} h30_imu_data_t;

/**
 * @brief H30 读取 IMU 数据
 * @param imu 解析后的 IMU 数据结构体指针
 * @return H30_PARSE_OK 成功; H30_PARSE_ERROR 解析失败; H30_I2C_ERROR I2C通信失败
 * @note  本函数先通过 I2C 读取原始数据，再按 H30 数据格式解析
 *        若 H30 的 I2C 协议与假设不同，请修改 hal_bsp_h30.c 中的解析逻辑
 */
int H30_ReadData(h30_imu_data_t *imu);

/**
 * @brief H30 初始化
 * @return HI_ERR_SUCCESS 成功; 其他值失败
 * @note  初始化 I2C 接口（I2C0 已由其他传感器初始化，此处仅确认配置）
 */
uint32_t H30_Init(void);

#endif // HAL_BSP_H30_H
