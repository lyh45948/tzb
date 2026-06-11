/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    stm32g0xx_it.c
  * @brief   Interrupt Service Routines.
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
#include "stm32g0xx_it.h"
/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include "usart.h"
#include <string.h>
#include "system_cfg.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN TD */

/* USER CODE END TD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
/* USER CODE BEGIN PV */
uint8_t gLastSensorMode = 0xFF; // 记录上一次从传感器收到的模式，用于微信优先逻辑的变化检测
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
extern uint8_t usart1RecvData;
extern uint8_t distance_buff[4];
extern uint8_t UART2Rxdata[2];
uint8_t gRx2BufferCounter = 0;
//
volatile uint8_t gLineOut = 0x00;	//光电管输出
volatile uint8_t gLineType = 0x00;	//巡线的类型
/* USER CODE END 0 */

/* External variables --------------------------------------------------------*/
extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim3;
extern TIM_HandleTypeDef htim14;
extern DMA_HandleTypeDef hdma_usart1_rx;
extern UART_HandleTypeDef huart1;
extern UART_HandleTypeDef huart2;
/* USER CODE BEGIN EV */

/* USER CODE END EV */

/******************************************************************************/
/*           Cortex-M0+ Processor Interruption and Exception Handlers          */
/******************************************************************************/
/**
  * @brief This function handles Non maskable interrupt.
  */
void NMI_Handler(void)
{
  /* USER CODE BEGIN NonMaskableInt_IRQn 0 */

  /* USER CODE END NonMaskableInt_IRQn 0 */
  /* USER CODE BEGIN NonMaskableInt_IRQn 1 */
  while (1)
  {
  }
  /* USER CODE END NonMaskableInt_IRQn 1 */
}

/**
  * @brief This function handles Hard fault interrupt.
  */
void HardFault_Handler(void)
{
  /* USER CODE BEGIN HardFault_IRQn 0 */

  /* USER CODE END HardFault_IRQn 0 */
  while (1)
  {
    /* USER CODE BEGIN W1_HardFault_IRQn 0 */
    /* USER CODE END W1_HardFault_IRQn 0 */
  }
}

/**
  * @brief This function handles System service call via SWI instruction.
  */
void SVC_Handler(void)
{
  /* USER CODE BEGIN SVC_IRQn 0 */

  /* USER CODE END SVC_IRQn 0 */
  /* USER CODE BEGIN SVC_IRQn 1 */

  /* USER CODE END SVC_IRQn 1 */
}

/**
  * @brief This function handles Pendable request for system service.
  */
void PendSV_Handler(void)
{
  /* USER CODE BEGIN PendSV_IRQn 0 */

  /* USER CODE END PendSV_IRQn 0 */
  /* USER CODE BEGIN PendSV_IRQn 1 */

  /* USER CODE END PendSV_IRQn 1 */
}

/**
  * @brief This function handles System tick timer.
  */
void SysTick_Handler(void)
{
  /* USER CODE BEGIN SysTick_IRQn 0 */

  /* USER CODE END SysTick_IRQn 0 */
  HAL_IncTick();
  /* USER CODE BEGIN SysTick_IRQn 1 */

  /* USER CODE END SysTick_IRQn 1 */
}

/******************************************************************************/
/* STM32G0xx Peripheral Interrupt Handlers                                    */
/* Add here the Interrupt Handlers for the used peripherals.                  */
/* For the available peripheral interrupt handler names,                      */
/* please refer to the startup file (startup_stm32g0xx.s).                    */
/******************************************************************************/

/**
  * @brief This function handles DMA1 channel 1 interrupt.
  */
void DMA1_Channel1_IRQHandler(void)
{
  /* USER CODE BEGIN DMA1_Channel1_IRQn 0 */

  /* USER CODE END DMA1_Channel1_IRQn 0 */
  HAL_DMA_IRQHandler(&hdma_usart1_rx);
  /* USER CODE BEGIN DMA1_Channel1_IRQn 1 */

  /* USER CODE END DMA1_Channel1_IRQn 1 */
}

/**
  * @brief This function handles TIM1 capture compare interrupt.
  */
void TIM1_CC_IRQHandler(void)
{
  /* USER CODE BEGIN TIM1_CC_IRQn 0 */

  /* USER CODE END TIM1_CC_IRQn 0 */
  HAL_TIM_IRQHandler(&htim1);
  /* USER CODE BEGIN TIM1_CC_IRQn 1 */

  /* USER CODE END TIM1_CC_IRQn 1 */
}

/**
  * @brief This function handles TIM3 global interrupt.
  */
void TIM3_IRQHandler(void)
{
  /* USER CODE BEGIN TIM3_IRQn 0 */

  /* USER CODE END TIM3_IRQn 0 */
  HAL_TIM_IRQHandler(&htim3);
  /* USER CODE BEGIN TIM3_IRQn 1 */

  /* USER CODE END TIM3_IRQn 1 */
}

/**
  * @brief This function handles TIM14 global interrupt.
  */
void TIM14_IRQHandler(void)
{
  /* USER CODE BEGIN TIM14_IRQn 0 */

  /* USER CODE END TIM14_IRQn 0 */
  HAL_TIM_IRQHandler(&htim14);
  /* USER CODE BEGIN TIM14_IRQn 1 */

  /* USER CODE END TIM14_IRQn 1 */
}

/**
  * @brief This function handles USART1 global interrupt / USART1 wake-up interrupt through EXTI line 25.
  */
