#include "system_init_task.h"
#include "hal_bsp_log.h"
#include "hal_bsp_structAll.h"
#include "hal_bsp_aw2013.h"
#include "hal_bsp_ssd1306.h"
#include "hal_bsp_ssd1306_bmp.h"
#include "hal_bsp_ap3216c.h"
#include "hal_bsp_nfc.h"
#include "hal_bsp_nfc_to_wifi.h"

#include "hi_nv.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>


osThreadId_t system_Init_Task_ID;  // 任务ID

void system_Init_Task(void *argument)
{
  uint8_t ndefLen = 0;           // ndef包的长度
  uint8_t ndef_Header = 0;        // ndef消息开始标志位-用不到
  uint32_t result_code = 0; // 函数的返回值
  
  /******************** 相关外设的初始化 ********************/
  AW2013_Init();
  SSD1306_Init();
  AP3216C_Init();
  nfc_Init();


  /********************* 读出NFC标签中的数据 *********************/
INIT_NFC_TO_WIFI:
  result_code = NT3HReadHeaderNfc(&ndefLen, &ndef_Header);
  if (result_code != true)  // 读整个数据的包头部分，读出整个数据的长度
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

  result_code = get_NDEFDataPackage(ndefBuff, ndefLen);
  if(result_code != HI_ERR_SUCCESS)
  {
    console_log_error("get_NDEFDataPackage is failed. result_code = %d", result_code);
    return ;
  }
  
  /********************* 根据读出来的信息，进行配置网络 *********************/
  result_code = NFC_configuresWiFiNetwork(ndefBuff);
  if (result_code != HI_ERR_SUCCESS)
  {
    console_log_error("NFC_configuresWiFiNetwork is failed.");
    
    SSD1306_DrawBMP(90,0,101,1,BMP9);    // 在OLED显示屏上显示连接WiFi出现异常
    sleep(1);
    SSD1306_CLS();  // 清屏

    goto INIT_NFC_TO_WIFI;
  }

  SSD1306_DrawBMP(90,0,101,1,BMP6);    // 在OLED显示屏上显示连接WiFi成功

  free(ndefBuff);
  ndefBuff = NULL;
}






