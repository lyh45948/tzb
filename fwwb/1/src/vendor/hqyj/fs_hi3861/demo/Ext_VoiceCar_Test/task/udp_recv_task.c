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

#include "udp_recv_task.h"
#include "udp_send_task.h"

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#include "ohos_init.h"
#include "cmsis_os2.h"
#include "hi_uart.h"

#include "sys_config.h"

#include "lwip/netifapi.h"
#include "lwip/sockets.h"
#include "lwip/api_shell.h"

#include "cJSON.h"
#include "hal_bsp_pcf8574.h"
#include "hal_bsp_aw2013.h"
#include "smart_light_task.h"

char udp_recvBuff[2048] = {0};                    // 增大缓冲区以接收完整路径
char uart_sendBuff[128] = {0};                   // 发送数据缓冲区
uint16_t L_PWM_Value = 350, R_PWM_Value = 350;   // 默认的PWM参数值
uint16_t base_pwm_speed_value = MOTOR_LOW_SPEED; // 速度倍率

void uart_send_control_status(te_car_status_t cmd)
{
    memset_s(uart_sendBuff, sizeof(uart_sendBuff), 0, sizeof(uart_sendBuff));
    switch (cmd) {
        case CAR_STATUS_ON:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff), "{\"control\":{\"power\":\"on\"}}");
            break;
        case CAR_STATUS_OFF:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff), "{\"control\":{\"power\":\"off\"}}");
            break;
        case CAR_STATUS_STOP:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff), "{\"control\":{\"turn\":\"stop\"}}");
            break;
        default:
            return;
    }
    uart_send_buff(uart_sendBuff, strlen(uart_sendBuff));
}
void uart_send_mode_cmd(te_car_mode_t mode)
{
    memset_s(uart_sendBuff, sizeof(uart_sendBuff), 0, sizeof(uart_sendBuff));
    const char *mode_str = "manual";
    uint16_t auto_speed = 500; // 默认低速档翻倍为 500
    
    // 根据当前全局档位设置自动模式的基准速度 (翻倍处理)
    if (base_pwm_speed_value == MOTOR_LOW_SPEED) auto_speed = 500;
    else if (base_pwm_speed_value == MOTOR_MIDDLE_SPEED) auto_speed = 800;
    else if (base_pwm_speed_value == MOTOR_HIGH_SPEED) auto_speed = 1100;

    switch (mode) {
        case CAR_MODE_MANUAL: mode_str = "manual"; break;
        case CAR_MODE_AVOID:  mode_str = "avoid";  break;
        case CAR_MODE_LINE:   mode_str = "line";   break;
        case CAR_MODE_PATH:   mode_str = "path";   break;
        default: return;
    }
    // 切换模式时同时下发 power:on 指令和 speed 基准值
    sprintf_s(uart_sendBuff, sizeof(uart_sendBuff), 
              "{\"control\":{\"power\":\"on\",\"mode\":\"%s\",\"speed\":%d}}", mode_str, auto_speed);
    uart_send_buff(uart_sendBuff, strlen(uart_sendBuff));
}
void uart_send_control_cmd(te_car_status_t cmd)
{
    memset_s(uart_sendBuff, sizeof(uart_sendBuff), 0, sizeof(uart_sendBuff));
    switch (cmd) {
        case CAR_STATUS_RUN:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff),
                          "{\"control\":{\"turn\":\"run\",\"pwm\":{\"L_Motor\":%d,\"R_Motor\":%d}}}",
                         base_pwm_speed_value + L_PWM_Value, base_pwm_speed_value + R_PWM_Value);
            break;
        case CAR_STATUS_BACK:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff),
                          "{\"control\":{\"turn\":\"back\",\"pwm\":{\"L_Motor\":%d,\"R_Motor\":%d}}}",
                          base_pwm_speed_value + L_PWM_Value, base_pwm_speed_value + R_PWM_Value);
            break;
        case CAR_STATUS_LEFT:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff),
                          "{\"control\":{\"turn\":\"left\",\"pwm\":{\"L_Motor\":%d,\"R_Motor\":%d}}}",
                         base_pwm_speed_value + L_PWM_Value, base_pwm_speed_value + R_PWM_Value);
            break;
        case CAR_STATUS_RIGHT:
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff),
                          "{\"control\":{\"turn\":\"right\",\"pwm\":{\"L_Motor\":%d,\"R_Motor\":%d}}}",
                          base_pwm_speed_value + L_PWM_Value, base_pwm_speed_value + R_PWM_Value);
            break;
        default:
            return;
    }
    uart_send_buff(uart_sendBuff, strlen(uart_sendBuff));
}

