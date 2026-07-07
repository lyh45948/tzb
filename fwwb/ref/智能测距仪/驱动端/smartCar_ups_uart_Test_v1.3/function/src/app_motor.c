#include "app_motor.h"
#include "system_cfg.h"
#include <string.h>
#include "cJSON.h"
#include "usart.h"

/**
 * 设置小车行驶速度的范围为0~192, 如何算出来的？
 * 现在所用的直流减速电机的型号为:
 *    单向脉冲编码器
 *    减速比：1:48
 *    额定电压：6V
 *    空载转速：220RPM
 *    编码器线数：11线
 *    编码器精度：528线
 *
 * 所以我们可以计算出小车在空载的时候，
 *   1分钟转220转，1秒钟转3.67转，大轮1转等于528个脉冲，那1秒钟约等于1936个脉冲，
 *   在程序中每隔100ms采集一次当前的脉冲数，可得出设置范围为0~190.
 */

__IO uint32_t left_encoder_temp, right_encoder_temp; // 左电机和右电机的编码器脉冲计数值 - 临时值
__IO float R_Current_Speed = 0.0;
__IO float L_Current_Speed = 0.0;
void motor_control_running_status(te_car_status_t status);
uint16_t L_Motor_PWM, R_Motor_PWM;
uint16_t L_Motor_ENC, R_Motor_ENC;

/*
 * 定时器的输入捕获上升沿触发的中断回调函数
 * */
void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
  /* 左电机编码器 */
  if ((htim->Instance == TIM1) && (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1))
  {
    left_encoder_temp++;
    HAL_TIM_IC_Start_IT(&htim1, TIM_CHANNEL_1);
  }

  /* 右电机编码器 */
  if ((htim->Instance == TIM14) && (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1))
  {
    right_encoder_temp++;
    HAL_TIM_IC_Start_IT(&htim14, TIM_CHANNEL_1);
  }
}
/**
 * @brief  直流电机编码器的初始化
 * @note
 * @retval None
 */
void motor_encoder_init(void)
{
  /* 清零计数器 */
    __HAL_TIM_SET_COUNTER(&htim1, 0);
    __HAL_TIM_SET_COUNTER(&htim14, 0);

    /* 使能输入捕获中断 */
    HAL_TIM_IC_Start_IT(&htim1, TIM_CHANNEL_1);
    HAL_TIM_IC_Start_IT(&htim14, TIM_CHANNEL_1);
}
/**
 * @brief  读取左轮编码器
 * @note
 * @retval
 */
uint32_t motor_read_encoder(te_L_R_Motor_t motor)
{
  uint32_t temp;
  switch (motor)
  {
  case L_MOTOR:
    temp = left_encoder_temp;
    left_encoder_temp = 0;
    break;
  case R_MOTOR:
    temp = right_encoder_temp;
    right_encoder_temp = 0;
    break;

  default:
    temp = 0;
    break;
  }

  return temp;
}

/**
 * @brief  解析JSON数据包
 * @note
 * @param  *pstr:
 * @retval None
 */
void parse_json_data(uint8_t *pstr, uint16_t len)
{
  if (pstr == NULL || len < 2)
    return;

  cJSON *json_root = cJSON_Parse((const char *)pstr);
  if (json_root)
  {
    cJSON *json_control = cJSON_GetObjectItem(json_root, "control");
    if (json_control)
    {
      cJSON *json_turn = cJSON_GetObjectItem(json_control, "turn");
      if (json_turn)
      {
        if (!strcmp(json_turn->valuestring, "run"))
        {
          console_log_success("control turn %s", json_turn->valuestring);
          systemValue.car_status = CAR_STATUS_RUN;
        }
        else if (!strcmp(json_turn->valuestring, "back"))
        {
          console_log_success("control turn %s", json_turn->valuestring);
          systemValue.car_status = CAR_STATUS_BACK;
        }
        else if (!strcmp(json_turn->valuestring, "left"))
        {
          console_log_success("control turn %s", json_turn->valuestring);
          systemValue.car_status = CAR_STATUS_LEFT;
        }
        else if (!strcmp(json_turn->valuestring, "right"))
        {
          console_log_success("control turn %s", json_turn->valuestring);
          systemValue.car_status = CAR_STATUS_RIGHT;
        }
				else if (!strcmp(json_turn->valuestring, "stop"))
        {
          console_log_success("control turn %s", json_turn->valuestring);
          systemValue.car_status = CAR_STATUS_STOP;
        }
      }
      json_turn = NULL;

      cJSON *json_power = cJSON_GetObjectItem(json_control, "power");
      if (json_power)
      {
        if (!strcmp(json_power->valuestring, "on"))
        {
          console_log_success("control power %s", json_power->valuestring);
          systemValue.car_status = CAR_STATUS_ON;
        }
        else if (!strcmp(json_power->valuestring, "off"))
        {
          console_log_success("control power %s", json_power->valuestring);
          systemValue.car_status = CAR_STATUS_OFF;
        }
      }
      json_power = NULL;

      cJSON *json_pwm = cJSON_GetObjectItem(json_control, "pwm");
      if (json_pwm)
      {
        cJSON *json_L_pwm = cJSON_GetObjectItem(json_pwm, "L_Motor");
        cJSON *json_R_pwm = cJSON_GetObjectItem(json_pwm, "R_Motor");

        L_Motor_PWM = json_L_pwm->valueint;
        R_Motor_PWM = json_R_pwm->valueint;
        console_log_success("control pwm_L: %d, pwm_R: %d", L_Motor_PWM, R_Motor_PWM);
      }
      json_pwm = NULL;
			
    }
    json_control = NULL;
  }
  cJSON_Delete(json_root);
  json_root = NULL;
}




