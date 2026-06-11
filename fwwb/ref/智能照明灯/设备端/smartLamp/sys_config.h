#ifndef __SYS_CONFIG_H
#define __SYS_CONFIG_H

#include "cmsis_os2.h"
#include "hal_bsp_structAll.h"

// 设备密码 fs12345678
// 设备ID
#define DEVICE_ID                           "62032704de9933029be700e2_hi3861_lamp"
// MQTT客户端ID
#define MQTT_CLIENT_ID                      "62032704de9933029be700e2_hi3861_lamp_0_0_2022021905"
// MQTT用户名
#define MQTT_USER_NAME                      "62032704de9933029be700e2_hi3861_lamp"
// MQTT密码
#define MQTT_PASS_WORD                      "c4562c65eaf802903b9429ae46c148b453fe09a4dc15d9e6d53ee8cf99b37be0"
// 华为云平台的IP地址
#define SERVER_IP_ADDR                      "121.36.42.100"   
// 华为云平台的IP端口号
#define SERVER_IP_PORT                      1883  
// 订阅 接收控制命令的主题
#define MQTT_TOPIC_SUB_COMMANDS             "$oc/devices/%s/sys/commands/#" 
// 发布 成功接收到控制命令后的主题
#define MQTT_TOPIC_PUB_COMMANDS_REQ         "$oc/devices/%s/sys/commands/response/request_id=%s"  
#define MALLOC_MQTT_TOPIC_PUB_COMMANDS_REQ  "$oc/devices//sys/commands/response/request_id="  
   

// 发布 设备属性数据的主题
#define MQTT_TOPIC_PUB_PROPERTIES           "$oc/devices/%s/sys/properties/report"        
#define MALLOC_MQTT_TOPIC_PUB_PROPERTIES    "$oc/devices//sys/properties/report"        
#define MQTT_PAYLOAD_PUB                    "{\"services\":[{\"service_id\":\"base\",\"properties\":{\"light\":%d,\"lamp\":\"%s\",\"red\":%d,\"blue\":%d,\"green\":%d}}]}"

 // 三色灯的PWM值
typedef struct _RGB_Value {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
}RGB_Value_t;

// 三合一传感器
typedef struct _AP3216C_Value {
  uint16_t light; // 光照强度
  uint16_t proximity; // 接近传感器
  uint16_t infrared;  // 人体红外传感器
}AP3216C_Value_t;

// 灯的状态
typedef enum _Lamp_Status {
  OFF_LAMP = 0,
  SUN_LIGHT_MODE,   // 白光模式
  SLEEP_MODE,       // 睡眠模式
  READ_BOOK_MODE,   // 看书模式
  LED_BLINK_MODE,   // 闪烁模式
  SET_RGB_MODE,//   RGB调光模式
} Lamp_Status_t ;

typedef struct message_data
{
  uint16_t lamp_delay_time;    // 延时时间
  uint8_t is_auto_light_mode;    // 是否开启光照自动控制
  uint8_t led_light_value;    // 灯的亮度控制值

  RGB_Value_t RGB_Value;    // RGB灯控制

  Lamp_Status_t Lamp_Status;    // 控制灯是否开灯
  AP3216C_Value_t AP3216C_Value;  // 三合一传感器的数据
}msg_data_t;


// 日期、时间
typedef struct date_time_value 
{
  uint16_t yaer;
  uint8_t month;
  uint8_t date;
  uint8_t hour;
  uint8_t min;
  uint8_t sec;
}date_time_value_t;


#endif