void USART1_IRQHandler(void)
{
  /* USER CODE BEGIN USART1_IRQn 0 */
  if(__HAL_UART_GET_FLAG(&huart1, UART_FLAG_IDLE) == SET)
  {
    uint16_t temp = 0;
    __HAL_UART_CLEAR_IDLEFLAG(&huart1);
    HAL_UART_DMAStop(&huart1);
    temp = huart1.Instance->ISR;
    temp = huart1.Instance->RDR;
    temp = hdma_usart1_rx.Instance->CNDTR;
    Usart1DMAReceive.UsartDMARecLen = USART_DMA_REC_SIE - temp;
    HAL_UART_RxCpltCallback(&huart1);
  }
  /* USER CODE END USART1_IRQn 0 */
  HAL_UART_IRQHandler(&huart1);
  /* USER CODE BEGIN USART1_IRQn 1 */
  HAL_UART_Receive_DMA(&huart1, Usart1DMAReceive.UsartDMARecBuffer, USART_DMA_REC_SIE);
  /* USER CODE END USART1_IRQn 1 */
}

/**
  * @brief This function handles USART2 global interrupt / USART2 wake-up interrupt through EXTI line 26.
  */
void USART2_IRQHandler(void)
{
  /* USER CODE BEGIN USART2_IRQn 0 */

  /* USER CODE END USART2_IRQn 0 */
  HAL_UART_IRQHandler(&huart2);
  /* USER CODE BEGIN USART2_IRQn 1 */
  if (__HAL_UART_GET_FLAG(&huart2, UART_FLAG_IDLE) != RESET)	//huart2产生空闲中断 
  {	
	__HAL_UART_CLEAR_IDLEFLAG(&huart2);	//清除空闲中断标志
	HAL_UART_AbortReceive_IT(&huart2);	//中止上一次的接收工作
  }
  /* USER CODE END USART2_IRQn 1 */
}

/* USER CODE BEGIN 1 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  if (huart->Instance == USART1)
  {
    if (Usart1DMAReceive.UsartRecLen > 0)
    {
      memcpy(&Usart1DMAReceive.UsartRecBuffer[Usart1DMAReceive.UsartRecLen],
             Usart1DMAReceive.UsartDMARecBuffer,
             Usart1DMAReceive.UsartDMARecLen);
      Usart1DMAReceive.UsartRecLen += Usart1DMAReceive.UsartDMARecLen;
    }
    else
    {
      memcpy(Usart1DMAReceive.UsartRecBuffer,
             Usart1DMAReceive.UsartDMARecBuffer,
             Usart1DMAReceive.UsartDMARecLen);
      Usart1DMAReceive.UsartRecLen = Usart1DMAReceive.UsartDMARecLen;
    }
    memset(Usart1DMAReceive.UsartDMARecBuffer, 0x00, sizeof(Usart1DMAReceive.UsartDMARecBuffer)); 
    Usart1DMAReceive.UsartRecFlag = 1;
  }
	else if (huart->Instance == USART2)
	{
		distance_buff[gRx2BufferCounter] = UART2Rxdata[0];
		gRx2BufferCounter++;
		UART2Rxdata[0] = 0;
		HAL_UART_Receive_IT(&huart2, UART2Rxdata, 1);
	}
}

/**
 * @brief  串口错误回调函数 (核心：解决经常性通信中断)
 * @note   一旦发生溢出错误 (ORE) 或帧错误，立即清除标志并重启接收
 */
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        __HAL_UART_CLEAR_FLAG(huart, UART_CLEAR_OREF | UART_CLEAR_NEF | UART_CLEAR_FEF);
        HAL_UART_Receive_DMA(&huart1, Usart1DMAReceive.UsartDMARecBuffer, USART_DMA_REC_SIE);
    }
    else if (huart->Instance == USART2)
    {
        __HAL_UART_CLEAR_FLAG(huart, UART_CLEAR_OREF | UART_CLEAR_NEF | UART_CLEAR_FEF);
        HAL_UART_Receive_IT(&huart2, UART2Rxdata, 1);
    }
}
void HAL_UART_AbortReceiveCpltCallback(UART_HandleTypeDef *huart)
{
	if(huart->Instance == USART2)
	{
		if(((distance_buff[0]  +distance_buff[1] + distance_buff[2]) & 0x00FF) == distance_buff[3])
		{
			gRx2BufferCounter = 0;
			//
			if(distance_buff[0] == 0xFF)
			{
				systemValue.distance = (distance_buff[1] << 8) + distance_buff[2];
			}	
			else if(distance_buff[0] == 0xAA)
			{
				gLineOut = distance_buff[1];		//巡线数据的二值化
				gLineType = distance_buff[2];		
        
        // --- 微信小程序优先逻辑 ---
        uint8_t mode_flag = (distance_buff[2] >> 4) & 0x0F;
        extern uint8_t gLastSensorMode;
        extern volatile uint32_t gModeLockTick;
        
        // 只有当距离上次微信指令超过 500ms，且按键发生“跳变”时，才响应物理按键
        if ((HAL_GetTick() - gModeLockTick > 500) && (mode_flag != gLastSensorMode))
        {
            if(mode_flag == 0x00) systemValue.car_mode = CAR_MODE_MANUAL;
            else if(mode_flag == 0x0D) systemValue.car_mode = CAR_MODE_AVOID;
            else if(mode_flag == 0x0F) systemValue.car_mode = CAR_MODE_LINE;
            else if(mode_flag == 0x0E) systemValue.car_mode = CAR_MODE_PATH;
            
            gLastSensorMode = mode_flag; 
        }
			}	
		}	
	else
		{
			gRx2BufferCounter = 0;
		}
		//重新开始接收
		HAL_UART_Receive_IT(&huart2, UART2Rxdata, 1);
	}
}
/* USER CODE END 1 */
