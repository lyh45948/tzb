/**
  ******************************************************************************
  * @file   user_app.c
  * @brief  用户应用程序部分的代码
  * 
  ******************************************************************************
  */
#include "string.h"
#include "stdlib.h"
#include "math.h"
#include "stdint.h"
#include "stdbool.h"
//
#include "main.h"
#include "user_app.h"
//系统任务
gTask_BitDef gTaskStateBit;  //任务执行过程中使用到的标志位
void (* g_OSTaskList[OS_TASKLISTCNT])(void);
//外部变量
extern uint8_t RED[3];
extern uint8_t GREEN[3];
extern uint8_t BLUE[3];
extern uint8_t WHITE[3];
extern uint8_t YELLOW[3];
extern uint8_t BLACK[3];
extern volatile uint8_t gUserButtonCnt;	//按键进行RGB显示切换
//全局变量
ADC_ValTypeDef gStruADC = {0,0,0,0,0,0,0}; //A/D通道实时采集的数据
TIM_ValTypeDef gStruTIM3 = {0,0,0,0}; //超声波测距
//
volatile uint8_t gLineOut = 0x00;	//光电管输出
volatile uint8_t gLineType = 0x00;	//巡线的类型
volatile uint8_t gSearchLine = 0xF0;	//巡线指令
volatile uint8_t gPathPlanning = 0xE0;	//路径规划指令
volatile uint16_t gLeftSpeed = 0;   //左轮速度(脉冲数)
volatile uint16_t gRightSpeed = 0;  //右轮速度(脉冲数)
volatile uint8_t gCarStatus = 0;    //车辆运行状态
volatile uint8_t gCarMode = 0;      //车辆当前模式
/***********************************************************************
* @fun     :IDLE_Task
* @brief   :空闲任务
* @param   :None
* @remark  :测试或者空闲时干的活
***********************************************************************/
void IDLE_Task(void)
{
    // 该任务现在不再显示测距和巡线状态，保持灯带简洁
    // 仅保留转向和倒车灯逻辑在 TurnSignal_Task 中运行
}
/***********************************************************************
* @fun     :RemoveJitter
* @brief   :消抖滤波法 + 一阶滞后滤波法
* @param   :None
* @remark  :消抖滤波法
						1、方法：
						设置一个滤波计数器;
						将每次采样值与当前有效值比较：
						如果采样值＝当前有效值，则计数器清零
						如果采样值>或<当前有效值，则计数器+1，并判断计数器是否>=上限N(溢出);
						如果计数器溢出，则将本次值替换当前有效值，并清计数器;

						2、优点：
						对于变化缓慢的被测参数有较好的滤波效果;
						可避免在临界值附近控制器的反复开/关跳动或显示器上数值抖动;

						3、缺点：
						对于快速变化的参数不宜;
						如果在计数器溢出的那一次采样到的值恰好是干扰值，则会将干扰值
						当作有效值导入交易系统;

						一阶滞后滤波法
						1、方法：
						取a=0~1
						本次滤波结果=（1-a）本次采样值+a上次滤波结果

						2、优点：
						对周期性干扰具有良好的抑制作用
						适用于波动频率较高的场合

						3、缺点：
						相位滞后，灵敏度低
						滞后程度取决于a值大小
						不能消除滤波频率高于采样频率的1/2的干扰信号
***********************************************************************/
static uint16_t RemoveJitter(uint16_t pRawdata)
{
		static uint8_t pCount = 0;
		static uint16_t pJitterValue = 0;
		//消抖滤波法
		if(abs(pRawdata - pJitterValue) > 100) //数据差突然大于100mm
		{
				pCount++;
				if(pCount >= 5) //约250ms周期
				{
						pCount = 0;
						pJitterValue = pRawdata;	
				}
				return pJitterValue;
		}
		else	//一阶滞后滤波
		{
				pCount = 0;
				pJitterValue = ((2 * pJitterValue) + (8 * pRawdata)) / 10;		//新值权重大
				//返回
				return pJitterValue;
		}
}
/***********************************************************************
* @fun     :Ultrasonic_Task
* @brief   :测距任务
* @param   :None
* @remark  :在TRIG管脚输入一个10us以上的高电平(一般建议50us左右)，芯片(TP,TN
						管脚)便可发出8个40kHz的超声波脉冲，然后(RP,RN)检测回波信号。当检
						测到回波信号后，通过ECHO管脚输出，根据ECHO管脚输出高电平的持续时
						间可以计算距离值。即距离值为：(高电平时间 * 340m/s)/2。
***********************************************************************/
void Ultrasonic_Task(void)
{
		uint16_t pDistanceValue = 0;
		//硬件启动测距
		switch(gStruTIM3.TIM3_CH2_Edge)
		{
			case 0:	//测量开始
					//变量初始化
					gStruTIM3.TIM3_CH2_VAL = 0;
					gStruTIM3.TIM3_CH2_OVER = 0;
					//拉高TRIG引脚一段时间
					CS100A_TRIG_ENABLE();
					HAL_Delay(1);
					CS100A_TRIG_DISABLE();
					//开启捕获与中断
					HAL_TIM_Base_Start_IT(&htim3);	//开启定时器3中断
					HAL_TIM_IC_Start_IT(&htim3, TIM_CHANNEL_2);		//开启输入捕获中断
			break;
			case 1:	//测量中
			break;
			case 2:	//测量完成
					gStruTIM3.TIM3_CH2_Edge = 0;  //重新开始捕获
					gStruTIM3.Distance = ((gStruTIM3.TIM3_CH2_VAL + (gStruTIM3.TIM3_CH2_OVER << 16)) * 34 / 100) / 2;
					//测距数据滤波
					pDistanceValue = RemoveJitter(gStruTIM3.Distance);
//					printf("The distance is %d mm\r\n", gStruTIM3.Distance);
					printf("The filtered ranging data is %d mm\r\n", pDistanceValue);
					//更新数据
					gStruTIM3.Distance = pDistanceValue;
			break;
		}
}
/***********************************************************************
* @fun     :Search_Second_Max
* @brief   :查找一个整数数组中第二大的数
* @param   :None
* @remark  :
						设置两个变量max1和max2，用来保存最大数和第二大数，然后将数组
						剩余的数依次与这两个数比较，如果这个数a比max1大，则先将max1赋
						给max2,使原先最大的数成为第二大的数，再将这个数a赋给max1,如果
						这个数a比max1小但比max2大，则将这个数a赋值给max2，依次类推，
						直到数组中的数都比较完。
***********************************************************************/
uint16_t Search_Second_Max(uint16_t *pArray, uint16_t pArrayLen)
{
		uint16_t pMax1, pMax2, pI;
		pMax1 = pArray[0];
		//
		for (pI = 1; pI < pArrayLen; pI++)
		{
				if (pArray[pI] > pMax1)
				{
						pMax2 = pMax1;
						pMax1 = pArray[pI];            
				}
				else
				{
						if (pI == 1)
								pMax2 = pArray[pI];
						else if (pArray[pI] > pMax2)
								pMax2 = pArray[pI];
				}
		}
		return pMax2;
}
/***********************************************************************
* @fun     :Phototube_Task
* @brief   :7位光电管巡线检测
* @param   :None
* @remark  :采用ADC+DMA，定时读取数据
***********************************************************************/
#define LINE_MIN_VALUE  1300
#define LINE_MID_VALUE  2000
#define LINE_MAX_VALUE  3000
void Phototube_Task(void)
{
		uint16_t pLineThreshold = 0;
		uint16_t pSecondMax = 0;
		uint32_t pLineLeftSum = 0;
		uint32_t pLineRightSum = 0;
		uint32_t pLineTotaltSum = 0;
		//DMA数据读取完成
		if((gTaskStateBit.ADCC))	//DMA采集完成
		{
			//取出数组中的第二大值,作为动态阈值参考
			pSecondMax = Search_Second_Max((uint16_t *)&gStruADC, 7);	
			
			/* 
			   降低灵敏度与增强鲁棒性的优化逻辑：
			   1. 纯白环境保护：如果第二大值小于 1000（说明都在白纸上），强制设为高阈值 2000，防止噪点误触发。
			   2. 压线补偿：如果检测到黑线，将阈值设为 pSecondMax - 300，这样当两条线同时压在黑线上时，
			      两路都能被判定为有效，解决“直行频繁修正”的问题。
			*/
			if (pSecondMax < 1000) 
			{
					pLineThreshold = 2000;  // 远高于白纸底噪
			} 
			else 
			{
					pLineThreshold = pSecondMax - 300; // 允许稍微低于第二大值的点也被判定为黑线
			}
//			printf("The second largest number in the array: %d\n\r",pLineThreshold);	//发送模拟值	
			//将7个光电管数据转化为一个字节的数据
			if(gStruADC.ADC_IN0 > pLineThreshold) gLineOut = gLineOut & 0xFE;	//AD0指示灯
			else  gLineOut = gLineOut | 0x01;	
			
			if(gStruADC.ADC_IN1 > pLineThreshold) gLineOut = gLineOut & 0xFD;	//AD1指示灯
			else  gLineOut = gLineOut | 0x02;	
			
			if(gStruADC.ADC_IN4 > pLineThreshold) gLineOut = gLineOut & 0xFB;	//AD4指示灯
			else  gLineOut = gLineOut | 0x04;	
			
			if(gStruADC.ADC_IN5 > pLineThreshold) gLineOut = gLineOut & 0xE7;	//AD5指示灯
			else  gLineOut = gLineOut | 0x18;	
			
			if(gStruADC.ADC_IN6 > pLineThreshold) gLineOut = gLineOut & 0xDF;	//AD6指示灯
			else  gLineOut = gLineOut | 0x20;	
			
			if(gStruADC.ADC_IN15 > pLineThreshold) gLineOut = gLineOut & 0xBF;	//AD15指示灯
			else  gLineOut = gLineOut | 0x40;	
			
			if(gStruADC.ADC_IN16 > pLineThreshold) gLineOut = gLineOut & 0x7F;	//AD16指示灯
			else  gLineOut = gLineOut | 0x80;	
			//对7通道数据累加求和
			pLineLeftSum = gStruADC.ADC_IN0 + gStruADC.ADC_IN1 + gStruADC.ADC_IN4 + gStruADC.ADC_IN5;
			pLineRightSum = gStruADC.ADC_IN5 + gStruADC.ADC_IN6 + gStruADC.ADC_IN15 + gStruADC.ADC_IN16;
			pLineTotaltSum = (pLineLeftSum + pLineRightSum) >> 3;	//求平均值
			//判断线的类型-朝左路口
			if((pLineLeftSum >> 2) > LINE_MAX_VALUE)	//-|型
			{
				gLineType = 0x02;	
			}
			//朝右路口
			if((pLineRightSum >> 2) > LINE_MAX_VALUE)	//|-型
			{
				gLineType = 0x03;	
			}
			//非黑线白底，此时gLineOut输出可能不准确
			if(pLineTotaltSum < LINE_MIN_VALUE)	//全白
			{
				gLineType = 0x00;	
			}
			else if(pLineTotaltSum > LINE_MAX_VALUE)	//全黑
			{
				gLineType = 0x01;	
			}			
			//转换状态复位
			gTaskStateBit.ADCC = 0;
		}
}
/***********************************************************************
* @fun     :SerialOut_Task
* @brief   :串口2输出任务
* @param   :None
* @remark  :协议兼容原来的超声波传感器，帧头	Data_H	Data_L	SUM
						----------------------------0XFF  0X**    0X** 	  0X**----- 
						距离值= Data_H*256+ Data_L=0X07A1
						转换成十进制等于1953；
						表示当前测量的距离值为1953毫米。
***********************************************************************/
void SerialOut_Task(void)
{
		uint8_t pUART2_TxBuf[4] = {0xFF,0x00,0x00,0x00};	//串口2数据发送缓冲区
		//赋值
		pUART2_TxBuf[1] = gStruTIM3.Distance>> 8;
		pUART2_TxBuf[2] = gStruTIM3.Distance & 0xFF;
		//校验和
		pUART2_TxBuf[3] = pUART2_TxBuf[0] + pUART2_TxBuf[1] +pUART2_TxBuf[2];
		//串口输出 (huart2 负责驱动小车)
		HAL_UART_Transmit(&huart2, pUART2_TxBuf, 4, 10);
		HAL_Delay(5);

		//巡线与模式数据发送
		pUART2_TxBuf[0] = 0xAA;	
		pUART2_TxBuf[1] = gLineOut;		//巡线数据的二值化
		
		// 根据按键状态切换模式 (0:遥控, 1:避障, 2:巡线, 3:规划)
        // 增加同步保护，如果底盘反馈的模式与当前不符，以底盘为准
		if(gUserButtonCnt == 0) // 遥控 (Manual)
		{
			pUART2_TxBuf[2] = 0x00 | gLineType;
		}
		else if(gUserButtonCnt == 1) // 自动避障 (Avoid)
		{
			pUART2_TxBuf[2] = 0xD0 | gLineType; 
		}
		else if(gUserButtonCnt == 2) // 自动巡线 (Line)
		{
			pUART2_TxBuf[2] = 0xF0 | gLineType; 
		}
		else if(gUserButtonCnt == 3) // 路径规划 (Path)
		{
			pUART2_TxBuf[2] = 0xE0 | gLineType; 
		}
		else
		{
			gUserButtonCnt = 0; // 越界重置
			pUART2_TxBuf[2] = 0x00 | gLineType;
		}

		//校验和
		pUART2_TxBuf[3] = pUART2_TxBuf[0] + pUART2_TxBuf[1] +pUART2_TxBuf[2];
		//串口输出 (huart2 负责驱动小车)
		HAL_UART_Transmit(&huart2, pUART2_TxBuf, 4, 10);

		// --- 发送 7 路 ADC 原始数据 (huart1 负责 Python 绘图) ---
		uint8_t pADC_TxBuf[16];
		pADC_TxBuf[0] = 0xCC; // 新的数据包头
		
		// 将 7 路 16位 ADC 数据拆分为高低字节 (大端发送)
		uint16_t *adc_ptr = (uint16_t *)&gStruADC;
		for(int i = 0; i < 7; i++) {
				pADC_TxBuf[1 + i*2] = (uint8_t)(adc_ptr[i] >> 8);   // 高字节
				pADC_TxBuf[2 + i*2] = (uint8_t)(adc_ptr[i] & 0xFF); // 低字节
		}
		
		// 计算校验和
		uint8_t sum = 0;
		for(int i = 0; i < 15; i++) sum += pADC_TxBuf[i];
		pADC_TxBuf[15] = sum;

		HAL_UART_Transmit(&huart1, pADC_TxBuf, 16, 20);
}

