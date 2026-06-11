/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * 农业安防扩展模块 - 传感器任务实现
 * 读取火焰传感器、可燃气体传感器、SGP30、ADC气体传感器
 */

#include "agriculture_sensor_task.h"
#include "sys_config.h"
#include "hal_bsp_pcf8574.h"
#include "hal_bsp_sgp30.h"
#include "hi_adc.h"
#include "hi_gpio.h"
#include "hi_pwm.h"
#include "hi_io.h"
#include "cmsis_os2.h"
#include "ohos_init.h"
#include <unistd.h>
#include <stdio.h>

#define GAS_ADC_CHANNEL HI_ADC_CHANNEL_6
#define FLAME_SENSOR_BIT 0x10    // PCF8574 bit4 - 火焰传感器
#define GAS_SENSOR_BIT 0x80      // PCF8574 bit7 - 可燃气体传感器

agriculture_value_t agricultureValue = {0};

/**
 * @brief 农业安防传感器读取任务
 * @note 读取火焰传感器、可燃气体状态、CO2、TVOC、ADC气体浓度
 */
void agriculture_sensor_task(void)
{
    printf("[AGRI] agriculture_sensor_task started\r\n");

    while (1) {
        uint8_t data = 0;

        // 读取PCF8574 IO扩展芯片
        PCF8574_Read(&data);

        // 火焰传感器检测 (bit4: 0=检测到火焰, 1=无火焰)
        if (data & FLAME_SENSOR_BIT) {
            agricultureValue.flame_status = FLAME_STATUS_OFF;
        } else {
            agricultureValue.flame_status = FLAME_STATUS_ON;
        }

        // 可燃气体传感器检测 (bit7: 0=检测到气体, 1=无气体)
        if (data & GAS_SENSOR_BIT) {
            agricultureValue.combustible_status = FLAMMABLE_STATUS_OFF;
        } else {
            agricultureValue.combustible_status = FLAMMABLE_STATUS_ON;
        }

        // 读取SGP30 CO2和TVOC数据
        uint16_t co2_val = 0, tvoc_val = 0;
        if (SGP30_ReadData(&co2_val, &tvoc_val) == HI_ERR_SUCCESS) {
            agricultureValue.co2 = co2_val;
            agricultureValue.tvoc = tvoc_val;
            // CO2数据已获取，仅更新数据，不自动触发设备
        }

        // 读取ADC气体浓度
        uint16_t adc_data = 0;
        hi_u32 ret = hi_adc_read(GAS_ADC_CHANNEL, &adc_data, HI_ADC_EQU_MODEL_4,
                                  HI_ADC_CUR_BAIS_DEFAULT, 0);
        if (ret == HI_ERR_SUCCESS) {
            float voltage = hi_adc_convert_to_voltage(adc_data);
            float gas_mic = voltage / 2.5f * 4.7f;
            if (gas_mic < 1.7f) {
                agricultureValue.gas_mic = 300;
            } else {
                agricultureValue.gas_mic = (uint16_t)((gas_mic * 1000 - 1440) / 0.64f);
            }
        }

        printf("[AGRI] Flame:%s Gas:%s CO2:%d TVOC:%d GAS_MIC:%d\r\n",
               agricultureValue.flame_status == FLAME_STATUS_ON ? "ON" : "OFF",
               agricultureValue.combustible_status == FLAMMABLE_STATUS_ON ? "ON" : "OFF",
               agricultureValue.co2, agricultureValue.tvoc, agricultureValue.gas_mic);

        sleep(2);  // 2秒读取一次
    }
}