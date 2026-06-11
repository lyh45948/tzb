#include "mqtt_recv_task.h"
#include "hal_bsp_mqtt.h"
#include "hal_bsp_log.h"
#include "hal_bsp_aw2013.h"
#include "hal_bsp_structAll.h"


#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>

#include "cJSON.h"
#include "cmsis_os2.h"
#include "sys_config.h"


extern msg_data_t sys_msg_data;

#if 0
// 计算出时间戳
uint32_t convert_to_timestamp(date_time_value_t *data)
{
  return ((data->yaer - 1970)*12*30*24*60*60) + \
         ((data->month - 1)*30*24*60*60) + \
         ((data->date - 1)*24*60*60) + \
         ((data->hour)*60*60) + \
         ((data->min)*60) + data->sec;
}

#endif

// 解析JSON数据
uint8_t cJSON_Parse_Payload(uint8_t * payload)
{
  uint8_t ret = 0;
  if (payload == NULL)
  {
    console_log_error("payload is NULL");
    return 1;
  }

  cJSON *root = cJSON_Parse((const char *)payload);
  if (root)
  {
    cJSON *service_id = cJSON_GetObjectItem(root, "service_id");
    if (!strcmp(service_id->valuestring, "control"))
    {
      cJSON *command_name = cJSON_GetObjectItem(root, "command_name");
      if (!strcmp(command_name->valuestring, "lamp"))           // 灯的手动控制
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");
        if (!strcmp(value->valuestring, "ON"))
        {
          console_log_info("command_name: lamp, value: ON.");
          sys_msg_data.Lamp_Status = SUN_LIGHT_MODE;
        }
        else if (!strcmp(value->valuestring, "OFF"))
        {
          console_log_info("command_name: lamp, value: OFF.");
          sys_msg_data.Lamp_Status = OFF_LAMP;
        }

        paras = value = NULL;
      }

      if (!strcmp(command_name->valuestring, "RGB"))            // RGB灯的颜色控制
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *red = cJSON_GetObjectItem(paras, "red");
        cJSON *green = cJSON_GetObjectItem(paras, "green");
        cJSON *blue = cJSON_GetObjectItem(paras, "blue");
        
        sys_msg_data.RGB_Value.red = red->valueint;
        sys_msg_data.RGB_Value.green = green->valueint;
        sys_msg_data.RGB_Value.blue = blue->valueint;

        sys_msg_data.Lamp_Status = SET_RGB_MODE;
        console_log_info("command_name: RGB, red: %d, green: %d, blue: %d.",
                                            red->valueint,
                                            green->valueint,
                                            blue->valueint);

        paras = red = green = blue = NULL;
      }

      if (!strcmp(command_name->valuestring, "led_light"))          // 手动调节亮度
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");

        console_log_info("command_name: is_auto_light_mode, value: ON.");
        sys_msg_data.led_light_value = value->valueint;

        paras = value = NULL;
      }

      /* 下面是自动控制的标志位 */
      if (!strcmp(command_name->valuestring, "is_auto_light_mode"))            // 是否开启自动亮度调节
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");

        if (!strcmp(value->valuestring, "ON"))
        {
          console_log_info("command_name: is_auto_light_mode, value: ON.");
          sys_msg_data.is_auto_light_mode = 1;

        }
        else if (!strcmp(value->valuestring, "OFF"))
        {
          console_log_info("command_name: is_auto_light_mode, value: OFF.");
          sys_msg_data.is_auto_light_mode = 0;
        }

        paras = value = NULL;
      }

      if (!strcmp(command_name->valuestring, "is_sleep_mode"))            // 是否开启睡眠模式
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");

        if (!strcmp(value->valuestring, "ON"))
        {
          console_log_info("command_name: is_sleep_mode, value: ON.");
          sys_msg_data.Lamp_Status = SLEEP_MODE;  // 睡眠模式
        }
        else if (!strcmp(value->valuestring, "OFF"))
        {
          console_log_info("command_name: is_sleep_mode, value: OFF.");
          sys_msg_data.Lamp_Status = OFF_LAMP;  // 关闭灯光
        }

        paras = value = NULL;
      }

      if (!strcmp(command_name->valuestring, "is_readbook_mode"))            // 是否开启阅读模式
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");

        if (!strcmp(value->valuestring, "ON"))
        {
          console_log_info("command_name: is_readbook_mode, value: ON.");
          sys_msg_data.Lamp_Status = READ_BOOK_MODE;  // 阅读模式
        }
        else if (!strcmp(value->valuestring, "OFF"))
        {
          console_log_info("command_name: is_readbook_mode, value: OFF.");
          sys_msg_data.Lamp_Status = OFF_LAMP;  // 关闭灯光
        }

        paras = value = NULL;
      }


      if (!strcmp(command_name->valuestring, "is_blink_mode"))            // 是否开启闪烁模式
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");

        if (!strcmp(value->valuestring, "ON"))
        {
          console_log_info("command_name: is_blink_mode, value: ON.");
          sys_msg_data.Lamp_Status = LED_BLINK_MODE;  // 阅读模式
        }
        else if (!strcmp(value->valuestring, "OFF"))
        {
          console_log_info("command_name: is_blink_mode, value: OFF.");
          sys_msg_data.Lamp_Status = OFF_LAMP;  // 关闭灯光
        }

        paras = value = NULL;
      }

      command_name = NULL;
    }
    service_id = NULL;
  }

  cJSON_Delete(root);
  root = NULL;

  return 0;
}

