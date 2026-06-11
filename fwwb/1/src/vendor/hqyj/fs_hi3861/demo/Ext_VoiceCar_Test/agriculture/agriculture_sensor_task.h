/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * 农业安防扩展模块 - 传感器任务
 * 火焰传感器、可燃气体传感器、SGP30空气 quality传感器
 */

#ifndef AGRICULTURE_SENSOR_TASK_H
#define AGRICULTURE_SENSOR_TASK_H

#include <stdint.h>

// 农业安防传感器状态
typedef enum {
    FLAMMABLE_STATUS_OFF = 0,  // 未检测到可燃气体
    FLAMMABLE_STATUS_ON,      // 检测到可燃气体
} te_combustible_status_t;

typedef enum {
    FLAME_STATUS_OFF = 0,      // 未检测到火焰
    FLAME_STATUS_ON,          // 检测到火焰
} te_flame_status_t;

// 农业安防全局数据结构
typedef struct _agriculture_value {
    te_flame_status_t flame_status;          // 火焰状态
    te_combustible_status_t combustible_status; // 可燃气体状态
    uint16_t co2;                           // CO2浓度 (ppm)
    uint16_t tvoc;                          // TVOC浓度 (ppb)
    uint16_t gas_mic;                       // 模拟气体浓度
} agriculture_value_t;

// 外部变量声明
extern agriculture_value_t agricultureValue;

// 函数声明
void agriculture_sensor_task(void);        // 农业传感器读取任务
void agriculture_oled_show_task(void);     // 农业OLED显示任务

#endif /* AGRICULTURE_SENSOR_TASK_H */