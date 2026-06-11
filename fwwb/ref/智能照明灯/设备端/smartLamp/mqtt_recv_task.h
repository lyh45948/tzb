#ifndef __MQTT_RECV_TASK_H
#define __MQTT_RECV_TASK_H

#include "cmsis_os2.h"

int8_t mqttClient_sub_callback(unsigned char *topic, unsigned char *payload);

void mqtt_recv_task(void);



#endif

