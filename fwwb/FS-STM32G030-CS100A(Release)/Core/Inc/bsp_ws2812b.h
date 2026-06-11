/**
  ******************************************************************************
  * @file   bsp_ws2812b.h
  * @brief  ws2812b采用单线归0码协议的LED控制器驱动
  *          
  ******************************************************************************
  */
#ifndef __BSP_WS2812B_H__
#define __BSP_WS2812B_H__
//
#include "main.h"
//
#define	LED_NUMS	23//灯的数量
//
#define CODE1  55//1码
#define CODE0  16//0码
//
//单个LED颜色设置，即将单个灯的颜色转换成对应的0码和1码
void RGB_Set_Color(uint8_t ID,uint8_t* pColor);
void RGB_Reflash(uint8_t pREF_NUM);	//PWM_DMA发送
void RGB_BLACK(uint8_t pRGB_LEN);	//全部黑色，用于初始化将其全部熄灭
void RGB_RED(uint8_t pRGB_LEN);  	//全部红色
void RGB_GREEN(uint8_t pRGB_LEN);	//全部绿色
void RGB_BLUE(uint8_t pRGB_LEN); 	//全部蓝色
void RGB_CUSTOM(uint8_t* pColor);	//自定义色彩
//
void RGB_ID_Show(uint8_t pID,uint8_t* pColor);	//设置某个灯珠的颜色
void RGB_ID_NO_Show(uint8_t pID);//熄灭某个灯珠
void RGB_BCD_LINE_Show(uint16_t pBcd,uint8_t* pBcdColor,uint8_t pLine,uint8_t* pLineColor);	//BCD码与巡线显示
#endif /* __BSP_WS2812B_H__ */

