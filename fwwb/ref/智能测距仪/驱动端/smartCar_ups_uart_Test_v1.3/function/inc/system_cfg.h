#ifndef __SYSTEM_CFG_H__
#define __SYSTEM_CFG_H__

#include <stdio.h>
#include "main.h"

typedef signed char s8;
typedef signed short s16;
typedef signed int s32;

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

/******************** 调试打印信息设置 ************************/
#define DEBUG_O
#ifdef DEBUG_ON
#define console_log_error(fmt, args...) printf("[error][%d][%s]==> " fmt " \r\n", __LINE__, __FUNCTION__, ##args)
#define console_log_success(fmt, args...) printf("[ok   ][%d][%s]==> " fmt " \r\n", __LINE__, __FUNCTION__, ##args)
#define console_log_info(fmt, args...) printf("[info ][%d][%s]==> " fmt " \r\n", __LINE__, __FUNCTION__, ##args)
#else
#define console_log_error(fmt, args...) \
	do                                    \
	{                                     \
	} while (0)
#define console_log_success(fmt, args...) \
	do                                      \
	{                                       \
	} while (0)
#define console_log_info(fmt, args...) \
	do                                   \
	{                                    \
	} while (0)
#endif


typedef enum
{
	L_MOTOR = 0x01, // 左电机
	R_MOTOR,				// 右电机
} te_L_R_Motor_t;
// 小车的当前状态值
typedef enum
{
	CAR_STATUS_RUN = 0x01, // 前进
	CAR_STATUS_BACK,			 // 后退
	CAR_STATUS_LEFT,			 // 左转
	CAR_STATUS_RIGHT,			 // 右转
	CAR_STATUS_STOP,			 // 右转
	CAR_STATUS_ON,				 // 开启电机
	CAR_STATUS_OFF,				 // 关闭电机
} te_car_status_t;

typedef struct {
	te_car_status_t car_status;			// 小车的状态

	uint16_t distance;		// 距离传感器的采集值
	uint16_t battery;		// 电池电压值
	uint16_t L_enc;		// 小车左轮速度
	uint16_t R_enc;		// 小车右轮速度
} ts_SystemValue_t;

extern ts_SystemValue_t systemValue;	

#endif
