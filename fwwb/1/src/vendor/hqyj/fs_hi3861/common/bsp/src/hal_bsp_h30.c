/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * H30 (Yesense YIS106) IMU 传感器 I2C 驱动
 * 
 * 说明：
 *   H30 通过转接口（水晶头/RJ45）连接在 Hi3861 的 I2C 总线上。
 *   本驱动通过 I2C 读取 H30 的姿态数据，解析后存入结构体。
 *   
 *   若 H30 的实际 I2C 寄存器地址或数据格式与以下假设不同，
 *   请修改 H30_ReadRawData() 和 H30_ParseData() 函数。
 */

#include "hal_bsp_h30.h"
#include "hi_i2c.h"
#include "hi_io.h"
#include "hi_errno.h"
#include <stdio.h>
#include <unistd.h>
#include <string.h>

// ============================================
// 内部辅助函数
// ============================================

/**
 * @brief 通过 I2C 向 H30 写入一个字节（通常用于指定寄存器地址）
 */
static uint32_t H30_WriteByte(uint8_t byte)
{
    hi_i2c_data i2cData = {0};
    uint8_t buffer[] = {byte};
    i2cData.send_buf = buffer;
    i2cData.send_len = sizeof(buffer);
    return hi_i2c_write(H30_I2C_IDX, H30_I2C_ADDR, &i2cData);
}

/**
 * @brief 通过 I2C 从 H30 读取数据
 * @param data 接收缓冲区
 * @param size 读取字节数
 */
static uint32_t H30_ReadBytes(uint8_t *data, size_t size)
{
    hi_i2c_data i2cData = {0};
    i2cData.receive_buf = data;
    i2cData.receive_len = size;
    return hi_i2c_read(H30_I2C_IDX, H30_I2C_ADDR, &i2cData);
}

/**
 * @brief 发送寄存器地址后读取数据（标准 I2C 寄存器读取流程）
 * @param regAddr 寄存器起始地址
 * @param buffer  接收缓冲区
 * @param len     读取长度
 * @return HI_ERR_SUCCESS 成功; 其他失败
 */
static uint32_t H30_ReadRegData(uint8_t regAddr, uint8_t *buffer, uint8_t len)
{
    uint32_t result;

    // 步骤1: 发送寄存器地址
    result = H30_WriteByte(regAddr);
    if (result != HI_ERR_SUCCESS) {
        printf("[H30] I2C write reg addr failed: 0x%x\r\n", result);
        return result;
    }

    // 步骤2: 等待设备准备数据（根据 H30 手册调整延时）
    usleep(5000);  // 5ms，若数据未就绪请增大此值

    // 步骤3: 读取数据
    result = H30_ReadBytes(buffer, len);
    if (result != HI_ERR_SUCCESS) {
        printf("[H30] I2C read data failed: 0x%x\r\n", result);
        return result;
    }

    return HI_ERR_SUCCESS;
}

/**
 * @brief 小端 int32 解析（YIS 协议数据格式）
 */
static int32_t H30_ParseInt32LE(const uint8_t *buf, uint8_t offset)
{
    return (int32_t)(buf[offset] | (buf[offset + 1] << 8) | 
                     (buf[offset + 2] << 16) | (buf[offset + 3] << 24));
}

/**
 * @brief 小端 int16 解析
 */
static int16_t H30_ParseInt16LE(const uint8_t *buf, uint8_t offset)
{
    return (int16_t)(buf[offset] | (buf[offset + 1] << 8));
}

// ============================================
// 数据解析（根据 H30 实际输出格式修改）
// ============================================

/**
 * @brief 解析 H30 I2C 原始数据
 * 
 * YIS Payload TLV 格式（与 ROS 驱动一致）：
 *   [DataID: 1B] [DataLen: 1B] [Value: DataLen bytes] ...
 *   
 *   若 H30 的 I2C 数据格式不同，请修改本函数。
 */