/**
 * @brief  生成JSON数据
 * @note   注意：生成JSON数据完成之后，一定要将packet_buff进行清空处理
 * @param  *sysData:
 * @retval
 */
void packet_json_data(ts_SystemValue_t *sysData)
{
  uint8_t packet_buff[125] = {0};

  sprintf((char *)packet_buff, "{\"status\":{\"distance\":%d,\"carPower\":%d,\"L_speed\":%d,\"R_speed\":%d}}",
          sysData->distance, sysData->battery, sysData->L_enc, sysData->R_enc);

  HAL_UART_Transmit(&huart1, packet_buff, strlen((char *)packet_buff), 10); // 将数据发送出去
//	console_log_info("buff: %s", packet_buff);
}

// 1ms产生一个中断
uint16_t TIM3_Times_Count = 0;
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  if (htim->Instance == TIM3)
  {
		TIM3_Times_Count++;
		if(!(TIM3_Times_Count % 5))
		{
			systemValue.L_enc = motor_read_encoder(L_MOTOR);
			systemValue.R_enc = motor_read_encoder(R_MOTOR);
		}
		
		if(!(TIM3_Times_Count % 10))
		{
			TIM3_Times_Count = 0;
			motor_control_running_status(systemValue.car_status);
		}
  }
}

uint32_t Motor_Middle_ENC = 0;
void motor_control_running_status(te_car_status_t status)
{
	L_Motor_ENC = systemValue.L_enc;
	R_Motor_ENC = systemValue.R_enc;
	
  switch (status)
  {
  case CAR_STATUS_RUN:
    Motor_Middle_ENC = (L_Motor_ENC + R_Motor_ENC) / 2;

    if (L_Motor_ENC > Motor_Middle_ENC)
      L_Motor_PWM -= 5;
    else if (L_Motor_ENC < Motor_Middle_ENC)
      L_Motor_PWM += 5;

    Motor_turn_run(L_Motor_PWM, R_Motor_PWM);
    break;

  case CAR_STATUS_BACK:
    Motor_Middle_ENC = (L_Motor_ENC + R_Motor_ENC) / 2;

    if (L_Motor_ENC > Motor_Middle_ENC)
      L_Motor_PWM -= 5;
    else if (L_Motor_ENC < Motor_Middle_ENC)
      L_Motor_PWM += 5;

    Motor_turn_back(L_Motor_PWM, R_Motor_PWM);
    break;

  case CAR_STATUS_LEFT:
    Motor_turn_left(L_Motor_PWM, R_Motor_PWM);
    break;

  case CAR_STATUS_RIGHT:
    Motor_turn_right(L_Motor_PWM, R_Motor_PWM);
    break;

  case CAR_STATUS_ON:
    Motor_turn_on();
    break;

  case CAR_STATUS_OFF:
    Motor_turn_off();
    break;
	
	case CAR_STATUS_STOP:
		Motor_turn_stop();
		break;
  default:
    break;
  }
}



/**
 * @brief  停止
 * @note
 * @retval None
 */
