/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2024 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "dma.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "user_app.h"		//用户应用程序

/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
#define	ADC_CONVERTED_DATA_BUFFER_SIZE	7	//ADC通道总的数据长度

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/*********************************printf重定向*********************************/
//仅用于调试输出，连接语音时，禁用调试口
int fputc(int ch, FILE *f)	
{
	uint8_t temp[1] = {ch};
	HAL_UART_Transmit(&huart1, temp, 1, 2);
	return ch;
}

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */
static uint8_t gTaskIndex = 0x00;  //系统任务索引变量
volatile uint8_t gUserButtonCnt = 0;	//按键切换模式 (0:遥控, 1:避障, 2:巡线, 3:规划)
extern gTask_BitDef gTaskStateBit;  //任务执行过程中使用到的标志位
extern ADC_ValTypeDef gStruADC; //A/D通道实时采集的数据
extern TIM_ValTypeDef gStruTIM3; //超声波测距
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_TIM16_Init();
  MX_USART1_UART_Init();
  MX_TIM1_Init();
  MX_TIM3_Init();
  MX_USART2_UART_Init();
  /* USER CODE BEGIN 2 */
	for(gTaskIndex = 0;gTaskIndex < OS_TASKLISTCNT;gTaskIndex++)	g_OSTaskList[gTaskIndex]=NULL;   //清空任务列表
	//进行ADC校准
	if (HAL_ADCEx_Calibration_Start(&hadc1)!= HAL_OK)	{Error_Handler();}
	
  // 开启串口2接收
  extern uint8_t gUART2RxData;
  __HAL_UART_CLEAR_FLAG(&huart2, UART_CLEAR_OREF);
  HAL_UART_Receive_IT(&huart2, &gUART2RxData, 1);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
	HAL_TIM_Base_Start_IT(&htim16);//开启定时器16开启,设备控制任务开始
	//启动ADC组与DMA的常规转换
	if (HAL_ADC_Start_DMA(&hadc1,(uint32_t *)&gStruADC,ADC_CONVERTED_DATA_BUFFER_SIZE) != HAL_OK)	{Error_Handler();}
  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
		for(gTaskIndex = 0;gTaskIndex < OS_TASKLISTCNT;gTaskIndex++)
		{
			if(g_OSTaskList[gTaskIndex] != NULL)
			{
				g_OSTaskList[gTaskIndex]();
				g_OSTaskList[gTaskIndex] = NULL;  
			}
		}
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSIDiv = RCC_HSI_DIV1;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
  RCC_OscInitStruct.PLL.PLLM = RCC_PLLM_DIV1;
  RCC_OscInitStruct.PLL.PLLN = 8;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */
//定时器16的任务分配
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
	static uint8_t p_Time16Cnt = 0;
	/***************************************************************************************/
	//定时器16进行5ms任务中断
	if (htim->Instance == htim16.Instance) 
	{
		p_Time16Cnt++;
		//光电管巡线
		if(!(p_Time16Cnt % 4))  //20ms(50Hz)进行触发刷新
		{
			g_OSTaskList[eTask_Phototube] = Phototube_Task; 	//更新巡线任务
		}	
		//超声波测距任务
		if(!(p_Time16Cnt % 10))  //50ms(20Hz)进行触发刷新
		{
			g_OSTaskList[eTask_Ultrasonic] = Ultrasonic_Task; 	//更新测距任务
		}	
		//空闲任务，RGB显示
		if(!(p_Time16Cnt % 15))  //75ms(13Hz)进行触发刷新
		{
			g_OSTaskList[eTask_Idle] = IDLE_Task; 	//更新空闲任务
		}	
		//串口2输出信息100ms
		if(!(p_Time16Cnt % 20))  //100ms(10Hz)进行触发刷新
		{
			g_OSTaskList[eTask_SerialOut] = SerialOut_Task; 	//更新串口2输出
		}	
		//1000ms运行一次，系统运行指示灯
		if(!(p_Time16Cnt % 200))  
		{
			p_Time16Cnt = 0; 
		}
    // 转向灯任务 50ms 刷新一次
    if(!(p_Time16Cnt % 10))
    {
      g_OSTaskList[eTask_TurnSignal] = TurnSignal_Task;
    }
	}
	/***************************************************************************************/
	//定时器3的溢出中断
	if(htim == &htim3)
	{
		if(gStruTIM3.TIM3_CH2_Edge == 1)
		{
			gStruTIM3.TIM3_CH2_OVER++;  //定时器溢出值增加
		}
	}
	/***************************************************************************************/
  /* Prevent unused argument(s) compilation warning */
  UNUSED(htim);
}
//定时器3通道2捕获输入
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
	if(htim == &htim3)
	{
		if(gStruTIM3.TIM3_CH2_Edge == 0) //捕获到上升沿
		{
			gStruTIM3.TIM3_CH2_Edge = 1;  //进入捕获下降沿状态
			gStruTIM3.TIM3_CH2_OVER = 0;  //定时器溢出值清零
			__HAL_TIM_SET_CAPTUREPOLARITY(&htim3,TIM_CHANNEL_2,TIM_ICPOLARITY_FALLING); //设置捕获极性为下降沿
			__HAL_TIM_SET_COUNTER(&htim3,0);  //设置定时器CNT计数器的值为0
		}
		else  //捕获到下升沿
		{
			HAL_TIM_IC_Stop_IT(&htim3,TIM_CHANNEL_2); //关闭定时器3
			gStruTIM3.TIM3_CH2_Edge = 2;  //大循环处理数据，并重新开始测量
			gStruTIM3.TIM3_CH2_VAL = HAL_TIM_ReadCapturedValue(&htim3,TIM_CHANNEL_2); //读取捕获通道的值
			__HAL_TIM_SET_CAPTUREPOLARITY(&htim3,TIM_CHANNEL_2,TIM_ICPOLARITY_RISING); //设置捕获极性为上降沿
		}
	}
}
//中断回调函数,在设定的PWM通过DMA发送完成后会调用
void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef* htim)
{
  /*
  在DMA中断函数中关闭DMA输出便不会产生杂波,解决灯带的第一颗
	灯珠突然闪绿色以及等待亮度突然爆闪一下
  */
  if(htim->Instance == TIM1) 
	{
    if(htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1) 
		{
      HAL_TIM_PWM_Stop_DMA(&htim1, TIM_CHANNEL_1);
    } 
  } 
}
//EXTI4_15_IRQ下升沿中断
void HAL_GPIO_EXTI_Falling_Callback(uint16_t GPIO_Pin)
{
  /* Prevent unused argument(s) compilation warning */
  UNUSED(GPIO_Pin);
	//判断按键是否按下
  if(HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_15) == GPIO_PIN_RESET)
  {
		gUserButtonCnt++;		//记录按键按下次数
  }
}
/**
  * @brief  Conversion complete callback in non blocking mode 
  * @param  hadc: ADC handle
  * @note   This example shows a simple way to report end of conversion
  *         and get conversion result. You can add your own implementation.
  * @retval None
  */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
  //更新DMA传输状态标志
  gTaskStateBit.ADCC = 1;  
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
