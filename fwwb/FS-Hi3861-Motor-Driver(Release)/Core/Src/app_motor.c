#include "app_motor.h"
#include "system_cfg.h"
#include <string.h>
#include <stdlib.h>
#include "cJSON.h"
#include "usart.h"

volatile uint8_t gMotorStatus = 0;	//PWM输出是否开启
extern volatile uint8_t gLineOut;	//光电管输出
extern volatile uint8_t gLineType;	//巡线的类型

/**
 * 现在所用的直流减速电机的型号为:
 * 单向脉冲编码器
 * 减速比：1:48
 * 空载转速：200RPM
 * 编码器线数：11线
 * 编码器精度：528线
 * 
 * 小车直径65mm，一圈的距离C = π * d = 3.14 * 65 mm = 204mm ，转一圈的脉冲为528个，一个脉冲距离为204/528 = 0.387mm
 * 编码器捕获采用双边沿计数，编码器精度528线，读取脉冲计数为528 * 2 = 1056 个脉冲
 * 调速周期为20ms一次，1秒调速50次，读取码盘的周期为20ms，注意全速下，码盘脉冲周期为300us左右，20ms最多计数140次左右
 * 最小速度设置为:200mm/s 表示20ms周期计数34个脉冲左右;最大速度设置为:1400mm/s 表示20ms周期计数140个脉冲
 * 速度值作为参考，实际速度有偏差，低速下，电机扭矩偏小，容易堵转，速度步增值为10
 */

__IO uint32_t left_encoder_temp, right_encoder_temp; // 左电机和右电机的编码器脉冲计数值 - 临时值
//
uint16_t L_Motor_PWM, R_Motor_PWM;
uint16_t L_Motor_ENC, R_Motor_ENC;
uint32_t L_enc_sum = 0, R_enc_sum = 0; // 用于 100ms 周期的速度累加
volatile uint16_t gAutoModeBaseSpeed = 250; // 自动模式全局基准速度
volatile uint32_t gModeLockTick = 0;        // 模式切换锁定计时器
//左右电机的PID参数结构体定义
TYPEDEF_PID_STRUCT gL_MotorPID;	
TYPEDEF_PID_STRUCT gR_MotorPID;	
//PID参数初始化
void PID_init(void)
{	
	//左电机
	gL_MotorPID.SetSpeed = 0.0;
	gL_MotorPID.ActualSpeed = 0.0;
	gL_MotorPID.err = 0.0;
	gL_MotorPID.err_next = 0.0;
	gL_MotorPID.err_last = 0.0;
	gL_MotorPID.Kp = 0.5;  // 降低比例系数，起步更柔和
	gL_MotorPID.Ki = 0.15; // 稍微降低积分
	gL_MotorPID.Kd = 0.01; // 引入微量微分，抑制过冲
	//右电机
	gR_MotorPID.SetSpeed = 0.0;
	gR_MotorPID.ActualSpeed = 0.0;
	gR_MotorPID.err = 0.0;
	gR_MotorPID.err_next = 0.0;
	gR_MotorPID.err_last = 0.0;
	gR_MotorPID.Kp = 0.5;
	gR_MotorPID.Ki = 0.15;
	gR_MotorPID.Kd = 0.01;
}

