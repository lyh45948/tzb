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

#include "uart_recv_task.h"
#include "sys_config.h"
#include "hi_uart.h"
#include "hi_io.h"
#include "hi_gpio.h"
#include "stdbool.h"

#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#include "cmsis_os2.h"
#include "cJSON.h"

hi_u8 recvBuff[200] = {0};
hi_u8 *pbuff = recvBuff;

void uart_send_buff(unsigned char *str, unsigned short len)
{
    hi_u32 ret = 0;
    ret = hi_uart_write(HI_UART_IDX_2, (uint8_t *)str, len);
    if (ret == HI_ERR_FAILURE)
    {
        printf("uart send buff is failed.\r\n");
    }
}

/**
 * @brief  解析JSON数据包
 * @note
 * @param  *pstr:
 * @retval None
 */
static void parse_json_data(uint8_t *pstr)
{
    printf("[UART_RECV_RAW]: %s\r\n", pstr); // 打印原始接收包用于调试
    cJSON *json_root = cJSON_Parse((const char *)pstr);
    if (json_root)
    {
        cJSON *json_status = cJSON_GetObjectItem(json_root, "status");
        if (json_status)
        {
            cJSON *json_distance = cJSON_GetObjectItem(json_status, "dist");
            if (json_distance) systemValue.distance = json_distance->valueint;

            cJSON *json_carPower = cJSON_GetObjectItem(json_status, "volt");
            if (json_carPower) systemValue.battery_voltage = json_carPower->valueint;

            cJSON *json_L_speed = cJSON_GetObjectItem(json_status, "L_spd");
            if (json_L_speed) systemValue.left_motor_speed = json_L_speed->valueint;

            cJSON *json_R_speed = cJSON_GetObjectItem(json_status, "R_spd");
            if (json_R_speed) systemValue.right_motor_speed = json_R_speed->valueint;
            
            printf("[UART_PARSED]: L:%d R:%d V:%d D:%d\r\n", 
                   systemValue.left_motor_speed, systemValue.right_motor_speed,
                   systemValue.battery_voltage, systemValue.distance);

            cJSON *json_carMode = cJSON_GetObjectItem(json_status, "mode");
            if (json_carMode)
            {
                if (!strcmp(json_carMode->valuestring, "manual")) systemValue.car_mode = CAR_MODE_MANUAL;
                else if (!strcmp(json_carMode->valuestring, "avoid")) systemValue.car_mode = CAR_MODE_AVOID;
                else if (!strcmp(json_carMode->valuestring, "line")) systemValue.car_mode = CAR_MODE_LINE;
                else if (!strcmp(json_carMode->valuestring, "path")) systemValue.car_mode = CAR_MODE_PATH;
            }
        }
    }
    cJSON_Delete(json_root);
}
// 辅助函数：发送预设路径点
static void send_preset_path(const int *d_list, const int *a_list, int count)
{
    // 1. 发送切换模式指令，通知 STM32 清除旧队列
    uart_send_mode_cmd(CAR_MODE_PATH);
    osDelay(100); 

    // 2. 逐个发送预设点
    for (int i = 0; i < count; i++) {
        char path_point[64];
        sprintf_s(path_point, sizeof(path_point), 
                  "{\"control\":{\"mode\":\"path\",\"d\":%d,\"a\":%d}}", d_list[i], a_list[i]);
        uart_send_buff(path_point, strlen(path_point));
        osDelay(60); 
    }
}

