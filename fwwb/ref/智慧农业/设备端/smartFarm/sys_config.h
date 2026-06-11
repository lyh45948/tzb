#ifndef __SYS_CONFIG_H
#define __SYS_CONFIG_H

#include "cmsis_os2.h"
#include "hal_bsp_structAll.h"

// DeviceSecret fs12345678
// 设备ID
#define DEVICE_ID                           "625e6092861486498f17d400_hi3861_farm"
// MQTT客户端ID
#define MQTT_CLIENT_ID                      "625e6092861486498f17d400_hi3861_farm_0_0_2022041907"
// MQTT用户名
#define MQTT_USER_NAME                      "625e6092861486498f17d400_hi3861_farm"
// MQTT密码
#define MQTT_PASS_WORD                      "a0f638d09eeb7429ec2833089a7b78c48f8cead62e38fd621a57439abccfa938"
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
#define MQTT_PAYLOAD_PUB                    "{\"services\":[{\"service_id\":\"base\",\"properties\":{\"humidity\":%.1f,\"temperature\":%.1f,\"fan\":\"%s\",\"humi_up\":%d,\"humi_down\":%d,\"autoMode\":\"%s\"}}]}"

typedef struct
{
  int top;  // 上边距
  int left; // 下边距
} margin_t;     // 边距类型

typedef struct message_data
{
  unsigned char fanStatus;      // 风扇的状态
  float humidity;   // 湿度值
  float temperature; // 温度值
  hi_nv_save_sensor_threshold nvFlash;
  tn_pcf8574_io_t pcf8574_io;
}msg_data_t;

#endif

