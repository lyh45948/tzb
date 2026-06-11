/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * 农业安防扩展模块 - PWM RGB LED驱动实现
 */

#include "pwm_rgb.h"
#include "hi_io.h"
#include "hi_gpio.h"
#include "hi_pwm.h"
#include "hi_errno.h"

#define GPIO_G_Pin  HI_IO_NAME_GPIO_7
#define GPIO_B_Pin  HI_IO_NAME_GPIO_8

#define PWM_G_Port HI_PWM_PORT_PWM0
#define PWM_B_Port HI_PWM_PORT_PWM1

/**
 * @brief PWM驱动RGB灯的初始化 (绿色通道)
 */
void pwm_rgb_init(void)
{
    hi_gpio_init();
    hi_io_set_pull(GPIO_G_Pin, HI_IO_PULL_NONE);
    hi_io_set_func(GPIO_G_Pin, HI_IO_FUNC_GPIO_7_PWM0_OUT);
    hi_gpio_set_dir(GPIO_G_Pin, HI_GPIO_DIR_OUT);
    hi_gpio_set_ouput_val(GPIO_G_Pin, HI_GPIO_VALUE0);
    hi_pwm_init(PWM_G_Port);
    hi_pwm_set_clock(PWM_CLK_160M);
}

/**
 * @brief PWM1 RGB初始化 (蓝色通道)
 */
void pwm1_rgb_init(void)
{
    hi_io_set_pull(GPIO_B_Pin, HI_IO_PULL_DOWN);
    hi_io_set_func(GPIO_B_Pin, HI_IO_FUNC_GPIO_8_PWM1_OUT);
    hi_gpio_set_dir(GPIO_B_Pin, HI_GPIO_DIR_OUT);
    hi_gpio_set_ouput_val(GPIO_B_Pin, HI_GPIO_VALUE0);
    hi_pwm_init(PWM_B_Port);
    hi_pwm_set_clock(PWM_CLK_160M);
}

/**
 * @brief 设置RGB灯的PWM值
 */
void pwm_rgb_set(uint8_t g_value, uint8_t b_value)
{
    hi_pwm_start(PWM_G_Port, g_value, 255);
    hi_pwm_start(PWM_B_Port, b_value, 255);
}

/**
 * @brief 关闭RGB灯
 */
void pwm_rgb_close(void)
{
    hi_pwm_stop(PWM_G_Port);
    hi_pwm_stop(PWM_B_Port);
}