//增量式PID控制算法
float PID_Control_Algorithm(float TargetSpeed, float ActualSpeed, TYPEDEF_PID_STRUCT *PID)
{
	float incrementSpeed;
	//设置速度
	PID->SetSpeed = TargetSpeed;
	//计算误差
	PID->err = PID->SetSpeed - ActualSpeed ;
	//算法实现
	incrementSpeed = PID->Kp * (PID->err - PID->err_next) + PID->Ki * PID->err + PID->Kd * (PID->err - 2 * PID->err_next + PID->err_last);
	
	// --- 新增：起步限幅与平滑处理 ---
	// 限制单次调节的最大增量，防止动力突然爆发
	if (incrementSpeed > 40.0f)  incrementSpeed = 40.0f;
	if (incrementSpeed < -40.0f) incrementSpeed = -40.0f;
	
	PID->ActualSpeed += incrementSpeed;
	//保存误差
	PID->err_last = PID->err_next ;
	PID->err_next = PID->err ;
	
	// 对输出值（PWM）进行限制，但不应影响 ActualSpeed 变量作为速度的记录
	float output = PID->ActualSpeed;
	if(output < 0) output = 0; // 防止负数
	if(output > 1000) output = 1000;
	
    // 渐进式死区处理：不再直接跳到 150，而是作为最低输出保障
    if(TargetSpeed > 0 && output < 120) output = 120; 
    if(TargetSpeed == 0) output = 0;

	return output;
}
/*
 * 定时器的输入捕获上升沿触发的中断回调函数
 *
 */
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
        // 手工控制具有最高权限，一旦触发任何转向/停止指令，立即退出自动模式 (如路径规划、巡线)
        systemValue.car_mode = CAR_MODE_MANUAL;
        
        if (!strcmp(json_turn->valuestring, "run"))
        {
          systemValue.car_status = CAR_STATUS_RUN;
        }
        else if (!strcmp(json_turn->valuestring, "back"))
        {
          systemValue.car_status = CAR_STATUS_BACK;
        }
        else if (!strcmp(json_turn->valuestring, "left"))
        {
          systemValue.car_status = CAR_STATUS_LEFT;
        }
        else if (!strcmp(json_turn->valuestring, "right"))
        {
          systemValue.car_status = CAR_STATUS_RIGHT;
        }
				else if (!strcmp(json_turn->valuestring, "stop"))
        {
          systemValue.car_status = CAR_STATUS_STOP;
        }
      }
      json_turn = NULL;

      cJSON *json_power = cJSON_GetObjectItem(json_control, "power");
      if (json_power)
      {
        if (!strcmp(json_power->valuestring, "on"))
        {
          systemValue.car_status = CAR_STATUS_ON;
        }
        else if (!strcmp(json_power->valuestring, "off"))
        {
          systemValue.car_status = CAR_STATUS_OFF;
        }
      }
      json_power = NULL;

      cJSON *json_pwm = cJSON_GetObjectItem(json_control, "pwm");
      if (json_pwm)
      {
        cJSON *json_L_pwm = cJSON_GetObjectItem(json_pwm, "L_Motor");
        cJSON *json_R_pwm = cJSON_GetObjectItem(json_pwm, "R_Motor");
				//保存设置的目标速度，手动档位物理速度翻倍
				if((json_L_pwm->valueint) == 390)	//低速档
				{
					gL_MotorPID.SetSpeed = 500;	// 原 250
					gR_MotorPID.SetSpeed = 500;
				}
				else if((json_L_pwm->valueint) == 420)	//中速档
				{
					gL_MotorPID.SetSpeed = 800;	// 原 400
					gR_MotorPID.SetSpeed = 800;
				}
				else if((json_L_pwm->valueint) == 450)	//高速档
				{
					gL_MotorPID.SetSpeed = 1100; // 原 550
					gR_MotorPID.SetSpeed = 1100;
				}
      }
      json_pwm = NULL;

      cJSON *json_mode = cJSON_GetObjectItem(json_control, "mode");
      if (json_mode)
      {
        extern uint8_t gLastSensorMode;
        gModeLockTick = HAL_GetTick(); // 记录切换时间，开启锁定保护
        
        if (!strcmp(json_mode->valuestring, "manual")) {
          systemValue.car_mode = CAR_MODE_MANUAL;
          gLastSensorMode = 0x00; 
        } else if (!strcmp(json_mode->valuestring, "avoid")) {
          systemValue.car_mode = CAR_MODE_AVOID;
          gLastSensorMode = 0x0D;
        } else if (!strcmp(json_mode->valuestring, "line")) {
          systemValue.car_mode = CAR_MODE_LINE;
          gLastSensorMode = 0x0F;
        } else if (!strcmp(json_mode->valuestring, "path")) {
          // 解析路径点坐标
          cJSON *json_d = cJSON_GetObjectItem(json_control, "d");
          cJSON *json_a = cJSON_GetObjectItem(json_control, "a");

          // 如果没有坐标参数，说明是“模式切换”或“复位信号”
          if (json_d == NULL && json_a == NULL) {
            systemValue.path_count = 0;
            systemValue.path_index = 0;
            gMotorStatus = 0; // 强制清除状态机，触发 Car_path_planning 重新初始化
          } 
          else {
            // 如果带坐标参数，存入队列
            if (systemValue.path_count < PATH_QUEUE_SIZE) {
              systemValue.path_queue[systemValue.path_count].d = json_d->valueint;
              systemValue.path_queue[systemValue.path_count].a = json_a->valueint;
              systemValue.path_count++;
            }
          }
          systemValue.car_mode = CAR_MODE_PATH;
          gLastSensorMode = 0x0E;
        }
      }
      
      cJSON *json_speed_val = cJSON_GetObjectItem(json_control, "speed");
      if (json_speed_val)
      {
          gAutoModeBaseSpeed = json_speed_val->valueint;
      }
      
      cJSON *json_joyX = cJSON_GetObjectItem(json_control, "joyX");
      cJSON *json_joyY = cJSON_GetObjectItem(json_control, "joyY");
      if (json_joyX != NULL && json_joyY != NULL)
      {
          int16_t x = (int16_t)json_joyX->valueint;
          int16_t y = (int16_t)json_joyY->valueint;

          // 只有当摇杆偏离中心时才视为“人工操作”，从而打断自动模式
          // 摇杆归中心 (0,0) 时不打断当前任务 (如路径规划)
          if (x != 0 || y != 0) {
              systemValue.car_mode = CAR_MODE_MANUAL;
          }

          systemValue.joyX = x;
          systemValue.joyY = y;
          systemValue.car_status = CAR_STATUS_JOYSTICK;
          gModeLockTick = HAL_GetTick(); // 摇杆操作也视为指令更新
      }

      json_mode = NULL;
			
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
  uint8_t packet_buff[120] = {0};
  char mode_str[10];
  
  __disable_irq();
  uint32_t l_sum = L_enc_sum;
  uint32_t r_sum = R_enc_sum;
  L_enc_sum = 0;
  R_enc_sum = 0;
  __enable_irq();

  if(sysData->car_mode == CAR_MODE_MANUAL) strcpy(mode_str, "manual");
  else if(sysData->car_mode == CAR_MODE_AVOID) strcpy(mode_str, "avoid");
  else if(sysData->car_mode == CAR_MODE_LINE) strcpy(mode_str, "line");
  else if(sysData->car_mode == CAR_MODE_PATH) strcpy(mode_str, "path");
  else strcpy(mode_str, "manual");

  // 这里的换算改为更直观的模式：100ms内的脉冲数 * 4 即可得到反馈单位 (与微信端 Scale 匹配)
  int l_spd_val = (int)(l_sum * 4); 
  int r_spd_val = (int)(r_sum * 4);

  // --- 根据 GPIO 电平判断方向 (IN1 为 SET 表示后退) ---
  if (HAL_GPIO_ReadPin(M2_IN1_GPIO_Port, M2_IN1_Pin) == GPIO_PIN_SET) {
      l_spd_val = -l_spd_val;
  }
  if (HAL_GPIO_ReadPin(M1_IN1_GPIO_Port, M1_IN1_Pin) == GPIO_PIN_SET) {
      r_spd_val = -r_spd_val;
  }

  // 极简 JSON，不含空格，减少串口负担
  sprintf((char *)packet_buff, "{\"status\":{\"dist\":%d,\"volt\":%d,\"L_spd\":%d,\"R_spd\":%d,\"mode\":\"%s\"}}",
          sysData->distance, sysData->battery, l_spd_val, r_spd_val, mode_str);

  HAL_UART_Transmit(&huart1, packet_buff, strlen((char *)packet_buff), 50); 
}

