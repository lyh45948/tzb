/**
  ******************************************************************************
  * @file   user_app.h
  * @brief  用户应用程序部分的代码
  * 
  ******************************************************************************
  */
#ifndef __USER_APP_H__
#define __USER_APP_H__
//
#include "stdio.h"	//串口实现Printf打印输出
#include "bsp_ws2812b.h"	//ws2812b驱动
//定时器/PWM
#include "tim.h"
//串口
#include "usart.h"
//A/D通道数据寄存器，ADC data register (ADC_DR)
typedef struct
{
  uint16_t ADC_IN0; //通道IN0         
  uint16_t ADC_IN1; //通道IN1 
  uint16_t ADC_IN4; //通道IN4    
  uint16_t ADC_IN5; //通道IN5    
  uint16_t ADC_IN6; //通道IN6    
  uint16_t ADC_IN15; //通道IN15 
  uint16_t ADC_IN16; //通道IN16  
} ADC_ValTypeDef;
//定时器3的的输入捕获
typedef struct
{
  uint8_t TIM3_CH2_Edge; //通道2的边沿捕获
  uint8_t TIM3_CH2_OVER; //计数器溢出的个数
  uint16_t TIM3_CH2_VAL; //储存计数器的记录值
	uint32_t Distance;	//距离值
} TIM_ValTypeDef;
//系统数据更新与控制任务
enum{
	eTask_Idle	= 0,			/* 空闲任务 */		
	eTask_Phototube = 1,	/* 光电管检测 */		
	eTask_Ultrasonic = 2,			/* 超声波测距 */	
	eTask_SerialOut  = 3,			/* 串口输出 */		
	eTask_TurnSignal = 4,			/* 转向灯任务 */
};
//任务状态标值
typedef struct
{
	uint32_t ADCC:1;					//ADC转换完成
	uint32_t UART2_Ready:1;   //UART2速度数据就绪
	uint32_t   :30;
}gTask_BitDef;

// Retrieve year info
#define OS_YEAR     ((((__DATE__ [7] - '0') * 10 + (__DATE__ [8] - '0')) * 10 \
                                    + (__DATE__ [9] - '0')) * 10 + (__DATE__ [10] - '0'))

// Retrieve month info
#define OS_MONTH    (__DATE__ [2] == 'n' ? (__DATE__ [1] == 'a' ? 1 : 6) \
                                : __DATE__ [2] == 'b' ? 2 \
                                : __DATE__ [2] == 'r' ? (__DATE__ [0] == 'M' ? 3 : 4) \
                                : __DATE__ [2] == 'y' ? 5 \
                                : __DATE__ [2] == 'l' ? 7 \
                                : __DATE__ [2] == 'g' ? 8 \
                                : __DATE__ [2] == 'p' ? 9 \
                                : __DATE__ [2] == 't' ? 10 \
                                : __DATE__ [2] == 'v' ? 11 : 12)

// Retrieve day info
#define OS_DAY      ((__DATE__ [4] == ' ' ? 0 : __DATE__ [4] - '0') * 10 \
                                + (__DATE__ [5] - '0'))

// Retrieve hour info
#define OS_HOUR     ((__TIME__ [0] - '0') * 10 + (__TIME__ [1] - '0'))

// Retrieve minute info
#define OS_MINUTE   ((__TIME__ [3] - '0') * 10 + (__TIME__ [4] - '0'))

// Retrieve second info
#define OS_SECOND   ((__TIME__ [6] - '0') * 10 + (__TIME__ [7] - '0'))
//
#define VREFINT_CAL ((uint16_t*) ((uint32_t) 0x1FFF75AA)) //内部参考电压源纠正值
#define TS_CAL1 		((uint16_t*) ((uint32_t) 0x1FFF75A8)) //内部温度纠正值
//
#define RTC_BKP0RL_VAULE			0x1A1B

//测距触发与指示
#define CS100A_TRIG_ENABLE()				HAL_GPIO_WritePin(TRIG_GPIO_Port, TRIG_Pin, GPIO_PIN_SET)		 				/* 拉高超声波测距触发引脚 */
#define CS100A_TRIG_DISABLE()	  		HAL_GPIO_WritePin(TRIG_GPIO_Port, TRIG_Pin, GPIO_PIN_RESET)					/* 拉低超声波测距触发引脚 */
//
void IDLE_Task(void);		//空闲任务
//定义的系统任务数量
#define OS_TASKLISTCNT	5  
extern void (* g_OSTaskList[OS_TASKLISTCNT])(void);
void IDLE_Task(void);	//空闲任务
void Ultrasonic_Task(void);	//测距任务
void Phototube_Task(void);	//巡线任务
void SerialOut_Task(void);	//串口2任务
void TurnSignal_Task(void); //转向灯任务
#endif /* __USER_APP_H__ */

