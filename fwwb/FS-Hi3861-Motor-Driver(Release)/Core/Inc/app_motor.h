#ifndef __APP_MOTOR_H
#define __APP_MOTOR_H

#include "tim.h"
#include "system_cfg.h"

#define MOTOR_DEAD_ZONE   300 // 电机的死区值

#define L_MOTOR_PWM_OUT  TIM16->CCR1    // 左电机PWM输出
#define R_MOTOR_PWM_OUT  TIM17->CCR1    // 右电机PWM输出
#define L_MOTOR_IN0(value)    HAL_GPIO_WritePin(M2_IN0_GPIO_Port, M2_IN0_Pin, value)
#define L_MOTOR_IN1(value)    HAL_GPIO_WritePin(M2_IN1_GPIO_Port, M2_IN1_Pin, value)
#define R_MOTOR_IN0(value)    HAL_GPIO_WritePin(M1_IN0_GPIO_Port, M1_IN0_Pin, value)
#define R_MOTOR_IN1(value)    HAL_GPIO_WritePin(M1_IN1_GPIO_Port, M1_IN1_Pin, value)
//PID结构体声明
typedef struct
{
		float SetSpeed;   //定义设定值
		float ActualSpeed; //定义实际值
		float err ;        // 定义偏差值
		float err_next;    //定义上一个偏差值
		float err_last;    //定义上上一个偏差值
		float Kp,Ki,Kd;    //定义比例、积分、微分系数
 } TYPEDEF_PID_STRUCT;
//调用接口
void PID_init(void);
float PID_Control_Algorithm(float TargetSpeed, float ActualSpeed, TYPEDEF_PID_STRUCT *PID);
//
void Motor_turn_on(void);
void Motor_turn_off(void);
void Motor_turn_stop(void);
void Car_search_black_Line(void);
void Motor_turn_run(uint16_t l_pwm, uint16_t r_pwm);
void Motor_turn_left(uint16_t l_pwm, uint16_t r_pwm);
void Motor_turn_back(uint16_t l_pwm, uint16_t r_pwm);
void Motor_turn_right(uint16_t l_pwm, uint16_t r_pwm);
void Car_path_planning(void);
void send_speed_to_sensor(void);
void motor_encoder_init(void); 
uint32_t motor_read_encoder(te_L_R_Motor_t motor);
void parse_json_data(uint8_t *pstr, uint16_t len);
void packet_json_data(ts_SystemValue_t *sysData);
void motor_control_running_status(te_car_status_t status);

#endif

