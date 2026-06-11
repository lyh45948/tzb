#ifndef __HAL_BSP_SGP30_H__
#define __HAL_BSP_SGP30_H__

#include "cmsis_os2.h"

#define SGP30_I2C_ADDR (0xB0)   // 器件的I2C从机地址
#define SGP30_I2C_IDX  0             // 模块的I2C总线号
#define SGP30_I2C_SPEED 100000       // 100KHz

/**
 * @brief 读取SGP30 CO2和TVOC数据
 * @param co2 OUT - CO2浓度值 (ppm)
 * @param tvoc OUT - TVOC挥发性有机物浓度 (ppb)
 * @return 成功返回HI_ERR_SUCCESS
 */
uint32_t SGP30_ReadData(uint16_t *co2, uint16_t *tvoc);

/**
 * @brief SGP30 初始化
 * @return 成功返回HI_ERR_SUCCESS
 */
uint32_t SGP30_Init(void);

#endif // !__HAL_BSP_SGP30_H__