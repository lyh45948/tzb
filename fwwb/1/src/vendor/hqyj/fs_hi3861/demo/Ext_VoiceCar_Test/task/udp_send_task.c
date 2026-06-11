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

#include "udp_send_task.h"
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include "ohos_init.h"
#include "cmsis_os2.h"
#include "sys_config.h"
#include "lwip/netifapi.h"
#include "lwip/sockets.h"
#include "lwip/api_shell.h"
#include "cJSON.h"
#include "hal_bsp_sht20.h"
#include "hal_bsp_ap3216c.h"
#include "hal_bsp_pcf8574.h"
#include "smart_light_task.h"
#include "agriculture_sensor_task.h"
#include "imu_task.h"

struct sockaddr_in client; // 客户端
#define  TASK_DELAY_TIME (50 * 1000)

void udp_send_task(void)
{
    int ret = 0;
    while (1) {
        // --- 读取最新环境数据 ---
        SHT20_ReadData(&systemValue.env_temp, &systemValue.env_humi);
        AP3216C_ReadData(&systemValue.env_ir, &systemValue.env_lux, &systemValue.env_ps);

        cJSON *json_root = cJSON_CreateObject();
        if (json_root) {
            cJSON_AddItemToObject(json_root, "carStatus", cJSON_CreateString(get_CurrentCarStatus(systemValue)));

            // 基础数据
            cJSON_AddItemToObject(json_root, "L_spd", cJSON_CreateNumber(systemValue.left_motor_speed));
            cJSON_AddItemToObject(json_root, "R_spd", cJSON_CreateNumber(systemValue.right_motor_speed));
            cJSON_AddItemToObject(json_root, "carPower", cJSON_CreateNumber(systemValue.battery_voltage));
            cJSON_AddItemToObject(json_root, "distance", cJSON_CreateNumber(systemValue.distance));

            // 环境数据 (封装在 env 对象中)
            cJSON *env = cJSON_CreateObject();
            cJSON_AddItemToObject(env, "temp", cJSON_CreateNumber((int)systemValue.env_temp));
            cJSON_AddItemToObject(env, "humi", cJSON_CreateNumber((int)systemValue.env_humi));
            cJSON_AddItemToObject(env, "lux",  cJSON_CreateNumber(systemValue.env_lux));
            cJSON_AddItemToObject(env, "ps",   cJSON_CreateNumber(systemValue.env_ps));
            cJSON_AddItemToObject(env, "ir",   cJSON_CreateNumber(systemValue.env_ir));
            cJSON_AddItemToObject(env, "fan",  cJSON_CreateNumber(pcf8574_io.bit.p0));
            cJSON_AddItemToObject(env, "led",  cJSON_CreateNumber(pcf8574_io.bit.p2 == 0 ? 1 : 0));
            cJSON_AddItemToObject(env, "buzzer",  cJSON_CreateNumber(pcf8574_io.bit.p1 == 0 ? 1 : 0));

            // 农业安防传感器数据
            cJSON *agri = cJSON_CreateObject();
            cJSON_AddItemToObject(agri, "flameStatus", cJSON_CreateNumber(agricultureValue.flame_status));
            cJSON_AddItemToObject(agri, "gasStatus", cJSON_CreateNumber(agricultureValue.combustible_status));
            cJSON_AddItemToObject(agri, "co2", cJSON_CreateNumber(agricultureValue.co2));
            cJSON_AddItemToObject(agri, "tvoc", cJSON_CreateNumber(agricultureValue.tvoc));
            cJSON_AddItemToObject(agri, "gasMic", cJSON_CreateNumber(agricultureValue.gas_mic));
            cJSON_AddItemToObject(env, "agri", agri);

            // 智能光照状态
            cJSON *smartLight = cJSON_CreateObject();
            cJSON_AddItemToObject(smartLight, "mode", cJSON_CreateNumber(smartLightState.auto_mode));
            cJSON_AddItemToObject(smartLight, "brightness", cJSON_CreateNumber(smartLightState.current_brightness));
            cJSON_AddItemToObject(smartLight, "targetBrightness", cJSON_CreateNumber(smartLightState.target_brightness));
            cJSON_AddItemToObject(smartLight, "timePeriod", cJSON_CreateNumber(smartLightState.time_period));
            cJSON_AddItemToObject(smartLight, "lightLevel", cJSON_CreateNumber(smartLightState.light_level));
            cJSON_AddItemToObject(env, "smartLight", smartLight);

            // LD-STL-19P 激光雷达数据
            cJSON *lidar = cJSON_CreateObject();
            cJSON_AddItemToObject(lidar, "speed", cJSON_CreateNumber(systemValue.lidar_speed));
            cJSON_AddItemToObject(lidar, "startAngle", cJSON_CreateNumber(systemValue.lidar_start_angle));
            cJSON_AddItemToObject(lidar, "endAngle", cJSON_CreateNumber(systemValue.lidar_end_angle));
            cJSON_AddItemToObject(lidar, "timestamp", cJSON_CreateNumber(systemValue.lidar_timestamp));
            // 12个测量点
            cJSON *points = cJSON_CreateArray();
            for (int i = 0; i < LIDAR_POINT_PER_PACK; i++) {
                cJSON *pt = cJSON_CreateObject();
                cJSON_AddItemToObject(pt, "d", cJSON_CreateNumber(systemValue.lidar_points[i].distance));
                cJSON_AddItemToObject(pt, "s", cJSON_CreateNumber(systemValue.lidar_points[i].intensity));
                cJSON_AddItemToArray(points, pt);
            }
            cJSON_AddItemToObject(lidar, "points", points);
            cJSON_AddItemToObject(json_root, "lidar", lidar);

            cJSON_AddItemToObject(json_root, "env", env);

            char mode_str[10];
            if(systemValue.car_mode == CAR_MODE_MANUAL) strcpy(mode_str, "manual");
            else if(systemValue.car_mode == CAR_MODE_AVOID) strcpy(mode_str, "avoid");
            else if(systemValue.car_mode == CAR_MODE_LINE) strcpy(mode_str, "line");
            else if(systemValue.car_mode == CAR_MODE_PATH) strcpy(mode_str, "path");
            else strcpy(mode_str, "manual");
            cJSON_AddItemToObject(json_root, "carMode", cJSON_CreateString(mode_str));

            // H30 IMU 传感器数据
            cJSON *imu = cJSON_CreateObject();
            if (g_imuDataValid && g_imuData.valid) {
                cJSON_AddItemToObject(imu, "tid", cJSON_CreateNumber(g_imuData.tid));
                cJSON_AddItemToObject(imu, "temperature", cJSON_CreateNumber(g_imuData.temperature));

                cJSON *accel = cJSON_CreateObject();
                cJSON_AddItemToObject(accel, "x", cJSON_CreateNumber(g_imuData.accel_x));
                cJSON_AddItemToObject(accel, "y", cJSON_CreateNumber(g_imuData.accel_y));
                cJSON_AddItemToObject(accel, "z", cJSON_CreateNumber(g_imuData.accel_z));
                cJSON_AddItemToObject(imu, "accel", accel);

                cJSON *gyro = cJSON_CreateObject();
                cJSON_AddItemToObject(gyro, "x", cJSON_CreateNumber(g_imuData.gyro_x));
                cJSON_AddItemToObject(gyro, "y", cJSON_CreateNumber(g_imuData.gyro_y));
                cJSON_AddItemToObject(gyro, "z", cJSON_CreateNumber(g_imuData.gyro_z));
                cJSON_AddItemToObject(imu, "gyro", gyro);

                cJSON *euler = cJSON_CreateObject();
                cJSON_AddItemToObject(euler, "pitch", cJSON_CreateNumber(g_imuData.pitch));
                cJSON_AddItemToObject(euler, "roll", cJSON_CreateNumber(g_imuData.roll));
                cJSON_AddItemToObject(euler, "yaw", cJSON_CreateNumber(g_imuData.yaw));
                cJSON_AddItemToObject(imu, "euler", euler);

                cJSON *quat = cJSON_CreateObject();
                cJSON_AddItemToObject(quat, "w", cJSON_CreateNumber(g_imuData.q0));
                cJSON_AddItemToObject(quat, "x", cJSON_CreateNumber(g_imuData.q1));
                cJSON_AddItemToObject(quat, "y", cJSON_CreateNumber(g_imuData.q2));
                cJSON_AddItemToObject(quat, "z", cJSON_CreateNumber(g_imuData.q3));
                cJSON_AddItemToObject(imu, "quaternion", quat);

                cJSON_AddItemToObject(imu, "fusion_status", cJSON_CreateNumber(g_imuData.fusion_status));
            }
            cJSON_AddItemToObject(json_root, "imu", imu);
        }
        char *payload = cJSON_PrintUnformatted(json_root);

        if (payload) {
            ret = sendto(systemValue.udp_socket_fd, payload, strlen(payload), 0,
                         (struct sockaddr *)&client, sizeof(client));
            free(payload);
        }
        cJSON_Delete(json_root);
        usleep(TASK_DELAY_TIME); // 50ms
    }
    closesocket(systemValue.udp_socket_fd);
}
