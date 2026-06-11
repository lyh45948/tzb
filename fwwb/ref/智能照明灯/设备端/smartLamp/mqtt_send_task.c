#include "mqtt_send_task.h"
#include "sys_config.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include "cJSON.h"
#include "cmsis_os2.h"

#include "hal_bsp_log.h"
#include "hal_bsp_mqtt.h"

#include "oled_show.h"

extern msg_data_t sys_msg_data;

void publish_sensor_data(msg_data_t* msg);

/**
 * @brief MQTT  发布消息任务
 */
void mqtt_send_task(void)
{
  while(1)
  {
    // 发布消息
    publish_sensor_data(&sys_msg_data);
    sleep(1); // 1s
  }
}

/**
 * @brief  发布传感器的信息
 * @note   
 * @param  msg: 
 * @retval None
 */
void publish_sensor_data(msg_data_t* msg)
{
  char *publish_topic = (char *)malloc(strlen(MALLOC_MQTT_TOPIC_PUB_PROPERTIES) + strlen(DEVICE_ID) + 1);
  if(publish_topic != NULL)
  {
    // 拼接Topic
    memset(publish_topic, 0, strlen(DEVICE_ID) + strlen(MALLOC_MQTT_TOPIC_PUB_PROPERTIES) + 1);
    sprintf(publish_topic, MQTT_TOPIC_PUB_PROPERTIES, DEVICE_ID);

    // 组装JSON数据
    cJSON *json_root = cJSON_CreateObject();
    cJSON *json_services = cJSON_CreateArray();
    cJSON *json_services_root = cJSON_CreateObject();
    cJSON *json_properties = cJSON_CreateObject();

    cJSON_AddItemToObject(json_root, "services", json_services);
    cJSON_AddItemToArray(json_services, json_services_root);
    cJSON_AddItemToObject(json_services_root, "service_id", cJSON_CreateString("base"));
    cJSON_AddItemToObject(json_services_root, "properties", json_properties);
    cJSON_AddItemToObject(json_properties, "light", cJSON_CreateNumber(msg->AP3216C_Value.light));
    cJSON_AddItemToObject(json_properties, "lamp", 
      (msg->Lamp_Status == OFF_LAMP) ? cJSON_CreateString("OFF") : cJSON_CreateString("ON"));
    cJSON_AddItemToObject(json_properties, "red", cJSON_CreateNumber(msg->RGB_Value.red));
    cJSON_AddItemToObject(json_properties, "green", cJSON_CreateNumber(msg->RGB_Value.green));
    cJSON_AddItemToObject(json_properties, "blue", cJSON_CreateNumber(msg->RGB_Value.blue));
    cJSON_AddItemToObject(json_properties, "auto_light_control", 
      (msg->is_auto_light_mode) ? cJSON_CreateString("ON") : cJSON_CreateString("OFF"));
  
    
    char *payload = cJSON_PrintUnformatted(json_root);
    // 发布消息
    MQTTClient_pub(publish_topic, payload, strlen((char *)payload));
    
    cJSON_Delete(json_root);
    free(publish_topic);

    json_root = json_services = json_services_root = json_properties = NULL; 
  }
  publish_topic = NULL;
}

