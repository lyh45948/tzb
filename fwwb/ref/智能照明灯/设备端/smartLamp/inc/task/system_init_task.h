#ifndef __SYSTEM_INIT_TASK_H
#define __SYSTEM_INIT_TASK_H


#include "cmsis_os2.h"

extern osThreadId_t system_Init_Task_ID;  // 任务ID


void system_Init_Task(void *argument);


#endif

