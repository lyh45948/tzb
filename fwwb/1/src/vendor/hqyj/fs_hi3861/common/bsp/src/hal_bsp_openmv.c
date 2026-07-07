/*
 * Copyright (c) 2023 Beijing HuaQing YuanJian Education Technology Co., Ltd
 * Licensed under the Apache License, Version 2.0 (the "License");
 * WT OpenMV 视觉模块 SPI 结果帧读取驱动
 */

#include "hal_bsp_openmv.h"
#include "hi_io.h"
#include "hi_errno.h"
#include <stdio.h>
#include <string.h>

static uint8_t OpenMV_CalcCrc8(const uint8_t *data, uint8_t len)
{
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x80) {
                crc = (uint8_t)((crc << 1) ^ 0x07);
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

static uint32_t OpenMV_ReadFrame(uint8_t *data, uint8_t size)
{
    uint8_t dummy[OPENMV_RESULT_FRAME_SIZE];
    if (data == NULL || size > OPENMV_RESULT_FRAME_SIZE) {
        return HI_ERR_FAILURE;
    }

    memset(dummy, OPENMV_SPI_DUMMY_BYTE, size);
    memset(data, 0, size);
    return hi_spi_host_writeread(OPENMV_SPI_IDX, dummy, data, size);
}

static uint16_t OpenMV_ReadU16LE(const uint8_t *buffer, uint8_t offset)
{
    return (uint16_t)(buffer[offset] | (buffer[offset + 1] << 8));
}

static int OpenMV_ParseResult(const uint8_t *raw, openmv_vision_t *vision)
{
    if (raw == NULL || vision == NULL) {
        return OPENMV_PARSE_ERROR;
    }

    if (raw[0] != OPENMV_MAGIC_0 || raw[1] != OPENMV_MAGIC_1) {
        return OPENMV_PARSE_ERROR;
    }

    uint8_t crc = OpenMV_CalcCrc8(raw, OPENMV_RESULT_PAYLOAD_SIZE);
    if (crc != raw[OPENMV_RESULT_PAYLOAD_SIZE]) {
        return OPENMV_PARSE_ERROR;
    }

    memset(vision, 0, sizeof(openmv_vision_t));
    vision->version = raw[2];
    vision->flags = raw[3];
    vision->obstacle_count = raw[4];
    if (vision->obstacle_count > OPENMV_MAX_OBSTACLES) {
        vision->obstacle_count = OPENMV_MAX_OBSTACLES;
    }

    for (uint8_t i = 0; i < vision->obstacle_count; i++) {
        uint8_t offset = 5 + (i * OPENMV_OBSTACLE_SIZE);
        vision->obstacles[i].class_id = raw[offset];
        vision->obstacles[i].confidence = raw[offset + 1];
        vision->obstacles[i].x = raw[offset + 2];
        vision->obstacles[i].y = raw[offset + 3];
        vision->obstacles[i].w = raw[offset + 4];
        vision->obstacles[i].h = raw[offset + 5];
        vision->obstacles[i].distance = OpenMV_ReadU16LE(raw, offset + 6);
    }

    uint8_t counterOffset = 5 + (OPENMV_MAX_OBSTACLES * OPENMV_OBSTACLE_SIZE);
    for (uint8_t i = 0; i < OPENMV_COUNTER_DIGITS_LEN; i++) {
        char ch = (char)raw[counterOffset + i];
        vision->counter_digits[i] = (ch >= '0' && ch <= '9') ? ch : '\0';
        if (vision->counter_digits[i] == '\0') {
            break;
        }
    }
    vision->counter_digits[OPENMV_COUNTER_DIGITS_LEN] = '\0';

    vision->frame_counter = OpenMV_ReadU16LE(raw, counterOffset + OPENMV_COUNTER_DIGITS_LEN);
    vision->crc8 = raw[OPENMV_RESULT_PAYLOAD_SIZE];
    vision->valid = (raw[3] & 0x01) ? 1 : 0;
    return OPENMV_PARSE_OK;
}

uint32_t OpenMV_Init(void)
{
    hi_spi_cfg_init_param initParam = {0};
    initParam.is_slave = 0;

    hi_spi_cfg_basic_info spiInfo = {0};
    spiInfo.cpol = HI_SPI_CFG_CLOCK_CPOL_0;
    spiInfo.cpha = HI_SPI_CFG_CLOCK_CPHA_0;
    spiInfo.fram_mode = HI_SPI_CFG_FRAM_MODE_MOTOROLA;
    spiInfo.data_width = HI_SPI_CFG_DATA_WIDTH_E_8BIT;
    spiInfo.endian = HI_SPI_CFG_ENDIAN_LITTLE;
    spiInfo.freq = OPENMV_SPI_FREQ;

    /* 1) 先 init SPI 控制器（申请 sem/event/irq、清 FIFO、配置 SCR） */
    uint32_t result = hi_spi_init(OPENMV_SPI_IDX, initParam, &spiInfo);
    if (result != HI_ERR_SUCCESS) {
        printf("[OpenMV] SPI init failed: 0x%x\r\n", result);
        return result;
    }

    /* 2) 关 loopback / 设中断模式 / 关 DMA —— SDK demo 标准三件套，缺一会卡在
     * hi_event_wait 里超时，hi_spi_host_writeread 永远返回 HI_ERR_SPI_*_TIMEOUT */
    (void)hi_spi_set_loop_back_mode(OPENMV_SPI_IDX, HI_FALSE);
    (void)hi_spi_set_irq_mode(OPENMV_SPI_IDX, HI_TRUE);
    (void)hi_spi_set_dma_mode(OPENMV_SPI_IDX, HI_FALSE);

    /* 3) 最后切 GPIO 复用功能，避免在 SPI 控制器未就绪时 CK/CSN 输出毛刺 */
    hi_io_set_func(HI_IO_NAME_GPIO_0, HI_IO_FUNC_GPIO_0_SPI1_CK);
    hi_io_set_func(HI_IO_NAME_GPIO_1, HI_IO_FUNC_GPIO_1_SPI1_RXD);
    hi_io_set_func(HI_IO_NAME_GPIO_2, HI_IO_FUNC_GPIO_2_SPI1_TXD);
    hi_io_set_func(HI_IO_NAME_GPIO_3, HI_IO_FUNC_GPIO_3_SPI1_CSN);
    hi_io_set_driver_strength(HI_IO_NAME_GPIO_0, HI_IO_DRIVER_STRENGTH_2);

    printf("[OpenMV] SPI init done, id=%d, freq=%d\r\n", OPENMV_SPI_IDX, OPENMV_SPI_FREQ);
    return HI_ERR_SUCCESS;
}

int OpenMV_ReadResult(openmv_vision_t *vision)
{
    uint8_t buffer[OPENMV_RESULT_FRAME_SIZE] = {0};
    uint32_t result = OpenMV_ReadFrame(buffer, OPENMV_RESULT_FRAME_SIZE);
    if (result != HI_ERR_SUCCESS) {
        return OPENMV_SPI_ERROR;
    }

    return OpenMV_ParseResult(buffer, vision);
}