static int H30_ParseData(const uint8_t *raw, uint8_t len, h30_imu_data_t *imu)
{
    if (raw == NULL || imu == NULL || len < 4) {
        return H30_PARSE_ERROR;
    }

    // 清零输出结构体
    memset(imu, 0, sizeof(h30_imu_data_t));
    imu->valid = 0;

    uint8_t offset = 0;

    // TLV 解析循环：DataID(1B) + DataLen(1B) + Value(NB)
    while (offset + 1 < len) {
        uint8_t data_id = raw[offset];
        uint8_t data_len = raw[offset + 1];

        if (offset + 2 + data_len > len) {
            printf("[H30] Payload 长度不足: id=0x%02X, len=%d, remain=%d\r\n",
                   data_id, data_len, len - offset - 2);
            break;
        }

        const uint8_t *value = &raw[offset + 2];

        switch (data_id) {
            case 0x01:  // 温度
                if (data_len >= 2) {
                    imu->temperature = H30_ParseInt16LE(value, 0) * 0.01f;
                }
                break;

            case 0x10:  // 加速度
                if (data_len >= 12) {
                    imu->accel_x = H30_ParseInt32LE(value, 0) * 1e-6f;
                    imu->accel_y = H30_ParseInt32LE(value, 4) * 1e-6f;
                    imu->accel_z = H30_ParseInt32LE(value, 8) * 1e-6f;
                }
                break;

            case 0x20:  // 角速度
                if (data_len >= 12) {
                    imu->gyro_x = H30_ParseInt32LE(value, 0) * 1e-6f;
                    imu->gyro_y = H30_ParseInt32LE(value, 4) * 1e-6f;
                    imu->gyro_z = H30_ParseInt32LE(value, 8) * 1e-6f;
                }
                break;

            case 0x40:  // 欧拉角
                if (data_len >= 12) {
                    imu->pitch = H30_ParseInt32LE(value, 0) * 1e-6f;
                    imu->roll  = H30_ParseInt32LE(value, 4) * 1e-6f;
                    imu->yaw   = H30_ParseInt32LE(value, 8) * 1e-6f;
                }
                break;

            case 0x41:  // 四元数
                if (data_len >= 16) {
                    imu->q0 = H30_ParseInt32LE(value, 0) * 1e-6f;
                    imu->q1 = H30_ParseInt32LE(value, 4) * 1e-6f;
                    imu->q2 = H30_ParseInt32LE(value, 8) * 1e-6f;
                    imu->q3 = H30_ParseInt32LE(value, 12) * 1e-6f;
                }
                break;

            case 0x80:  // 融合状态
                if (data_len >= 1) {
                    imu->fusion_status = value[0];
                }
                break;

            default:
                // 未知 DataID，跳过
                break;
        }

        offset += 2 + data_len;
    }

    // 判断数据是否有效（至少要有加速度或角速度）
    if (imu->accel_x != 0.0f || imu->accel_y != 0.0f || imu->accel_z != 0.0f ||
        imu->gyro_x != 0.0f || imu->gyro_y != 0.0f || imu->gyro_z != 0.0f) {
        imu->valid = 1;
    }

    return H30_PARSE_OK;
}

// ============================================
// 对外接口
// ============================================

/**
 * @brief H30 读取并解析 IMU 数据
 */
int H30_ReadData(h30_imu_data_t *imu)
{
    uint32_t result;
    uint8_t buffer[H30_DATA_BUF_SIZE] = {0};

    // 读取原始数据（从 H30_DATA_REG_ADDR 开始，读取 H30_DATA_BUF_SIZE 字节）
    result = H30_ReadRegData(H30_DATA_REG_ADDR, buffer, H30_DATA_BUF_SIZE);
    if (result != HI_ERR_SUCCESS) {
        return H30_I2C_ERROR;
    }

    // 解析数据
    return H30_ParseData(buffer, H30_DATA_BUF_SIZE, imu);
}

/**
 * @brief H30 初始化
 * @note I2C0 已由 SHT20/AP3216C/PCF8574 初始化，此处仅确认上拉电阻配置
 */
uint32_t H30_Init(void)
{
    uint32_t result;

    // GPIO_9 复用为 I2C_SCL（与现有 I2C 设备共享）
    hi_io_set_pull(HI_IO_NAME_GPIO_9, HI_IO_PULL_UP);
    hi_io_set_func(HI_IO_NAME_GPIO_9, HI_IO_FUNC_GPIO_9_I2C0_SCL);
    
    // GPIO_10 复用为 I2C_SDA
    hi_io_set_pull(HI_IO_NAME_GPIO_10, HI_IO_PULL_UP);
    hi_io_set_func(HI_IO_NAME_GPIO_10, HI_IO_FUNC_GPIO_10_I2C0_SDA);

    // 初始化 I2C0（若已被其他设备初始化，重复调用通常无害）
    result = hi_i2c_init(H30_I2C_IDX, H30_I2C_SPEED);
    if (result != HI_ERR_SUCCESS && result != 0x80001044) {  // 0x80001044 可能是已初始化错误码
        printf("[H30] I2C init failed: 0x%x\r\n", result);
        return result;
    }

    printf("[H30] IMU sensor init succeeded! I2C addr=0x%02X, speed=%d\r\n",
           H30_I2C_ADDR, H30_I2C_SPEED);
    return HI_ERR_SUCCESS;
}
