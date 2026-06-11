/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "hal_bsp_sgp30.h"
#include "hi_gpio.h"
#include "hi_io.h"
#include "hi_i2c.h"
#include "hi_errno.h"

#define SGP30_I2C_ADDR (0xB0)
#define SGP30_I2C_IDX  0
#define SGP30_I2C_SPEED 100000

#define SGP30_FEATURE_SET_REG 0x20
#define SGP30_FEATURE_SET_CMD 0x03

#define SGP30_MEASURE_RAW_CMD 0x2008
#define READ_DATA_NUM 6

#define CO2_LEFT_SHIFT_8 8
#define TVOC_LEFT_SHIFT_8 8

// 读从机设备的数据
static uint32_t SGP30_RecvData(uint8_t *data, size_t size)
{
    hi_i2c_data i2cData = {0};
    i2cData.receive_buf = data;
    i2cData.receive_len = size;

    return hi_i2c_read(SGP30_I2C_IDX, SGP30_I2C_ADDR, &i2cData);
}

// 向从机设备发送数据
static uint32_t SGP30_WriteByteData(uint8_t byte1, uint8_t byte2)
{
    uint8_t buffer[] = {byte1, byte2};
    hi_i2c_data i2cData = {0};
    i2cData.send_buf = buffer;
    i2cData.send_len = sizeof(buffer);

    return hi_i2c_write(SGP30_I2C_IDX, SGP30_I2C_ADDR, &i2cData);
}

/**
 * @brief 读取SGP30 CO2和TVOC数据
 * @param co2 OUT - CO2浓度值 (ppm)
 * @param tvoc OUT - TVOC挥发性有机物浓度 (ppb)
 * @return 成功返回HI_ERR_SUCCESS
 */
uint32_t SGP30_ReadData(uint16_t *co2, uint16_t *tvoc)
{
    uint32_t result;
    uint8_t buffer[6] = {0};

    // 发送检测命令 (Measure Air Quality)
    result = SGP30_WriteByteData(0x20, 0x08);
    if (result != HI_ERR_SUCCESS) {
        printf("SGP30 write cmd failed: 0x%x\r\n", result);
        return result;
    }
    msleep(100);

    // 读数据
    result = SGP30_RecvData(buffer, READ_DATA_NUM);
    if (result != HI_ERR_SUCCESS) {
        printf("SGP30 read failed: 0x%x\r\n", result);
        return result;
    }

    // SGP30数据格式:
    // buffer[0,1] = CO2值 (big-endian, ppm)
    // buffer[3,4] = TVOC值 (big-endian, ppb)
    *co2 = (buffer[0] << CO2_LEFT_SHIFT_8) | buffer[1];
    *tvoc = (buffer[3] << TVOC_LEFT_SHIFT_8) | buffer[4];

    memset_s(buffer, sizeof(buffer), 0, sizeof(buffer));
    return HI_ERR_SUCCESS;
}

uint32_t SGP30_Init(void)
{
    uint32_t result;
    // GPIO_9 复用为 I2C_SCL
    hi_io_set_pull(HI_IO_NAME_GPIO_9, HI_IO_PULL_UP);
    hi_io_set_func(HI_IO_NAME_GPIO_9, HI_IO_FUNC_GPIO_9_I2C0_SCL);
    // GPIO_10 复用为 I2C_SDA
    hi_io_set_pull(HI_IO_NAME_GPIO_10, HI_IO_PULL_UP);
    hi_io_set_func(HI_IO_NAME_GPIO_10, HI_IO_FUNC_GPIO_10_I2C0_SDA);

    result = hi_i2c_init(SGP30_I2C_IDX, SGP30_I2C_SPEED);
    if (result != HI_ERR_SUCCESS) {
        printf("I2C SGP30 Init failed: 0x%x\r\n", result);
        return result;
    }

    // 发送特性设置命令
    result = SGP30_WriteByteData(SGP30_FEATURE_SET_REG, SGP30_FEATURE_SET_CMD);
    if (result != HI_ERR_SUCCESS) {
        printf("SGP30 feature set failed: 0x%x\r\n", result);
        return result;
    }

    printf("SGP30 initialized successfully\r\n");
    return HI_ERR_SUCCESS;
}