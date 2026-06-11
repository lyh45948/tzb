#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "ohos_init.h"
#include "cmsis_os2.h"
#include "hal_bsp_sht20.h"
#include "hal_bsp_ssd1306.h"
#include "hal_bsp_ssd1306_bmps.h"


#define u8 unsigned char

osThreadId_t Task1_ID;   //  任务1 ID

typedef struct
{
  int top;  // 上边距
  int left; // 左边距
} margin_t;     // 边距类型

margin_t /* 标题-温度 */       temp_title     = { .top = 0, .left = 0, };
margin_t /* 标题=湿度 */       humi_title     = { .top = 0, .left = 0, };
margin_t /* 数字-十位 */  number_1  = { .top = 16, .left = 8, };
margin_t /* 数字-个位 */  number_2  = { .top = 16, .left = 24, };
margin_t /* 小数点 */     dian      = { .top = 32, .left = 40 };
margin_t /* 数字-小数 */  number_3  = { .top = 32, .left = 56 };
margin_t /* 单位 */       danwei    = { .top = 16, .left = 52 };
margin_t /* 图片 */       image     = { .top = 16, .left = 80, };

/**
 * @brief  显示温度页面
 * @note   
 * @param  val: 
 * @retval None
 */
void show_temp_page(float val)
{
  SSD1306_CLS();
  // 显示标题 中间居中显示
  SSD1306_ShowStr(temp_title.left, temp_title.top, "   Temperature ", 16);

  int x = (val * 100) / 1000;
  SSD1306_DrawBMP(number_1.left, number_1.top, 16, 32, bmp_16X32_number[x]);// 显示数字的十位

  x = ((int)(val * 100)) / 100 % 10;
  SSD1306_DrawBMP(number_2.left, number_2.top, 16, 32, bmp_16X32_number[x]); // 显示数字的个位
  SSD1306_DrawBMP(dian.left, dian.top, 16, 16, bmp_16X16_dian);// 显示小数点
  SSD1306_DrawBMP(danwei.left, danwei.top, 16, 16, bmp_16X16_sheShiDu); // 显示℃符号

  x = ((int)(val * 100)) / 10 % 10;
  SSD1306_DrawBMP(number_3.left, number_3.top, 8, 16, bmp_8X16_number[x]); // 数字小数位

  // 适宜温度 0 ~ 30℃
  if (val < 0)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_5_ku_qi); 
  else if(val >= 0 && val < 6)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_5_ku_qi); 
  else if(val >= 6 && val < 12)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_4_nan_guo); 
  else if(val >= 12 && val < 18)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_2_wei_xiao); 
  else if(val >= 18 && val < 24)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_1_mi_yan_xiao); 
  else if(val >= 24)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_3_wu_biao_qing);  
}

/**
 * @brief  显示湿度页面
 * @note   
 * @param  val: 
 * @retval None
 */
void show_humi_page(float val)
{
  // 显示标题 中间居中显示
  SSD1306_CLS();
  SSD1306_ShowStr(humi_title.left, humi_title.top, "    Humidity   ", 16);

  int x = (val * 100) / 1000;
  SSD1306_DrawBMP(number_1.left, number_1.top, 16, 32, bmp_16X32_number[x]);// 显示数字的十位

  x = ((int)(val * 100)) / 100 % 10;
  SSD1306_DrawBMP(number_2.left, number_2.top, 16, 32, bmp_16X32_number[x]); // 显示数字的个位
  SSD1306_DrawBMP(dian.left, dian.top, 16, 16, bmp_16X16_dian);// 显示小数点
  SSD1306_DrawBMP(danwei.left, danwei.top, 16, 16, bmp_16X16_baifenhao); // 显示%符号

  x = ((int)(val * 100)) / 10 % 10;
  SSD1306_DrawBMP(number_3.left, number_3.top, 8, 16, bmp_8X16_number[x]); // 数字小数位

  // 范围： 0 ~ 100%
  if(val >= 0 && val < 20)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_5_ku_qi); 
  else if(val >= 20 && val < 40)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_4_nan_guo); 
  else if(val >= 40 && val < 60)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_3_wu_biao_qing); 
  else if(val >= 60 && val < 80)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_2_wei_xiao); 
  else if(val >= 80)
    SSD1306_DrawBMP(image.left, image.top, 48, 48, bmp_48X48_1_mi_yan_xiao);  
}

/**
 * @description: 任务1为低优先级任务
 * @param {*}
 * @return {*}
 */
void Task1(void *argument) 
{
  (void)argument;
  u8 x = 0, y = 0;
  while (1)
  {
    float temp_val, humi_val;
    SHT20_ReadData(&temp_val, &humi_val);   // 读取温湿度传感器的值
    printf("temp_val: %.2f   humi_val: %.2f\r\n", temp_val, humi_val);

    show_temp_page(temp_val);   // 显示温度页面
    sleep(3);
    show_humi_page(humi_val);   // 显示湿度页面
    sleep(3);  
  }
}

static void smartTemp_demo(void)
{
  printf("Enter smartTemp_demo()!");

  SHT20_Init(); // SHT20初始化
  SSD1306_Init();				//初始化OLED
  SSD1306_CLS(); // 清屏

  osThreadAttr_t options;
  options.name = "Task1";       // 任务的名字
  options.attr_bits = 0;      // 属性位
  options.cb_mem = NULL;      // 堆空间地址
  options.cb_size = 0;        // 堆空间大小
  options.stack_mem = NULL;   // 栈空间地址
  options.stack_size = 1024*5;  // 栈空间大小 单位:字节
  options.priority = osPriorityNormal;  // 任务的优先级

  Task1_ID = osThreadNew((osThreadFunc_t)Task1, NULL, &options);      // 创建任务1
  if (Task1_ID != NULL)
  {
    printf("ID = %d, Create Task1_ID is OK!\n", Task1_ID);
  }
}
SYS_RUN(smartTemp_demo);