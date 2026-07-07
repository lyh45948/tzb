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

#ifndef SYS_CONFIG_H
#define SYS_CONFIG_H
#include <stdint.h>

#include "cmsis_os2.h"

#define MIN_DISTANCE_VOL        300     // 避障距离阈值(mm)，需与下位机一致
#define MANUAL_OVERRIDE_MS      800     // 手动指令优先时间窗口
#define AUTO_LOOP_PERIOD_MS     5       // 自动避障轮询周期

#define UNUSED(x) (void)(x)

#include "hal_bsp_structAll.h"
#include "hal_bsp_openmv.h"

#define MOTOR_LOW_SPEED 40    // 低等速度
#define MOTOR_MIDDLE_SPEED 70 // 中等速度
#define MOTOR_HIGH_SPEED 100  // 高等速度

#define UDP_PORT 7788

// ============================================
// 农业安防模块 - CO2报警阈值
// ============================================
#define CO2_WARNING 800
#define CO2_DANGER 1000

// 小车的当前状态值
typedef enum {
    CAR_STATUS_RUN = 0x01, // 前进
    CAR_STATUS_BACK,       // 后退
    CAR_STATUS_LEFT,       // 左转
    CAR_STATUS_RIGHT,      // 右转
    CAR_STATUS_STOP,       // 停止
    CAR_STATUS_ON,         // 开启电机
    CAR_STATUS_OFF,        // 关闭电机
    CAR_STATUS_L_SPEED,    // 低速行驶
    CAR_STATUS_M_SPEED,    // 中速行驶
    CAR_STATUS_H_SPEED,    // 高速行驶
} te_car_status_t;

// 小车模式
typedef enum {
    CAR_MODE_MANUAL = 0,   // 手动遥控
    CAR_MODE_AVOID,        // 自动避障
    CAR_MODE_LINE,         // 自动巡线
    CAR_MODE_PATH,         // 路径规划
} te_car_mode_t;

// ============================================
// LD-STL-19P 激光雷达
// ============================================
#define LIDAR_POINT_PER_PACK 12
#define LIDAR_FRAME_SIZE 47

typedef struct __attribute__((packed)) {
    uint16_t distance;   // 距离 (mm)
    uint8_t intensity;    // 信号强度
} LidarPoint;

typedef struct __attribute__((packed)) {
    uint8_t header;          // 0x54
    uint8_t ver_len;         // 0x2C
    uint16_t speed;          // 转速 (deg/s)
    uint16_t start_angle;    // 起始角度 (0.01°)
    LidarPoint points[LIDAR_POINT_PER_PACK];
    uint16_t end_angle;      // 结束角度 (0.01°)
    uint16_t timestamp;      // 时间戳 (ms)
    uint8_t crc8;            // CRC校验
} LiDARFrame;

/*********************************** 系统的全局变量 ***********************************/
typedef struct _system_value {
    te_car_status_t car_status; // 小车的状态
    te_car_mode_t car_mode;     // 小车的模式
    int16_t left_motor_speed;       // 左电机的编码器值 (支持正负)
    int16_t right_motor_speed;      // 右电机的编码器值 (支持正负)
    uint16_t battery_voltage;        // 电池当前电压值
    uint16_t distance;               // 距离传感器
    uint8_t auto_abstacle_flag;      // 是否开启避障功能
    int udp_socket_fd;          // UDP通信的套接字

    // --- 新增环境监测数据 ---
    float env_temp;             // SHT20 温度
    float env_humi;             // SHT20 湿度
    uint16_t env_lux;           // AP3216C 光照强度
    uint16_t env_ps;            // AP3216C 接近距离
    uint16_t env_ir;            // AP3216C 人体检测

    // --- LD-STL-19P 激光雷达 ---
    uint16_t lidar_speed;           // 雷达转速 (deg/s)
    uint16_t lidar_start_angle;     // 起始角度 (0.01°)
    uint16_t lidar_end_angle;       // 结束角度 (0.01°)
    LidarPoint lidar_points[LIDAR_POINT_PER_PACK]; // 12个测量点
    uint16_t lidar_timestamp;       // 时间戳 (ms)

    // --- WT OpenMV 视觉识别结果 ---
    openmv_vision_t vision;         // I2C 读取的紧凑视觉结果
} system_value_t;
extern system_value_t systemValue; // 系统全局变量

extern tn_pcf8574_io_t pcf8574_io;
#define IO_FAN pcf8574_io.bit.p0
#define IO_BUZZER pcf8574_io.bit.p1
#define IO_LED pcf8574_io.bit.p2

extern volatile uint32_t g_lastManualTick;   // 最近手动指令时间
extern uint8_t g_turnToggle;                 // 左右转交替
extern osThreadId_t auto_avoid_task_id;      // 自动避障任务句柄

#endif