void Motor_turn_stop(void)
{
  L_MOTOR_IN0(GPIO_PIN_RESET);
  L_MOTOR_IN1(GPIO_PIN_RESET);
  R_MOTOR_IN0(GPIO_PIN_RESET);
  R_MOTOR_IN1(GPIO_PIN_RESET);
  L_MOTOR_PWM_OUT = R_MOTOR_PWM_OUT = 0;
  L_Motor_PWM = R_Motor_PWM = 0;
	systemValue.L_enc = systemValue.R_enc = 0;
}

/**
 * @brief  左转
 * @note
 * @param  l_pwm:
 * @param  r_pwm:
 * @retval None
 */
void Motor_turn_left(uint16_t l_pwm, uint16_t r_pwm)
{
  L_MOTOR_IN0(GPIO_PIN_SET);
  L_MOTOR_IN1(GPIO_PIN_RESET);
  R_MOTOR_IN0(GPIO_PIN_RESET);
  R_MOTOR_IN1(GPIO_PIN_SET);

  L_MOTOR_PWM_OUT = l_pwm;
  R_MOTOR_PWM_OUT = r_pwm;
}
/**
 * @brief  右转
 * @note
 * @param  l_pwm:
 * @param  r_pwm:
 * @retval None
 */
void Motor_turn_right(uint16_t l_pwm, uint16_t r_pwm)
{
  L_MOTOR_IN0(GPIO_PIN_RESET);
  L_MOTOR_IN1(GPIO_PIN_SET);
  R_MOTOR_IN0(GPIO_PIN_SET);
  R_MOTOR_IN1(GPIO_PIN_RESET);

  L_MOTOR_PWM_OUT = l_pwm;
  R_MOTOR_PWM_OUT = r_pwm;
}
/**
 * @brief  前进
 * @note
 * @param  l_pwm:
 * @param  r_pwm:
 * @retval None
 */
void Motor_turn_run(uint16_t l_pwm, uint16_t r_pwm)
{
  L_MOTOR_IN0(GPIO_PIN_SET);
  L_MOTOR_IN1(GPIO_PIN_RESET);
  R_MOTOR_IN0(GPIO_PIN_SET);
  R_MOTOR_IN1(GPIO_PIN_RESET);

  L_MOTOR_PWM_OUT = l_pwm;
  R_MOTOR_PWM_OUT = r_pwm;
}
/**
 * @brief  后退
 * @note
 * @param  l_pwm:
 * @param  r_pwm:
 * @retval None
 */
void Motor_turn_back(uint16_t l_pwm, uint16_t r_pwm)
{
  L_MOTOR_IN0(GPIO_PIN_RESET);
  L_MOTOR_IN1(GPIO_PIN_SET);
  R_MOTOR_IN0(GPIO_PIN_RESET);
  R_MOTOR_IN1(GPIO_PIN_SET);

  L_MOTOR_PWM_OUT = l_pwm;
  R_MOTOR_PWM_OUT = r_pwm;
}
/**
 * @brief  开启电机
 * @note
 * @retval None
 */
void Motor_turn_on(void)
{
  L_MOTOR_IN0(GPIO_PIN_SET);
  L_MOTOR_IN1(GPIO_PIN_SET);
  R_MOTOR_IN0(GPIO_PIN_SET);
  R_MOTOR_IN1(GPIO_PIN_SET);
  L_MOTOR_PWM_OUT = 0;
  R_MOTOR_PWM_OUT = 0;
	L_Motor_PWM = R_Motor_PWM = 0;
//	systemValue.L_enc = systemValue.R_enc = 0;
  HAL_TIM_PWM_Start(&htim16, TIM_CHANNEL_1); // 电机1
  HAL_TIM_PWM_Start(&htim17, TIM_CHANNEL_1); // 电机2
}
/**
 * @brief  关闭电机
 * @note
 * @retval None
 */
void Motor_turn_off(void)
{
  L_MOTOR_IN0(GPIO_PIN_RESET);
  L_MOTOR_IN1(GPIO_PIN_RESET);
  R_MOTOR_IN0(GPIO_PIN_RESET);
  R_MOTOR_IN1(GPIO_PIN_RESET);
  L_MOTOR_PWM_OUT = R_MOTOR_PWM_OUT = 0;
  L_Motor_PWM = R_Motor_PWM = 0;
//	systemValue.L_enc = systemValue.R_enc = 0;
  HAL_TIM_PWM_Stop(&htim16, TIM_CHANNEL_1); // 电机1
  HAL_TIM_PWM_Stop(&htim17, TIM_CHANNEL_1); // 电机2
}


