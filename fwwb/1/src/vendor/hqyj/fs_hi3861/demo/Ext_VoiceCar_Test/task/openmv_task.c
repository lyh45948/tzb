/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * WT OpenMV 视觉结果读取任务
 */

#include "openmv_task.h"
#include "sys_config.h"
#include "hal_bsp_openmv.h"
#include <stdio.h>
#include <unistd.h>

uint8_t g_openmvDataValid = 0;

void openmv_task(void)
{
    uint16_t failCount = 0;
    uint16_t lastFrame = 0;

    printf("[OpenMV] openmv_task started\r\n");

    while (1) {
        openmv_vision_t vision = {0};
        int ret = OpenMV_ReadResult(&vision);
        if (ret == OPENMV_PARSE_OK && vision.valid) {
            systemValue.vision = vision;
            g_openmvDataValid = 1;
            failCount = 0;

            if (vision.frame_counter != lastFrame) {
                lastFrame = vision.frame_counter;
                printf("[OpenMV] frame=%d obstacles=%d counter=%s\r\n",
                       vision.frame_counter, vision.obstacle_count, vision.counter_digits);
            }
        } else {
            g_openmvDataValid = 0;
            systemValue.vision.valid = 0;
            failCount++;
            if ((failCount % 50) == 1) {
                if (ret == OPENMV_SPI_ERROR) {
                    printf("[OpenMV] SPI read error\r\n");
                } else {
                    printf("[OpenMV] invalid result frame\r\n");
                }
            }
        }

        usleep(OPENMV_TASK_PERIOD_MS * 1000);
    }
}
