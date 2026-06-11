/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>

#include "ohos_init.h"
#include "cmsis_os2.h"

#include "hi_io.h"
#include "hi_gpio.h"
#include "hi_uart.h"
#include "stdbool.h"

#include "hal_bsp_ssd1306.h"
#include "hal_bsp_nfc.h"
#include "hal_bsp_nfc_to_wifi.h"
#include "hal_bsp_wifi.h"
#include "hal_bsp_pcf8574.h"
#include "hal_bsp_aw2013.h"
#include "hal_bsp_sht20.h"
#include "hal_bsp_ap3216c.h"
#include "hal_bsp_sgp30.h"

#include "sys_config.h"
#include "oled_show_log.h"
#include "oled_show_task.h"
#include "udp_send_task.h"
#include "udp_recv_task.h"
#include "uart_recv_task.h"
#include "smart_light_task.h"
#include "agriculture/agriculture_sensor_task.h"
#include "agriculture/pwm_rgb.h"
#include "task/imu_task.h"
#include "hal_bsp_h30.h"

#include "lwip/netifapi.h"
#include "lwip/sockets.h"
#include "lwip/api_shell.h"

osThreadId_t oled_show_task_id;
osThreadId_t uart_recv_task_id;
osThreadId_t uart1_recv_task_id;
osThreadId_t udp_send_task_id;
osThreadId_t udp_recv_task_id;
osThreadId_t auto_avoid_task_id;
osThreadId_t smart_light_task_id;
osThreadId_t agriculture_sensor_task_id;
osThreadId_t imu_task_id;
tn_pcf8574_io_t pcf8574_io;

system_value_t systemValue = {0}; // 系统全局变量

#include "sys_config.h"
volatile uint32_t g_lastManualTick = 0;
uint8_t g_turnToggle = 0;
void auto_avoid_task(void *arg);


#define TASK_STACK_SIZE (1024 * 5)

/**
 * @brief  串口初始化
 * @note   与STM32单片机之间的串口通信
 * @retval None
 */
void uart_init(void)
{
    uint32_t ret = 0,ret1 = 0;
    // 初始化串口
    hi_io_set_func(HI_IO_NAME_GPIO_5, HI_IO_FUNC_GPIO_5_UART1_RXD);
    hi_io_set_func(HI_IO_NAME_GPIO_6, HI_IO_FUNC_GPIO_6_UART1_TXD);

    hi_io_set_func(HI_IO_NAME_GPIO_11, HI_IO_FUNC_GPIO_11_UART2_TXD);
    hi_io_set_func(HI_IO_NAME_GPIO_12, HI_IO_FUNC_GPIO_12_UART2_RXD);

    hi_uart_attribute uart_param = {
        .baud_rate = 115200,
        .data_bits = 8,
        .stop_bits = 1,
        .parity = 0,
    };
    ret = hi_uart_init(HI_UART_IDX_2, &uart_param, NULL);
    if (ret != HI_ERR_SUCCESS) {
        printf("hi uart init is faild.\r\n");
    }

     ret1 = hi_uart_init(HI_UART_IDX_1, &uart_param, NULL);
    if (ret1 != HI_ERR_SUCCESS) {
        printf("hi uart init is faild.\r\n");
    }
}

