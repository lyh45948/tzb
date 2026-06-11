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

#include "cmsis_os2.h"
#include "sys_config.h"
#include "udp_recv_task.h"

// 仅声明在 udp_recv_task.c 中实现的控制发送函数
void uart_send_control_cmd(te_car_status_t cmd);

void auto_avoid_task(void *arg)
{
    UNUSED(arg);
    for (;;) {
        if (systemValue.auto_abstacle_flag && systemValue.car_status != CAR_STATUS_OFF) {
            uint32_t now = osKernelGetTickCount();
            if ((now - g_lastManualTick) > MANUAL_OVERRIDE_MS) {
                if (systemValue.distance <= MIN_DISTANCE_VOL) {
                    uart_send_control_cmd(CAR_STATUS_BACK);
                    osDelay(30);
                    uart_send_control_cmd(g_turnToggle ? CAR_STATUS_LEFT : CAR_STATUS_RIGHT);
                    g_turnToggle ^= 1;
                    osDelay(30);
                } else {
                    uart_send_control_cmd(CAR_STATUS_RUN);
                }
            }
        }
        osDelay(AUTO_LOOP_PERIOD_MS);
    }
}


