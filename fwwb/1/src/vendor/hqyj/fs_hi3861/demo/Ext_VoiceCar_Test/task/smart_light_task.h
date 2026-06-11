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

#ifndef SMART_LIGHT_TASK_H
#define SMART_LIGHT_TASK_H

#include <stdint.h>

// 时间段定义
typedef enum {
    TIME_PERIOD_DAWN = 0,      // 黎明 5:00-7:00
    TIME_PERIOD_MORNING,       // 上午 7:00-12:00
    TIME_PERIOD_NOON,          // 中午 12:00-14:00
    TIME_PERIOD_AFTERNOON,     // 下午 14:00-18:00
    TIME_PERIOD_DUSK,          // 黄昏 18:00-20:00
    TIME_PERIOD_EVENING,       // 晚间 20:00-23:00
    TIME_PERIOD_NIGHT          // 深夜 23:00-5:00
} time_period_t;

// 光照等级定义
typedef enum {
    LIGHT_LEVEL_DARK = 0,      // < 50 lux
    LIGHT_LEVEL_DIM,           // 50-200
    LIGHT_LEVEL_LOW,           // 200-500
    LIGHT_LEVEL_NORMAL,        // 500-1000
    LIGHT_LEVEL_BRIGHT,        // 1000-2000
    LIGHT_LEVEL_VERY_BRIGHT    // > 2000
} light_level_t;

// 智能光照状态结构体
typedef struct {
    time_period_t time_period;      // 当前时间段
    light_level_t light_level;      // 当前光照等级
    uint8_t target_brightness;      // 目标亮度 (0-100)
    uint8_t current_brightness;     // 当前亮度 (0-100)
    uint8_t auto_mode;              // 自动模式标志 (1=auto, 0=manual)
} smart_light_state_t;

// 全局状态变量声明
extern smart_light_state_t smartLightState;

/**
 * @brief 初始化智能光照模块
 */
void smart_light_init(void);

/**
 * @brief 设置自动/手动模式
 * @param mode 1=自动模式, 0=手动模式
 */
void smart_light_set_mode(uint8_t mode);

/**
 * @brief 设置手动亮度
 * @param brightness 亮度值 0-100
 */
void smart_light_set_brightness(uint8_t brightness);

/**
 * @brief 设置用户自定义RGB颜色（智能光照只调节亮度，不改变颜色）
 * @param r 红色分量 0-255
 * @param g 绿色分量 0-255
 * @param b 蓝色分量 0-255
 */
void smart_light_set_rgb(uint8_t r, uint8_t g, uint8_t b);

/**
 * @brief 获取当前时间段
 * @return 时间段枚举值
 */
time_period_t get_time_period(void);

/**
 * @brief 智能光照主任务
 */
void smart_light_task(void);

#endif // SMART_LIGHT_TASK_H
