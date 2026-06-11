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

#include "smart_light_task.h"
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "sys_config.h"
#include "hal_bsp_aw2013.h"

// RGB颜色状态（保存用户设置的RGB颜色）
static uint8_t saved_rgb_r = 255;
static uint8_t saved_rgb_g = 200;
static uint8_t saved_rgb_b = 150;

// 全局状态变量
smart_light_state_t smartLightState = {
    .time_period = TIME_PERIOD_NIGHT,
    .light_level = LIGHT_LEVEL_NORMAL,
    .target_brightness = 0,
    .current_brightness = 0,
    .auto_mode = 0  // 默认手动模式，避免覆盖用户设置的RGB
};

// 获取当前时间段（简化版：使用固定模拟时间或从NTP获取）
// 由于Hi3861可能没有RTC，这里使用简单的模拟方式
time_period_t get_time_period(void)
{
    // TODO: 如果有网络时间同步，可以从NTP获取真实时间
    // 这里暂时返回白天模式用于演示
    // 修复：返回上午时段，允许自动补光
    return TIME_PERIOD_MORNING;
}

// 根据时间段获取补光策略系数 (0-100)
static uint8_t get_time_factor(time_period_t period)
{
    /*
     * 时间-补光策略映射：
     * - 白天(7:00-18:00)：正常补光，光照不足时补光
     * - 黎明/黄昏：适度补光
     * - 晚间(20:00-23:00)：低强度补光
     * - 深夜(23:00-5:00)：基本不补光（除非手动开启）
     */
    switch (period) {
        case TIME_PERIOD_MORNING:
        case TIME_PERIOD_NOON:
        case TIME_PERIOD_AFTERNOON:
            return 100;  // 白天正常补光
        case TIME_PERIOD_DAWN:
        case TIME_PERIOD_DUSK:
            return 70;   // 过渡时段适度补光
        case TIME_PERIOD_EVENING:
            return 40;   // 晚间低强度补光
        case TIME_PERIOD_NIGHT:
        default:
            return 0;    // 深夜不自动补光
    }
}

// 根据环境光照获取光照等级
static light_level_t get_light_level(uint16_t env_lux)
{
    if (env_lux < 50)       return LIGHT_LEVEL_DARK;
    else if (env_lux < 200) return LIGHT_LEVEL_DIM;
    else if (env_lux < 500) return LIGHT_LEVEL_LOW;
    else if (env_lux < 1000) return LIGHT_LEVEL_NORMAL;
    else if (env_lux < 2000) return LIGHT_LEVEL_BRIGHT;
    else return LIGHT_LEVEL_VERY_BRIGHT;
}

// 智能算法核心：结合环境光照 + 时间因素计算目标亮度
static uint8_t smart_light_calculate(uint16_t env_lux, time_period_t period)
{
    // 1. 获取时间因素系数
    uint8_t time_factor = get_time_factor(period);

    // 深夜不自动补光
    if (time_factor == 0) {
        return 0;
    }

    // 2. 根据环境光照计算基础补光需求
    uint8_t base_brightness = 0;

    // 分段映射：环境光照越低，补光需求越高
    if (env_lux < 50)       base_brightness = 100;  // 黑暗：全亮度
    else if (env_lux < 100) base_brightness = 90;   // 极暗：90%
    else if (env_lux < 200) base_brightness = 75;   // 昏暗：75%
    else if (env_lux < 400) base_brightness = 50;   // 偏暗：50%
    else if (env_lux < 700) base_brightness = 30;   // 略暗：30%
    else if (env_lux < 1000) base_brightness = 15;  // 接近正常：15%
    else if (env_lux < 1500) base_brightness = 5;   // 正常：5%维持
    else base_brightness = 0;                        // 明亮：关闭

    // 3. 综合时间因素计算最终亮度
    uint8_t final_brightness = (base_brightness * time_factor) / 100;

    return final_brightness;
}

// 平滑过渡：避免亮度突变
static uint8_t smooth_transition(uint8_t current, uint8_t target)
{
    int16_t diff = (int16_t)target - (int16_t)current;

    if (diff > 5) {
        return current + 5;  // 渐增
    } else if (diff < -5) {
        return current - 5;  // 渐减
    }
    return target;  // 接近目标，直接设置
}