/**
 * @brief  向传感器板发送实时速度数据用于转向灯
 * @note   格式：0xBB, L_speed(H), L_speed(L), R_speed(H), R_speed(L), CheckSum
 * @retval None
 */
void send_speed_to_sensor(void)
{
  uint8_t speed_packet[8]; // 增加到 8 字节
  // 使用编码器脉冲值作为速度参考，更实时
  uint16_t l_speed = (uint16_t)L_Motor_ENC;
  uint16_t r_speed = (uint16_t)R_Motor_ENC;

  speed_packet[0] = 0xBB; // 帧头
  speed_packet[1] = (l_speed >> 8) & 0xFF;
  speed_packet[2] = l_speed & 0xFF;
  speed_packet[3] = (r_speed >> 8) & 0xFF;
  speed_packet[4] = r_speed & 0xFF;
  
  // 决定发送给传感器板的状态：如果是摇杆模式且正在后退，则上报后退状态(2)
  uint8_t report_status = (uint8_t)systemValue.car_status;
  if (report_status == CAR_STATUS_JOYSTICK && systemValue.joyY < 0) {
      report_status = CAR_STATUS_BACK;
  }
  speed_packet[5] = report_status; 
  
  speed_packet[6] = (uint8_t)systemValue.car_mode;   // 发送车辆当前模式
  
  uint8_t sum = 0;
  for(int i = 0; i < 7; i++) sum += speed_packet[i];
  speed_packet[7] = sum;

  HAL_UART_Transmit(&huart2, speed_packet, 8, 10);
}

