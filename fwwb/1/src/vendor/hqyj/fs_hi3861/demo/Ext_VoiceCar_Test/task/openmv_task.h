/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * WT OpenMV 视觉结果读取任务
 */

#ifndef OPENMV_TASK_H
#define OPENMV_TASK_H

#include <stdint.h>

#define OPENMV_TASK_PERIOD_MS  100

extern uint8_t g_openmvDataValid;

void openmv_task(void);

#endif // OPENMV_TASK_H
