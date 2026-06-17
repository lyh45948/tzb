/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * WT OpenMV 视觉模块 SPI 结果帧读取驱动
 */

#ifndef HAL_BSP_OPENMV_H
#define HAL_BSP_OPENMV_H

#include <stdint.h>
#include "hi_spi.h"

#define OPENMV_SPI_IDX             HI_SPI_ID_1
#define OPENMV_SPI_FREQ            1000000
#define OPENMV_SPI_DUMMY_BYTE      0xFF

#define OPENMV_MAGIC_0             0x5A
#define OPENMV_MAGIC_1             0xA5
#define OPENMV_PROTOCOL_VERSION    1
#define OPENMV_MAX_OBSTACLES       4
#define OPENMV_COUNTER_DIGITS_LEN  6
#define OPENMV_OBSTACLE_SIZE       8
#define OPENMV_RESULT_HEADER_SIZE  13
#define OPENMV_RESULT_PAYLOAD_SIZE (OPENMV_RESULT_HEADER_SIZE + (OPENMV_MAX_OBSTACLES * OPENMV_OBSTACLE_SIZE))
#define OPENMV_RESULT_FRAME_SIZE   (OPENMV_RESULT_PAYLOAD_SIZE + 1)

#define OPENMV_PARSE_OK            0
#define OPENMV_PARSE_ERROR         1
#define OPENMV_SPI_ERROR           2

typedef struct _openmv_obstacle {
    uint8_t class_id;
    uint8_t confidence;
    uint8_t x;
    uint8_t y;
    uint8_t w;
    uint8_t h;
    uint16_t distance;   // mm，0 表示未知
} openmv_obstacle_t;

typedef struct _openmv_vision {
    uint8_t valid;
    uint8_t version;
    uint8_t flags;
    uint8_t obstacle_count;
    openmv_obstacle_t obstacles[OPENMV_MAX_OBSTACLES];
    char counter_digits[OPENMV_COUNTER_DIGITS_LEN + 1];
    uint16_t frame_counter;
    uint8_t crc8;
} openmv_vision_t;

uint32_t OpenMV_Init(void);
int OpenMV_ReadResult(openmv_vision_t *vision);

#endif // HAL_BSP_OPENMV_H