// 暂时先废弃，改为在应用端做
#if 0   
      if (!strcmp(command_name->valuestring, "auto_delay_control"))            // 是否开启自动延时控制
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *value = cJSON_GetObjectItem(paras, "value");

        if (!strcmp(value->valuestring, "ON"))
        {
          console_log_info("command_name: auto_delay_control, value: ON.");
          sys_msg_data.is_auto_delay_control = 1;
        }
        else if (!strcmp(value->valuestring, "OFF"))
        {
          console_log_info("command_name: auto_delay_control, value: OFF.");
          sys_msg_data.is_auto_delay_control = 0;
        }
        paras = value = NULL;
      }
#endif
// 暂时先废弃，改为在应用端做
#if 0   
      if (!strcmp(command_name->valuestring, "delay_control"))            // 延时控制
      {
        cJSON *paras = cJSON_GetObjectItem(root, "paras");
        cJSON *status = cJSON_GetObjectItem(paras, "status");
        cJSON *times = cJSON_GetObjectItem(paras, "times");
        cJSON *begin = cJSON_GetObjectItem(times, "begin");
        cJSON *end = cJSON_GetObjectItem(times, "end");

        date_time_value_t begin_date_time = {0};
        date_time_value_t end_date_time = {0};
        // 分析出开始时间 
        sscanf(begin->valuestring, "%d-%d-%dT%d:%d:%d.000Z", &begin_date_time.yaer,
                                                             &begin_date_time.month,
                                                             &begin_date_time.date,
                                                             &begin_date_time.hour,
                                                             &begin_date_time.min,
                                                             &begin_date_time.sec);
        
        // 分析出结束时间
        sscanf(end->valuestring, "%d-%d-%dT%d:%d:%d.000Z", &end_date_time.yaer,
                                                             &end_date_time.month,
                                                             &end_date_time.date,
                                                             &end_date_time.hour,
                                                             &end_date_time.min,
                                                             &end_date_time.sec);                                                 
        
        // 计算出延时时间
        begin_date_time.hour -= 8;  // 得到的数据与正常的时间相差8个小时
        end_date_time.hour -= 8;  // 得到的数据与正常的时间相差8个小时

        sys_msg_data.lamp_delay_time = convert_to_timestamp(&begin_date_time) - convert_to_timestamp(&end_date_time);
        if (!strcmp(status->valuestring, "ON"))
        {
          console_log_info("delay_control: %d, status: ON.", sys_msg_data.lamp_delay_time);
          sys_msg_data.Lamp_Status = SUN_LIGHT_MODE;
        }
        else if (!strcmp(status->valuestring, "OFF"))
        {
          console_log_info("delay_control: %d, status: OFF.",sys_msg_data.lamp_delay_time);
          sys_msg_data.Lamp_Status = OFF_LAMP;
        }       
        
        paras = status = times = NULL;
      }
#endif

/**
 * @brief MQTT接收数据的回调函数
 */
int8_t mqttClient_sub_callback(unsigned char *topic, unsigned char *payload)
{
  if ((topic == NULL) || (payload == NULL))
    return -1;
  else 
  {
    console_log_info("topic: %s", topic);
    console_log_info("payload: %s", payload);

    // 提取出topic中的request_id
    char request_id[50] = {0};
    int ret_code = 1;   // 0为成功, 其余为失败。不带默认表示成功
    strcpy(request_id, topic + strlen(DEVICE_ID) + strlen("$oc/devices//sys/commands/request_id="));
    console_log_info("request_id: %s", request_id);

    // 解析JSON数据并控制
    ret_code = cJSON_Parse_Payload(payload);

    // 向云端发送命令设置的返回值
    char *request_topic = (char*)malloc(strlen(MALLOC_MQTT_TOPIC_PUB_COMMANDS_REQ) + strlen(DEVICE_ID) + strlen(request_id) + 10);
    if(request_topic != NULL)
    {
      memset(request_topic, 0, strlen(DEVICE_ID) + strlen(MALLOC_MQTT_TOPIC_PUB_COMMANDS_REQ) + 10);
      sprintf(request_topic, MQTT_TOPIC_PUB_COMMANDS_REQ, DEVICE_ID, request_id);
      printf("topic: %s", request_topic);
      if(ret_code == 0){
        MQTTClient_pub(request_topic, "{\"result_code\":0}", strlen("{\"result_code\":0}"));
      }
      else if(ret_code == 1){
        MQTTClient_pub(request_topic, "{\"result_code\":1}", strlen("{\"result_code\":1}"));
      }
      free(request_topic);
    }
    request_topic = NULL; 
  }    
  return 0;
}

/**
 * @brief MQTT  接收消息任务
 */
void mqtt_recv_task(void)
{
  while (1)
  {
    MQTTClient_sub();
    usleep(1000 * 200);
  }
}