int nfc_connect_wifi_init(void)
{
    /********************************* NFC碰一碰联网 *********************************/
    // 默认WiFi配置
    #define DEFAULT_WIFI_SSID "205"
    #define DEFAULT_WIFI_PASSWORD "17857009223"
    
    uint8_t ndefLen = 0;      // ndef包的长度
    uint8_t ndef_Header = 0;  // ndef消息开始标志位-用不到
    uint32_t result_code = 0; // 函数的返回值
    bool use_default_wifi = false;
    
    // 擦除NFC芯片中的旧数据
    printf("Erasing NFC tag data...\r\n");
    if (NT3HEraseAllTag() == true) {
        printf("NFC tag erased successfully.\r\n");
    } else {
        printf("NFC tag erase failed, continue anyway.\r\n");
    }
    
    // 读整个数据的包头部分，读出整个数据的长度
    if (result_code = NT3HReadHeaderNfc(&ndefLen, &ndef_Header) != true) {
        printf("NT3HReadHeaderNfc is failed. result_code = %d\r\n", result_code);
        printf("Using default WiFi: SSID=%s\r\n", DEFAULT_WIFI_SSID);
        use_default_wifi = true;
    } else {
        ndefLen += NDEF_HEADER_SIZE; // 加上头部字节
        if (ndefLen <= NDEF_HEADER_SIZE) {
            printf("ndefLen <= 2, using default WiFi: SSID=%s\r\n", DEFAULT_WIFI_SSID);
            use_default_wifi = true;
        }
    }
    
    // 如果NFC读取失败，使用默认WiFi配置
    if (use_default_wifi) {
        printf("Connecting to default WiFi: SSID=%s\r\n", DEFAULT_WIFI_SSID);
        while (WiFi_connectHotspots(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD) != WIFI_SUCCESS) {
            printf("Default wifi connect failed!\r\n");
            oled_consle_log("wifi no.");
            sleep(1);
            SSD1306_CLS(); // 清屏
        }
        oled_consle_log("wifi yes.");
        return 0;
    }
    
    // 从NFC标签读取WiFi配置
    uint8_t *ndefBuff = (uint8_t *)malloc(ndefLen + 1);
    if (ndefBuff == NULL) {
        printf("ndefBuff malloc is Falied! Using default WiFi.\r\n");
        while (WiFi_connectHotspots(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD) != WIFI_SUCCESS) {
            printf("Default wifi connect failed!\r\n");
            oled_consle_log("wifi no.");
            sleep(1);
            SSD1306_CLS(); // 清屏
        }
        oled_consle_log("wifi yes.");
        return 0;
    }

    if (result_code = get_NDEFDataPackage(ndefBuff, ndefLen) != HI_ERR_SUCCESS) {
        printf("get_NDEFDataPackage is failed. result_code = %d\r\n", result_code);
        printf("Using default WiFi: SSID=%s\r\n", DEFAULT_WIFI_SSID);
        free(ndefBuff);
        while (WiFi_connectHotspots(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD) != WIFI_SUCCESS) {
            printf("Default wifi connect failed!\r\n");
            oled_consle_log("wifi no.");
            sleep(1);
            SSD1306_CLS(); // 清屏
        }
        oled_consle_log("wifi yes.");
        return 0;
    }

    printf("start print ndefBuff.\r\n");
    for (size_t i = 0; i < ndefLen; i++) {
        printf("0x%x ", ndefBuff[i]);
    }
    printf("\n");

    // 尝试使用NFC配置连接WiFi，如果失败则使用默认配置
    if (NFC_configuresWiFiNetwork(ndefBuff) != WIFI_SUCCESS) {
        printf("NFC WiFi config failed, trying default WiFi: SSID=%s\r\n", DEFAULT_WIFI_SSID);
        free(ndefBuff);
        while (WiFi_connectHotspots(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD) != WIFI_SUCCESS) {
            printf("Default wifi connect failed!\r\n");
            oled_consle_log("wifi no.");
            sleep(1);
            SSD1306_CLS(); // 清屏
        }
        oled_consle_log("wifi yes.");
        return 0;
    }
    
    free(ndefBuff);
    oled_consle_log("wifi yes.");
    return 0;
}

int SC_udp_init(void)
{
    uint32_t result_code = 0; // 函数的返回值
    /********************************** 创建UDP服务端 **********************************/
    printf("wifi IP: %s", WiFi_GetLocalIP());
    // 创建socket
    if ((systemValue.udp_socket_fd = socket(AF_INET, SOCK_DGRAM, 0)) == -1) {
        printf("create socket failed!\r\n");
        return -1;
    }

    // 命名套接字
    struct sockaddr_in local;
    local.sin_family = AF_INET;                           // IPV4
    local.sin_port = htons(UDP_PORT);                     // 端口号
    local.sin_addr.s_addr = inet_addr(WiFi_GetLocalIP()); // 使用本地IP地址进行创建UDP服务端

    // 绑定端口号
    result_code = bind(systemValue.udp_socket_fd, (const struct sockaddr *)&local, sizeof(local));
    if (result_code < 0) {
        printf("udp server bind IP is failed.\r\n");
        return -1;
    } else {
        printf("udp server bind IP is success.");
    }

    SSD1306_CLS(); // 清屏
    return 0;
}
void SC_peripheral_init(void)
{
    /********************************** 外设初始化 **********************************/
    SSD1306_Init(); // OLED 显示屏初始化
    SSD1306_CLS();  // 清屏
    nfc_Init();     // NFC 初始化
    // 外设的初始化
    PCF8574_Init();
    AW2013_Init(); // 三色LED灯的初始化
    AW2013_Control_Red(0);
    AW2013_Control_Green(0);
    AW2013_Control_Blue(0);
    SHT20_Init();   // 温湿度初始化
    AP3216C_Init(); // 三合一传感器初始化
    SGP30_Init();   // SGP30 CO2/TVOC传感器初始化
    pwm_rgb_init(); // PWM RGB初始化 (绿色通道)
    pwm1_rgb_init(); // PWM1 RGB初始化 (蓝色通道)
    smart_light_init(); // 智能光照初始化
    uart_init(); // 串口初始化
    H30_Init();  // H30 IMU 传感器初始化
}
/**
 * @brief  智能小车的入口函数
 * @note
 * @retval None
 */