// 设置用户自定义的RGB颜色（保存起来，智能光照只调节亮度）
void smart_light_set_rgb(uint8_t r, uint8_t g, uint8_t b)
{
    saved_rgb_r = r;
    saved_rgb_g = g;
    saved_rgb_b = b;
    printf("[SmartLight] RGB color saved: R=%d, G=%d, B=%d\n", r, g, b);

    // 如果当前是手动模式，直接应用颜色（亮度100%）
    if (!smartLightState.auto_mode) {
        AW2013_Control_RGB(r, g, b);
    }
}

// 亮度值应用到保存的RGB颜色上（不改变颜色，只改变亮度）
static void set_light_brightness(uint8_t brightness)
{
    // 将亮度(0-100)应用到保存的RGB颜色上
    uint8_t r = (saved_rgb_r * brightness) / 100;
    uint8_t g = (saved_rgb_g * brightness) / 100;
    uint8_t b = (saved_rgb_b * brightness) / 100;
    AW2013_Control_RGB(r, g, b);
}

// 初始化智能光照模块
void smart_light_init(void)
{
    smartLightState.time_period = get_time_period();
    smartLightState.light_level = LIGHT_LEVEL_NORMAL;
    smartLightState.target_brightness = 0;
    smartLightState.current_brightness = 0;
    smartLightState.auto_mode = 0;  // 默认手动模式，避免覆盖用户设置的RGB

    // 初始化LED为关闭状态
    set_light_brightness(0);

    printf("[SmartLight] Initialized, auto_mode=%d (MANUAL by default)\n", smartLightState.auto_mode);
}

// 设置自动/手动模式
void smart_light_set_mode(uint8_t mode)
{
    smartLightState.auto_mode = mode;
    printf("[SmartLight] Mode set to: %s\n", mode ? "AUTO" : "MANUAL");

    // 当切换到自动模式时，如果没有传感器数据，使用默认亮度
    if (mode == 1 && systemValue.env_lux == 0) {
        smartLightState.target_brightness = 50;  // 默认50%亮度
        printf("[SmartLight] No sensor data, using default brightness 50%%\n");
    }
}

// 设置手动亮度
void smart_light_set_brightness(uint8_t brightness)
{
    if (brightness > 100) brightness = 100;
    smartLightState.target_brightness = brightness;
    // 设置亮度时自动切换到手动模式
    smartLightState.auto_mode = 0;
    printf("[SmartLight] Brightness set to: %d%% (switched to MANUAL mode)\n", brightness);
}

// 智能光照主任务
void smart_light_task(void)
{
    time_period_t last_period = TIME_PERIOD_NIGHT;
    uint8_t sensor_valid = 0;  // 传感器数据是否有效的标志

    printf("[SmartLight] Task started\n");

    while (1) {
        // 获取当前时间段
        time_period_t current_period = get_time_period();

        // 时间段变化时更新状态
        if (current_period != last_period) {
            smartLightState.time_period = current_period;
            last_period = current_period;
            printf("[SmartLight] Time period changed to: %d\n", current_period);
        }

        // 更新光照等级
        smartLightState.light_level = get_light_level(systemValue.env_lux);

        if (smartLightState.auto_mode) {
            // 自动模式：综合环境光 + 时间因素
            if (systemValue.env_lux == 0) {
                // 传感器数据无效时，使用默认补光亮度（而不是关闭）
                // 这样即使没有传感器，智能光照也能工作
                smartLightState.target_brightness = 50;
                printf("[SmartLight] Sensor unavailable, using default brightness 50%%\n");
            } else {
                // 传感器数据有效，正常计算
                sensor_valid = 1;
                uint8_t target = smart_light_calculate(
                    systemValue.env_lux,
                    smartLightState.time_period
                );
                smartLightState.target_brightness = target;
            }
        }

        // 平滑过渡到目标亮度
        smartLightState.current_brightness = smooth_transition(
            smartLightState.current_brightness,
            smartLightState.target_brightness
        );

        // 只有在自动模式下才应用亮度（避免覆盖用户手动设置的RGB）
        if (smartLightState.auto_mode) {
            // 应用亮度
            set_light_brightness(smartLightState.current_brightness);
        }

        usleep(50000);  // 50ms周期
    }
}