// 10ms产生一个中断
volatile uint16_t TIM3_Times_Count = 0;
//
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  if (htim->Instance == TIM3) 
  {
		TIM3_Times_Count++;
		if(!(TIM3_Times_Count % 2))
		{
			TIM3_Times_Count = 0;
			//读取编码器值
			uint32_t l_pulse = motor_read_encoder(L_MOTOR);
			uint32_t r_pulse = motor_read_encoder(R_MOTOR);
			
			systemValue.L_enc = (uint16_t)l_pulse;
			systemValue.R_enc = (uint16_t)r_pulse;
			
			// 累加脉冲用于 100ms 速度显示
			L_enc_sum += l_pulse;
			R_enc_sum += r_pulse;

			//设置输出PWM
			motor_control_running_status(systemValue.car_status);
		}
  }
}

// 自动避障状态机
#define AVOID_STATE_IDLE   0x00	
#define AVOID_STATE_BACK   0x01	
#define AVOID_STATE_TURN   0x02	

static uint8_t  gAvoidState   = AVOID_STATE_IDLE;  
static uint16_t gAvoidCounter = 0;                 

void motor_control_running_status(te_car_status_t status)
{
	L_Motor_ENC = systemValue.L_enc;
	R_Motor_ENC = systemValue.R_enc;

    // 如果处于模式切换锁定期间（500ms），优先执行当前模式，忽略来自传感器板的旧指令冲突
    if (HAL_GetTick() - gModeLockTick < 500)
    {
        // 锁定期间，跳过传感器板的按键同步判断，直接进入模式执行
    }

	// --- 1. 自动模式判断 ---
	if (systemValue.car_mode == CAR_MODE_LINE || systemValue.car_mode == CAR_MODE_AVOID)
	{
		Car_search_black_Line();
		return;
	}
	else if (systemValue.car_mode == CAR_MODE_PATH)
	{
		Car_path_planning();
		return;
	}

	// --- 2. 手动控制或自动避障执行 (统一反馈单位为 mm/s, 系数约为 19) ---
    // 手动按键模式下，只有在真正的运动指令下才赋予目标速度
    if (systemValue.car_mode == CAR_MODE_MANUAL && status != CAR_STATUS_JOYSTICK)
    {
        if (status == CAR_STATUS_RUN || status == CAR_STATUS_BACK || 
            status == CAR_STATUS_LEFT || status == CAR_STATUS_RIGHT) 
        {
            gL_MotorPID.SetSpeed = (float)gAutoModeBaseSpeed;
            gR_MotorPID.SetSpeed = (float)gAutoModeBaseSpeed;
        }
        else 
        {
            gL_MotorPID.SetSpeed = 0;
            gR_MotorPID.SetSpeed = 0;
            gL_MotorPID.ActualSpeed = 0;
            gR_MotorPID.ActualSpeed = 0;
            gL_MotorPID.err = 0; gL_MotorPID.err_next = 0; gL_MotorPID.err_last = 0;
            gR_MotorPID.err = 0; gR_MotorPID.err_next = 0; gR_MotorPID.err_last = 0;
        }
    }

	L_Motor_PWM = (uint16_t) PID_Control_Algorithm(gL_MotorPID.SetSpeed, L_Motor_ENC * 9.67f, &gL_MotorPID);
	R_Motor_PWM = (uint16_t) PID_Control_Algorithm(gR_MotorPID.SetSpeed, R_Motor_ENC * 9.67f, &gR_MotorPID);

  switch (status)
  {
    case CAR_STATUS_RUN:	// 前进
      Motor_turn_run(L_Motor_PWM, R_Motor_PWM);
    break;

    case CAR_STATUS_BACK:	// 后退
      Motor_turn_back(L_Motor_PWM, R_Motor_PWM);
    break;

    case CAR_STATUS_LEFT:	// 左转 (改为 PID 闭环)
			Motor_turn_left(L_Motor_PWM, R_Motor_PWM);
    break;

    case CAR_STATUS_RIGHT:	// 右转 (改为 PID 闭环)
			Motor_turn_right(L_Motor_PWM, R_Motor_PWM);
    break;

    case CAR_STATUS_ON:
			Motor_turn_on();	// 开启PWM输出
    break;

    case CAR_STATUS_OFF:
			// 速度值归零
			gL_MotorPID.ActualSpeed = 0.0;
			gR_MotorPID.ActualSpeed = 0.0;		
			gMotorStatus = 0x00;	
			Motor_turn_off();	// 关闭PWM输出
    break;
	
    case CAR_STATUS_STOP:	// PWM输出为零
			// 速度值归零
			gL_MotorPID.ActualSpeed = 0.0;
			gR_MotorPID.ActualSpeed = 0.0;
			Motor_turn_stop();
		break;
		
    case CAR_STATUS_JOYSTICK:
    {
        // 摇杆差速运动学模型 (回归标准逻辑：L=Y+X, R=Y-X)
        // 范围 joyX, joyY 为 -100 ~ 100
        float v_limit = (float)gAutoModeBaseSpeed;
        
        // --- 取消原地自旋逻辑 ---
        // 只有当有纵向分量(Y)时，横向分量(X)才生效
        float steering_factor = (float)abs(systemValue.joyY) / 100.0f;
        if (steering_factor < 0.15f) steering_factor = 0.0f; 

        // 标准差速叠加公式 (倒车时 X 轴反向，确保转向逻辑符合后退直觉)
        float target_l, target_r;
        if (systemValue.joyY >= 0) {
            target_l = (float)(systemValue.joyY + systemValue.joyX * steering_factor) * (v_limit / 100.0f);
            target_r = (float)(systemValue.joyY - systemValue.joyX * steering_factor) * (v_limit / 100.0f);
        } else {
            target_l = (float)(systemValue.joyY - systemValue.joyX * steering_factor) * (v_limit / 100.0f);
            target_r = (float)(systemValue.joyY + systemValue.joyX * steering_factor) * (v_limit / 100.0f);
        }
        
        // 限制目标速度不超标
        if(target_l > v_limit) target_l = v_limit;
        if(target_l < -v_limit) target_l = -v_limit;
        if(target_r > v_limit) target_r = v_limit;
        if(target_r < -v_limit) target_r = -v_limit;

        // 设置左电机方向 (target_l > 0 为前进)
        if (target_l >= 0) {
            L_MOTOR_IN0(GPIO_PIN_SET); L_MOTOR_IN1(GPIO_PIN_RESET);
        } else {
            L_MOTOR_IN0(GPIO_PIN_RESET); L_MOTOR_IN1(GPIO_PIN_SET);
            target_l = -target_l;
        }
        
        // 设置右电机方向 (target_r > 0 为前进)
        if (target_r >= 0) {
            R_MOTOR_IN0(GPIO_PIN_SET); R_MOTOR_IN1(GPIO_PIN_RESET);
        } else {
            R_MOTOR_IN0(GPIO_PIN_RESET); R_MOTOR_IN1(GPIO_PIN_SET);
            target_r = -target_r;
        }
        
        // PID 闭环计算 (使用绝对值目标速)
        L_Motor_PWM = (uint16_t) PID_Control_Algorithm(target_l, L_Motor_ENC * 9.67f, &gL_MotorPID);
        R_Motor_PWM = (uint16_t) PID_Control_Algorithm(target_r, R_Motor_ENC * 9.67f, &gR_MotorPID);
        
        L_MOTOR_PWM_OUT = L_Motor_PWM;
        R_MOTOR_PWM_OUT = R_Motor_PWM;
        
        // 如果摇杆回到中心，进入停止逻辑
        if (systemValue.joyX == 0 && systemValue.joyY == 0) {
            gL_MotorPID.ActualSpeed = 0.0;
            gR_MotorPID.ActualSpeed = 0.0;
            gL_MotorPID.err = 0; gL_MotorPID.err_next = 0; gL_MotorPID.err_last = 0;
            gR_MotorPID.err = 0; gR_MotorPID.err_next = 0; gR_MotorPID.err_last = 0;
            Motor_turn_stop();
        }
    }
    break;

    default:
    break;
  }
}
//巡线模式，黑色非反光胶带，宽度20mm，白色背景，巡线指示灯为绿色，非白色背景，巡线指示灯黄色、红色或者白色
void Car_search_black_Line(void)
{

	//进入巡线模式，先开启PWM输出
	if(gMotorStatus == 0x00)	//未初始化PWM输出
	{
		gMotorStatus = 0xFF;
		Motor_turn_on();	//开启PWM输出
	}
	
	// 如果正在避障，跳过巡线逻辑，直接执行避障动作
	if (gAvoidState != AVOID_STATE_IDLE)
	{
		// 避障状态下，不执行巡线逻辑，直接跳到避障状态机处理
	}
	else
	{
		// 正常巡线模式：根据gLineOut信号，调节左右电机转速
		switch (gLineOut)
		{
			case 0xFE:	// 极左偏移，大幅右转
			case 0xFD:
				gL_MotorPID.SetSpeed = gAutoModeBaseSpeed * 0.4f; 
				gR_MotorPID.SetSpeed = gAutoModeBaseSpeed * 1.2f; 
				break;

			case 0xFB:	// 稍微偏左
				gL_MotorPID.SetSpeed = gAutoModeBaseSpeed * 0.7f; 
				gR_MotorPID.SetSpeed = gAutoModeBaseSpeed * 1.1f; 
				break;

			case 0xE7:	// 正中，稳定前进
				gL_MotorPID.SetSpeed = gAutoModeBaseSpeed; 
				gR_MotorPID.SetSpeed = gAutoModeBaseSpeed; 
				break;

			case 0xDF:	// 稍微偏右
				gL_MotorPID.SetSpeed = gAutoModeBaseSpeed * 1.1f; 
				gR_MotorPID.SetSpeed = gAutoModeBaseSpeed * 0.7f; 
				break;

			case 0xBF:	// 较右偏移
			case 0x7F:
				gL_MotorPID.SetSpeed = gAutoModeBaseSpeed * 1.2f; 
				gR_MotorPID.SetSpeed = gAutoModeBaseSpeed * 0.4f; 
				break;

			case 0xFF:  // 丢线（全白），慢速搜索
			default:
				gL_MotorPID.SetSpeed = gAutoModeBaseSpeed * 0.6f; 
				gR_MotorPID.SetSpeed = gAutoModeBaseSpeed * 0.6f;
				break;
		}

		// 统一计算 PWM 值，反馈单位统一为 mm/s
		L_Motor_PWM = (uint16_t) PID_Control_Algorithm(gL_MotorPID.SetSpeed, L_Motor_ENC * 9.67f, &gL_MotorPID);
		R_Motor_PWM = (uint16_t) PID_Control_Algorithm(gR_MotorPID.SetSpeed, R_Motor_ENC * 9.67f, &gR_MotorPID);
	}
	
	// ========== 避障状态机处理 ==========
	// 状态机流程：IDLE -> BACK -> TURN -> IDLE
	// 
	// 触发条件：检测到前方距离 <= 150mm
	// BACK状态：后退约1秒，远离障碍物
	// TURN状态：左转搜索新路线，如果前方安全则恢复巡线，否则最多转2秒后强制恢复
	
	// 如果当前没有在避障状态且探测到前方距离过近，则进入避障状态
	if ((gAvoidState == AVOID_STATE_IDLE) && (systemValue.distance <= 150))	//距离小于150mm
	{
		gAvoidState   = AVOID_STATE_BACK;
		gAvoidCounter = 0;
	}

	// 根据避障状态执行相应动作
	if (gAvoidState == AVOID_STATE_IDLE)
	{
		// 正常巡线输出
		if(systemValue.distance <= 150)	// 冗余保护：万一上面的判定遗漏
		{
			Motor_turn_stop();
			gL_MotorPID.SetSpeed = 0; 
			gR_MotorPID.SetSpeed = 0; 
		}
		else	//前方安全，正常巡线
		{
			Motor_turn_run(L_Motor_PWM, R_Motor_PWM);
		}
	}
	else
	{
		// 避障状态机执行
		switch (gAvoidState)
		{
			case AVOID_STATE_BACK:	// 后退状态 (速度与对应档位的手动倒车一致)
				L_Motor_PWM = (uint16_t) PID_Control_Algorithm(gAutoModeBaseSpeed, L_Motor_ENC * 9.67f, &gL_MotorPID);
				R_Motor_PWM = (uint16_t) PID_Control_Algorithm(gAutoModeBaseSpeed, R_Motor_ENC * 9.67f, &gR_MotorPID);
				Motor_turn_back(L_Motor_PWM, R_Motor_PWM);
				gAvoidCounter++;
				if (gAvoidCounter >= 50)		// 约 1s
				{
					gAvoidCounter = 0;
					gAvoidState   = AVOID_STATE_TURN; 
				}
			break;

			case AVOID_STATE_TURN:	// 左弯状态 (速度与对应档位的手动转向一致)
				L_Motor_PWM = (uint16_t) PID_Control_Algorithm(gAutoModeBaseSpeed, L_Motor_ENC * 9.67f, &gL_MotorPID);
				R_Motor_PWM = (uint16_t) PID_Control_Algorithm(gAutoModeBaseSpeed, R_Motor_ENC * 9.67f, &gR_MotorPID);
				Motor_turn_left(L_Motor_PWM, R_Motor_PWM);
				gAvoidCounter++;
				if (gAvoidCounter >= 50)		// 约 1s 左转后检查
				{
					// 如果此时前方已经没有障碍，则回到正常巡线
					if (systemValue.distance > 150)
					{
						gAvoidCounter = 0;
						gAvoidState = AVOID_STATE_IDLE;  // 恢复巡线
					}
					// 如果前方仍有障碍，继续左转（最多再转1秒，总共2秒）
					else if (gAvoidCounter >= 100)  // 如果转了2秒还没找到路，强制恢复
					{
						gAvoidCounter = 0;
						gAvoidState = AVOID_STATE_IDLE;  // 强制恢复巡线
					}
					// 否则继续左转（gAvoidCounter继续累加，等待下次检查）
				}
			break;

			default:	// 异常状态，强制恢复
				gAvoidState   = AVOID_STATE_IDLE;
				gAvoidCounter = 0;
				Motor_turn_stop();
			break;
		}
	}
	
}
//
/**
 * @brief  路径规划模式 - 执行动态路径指令缓冲区
 * @note   基于编码器脉冲精确控制：依次执行队列中的 (旋转角度 -> 行进距离)
 * @retval None
 */