static void smartCar_example(void)
{
     SC_peripheral_init();
    if (nfc_connect_wifi_init() == -1) {
        return ;
    }
    if (SC_udp_init() == -1) {
        return ;
    }
    /********************************** 创建线程 **********************************/
    osThreadAttr_t options;
    options.attr_bits = 0;
    options.cb_mem = NULL;
    options.cb_size = 0;
    options.stack_mem = NULL;
    options.stack_size = TASK_STACK_SIZE;

    /********************************** UART2接收任务 **********************************/
    options.name = "uart_recv_task";
    options.priority = osPriorityNormal;
    uart_recv_task_id = osThreadNew((osThreadFunc_t)uart2_recv_task, NULL, &options);
    if (uart_recv_task_id != NULL) {
        printf("ID = %d, Create uart_recv_task_id is OK!\r\n", uart_recv_task_id);
    }
    /********************************** UART1接收任务 **********************************/
    options.name = "uart1_recv_task";
    options.priority = osPriorityNormal;
    uart1_recv_task_id = osThreadNew((osThreadFunc_t)uart1_recv_task, NULL, &options);
    if (uart1_recv_task_id != NULL) {
        printf("ID = %d, Create uart1_recv_task_id is OK!\r\n", uart1_recv_task_id);
    }

    /********************************** OLED显示任务 **********************************/
    options.name = "oled_show_task";
    options.priority = osPriorityNormal;
    oled_show_task_id = osThreadNew((osThreadFunc_t)oled_show_task, NULL, &options);
    if (oled_show_task_id != NULL) {
        printf("ID = %d, Create oled_show_task_id is OK!\r\n", oled_show_task_id);
    }

    /********************************** UDP发送任务 **********************************/
    options.name = "udp_send_task";
    options.priority = osPriorityNormal;
    udp_send_task_id = osThreadNew((osThreadFunc_t)udp_send_task, NULL, &options);
    if (udp_send_task_id != NULL) {
        printf("ID = %d, Create udp_send_task_id is OK!\r\n", udp_send_task_id);
    }

    /********************************** UDP接收任务 **********************************/
    options.name = "udp_recv_task";
    options.priority = osPriorityNormal1;
    udp_recv_task_id = osThreadNew((osThreadFunc_t)udp_recv_task, NULL, &options);
    if (udp_recv_task_id != NULL) {
        printf("ID = %d, Create udp_recv_task_id is OK!\r\n", udp_recv_task_id);
    }

    /********************************** 自动避障任务 **********************************/
    options.name = "auto_avoid_task";
    options.priority = osPriorityNormal;  // 与 UDP 线程错开一级避免抢占
    options.stack_size = 2048;
    auto_avoid_task_id = osThreadNew((osThreadFunc_t)auto_avoid_task, NULL, &options);
    if (auto_avoid_task_id != NULL) {
        printf("ID = %d, Create auto_avoid_task_id is OK!\r\n", auto_avoid_task_id);
    }

    /********************************** 智能光照任务 **********************************/
    options.name = "smart_light_task";
    options.priority = osPriorityNormal;
    options.stack_size = 2048;
    smart_light_task_id = osThreadNew((osThreadFunc_t)smart_light_task, NULL, &options);
    if (smart_light_task_id != NULL) {
        printf("ID = %d, Create smart_light_task_id is OK!\r\n", smart_light_task_id);
    }

    /********************************** 农业安防传感器任务 **********************************/
    options.name = "agriculture_sensor_task";
    options.priority = osPriorityNormal;
    options.stack_size = 2048;
    agriculture_sensor_task_id = osThreadNew((osThreadFunc_t)agriculture_sensor_task, NULL, &options);
    if (agriculture_sensor_task_id != NULL) {
        printf("ID = %d, Create agriculture_sensor_task_id is OK!\r\n", agriculture_sensor_task_id);
    }

    /********************************** IMU传感器读取任务 **********************************/
    options.name = "imu_task";
    options.priority = osPriorityNormal;
    options.stack_size = 4096;  // IMU 解析需要较大栈空间
    imu_task_id = osThreadNew((osThreadFunc_t)imu_task, NULL, &options);
    if (imu_task_id != NULL) {
        printf("ID = %d, Create imu_task_id is OK!\r\n", imu_task_id);
    }
}
SYS_RUN(smartCar_example);
