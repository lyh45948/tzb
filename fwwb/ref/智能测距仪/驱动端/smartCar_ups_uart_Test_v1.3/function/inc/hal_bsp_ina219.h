#ifndef __HAL_BSP_INA219_H__
#define __HAL_BSP_INA219_H__

#include "main.h"

#define INA219_I2C_ADDR (0x82)   // 器件的I2C从机地址
#define INA219_I2C_IDX  0             // 模块的I2C总线号
#define INA219_I2C_SPEED 100000       // 100KHz


// 获取电压值
uint16_t INA219_get_bus_voltage_mv(void);


// 获取电流值
uint16_t INA219_get_current_ma(void);

// 获取电源功率值
uint16_t INA219_get_power_mw(void);
// 初始化函数
uint32_t INA219_Init(void);




#endif