void Car_path_planning(void)
{
	static uint32_t step_pulses = 0;   // 当前步骤已行驶的脉冲总数
	static uint8_t  sub_step = 0;      // 0: 旋转, 1: 直行
	static uint32_t target_pulses = 0;
	static uint16_t stop_delay = 0;    // 停顿计时器

	// 比例常数 (基于 528线电机 & 65mm 轮径)
	// 修正：如果转多了，降低 PULSES_PER_DEG。原值 14.83 (1335/90) 调整为 14.0
	const float PULSES_PER_DEG = 12.9f; 
	const float PULSES_PER_MM  = 5.17f;  // 1056/204

	// 处于停顿等待期
	if (stop_delay > 0) {
		stop_delay--;
		Motor_turn_stop();
		return;
	}

	// 进入路径规划模式，初始化状态
	if(gMotorStatus != 0xEE) 
	{
		gMotorStatus = 0xEE;
		Motor_turn_on();
		step_pulses = 0;
		sub_step = 0;
		PID_init(); 
		target_pulses = 0; 
		stop_delay = 0;
	}

	// 检查是否所有点都执行完毕，或者队列还是空的
	if (systemValue.path_index >= systemValue.path_count) {
		Motor_turn_stop();
		return;
	}

	ts_PathPoint_t *current_point = &systemValue.path_queue[systemValue.path_index];

	// 如果当前没有目标脉冲（刚开始或点位刚到），加载当前点的目标值
	if (target_pulses == 0) {
		if (sub_step == 0) {
			target_pulses = (uint32_t)(abs(current_point->a) * PULSES_PER_DEG);
		} else {
			target_pulses = (uint32_t)(current_point->d * PULSES_PER_MM);
		}
	}

	// 累计当前 20ms 周期的平均脉冲
	step_pulses += (L_Motor_ENC + R_Motor_ENC) / 2;
	
	if(sub_step == 0) // 子步骤0：旋转
	{
		// 如果角度为0，直接跳过旋转
		if (current_point->a == 0) {
			sub_step = 1;
			step_pulses = 0;
			target_pulses = (uint32_t)(current_point->d * PULSES_PER_MM);
			return;
		}

		float turn_speed = (float)gAutoModeBaseSpeed * 0.7f;
		uint32_t remain = (target_pulses > step_pulses) ? (target_pulses - step_pulses) : 0;
		// 稍微平滑化转向减速
		if (remain < 150) turn_speed *= 0.5f;

		gL_MotorPID.SetSpeed = turn_speed; 
		gR_MotorPID.SetSpeed = turn_speed; 
		L_Motor_PWM = (uint16_t) PID_Control_Algorithm(gL_MotorPID.SetSpeed, L_Motor_ENC * 9.67f, &gL_MotorPID);
		R_Motor_PWM = (uint16_t) PID_Control_Algorithm(gR_MotorPID.SetSpeed, R_Motor_ENC * 9.67f, &gR_MotorPID);

		if (current_point->a > 0) {
			systemValue.car_status = CAR_STATUS_RIGHT;
			Motor_turn_right(L_Motor_PWM, R_Motor_PWM);
		} else {
			systemValue.car_status = CAR_STATUS_LEFT;
			Motor_turn_left(L_Motor_PWM, R_Motor_PWM);
		}

		if(step_pulses >= target_pulses) 
		{
			// 大角度转向后（>20度）强制停止并复位PID，确保惯性不影响后续直行精准度
			if (abs(current_point->a) > 20) {
				Motor_turn_stop();
				PID_init(); 
				stop_delay = 15; // 停顿约 300ms (15 * 20ms)
			}
			step_pulses = 0;
			sub_step = 1;
			target_pulses = 0; 
		}
	}
	else // 子步骤1：直行
	{
		systemValue.car_status = CAR_STATUS_RUN; 
		float run_speed = (float)gAutoModeBaseSpeed;
		
		uint32_t remain = (target_pulses > step_pulses) ? (target_pulses - step_pulses) : 0;
		// 减缓减速力度，让运动更连贯
		if (remain < 200) run_speed *= 0.5f;

		gL_MotorPID.SetSpeed = run_speed; 
		gR_MotorPID.SetSpeed = run_speed; 
		L_Motor_PWM = (uint16_t) PID_Control_Algorithm(gL_MotorPID.SetSpeed, L_Motor_ENC * 9.67f, &gL_MotorPID);
		R_Motor_PWM = (uint16_t) PID_Control_Algorithm(gR_MotorPID.SetSpeed, R_Motor_ENC * 9.67f, &gR_MotorPID);
		Motor_turn_run(L_Motor_PWM, R_Motor_PWM);

		if(step_pulses >= target_pulses) 
		{
			// 如果下一个点的转向角度很大（>20度），则先完全停稳再开始转弯
			if (systemValue.path_index + 1 < systemValue.path_count) {
				if (abs(systemValue.path_queue[systemValue.path_index + 1].a) > 20) {
					Motor_turn_stop();
					PID_init();
					stop_delay = 15; // 停顿约 300ms
				}
			}
			step_pulses = 0;
			sub_step = 0;
			systemValue.path_index++;
			target_pulses = 0; 
		}
	}
}
//
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
  // 左轮前进 + 右轮后退 = 原地右转 (逻辑名与物理名修正)
  // 如果逻辑反了，则在此处对换 SET/RESET
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
  // 左轮后退 + 右轮前进 = 原地左转
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
  // 开启时先确保所有状态清零，防止漂移
  PID_init();
  L_MOTOR_IN0(GPIO_PIN_RESET);
  L_MOTOR_IN1(GPIO_PIN_RESET);
  R_MOTOR_IN0(GPIO_PIN_RESET);
  R_MOTOR_IN1(GPIO_PIN_RESET);
  L_MOTOR_PWM_OUT = 0;
  R_MOTOR_PWM_OUT = 0;
  L_Motor_PWM = R_Motor_PWM = 0;
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
