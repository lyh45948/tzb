#include "sensor_collect_task.h"

#include "hal_bsp_sht20.h"
#include "hal_bsp_pcf8574.h"
#include "hal_bsp_ssd1306.h"
#include "hal_bsp_ssd1306_bmps.h"

#include "hal_bsp_log.h"
#include "hal_bsp_key.h"
#include "hal_bsp_mqtt.h"

#include "oled_show.h"
#include "sys_config.h"


msg_data_t sys_msg_data = {0};    // 传感器的数据

margin_t   bmp_number_1   = { .top = 16+8, .left = 8, };// 数字-十位 
margin_t   bmp_number_2   = { .top = 16+8, .left = 24, };// 数字-个位 
margin_t   bmp_dian       = { .top = 32+8, .left = 40 };// 小数点  
margin_t   bmp_number_3   = { .top = 32+8, .left = 56 };// 数字-小数 
margin_t   bmp_danwei     = { .top = 16+8, .left = 52 };// 单位  
margin_t   bmp_image      = { .top = 16, .left = 72, };// 图片  


/**
 * @brief  显示湿度页面
 * @note   
 * @param  val: 
 * @retval None
 */
void show_humi_page(float val)
{
  SSD1306_ShowStr(0, 0, " Smart Farm", 16);

  int x = (val * 100) / 1000;
  SSD1306_DrawBMP(bmp_number_1.left, bmp_number_1.top, 16, 32, bmp_16X32_number[x]);// 显示数字的十位

  x = ((int)(val * 100)) / 100 % 10;
  SSD1306_DrawBMP(bmp_number_2.left, bmp_number_2.top, 16, 32, bmp_16X32_number[x]); // 显示数字的个位
  SSD1306_DrawBMP(bmp_dian.left, bmp_dian.top, 16, 16, bmp_16X16_dian);// 显示小数点
  SSD1306_DrawBMP(bmp_danwei.left, bmp_danwei.top, 16, 16, bmp_16X16_baifenhao); // 显示%符号

  x = ((int)(val * 100)) / 10 % 10;
  SSD1306_DrawBMP(bmp_number_3.left, bmp_number_3.top, 8, 16, bmp_8X16_number[x]); // 显示数字的小数位

  // 风扇动态显示
  if(sys_msg_data.fanStatus == 0)
  {
    SSD1306_DrawBMP(bmp_image.left, bmp_image.top, 48, 48, bmp_48X48_fan_gif[0]);   // 静态显示
  }
  else
  {
    static uint8_t fan_gif_index = 0;
    fan_gif_index++;
    if(fan_gif_index > 3)
      fan_gif_index = 0;
    SSD1306_DrawBMP(bmp_image.left, bmp_image.top, 48, 48, bmp_48X48_fan_gif[fan_gif_index]);   // 动态显示
  }
}

/**
 * @brief  传感器采集任务
 * @note   
 * @retval None
 */
void sensor_collect_task(void)
{
  while(1)
  {
    // 采集传感器的值
    SHT20_ReadData(&sys_msg_data.temperature, &sys_msg_data.humidity);
    // 显示在OLED显示屏上
    show_humi_page(sys_msg_data.humidity);

    if(sys_msg_data.fanStatus != 0)
      sys_msg_data.pcf8574_io.bit.p0 = 1;   // 风扇打开
    else
      sys_msg_data.pcf8574_io.bit.p0 = 0;   // 风扇关闭

    // 逻辑判断
    if(sys_msg_data.nvFlash.smartControl_flag != 0)   // 查看是否开启自动控制
    {
      if(sys_msg_data.humidity >= sys_msg_data.nvFlash.humi_upper){
        sys_msg_data.fanStatus = 1;
        sys_msg_data.pcf8574_io.bit.p0 = sys_msg_data.fanStatus;
        PCF8574_Write(sys_msg_data.pcf8574_io.all);
      }
      else if(sys_msg_data.humidity <= sys_msg_data.nvFlash.humi_lower){
        sys_msg_data.fanStatus = 0;
        sys_msg_data.pcf8574_io.bit.p0 = sys_msg_data.fanStatus;
        PCF8574_Write(sys_msg_data.pcf8574_io.all);
      }
      else{
        // 保持上一状态; 上一次状态是开，那就继续开; 反之，关
        sys_msg_data.pcf8574_io.bit.p0 = sys_msg_data.fanStatus;
        PCF8574_Write(sys_msg_data.pcf8574_io.all);
      }
    }
    else{
      if(sys_msg_data.fanStatus != 0)
        sys_msg_data.pcf8574_io.bit.p0 = 1;   // 开
      else 
        sys_msg_data.pcf8574_io.bit.p0 = 0;   // 关风扇

      PCF8574_Write(sys_msg_data.pcf8574_io.all);
    }

    usleep(100*1000);
  }
}




