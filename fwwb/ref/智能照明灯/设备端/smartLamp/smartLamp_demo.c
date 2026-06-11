#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#include "ohos_init.h"
#include "cmsis_os2.h"
#include "cJSON.h"
#include "sys_config.h"

#include "hal_bsp_wifi.h"
#include "hal_bsp_mqtt.h"
#include "hal_bsp_key.h"
#include "hal_bsp_ap3216c.h"
#include "hal_bsp_aw2013.h"
#include "hal_bsp_ssd1306.h"
#include "hal_bsp_log.h"
#include "hal_bsp_nfc.h"
#include "hal_bsp_nfc_to_wifi.h"

#include "mqtt_send_task.h"
#include "mqtt_recv_task.h"
#include "sensor_collect_task.h"
#include "oled_show.h"

extern msg_data_t sys_msg_data;


osThreadId_t mqtt_send_task_id; // mqtt 发布数据任务ID
osThreadId_t mqtt_recv_task_id; // mqtt 接收数据任务ID
osThreadId_t sensor_collect_task_id;  // 传感器采集任务ID
static void smartLamp_Project_example(void)
{
  console_log_info("Enter smartLamp_Project_example()!");
  p_MQTTClient_sub_callback = &mqttClient_sub_callback;

  // 全局变量的初始化 
  sys_msg_data.led_light_value = 100;   // RGB灯的亮度值为100%的状态
  
  // 外设的初始化
  KEY_Init(); // 按键初始化
  AW2013_Init();    // 三色LED灯的初始化
  AW2013_Control_RGB(0, 0, 0);
  AP3216C_Init();   // 三合一传感器初始化
  SSD1306_Init(); // OLED 显示屏初始化
  SSD1306_CLS(); // 清屏
  nfc_Init();
  sleep(2);
#if 1
  // 通过NFC芯片进行连接WiFi
  uint8_t ndefLen = 0;           // ndef包的长度
  uint8_t ndef_Header = 0;        // ndef消息开始标志位-用不到
  uint32_t result_code = 0; // 函数的返回值
  // 读整个数据的包头部分，读出整个数据的长度
  if (result_code = NT3HReadHeaderNfc(&ndefLen, &ndef_Header) != true)
  {
    console_log_error("NT3HReadHeaderNfc is failed. result_code = %d", result_code);
    return ;
  }

  ndefLen += NDEF_HEADER_SIZE;   // 加上头部字节

  uint8_t *ndefBuff = (uint8_t*)malloc(ndefLen+1);
  if(ndefBuff == NULL)
  {
    console_log_error("ndefBuff malloc is Falied!");
    return ;
  }

  if(result_code = get_NDEFDataPackage(ndefBuff, ndefLen) != HI_ERR_SUCCESS)
  {
    console_log_error("get_NDEFDataPackage is failed. result_code = %d", result_code);
    return ;
  }

  console_log_info("start print ndefBuff.");
  for (size_t i = 0; i < ndefLen; i++)
  {
    printf("0x%x ", ndefBuff[i]);
  }
  
CONNECT_WIFI:
  if (NFC_configuresWiFiNetwork(ndefBuff) != WIFI_SUCCESS)
  {
    console_log_error("nfc connect wifi is failed!");
    oled_consle_log("wifi no.");
    sleep(1);    
    SSD1306_CLS(); // 清屏
    goto CONNECT_WIFI;
  }
  else
  {
    console_log_info("nfc connect wifi is SUCCESS");
    oled_consle_log("wifi yes.");
    sleep(1);
  }
#endif  

#if 0
CONNECT_WIFI:
  // 手动输入WiFi信息，连接WiFi
  if (WiFi_connectHotspots("AI_DEV", "HQYJ12345678") != WIFI_SUCCESS)
  {
    console_log_error("connectWiFiHotspots");
    oled_consle_log("wifi no.");
    sleep(1);    
    SSD1306_CLS(); // 清屏
    goto CONNECT_WIFI;
  }
  else
  {
    console_log_info("connectWiFiHotspots");
    oled_consle_log("wifi yes.");
    sleep(1);
  }
#endif

CONNECT_MQTT_SERVER:
  // 连接MQTT服务器
  if (MQTTClient_connectServer(SERVER_IP_ADDR, SERVER_IP_PORT) != 0)
  {
    console_log_error("mqttClient_connectServer");
    oled_consle_log("mqtt ser no.");
    sleep(1);
    SSD1306_CLS(); // 清屏

    goto CONNECT_MQTT_SERVER;
  }
  else
  {
    console_log_info("mqttClient_connectServer");
    oled_consle_log("mqtt ser yes.");
    sleep(1);
  }

CONNECT_MQTT_CLIENT:
  // 初始化MQTT客户端
  if (MQTTClient_init(MQTT_CLIENT_ID, MQTT_USER_NAME, MQTT_PASS_WORD) != 0)
  {
    console_log_error("mqttClient_init");
    oled_consle_log("mqtt cli no.");
    sleep(1);
    SSD1306_CLS(); // 清屏

    goto CONNECT_MQTT_CLIENT;
  }
  else
  {
    console_log_info("mqttClient_init");
    oled_consle_log("mqtt cli yes.");
    sleep(1);
  }

CONNECT_MQTT_SUB:
  // 订阅主题
  if (MQTTClient_subscribe(MQTT_TOPIC_SUB_COMMANDS) != 0)
  {
    console_log_error("mqttClient_subscribe");
    oled_consle_log("mqtt sub no.");
    sleep(1);
    SSD1306_CLS(); // 清屏

    goto CONNECT_MQTT_SUB;
  }
  else
  {
    console_log_info("mqttClient_subscribe");
    oled_consle_log("mqtt sub yes.");
    sleep(1);
  }
  SSD1306_CLS(); // 清屏


  //  创建线程
  osThreadAttr_t options;
  options.name = "mqtt_send_task";
  options.attr_bits = 0;
  options.cb_mem = NULL;
  options.cb_size = 0;
  options.stack_mem = NULL;
  options.stack_size = 1024*5;
  options.priority = osPriorityNormal;
  mqtt_send_task_id = osThreadNew((osThreadFunc_t)mqtt_send_task, NULL, &options);
  if (mqtt_send_task_id != NULL)
  {
    console_log_info("ID = %d, Create mqtt_send_task_id is OK!", mqtt_send_task_id);
  }

  options.name = "mqtt_recv_task";
  options.stack_size = 1024*5;
  mqtt_recv_task_id = osThreadNew((osThreadFunc_t)mqtt_recv_task, NULL, &options);
  if (mqtt_recv_task_id != NULL)
  {
    console_log_info("ID = %d, Create mqtt_recv_task_id is OK!", mqtt_recv_task_id);
  }

  options.name = "sensor_collect_task";
  options.stack_size = 1024*5;
  sensor_collect_task_id = osThreadNew((osThreadFunc_t)sensor_collect_task, NULL, &options);
  if (sensor_collect_task_id != NULL)
  {
    console_log_info("ID = %d, Create sensor_collect_task_id is OK!", sensor_collect_task_id);
  }
}

SYS_RUN(smartLamp_Project_example);