// 解析语音模块包 (V2.0 重构)
void voice_control_data(uint8_t *pstr)
{
    float temperature = 0, humidity = 0;
    char reply[6] = {0xAA, 0X55, 0X00, 0X00, 0x55, 0xAA};
    uint8_t cmd_code = pstr[0];

    printf("[VOICE_RECV]: 0x%02X\n", cmd_code);

    switch (cmd_code)
    {
    // --- 电源控制 ---
    case 0x10: // 开启电机
        uart_send_control_status(CAR_STATUS_ON);
        systemValue.car_status = CAR_STATUS_ON;
        break;
    case 0x11: // 关闭电机
        uart_send_control_status(CAR_STATUS_OFF);
        systemValue.car_status = CAR_STATUS_OFF;
        break;

    // --- 运动控制 ---
    case 0x20: // 前进
        systemValue.car_mode = CAR_MODE_MANUAL;
        uart_send_control_cmd(CAR_STATUS_RUN);
        systemValue.car_status = CAR_STATUS_RUN;
        break;
    case 0x21: // 后退
        systemValue.car_mode = CAR_MODE_MANUAL;
        uart_send_control_cmd(CAR_STATUS_BACK);
        systemValue.car_status = CAR_STATUS_BACK;
        break;
    case 0x22: // 左转
        systemValue.car_mode = CAR_MODE_MANUAL;
        uart_send_control_cmd(CAR_STATUS_LEFT);
        systemValue.car_status = CAR_STATUS_LEFT;
        break;
    case 0x23: // 右转
        systemValue.car_mode = CAR_MODE_MANUAL;
        uart_send_control_cmd(CAR_STATUS_RIGHT);
        systemValue.car_status = CAR_STATUS_RIGHT;
        break;
    case 0x24: // 停止 (强力打断避障、巡线及所有自动任务)
        systemValue.car_mode = CAR_MODE_MANUAL;
        systemValue.auto_abstacle_flag = 0;
        // 先发送模式切换确保底座状态机复位，清空路径队列
        uart_send_mode_cmd(CAR_MODE_MANUAL);
        osDelay(20); 
        // 下发紧急停止指令
        uart_send_control_status(CAR_STATUS_STOP);
        systemValue.car_status = CAR_STATUS_STOP;
        break;

    // --- 智能模式 ---
    case 0x30: // 开启避障
        systemValue.auto_abstacle_flag = 1;
        uart_send_mode_cmd(CAR_MODE_AVOID);
        systemValue.car_mode = CAR_MODE_AVOID;
        break;
    case 0x31: // 开启巡线
        systemValue.auto_abstacle_flag = 0;
        uart_send_mode_cmd(CAR_MODE_LINE);
        systemValue.car_mode = CAR_MODE_LINE;
        break;

    // --- 预设路径 (正方形/三角形) ---
    case 0x40: { // 走正方形 (每边300mm，转90度)
        static const int sq_d[] = {300, 300, 300, 300};
        static const int sq_a[] = {90, 90, 90, 90};
        send_preset_path(sq_d, sq_a, 4);
        break;
    }
    case 0x41: { // 走三角形 (每边350mm，转120度)
        static const int tr_d[] = {350, 350, 350};
        static const int tr_a[] = {120, 120, 120};
        send_preset_path(tr_d, tr_a, 3);
        break;
    }

    // --- 外设控制 ---
    case 0x50: 
        set_fan(true); 
        break;
    case 0x51: 
        set_fan(false); 
        break;

    // --- 环境查询 ---
    case 0x60: 
        SHT20_ReadData(&temperature, &humidity);
        
        // 1. 发送温度包 (消息编号 0x01)
        // 格式: AA 55 [消息编号] [数据值] 55 AA
        char temp_reply[6] = {0xAA, 0x55, 0x01, 0x00, 0x55, 0xAA};
        temp_reply[3] = (int)temperature; 
        hi_uart_write(HI_UART_IDX_1, (uint8_t *)temp_reply, 6);
        
        osDelay(20); // 短暂延迟防止消息堆叠

        // 2. 发送湿度包 (消息编号 0x02)
        char humi_reply[6] = {0xAA, 0x55, 0x02, 0x00, 0x55, 0xAA};
        humi_reply[3] = (int)humidity;
        hi_uart_write(HI_UART_IDX_1, (uint8_t *)humi_reply, 6);
        break;

    default:
        printf("[VOICE_ERR]: Unknown cmd 0x%02X\n", cmd_code);
        break;
    }
    memset_s((char *)pstr, 20, 0, 20); // 清理缓冲区
}

void uart2_recv_task(void)
{
    hi_u8 uart_buff[1] = {0};
    int brace_count = 0;
    uint16_t idx = 0;
    bool start_flag = false;
    uint32_t last_recv_tick = 0;

    while (1)
    {
        hi_u32 len = hi_uart_read(HI_UART_IDX_2, uart_buff, 1);
        if (len > 0)
        {
            last_recv_tick = osKernelGetTickCount(); // 记录活跃时间
            if (uart_buff[0] == '{')
            {
                if (brace_count == 0)
                {
                    start_flag = true;
                    idx = 0;
                    memset_s(recvBuff, sizeof(recvBuff), 0, sizeof(recvBuff));
                }
                brace_count++;
            }
            
            if (start_flag)
            {
                if (idx < sizeof(recvBuff) - 1)
                {
                    recvBuff[idx++] = uart_buff[0];
                }
                else
                {
                    // 缓冲区溢出保护
                    start_flag = false;
                    brace_count = 0;
                    idx = 0;
                }

                if (uart_buff[0] == '}')
                {
                    brace_count--;
                    if (brace_count <= 0) 
                    {
                        start_flag = false;
                        brace_count = 0;
                        recvBuff[idx] = '\0';
                        parse_json_data(recvBuff);
                    }
                }
            }
        }
        else
        {
            // 超时自愈：如果进入了接收状态但超过 50ms 没收到结束符，强制重置状态机
            // (底座发送频率为 200ms，50ms 足够接收一个完整包)
            if (start_flag && (osKernelGetTickCount() - last_recv_tick > 50)) 
            {
                start_flag = false;
                brace_count = 0;
                idx = 0;
            }
            osDelay(1);
        }
    }
}

void uart1_recv_task(void)
{
    hi_u8 voice_buff[20] = {0};
    while (1)
    {
        
        // 阻塞接收串口1
        if (memset_s((char *)voice_buff, sizeof(voice_buff), 0, sizeof(voice_buff)) == 0)
        {
            hi_u32 len = hi_uart_read(HI_UART_IDX_1, voice_buff, sizeof(voice_buff));
            printf("voice_buff:%s\n", voice_buff);
            if (len > 0)
            {
                printf("voice_buff:%s\n", voice_buff);
                voice_control_data(voice_buff);
                memset_s((char *)voice_buff, sizeof(voice_buff), 0, sizeof(voice_buff));
            }
        }
    }
}