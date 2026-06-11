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
#include "dma.h"
#include "i2c.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <string.h>
#include "bsp_ina219.h"
#include "system_cfg.h"
#include "app_motor.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */
UARTx_DMA_RECEIVE_STRUCT Usart1DMAReceive;  // 串口1接收不定长的数据		
ts_SystemValue_t systemValue = {.car_status = CAR_STATUS_OFF,};
uint8_t distance_buff[4] = {0};
uint8_t UART2Rxdata[2] =  {0};
//
uint8_t distance_send_data = 0xFF;
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
  MX_USART2_UART_Init();
  MX_I2C2_Init();
  MX_TIM1_Init();
  MX_TIM3_Init();
  MX_TIM14_Init();
  MX_USART1_UART_Init();
  MX_TIM16_Init();
  MX_TIM17_Init();
  /* USER CODE BEGIN 2 */
  console_log_info("-------------start UPS Test-------------");
	
  /* 初始化编码定时器 */
	PID_init();	//PID参数初始化
  motor_encoder_init();
  
  /* 开启电机 PWM 输出 */
  HAL_TIM_PWM_Start(&htim16, TIM_CHANNEL_1);
  HAL_TIM_PWM_Start(&htim17, TIM_CHANNEL_1);
  
  /* 电源检测芯片初始化 */
  INA219_Init();
  
  /* 开启定时器3中断 */
  HAL_TIM_Base_Start_IT(&htim3);

	/* 开启串口2的接收中断 */
  __HAL_UART_ENABLE_IT(&huart2, UART_IT_IDLE); // 开启串口2的空闲中断
  __HAL_UART_CLEAR_IDLEFLAG(&huart2);
	HAL_UART_Receive_IT(&huart2, UART2Rxdata, 1);
	
  /* 开启串口1的空闲中断 */
  __HAL_UART_ENABLE_IT(&huart1, UART_IT_IDLE); // 开启串口1的空闲中断
  __HAL_UART_CLEAR_IDLEFLAG(&huart1);
  HAL_UART_Receive_DMA(&huart1, Usart1DMAReceive.UsartDMARecBuffer, USART_DMA_REC_SIE);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  uint32_t last_telemetry_tick = 0;
  while (1)
  {
    // 串口1 接收不定长数据, 并进行解析数据
    if(Usart1DMAReceive.UsartRecFlag)
	  {
		  // 解析JSON数据 (屏蔽日志以减少对通信的干扰)
		  parse_json_data(Usart1DMAReceive.UsartRecBuffer, Usart1DMAReceive.UsartRecLen);
		  Usart1DMAReceive.UsartRecFlag = 0;
		  Usart1DMAReceive.UsartRecLen = 0;
		  memset(Usart1DMAReceive.UsartRecBuffer, 0, sizeof(Usart1DMAReceive.UsartRecBuffer));
	  }

    // 采集数据 (使用差值判断，确保不会错过发送窗口)
    if(HAL_GetTick() - last_telemetry_tick >= 100)
    {
      last_telemetry_tick = HAL_GetTick();
      
		  // 采集超声波传感器的值，必须大于70ms
		  HAL_UART_Transmit(&huart2, (uint8_t *)&distance_send_data, 1, 100);
      
      // 发送电机速度给传感器板用于转向灯
      send_speed_to_sensor();
      
		  systemValue.battery = INA219_get_bus_voltage_mv();
		  // 打包JSON数据
		  packet_json_data(&systemValue);	
    }
		
	  // 系统运行指示灯
	  if(!(HAL_GetTick() % 200))
	  {
		  HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_0);
	  }
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
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
int fputc(int ch, FILE *f)
{
  // 彻底禁用调试日志打印，确保 UART1 仅用于 JSON 通信
  // HAL_UART_Transmit(&huart1, (uint8_t *)&ch, 1, 10);
  return ch;
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