/***********************************************************************
* @fun     :TurnSignal_Task
* @brief   :根据车辆状态和轮速差实现转向灯效果
* @param   :None
* @remark  :LED映射：右侧(0-7)，左侧(8-15)，其余(16-22)
***********************************************************************/
void TurnSignal_Task(void)
{
    static uint32_t last_tick = 0;
    static uint32_t turn_start_tick = 0;
    static uint8_t blink = 0;
    static int current_turn_side = 0; // 0:无, 1:左, 2:右
    
    // 使用外部定义的标准颜色 (低亮度更安全)
    extern uint8_t YELLOW[3];
    extern uint8_t RED[3];
    extern uint8_t WHITE[3];
    extern uint8_t BLACK[3];
    
    // 1. 闪烁计时 (200ms)
    if(HAL_GetTick() - last_tick > 200) 
    {
        blink = !blink;
        last_tick = HAL_GetTick();
    }

    // 2. 确定基础颜色 (倒车红[状态2]，其余白)
    uint8_t *pBaseColor = (gCarStatus == 2) ? RED : WHITE;

    // 3. 转向状态判定 (轮速差优先级高于指令)
    int detected_side = 0;
    const int threshold_on = 8;  // 开启阈值
    const int threshold_off = 4; // 关闭阈值 (滞后)
    int speed_diff = (int)gLeftSpeed - (int)gRightSpeed;

    // 如果速度极低，忽略轮速差判定 (防止噪点)
    if (gLeftSpeed < 3 && gRightSpeed < 3) 
    {
        if (gCarStatus == 3) detected_side = 1;
        else if (gCarStatus == 4) detected_side = 2;
        else detected_side = 0;
    }
    else 
    {
        // 运动状态：轮速差优先
        if (speed_diff > threshold_on) detected_side = 2;      // 右转
        else if (speed_diff < -threshold_on) detected_side = 1; // 左转
        else if (abs(speed_diff) < threshold_off) detected_side = 0;
        else detected_side = current_turn_side; // 维持现状
        
        // 如果轮速差不显著，则看指令同步
        if (detected_side == 0) {
            if (gCarStatus == 3) detected_side = 1;
            else if (gCarStatus == 4) detected_side = 2;
        }
    }

    // 3.3 状态锁定 (一旦开始转向，至少维持 500ms，防止闪烁)
    if (detected_side != 0) 
    {
        if (detected_side != current_turn_side) 
        {
            current_turn_side = detected_side;
            turn_start_tick = HAL_GetTick();
        }
    } 
    else 
    {
        // 只有当维持时间超过 500ms 且检测到无转向时，才恢复基础状态
        if (HAL_GetTick() - turn_start_tick > 500) 
        {
            current_turn_side = 0;
        }
    }

    // 4. 执行灯光显示 (物理布局: U1-U8右侧, U9-U16左侧, U17-U23背景)
    for(int i = 0; i < 23; i++) 
    {
        if (current_turn_side == 1 && i >= 8 && i <= 15) // 左转向灯区域 (U9-U16)
        {
            RGB_Set_Color(i, blink ? YELLOW : pBaseColor);
        }
        else if (current_turn_side == 2 && i >= 0 && i <= 7) // 右转向灯区域 (U1-U8)
        {
            RGB_Set_Color(i, blink ? YELLOW : pBaseColor);
        }
        else // 其他区域 (U17-U23 及非活动转向侧)
        {
            RGB_Set_Color(i, pBaseColor);
        }
    }

    RGB_Reflash(LED_NUMS);
}

/**
 * @brief  USR 按键外部中断回调
 * @note   用于循环切换 4 种模式 (0:遥控, 1:避障, 2:巡线, 3:规划)
 */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    static uint32_t last_press_tick = 0;
    if(GPIO_Pin == USER_Pin)
    {
        // 使用更严谨的时间消抖 (200ms 内只允许触发一次)
        if(HAL_GetTick() - last_press_tick > 200)
        {
            if(HAL_GPIO_ReadPin(USER_GPIO_Port, USER_Pin) == GPIO_PIN_RESET)
            {
                gUserButtonCnt++;
                if(gUserButtonCnt > 3) gUserButtonCnt = 0;
                last_press_tick = HAL_GetTick();
            }
        }
    }
}
