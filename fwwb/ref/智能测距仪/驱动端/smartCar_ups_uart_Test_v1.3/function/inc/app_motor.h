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


void Motor_turn_on(void);
void Motor_turn_off(void);
void Motor_turn_stop(void);
void Motor_turn_run(uint16_t l_pwm, uint16_t r_pwm);
void Motor_turn_left(uint16_t l_pwm, uint16_t r_pwm);
void Motor_turn_back(uint16_t l_pwm, uint16_t r_pwm);
void Motor_turn_right(uint16_t l_pwm, uint16_t r_pwm);
void motor_encoder_init(void); 
uint32_t motor_read_encoder(te_L_R_Motor_t motor);
void parse_json_data(uint8_t *pstr, uint16_t len);
void packet_json_data(ts_SystemValue_t *sysData);


#endif