static void parse_json_data(const char *payload)
{
    /* 解析JSON数据 */
    cJSON *root = cJSON_Parse(udp_recvBuff);
    if (root) {
        cJSON *json_carSpeed = cJSON_GetObjectItem(root, "carSpeed");
        if (json_carSpeed != NULL) {
            printf("carSpeed: %s\r\n", json_carSpeed->valuestring);
            if (!strcmp(json_carSpeed->valuestring, "low")) {
                systemValue.car_status = CAR_STATUS_L_SPEED;
                base_pwm_speed_value = MOTOR_LOW_SPEED;
            } else if (!strcmp(json_carSpeed->valuestring, "middle")) {
                systemValue.car_status = CAR_STATUS_M_SPEED;
                base_pwm_speed_value = MOTOR_MIDDLE_SPEED;
            } else if (!strcmp(json_carSpeed->valuestring, "high")) {
                systemValue.car_status = CAR_STATUS_H_SPEED;
                base_pwm_speed_value = MOTOR_HIGH_SPEED;
            }
            // 档位改变后，立即同步速度给底座（无论手动还是自动模式）
            uart_send_mode_cmd(systemValue.car_mode);
            json_carSpeed = NULL;
        }
        cJSON *json_autoMode = cJSON_GetObjectItem(root, "autoMode");
        if (json_autoMode != NULL) {
            systemValue.auto_abstacle_flag = json_autoMode->valueint;
            if (systemValue.auto_abstacle_flag) {
                systemValue.car_mode = CAR_MODE_AVOID;
                uart_send_mode_cmd(CAR_MODE_AVOID);
            } else {
                systemValue.car_mode = CAR_MODE_MANUAL;
                uart_send_mode_cmd(CAR_MODE_MANUAL);
            }
        }
        cJSON *json_carMode = cJSON_GetObjectItem(root, "carMode");
        if (json_carMode != NULL) {
            // 只要切换模式，默认开启电机逻辑状态 (逻辑移入 uart_send_mode_cmd)
            systemValue.car_status = CAR_STATUS_ON;

            if (!strcmp(json_carMode->valuestring, "manual")) {
                systemValue.car_mode = CAR_MODE_MANUAL;
                systemValue.auto_abstacle_flag = 0;
                uart_send_mode_cmd(CAR_MODE_MANUAL);
            } else if (!strcmp(json_carMode->valuestring, "avoid")) {
                systemValue.car_mode = CAR_MODE_AVOID;
                systemValue.auto_abstacle_flag = 1;
                uart_send_mode_cmd(CAR_MODE_AVOID);
            } else if (!strcmp(json_carMode->valuestring, "line")) {
                systemValue.car_mode = CAR_MODE_LINE;
                systemValue.auto_abstacle_flag = 0;
                uart_send_mode_cmd(CAR_MODE_LINE);
            } else if (!strcmp(json_carMode->valuestring, "path")) {
                systemValue.car_mode = CAR_MODE_PATH;
                systemValue.auto_abstacle_flag = 0;
                
                // 1. 先发送切换模式指令，不带 d/a 参数，通知 STM32 清除旧队列
                uart_send_mode_cmd(CAR_MODE_PATH);
                osDelay(100); // 给 STM32 充足的清除时间
                
                // 2. 处理路径数据并逐个发送
                cJSON *json_path = cJSON_GetObjectItem(root, "path");
                if (json_path != NULL && cJSON_IsArray(json_path)) {
                    int path_size = cJSON_GetArraySize(json_path);
                    // 限制最大发送 50 个点，防止溢出
                    int send_limit = (path_size > 50) ? 50 : path_size;
                    
                    for (int i = 0; i < send_limit; i++) {
                        cJSON *item = cJSON_GetArrayItem(json_path, i);
                        cJSON *d = cJSON_GetObjectItem(item, "d");
                        cJSON *a = cJSON_GetObjectItem(item, "a");
                        if (d && a) {
                            memset_s(uart_sendBuff, sizeof(uart_sendBuff), 0, sizeof(uart_sendBuff));
                            // 发送路径点指令：{"control":{"mode":"path","d":100,"a":90}}
                            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff), 
                                      "{\"control\":{\"mode\":\"path\",\"d\":%d,\"a\":%d}}", d->valueint, a->valueint);
                            uart_send_buff(uart_sendBuff, strlen(uart_sendBuff));
                            osDelay(60); // 增加一点延迟，确保 STM32 串口 DMA 不会丢包
                        }
                    }
                }
            }
        }
        cJSON *json_carStatus = cJSON_GetObjectItem(root, "carStatus");
        if (json_carStatus != NULL) {
            if (!strcmp(json_carStatus->valuestring, "on")) {
                systemValue.car_status = CAR_STATUS_ON;
                uart_send_control_status(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            } else if (!strcmp(json_carStatus->valuestring, "off")) {
                systemValue.car_status = CAR_STATUS_OFF;
                uart_send_control_status(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            } else if (!strcmp(json_carStatus->valuestring, "stop")) {
                systemValue.car_status = CAR_STATUS_STOP;
                uart_send_control_status(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            } else if (!strcmp(json_carStatus->valuestring, "run")) {
                systemValue.car_status = CAR_STATUS_RUN;
                uart_send_control_cmd(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            } else if (!strcmp(json_carStatus->valuestring, "back")) {
                systemValue.car_status = CAR_STATUS_BACK;
                uart_send_control_cmd(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            } else if (!strcmp(json_carStatus->valuestring, "left")) {
                systemValue.car_status = CAR_STATUS_LEFT;
                uart_send_control_cmd(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            } else if (!strcmp(json_carStatus->valuestring, "right")) {
                systemValue.car_status = CAR_STATUS_RIGHT;
                uart_send_control_cmd(systemValue.car_status);
                g_lastManualTick = osKernelGetTickCount();
            }
            json_carStatus = NULL;
        }

        cJSON *json_joyX = cJSON_GetObjectItem(root, "joyX");
        cJSON *json_joyY = cJSON_GetObjectItem(root, "joyY");
        if (json_joyX != NULL && json_joyY != NULL) {
            memset_s(uart_sendBuff, sizeof(uart_sendBuff), 0, sizeof(uart_sendBuff));
            sprintf_s(uart_sendBuff, sizeof(uart_sendBuff), 
                      "{\"control\":{\"joyX\":%d,\"joyY\":%d}}", json_joyX->valueint, json_joyY->valueint);
            uart_send_buff(uart_sendBuff, strlen(uart_sendBuff));
            g_lastManualTick = osKernelGetTickCount();
        }

        // --- 新增：环境外设控制 ---
        cJSON *json_fan = cJSON_GetObjectItem(root, "fan");
        if (json_fan != NULL) {
            set_fan(json_fan->valueint ? true : false);
        }

        cJSON *json_led = cJSON_GetObjectItem(root, "led");
        if (json_led != NULL) {
            set_led(json_led->valueint ? true : false);
        }

        cJSON *json_buzzer = cJSON_GetObjectItem(root, "buzzer");
        if (json_buzzer != NULL) {
            set_buzzer(json_buzzer->valueint ? true : false);
        }

        cJSON *json_rgb = cJSON_GetObjectItem(root, "rgb");
        if (json_rgb != NULL) {
            cJSON *r = cJSON_GetObjectItem(json_rgb, "r");
            cJSON *g = cJSON_GetObjectItem(json_rgb, "g");
            cJSON *b = cJSON_GetObjectItem(json_rgb, "b");
            if (r && g && b) {
                printf("[UDP_RGB]: R=%d, G=%d, B=%d\n", r->valueint, g->valueint, b->valueint);
                // 使用智能光照模块设置RGB颜色（保存颜色，智能光照只调节亮度）
                smart_light_set_rgb((uint8_t)r->valueint, (uint8_t)g->valueint, (uint8_t)b->valueint);
            }
        }

        // --- 新增：智能光照控制 ---
        cJSON *json_smartLight = cJSON_GetObjectItem(root, "smartLight");
        if (json_smartLight != NULL) {
            cJSON *mode = cJSON_GetObjectItem(json_smartLight, "mode");
            cJSON *brightness = cJSON_GetObjectItem(json_smartLight, "brightness");

            int is_auto_mode = -1;  // -1 = 未设置, 0 = manual, 1 = auto

            // 解析模式
            if (mode != NULL) {
                if (!strcmp(mode->valuestring, "auto")) {
                    is_auto_mode = 1;
                    printf("[UDP_SmartLight]: Mode=AUTO\n");
                } else if (!strcmp(mode->valuestring, "manual")) {
                    is_auto_mode = 0;
                    printf("[UDP_SmartLight]: Mode=MANUAL\n");
                }
            }

            // 设置亮度（仅在手动模式下生效，自动模式亮度由算法计算）
            // 注意：smart_light_set_brightness 会自动切换到手动模式，所以要先判断
            if (brightness != NULL && is_auto_mode != 1) {
                uint8_t val = (uint8_t)brightness->valueint;
                if (val > 100) val = 100;
                smart_light_set_brightness(val);
            }

            // 最后设置模式（在亮度之后），确保模式不会被覆盖
            if (is_auto_mode == 1) {
                smart_light_set_mode(1);
            } else if (is_auto_mode == 0) {
                smart_light_set_mode(0);
            }
        }
    }
    cJSON_Delete(root);
    root = NULL;
}
void udp_recv_task(void)
{
   
    socklen_t len = sizeof(client);
    while (1) {
        if (recvfrom(systemValue.udp_socket_fd, udp_recvBuff, sizeof(udp_recvBuff) - 1,
                     0, (struct sockaddr *)&client, &len) > 0) {
            // 读成功
            printf("udp recv data is \" %s \".\r\n", udp_recvBuff);
            parse_json_data((const char *)udp_recvBuff);
            memset_s(udp_recvBuff, sizeof(udp_recvBuff), 0, sizeof(udp_recvBuff));
        }
        else
        {
            return;
        }
    }
    closesocket(systemValue.udp_socket_fd);
}
