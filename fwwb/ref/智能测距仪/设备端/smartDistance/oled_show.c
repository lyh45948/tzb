#include "oled_show.h"
#include "hal_bsp_ssd1306.h"
#include "hal_bsp_log.h"

#include <string.h>

/**
 * @brief  打印一行数据
 * @note   字体默认选择8*16, 
 * @param  line: 行数, 最大行数为4行
 * @param  *string: 显示的字符串，最大显示的字符个数为16个
 * @retval None
 */
uint8_t oled_show_line_string(uint8_t line, char *string)
{
  if (line > 4) {
    // console_log_error("line is > 4");
    return 1;
  }
  else if (line <= 0) {
    console_log_error("line is <= 0");
    return 2;
  }
  else if (string == NULL) {
    console_log_error("string is NULL");
    return 3;
  }
  else if (strlen(string) > 16) {
    console_log_error("string of length is > 16");
    return 4;
  }
  
  SSD1306_ShowStr(0, line-1, string, 16);
}

#define INIT_LINE 2 // 记录初始行数
#define MAX_LINE 4  // 记录最大行数
static uint8_t current_line = INIT_LINE;

uint8_t oled_consle_log(char *string)
{
  if (string == NULL)
  {
    console_log_error("string is NULL");
    return 1;
  }

  oled_show_line_string(current_line, "               ");    // 清除这一行数据
  // 先打印首行
  if (current_line == INIT_LINE) {
    oled_show_line_string(current_line, string);  
    // 打印首行的时候，将下面的两行进行删除
    oled_show_line_string(3, "               ");    // 清除这一行数据
    oled_show_line_string(4, "               ");    // 清除这一行数据
  }
  else {
    if (current_line > MAX_LINE)
      current_line = INIT_LINE;
    oled_show_line_string(current_line, string);
  }
  current_line++;

  return 0;
}
