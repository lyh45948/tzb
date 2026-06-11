#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include "ohos_init.h"
#include "cmsis_os2.h"

#include "system_init_task.h"
#include "hal_bsp_log.h"

static void smartLamp_main(void)
{
  // 创建系统初始化任务
  osThreadAttr_t options;
  options.name = "system_Init_Task";
  options.attr_bits = 0;
  options.cb_mem = NULL;
  options.cb_size = 0;
  options.stack_mem = NULL;
  options.stack_size = 1024*5;
  options.priority = osPriorityNormal;
  system_Init_Task_ID = osThreadNew((osThreadFunc_t)system_Init_Task, NULL, &options);
  if (system_Init_Task_ID != NULL) {
    console_log_info("ID = %d, Create mqtt_send_task_id is OK!", system_Init_Task_ID);
  }

}
SYS_RUN(smartLamp_main);