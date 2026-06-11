#ifndef __SYS_CONFIG_H
#define __SYS_CONFIG_H

#include "cmsis_os2.h"
#include "hal_bsp_structAll.h"

#define event1_Flags 0x00000001U  // 事件掩码 每一位代表一个事件

typedef struct
{
  int top;  // 上边距
  int left; // 下边距
} margin_t;     // 边距类型

typedef struct message_data
{
  unsigned short distance;   // 距离传感器的值
  tn_pcf8574_io_t pcf8574_io;
}msg_data_t;

#endif

