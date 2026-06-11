/**
  ******************************************************************************
  * @file   bsp_ws2812b.c
  * @brief  ws2812b采用单线归0码协议的LED控制器驱动
  *   
  ******************************************************************************
  */
#include "bsp_ws2812b.h"	
#include "tim.h"
//
uint8_t BLACK[3] = {0,0,0};
uint8_t RED[3]   = {20,0,0};
uint8_t GREEN[3] = {0,20,0};
uint8_t BLUE[3]  = {0,0,20};
uint8_t WHITE[3] = {20,20,20};
uint8_t YELLOW[3] = {20,20,0};;
uint32_t LED_BUFFER[24* (LED_NUMS + 3)];
//定时器1的句柄
extern TIM_HandleTypeDef htim1;
/***********************************************************************
* @fun     :RGB_Set_Color
* @brief   :单个LED颜色设置，即将单个灯的颜色转换成对应的0码和1码
* @param   :ID:灯珠的ID号，pColor指向GRB颜色值的指针
* @return  :None
***********************************************************************/
void RGB_Set_Color(uint8_t pID,uint8_t* pColor)
{
    uint16_t pI=0;
		//根据数据位设置输出占空比
    for(pI = 0; pI < 8; pI++) { //green
        LED_BUFFER[pID*24+pI] = ((pColor[1] << pI) & 0x80) ? CODE1 : CODE0;
    }
    for(pI = 0; pI < 8; pI++) { //red
        LED_BUFFER[pID*24+8+pI] = ((pColor[0] << pI) & 0x80) ? CODE1 : CODE0;
    }
    for(pI = 0; pI < 8; pI++) { //blue
        LED_BUFFER[pID*24+16+pI] = ((pColor[2] << pI) & 0x80) ? CODE1 : CODE0;
    }
}
/***********************************************************************
* @fun     :RGB_Reflash
* @brief   :PWM外设的DMA发送函数
* @param   :pREF_NUM:灯珠的数量
* @return  :None
***********************************************************************/
void RGB_Reflash(uint8_t pREF_NUM)
{
    HAL_TIM_PWM_Start_DMA(&htim1, TIM_CHANNEL_1,	LED_BUFFER, 24 * (pREF_NUM + 3));
}
/***********************************************************************
* @fun     :RGB_BLACK
* @brief   :设置灯珠熄灭，用于初始化将其所有灯珠
* @param   :RGB_LEN:灯珠的数量
* @return  :None
***********************************************************************/
void RGB_BLACK(uint8_t pRGB_LEN)
{
	  uint16_t pI = 0;
		//设置颜色
    for(pI = 0; pI < pRGB_LEN; pI++)
    {
        RGB_Set_Color(pI,BLACK);   
    }
		//刷新输出
		RGB_Reflash(pRGB_LEN);
}
/***********************************************************************
* @fun     :RGB_RED
* @brief   :设置灯珠红色
* @param   :RGB_LEN:灯珠的数量
* @return  :None
***********************************************************************/
void RGB_RED(uint8_t pRGB_LEN)
{
		uint16_t pI = 0;
		//设置颜色
    for(pI = 0; pI < pRGB_LEN; pI++)
    {
        RGB_Set_Color(pI,RED);
    }
		//刷新输出
		RGB_Reflash(pRGB_LEN);
}
/***********************************************************************
* @fun     :RGB_GREEN
* @brief   :设置灯珠绿色
* @param   :RGB_LEN:灯珠的数量
* @return  :None
***********************************************************************/
void RGB_GREEN(uint8_t pRGB_LEN)
{
		uint16_t pI = 0;
		//设置颜色
    for(pI = 0; pI < pRGB_LEN; pI++)
    {
        RGB_Set_Color(pI,GREEN);
    }
		//刷新输出
		RGB_Reflash(pRGB_LEN);
}
/***********************************************************************
* @fun     :RGB_BLUE
* @brief   :设置灯珠蓝色
* @param   :RGB_LEN:灯珠的数量
* @return  :None
***********************************************************************/
void RGB_BLUE(uint8_t pRGB_LEN)
{
		uint16_t pI = 0;
		//设置颜色
    for(pI = 0; pI < pRGB_LEN; pI++)
    {
        RGB_Set_Color(pI,BLUE);
    }
		//刷新输出
		RGB_Reflash(pRGB_LEN);
}
/***********************************************************************
* @fun     :RGB_CUSTOM
* @brief   :设置自定义色彩
* @param   :pColor:全部灯珠的色彩
* @return  :None
***********************************************************************/
void RGB_CUSTOM(uint8_t* pColor)
{
		uint16_t pI = 0;
		//设置颜色
    for(pI = 0; pI < LED_NUMS; pI++)
    {
        RGB_Set_Color(pI,pColor);
    }
		//刷新输出
		RGB_Reflash(LED_NUMS);
}
/***********************************************************************
* @fun     :RGB_ID_Show
* @brief   :根据ID号熄灭灯珠设置灯珠点亮
* @param   :pID:灯珠ID   pColor：灯珠的颜色
* @return  :None
***********************************************************************/
void RGB_ID_Show(uint8_t pID,uint8_t* pColor)
{
	  uint16_t pI = 0;
		//参数值约束
	  if(pID > 22) return;
		//
    for(pI = 0; pI < 8; pI++) { //green
        LED_BUFFER[pID*24+pI] = ((pColor[1] << pI) & 0x80) ? CODE1 : CODE0;
    }
    for(pI = 0; pI < 8; pI++) { //red
        LED_BUFFER[pID*24+8+pI] = ((pColor[0] << pI) & 0x80) ? CODE1 : CODE0;
    }
    for(pI = 0; pI < 8; pI++) { //blue
        LED_BUFFER[pID*24+16+pI] = ((pColor[2] << pI) & 0x80) ? CODE1 : CODE0;
    }
		//刷新全部灯珠数据
		RGB_Reflash(LED_NUMS);
}
/***********************************************************************
* @fun     :RGB_ID_NO_Show
* @brief   :根据ID号熄灭灯珠
* @param   :pID:灯珠编号 
* @return  :None
***********************************************************************/
void RGB_ID_NO_Show(uint8_t pID)
{
	  uint16_t pI = 0;
		//参数值约束
	  if(pID > 22) return;
		//
    for(pI = 0; pI < 8; pI++) { //green
        LED_BUFFER[pID*24+pI] = ((BLACK[1] << pI) & 0x80) ? CODE1 : CODE0;
    }
    for(pI = 0; pI < 8; pI++) { //red
        LED_BUFFER[pID*24+8+pI] = ((BLACK[0] << pI) & 0x80) ? CODE1 : CODE0;
    }
    for(pI = 0; pI < 8; pI++) { //blue
        LED_BUFFER[pID*24+16+pI] = ((BLACK[2] << pI) & 0x80) ? CODE1 : CODE0;
    }
		//刷新全部灯珠数据
		RGB_Reflash(LED_NUMS);
}
/***********************************************************************
* @fun     :RGB_BCD_LINE_Show
* @brief   :前16位灯珠将测距数据采用BCD码输出,16-23位灯珠显示巡线
* @param   :pBcd:显示数据 pBcdColor:字体颜色 pLine:显示数据 pLineColor:字体颜色 
* @return  :None
***********************************************************************/
void RGB_BCD_LINE_Show(uint16_t pBcd,uint8_t* pBcdColor,uint8_t pLine,uint8_t* pLineColor)
{
		uint8_t pDataBuf[4] = {0x00,0x00,0x00,0x00};
		//测距数据进行赋值2365
		pDataBuf[0] = (pBcd / 1000);
		pDataBuf[1] = (pBcd / 100) % 10;
		pDataBuf[2] = (pBcd / 10) % 10;
		pDataBuf[3] = (pBcd % 10);
		//局部变量
		uint8_t pI = 0,pJ = 0;
	  uint8_t pID = 0;
		//参数值约束
	  if(pBcd > 9999) return;
		//前16位灯珠BCD码显示
    for (pI = 0; pI < 4; pI++) 
		{
				for (pJ = 0; pJ < 4; pJ++) 
				{
						if((pDataBuf[pI] << pJ) & 0x08)	//取出位数据点亮
						{
								RGB_Set_Color(pID++,pBcdColor);
						}
						else
						{
								RGB_Set_Color(pID++,BLACK);
						}
				}
		}
		//从16-23灯珠巡线指示
		pID = 16;	//从第16个灯珠开始显示
		//
    for (pI = 0; pI < 8; pI++) 
		{
				if((pLine >> pI) & 0x01)	//取出位数据点亮
				{
						RGB_Set_Color(pID++,pLineColor);
				}
				else
				{
						RGB_Set_Color(pID++,BLACK);
				}
				//pData的数据3/4位相同,跳过第4位
				if(pI == 3) pI = 4;
		}
		//刷新全部灯珠数据
		RGB_Reflash(LED_NUMS);
}
