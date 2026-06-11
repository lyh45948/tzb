#ifndef __OLED_SHOW_H
#define __OLED_SHOW_H

#include "cmsis_os2.h"

#define OLED_DISPLAY_BUFF_SIZE 30   // OLED显示屏显示缓冲区最大为30

/**
 * @brief  打印一行数据
 * @note   字体默认选择8*16, 
 * @param  line: 行数, 最大行数为4行
 * @param  *string: 显示的字符串，最大显示的字符个数为16个
 * @retval None
 */
uint8_t oled_show_line_string(uint8_t line, char *string);

/**
 * @brief  按照终端的形式，一行行的打印输出
 * @note   默认显示行数为第2行
 * @param  *string: 显示的字符串，最大显示的字符个数为16个
 * @retval 
 */
uint8_t oled_consle_log(char *string);

#endif
