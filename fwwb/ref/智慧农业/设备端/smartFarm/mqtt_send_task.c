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
    char *pubDataBuff = (char *)malloc(strlen(MQTT_PAYLOAD_PUB)+32);
    if(pubDataBuff != NULL)
    {
      memset(pubDataBuff, 0, sizeof(pubDataBuff));
      sprintf(pubDataBuff, MQTT_PAYLOAD_PUB, 
                                            msg->humidity, 
                                            msg->temperature, 
                                            (msg->fanStatus != 0) ? "ON": "OFF",
                                            msg->nvFlash.humi_upper, 
                                            msg->nvFlash.humi_lower,
                                            (msg->nvFlash.smartControl_flag != 0) ? "ON" : "OFF");
      console_log_info("pubDataBuff: %s", pubDataBuff);
      // 发布消息
      MQTTClient_pub(publish_topic, pubDataBuff, strlen((char *)pubDataBuff));
      free(pubDataBuff);
    }
    free(publish_topic);
    pubDataBuff = NULL;
  }
  publish_topic = NULL;
}

