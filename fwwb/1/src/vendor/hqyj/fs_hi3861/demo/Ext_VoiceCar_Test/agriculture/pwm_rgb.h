/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * 农业安防扩展模块 - PWM RGB LED驱动
 */

#ifndef PWM_RGB_H
#define PWM_RGB_H

#include <stdint.h>

/**
 * @brief PWM RGB初始化 (GPIO_7 -> PWM0 绿色通道)
 */
void pwm_rgb_init(void);

/**
 * @brief PWM1 RGB初始化 (GPIO_8 -> PWM1 蓝色通道)
 */
void pwm1_rgb_init(void);

/**
 * @brief 设置RGB灯PWM值
 * @param g_value 绿色值 (0-255)
 * @param b_value 蓝色值 (0-255)
 */
void pwm_rgb_set(uint8_t g_value, uint8_t b_value);

/**
 * @brief 关闭RGB灯
 */
void pwm_rgb_close(void);

#endif /* PWM_RGB_H */