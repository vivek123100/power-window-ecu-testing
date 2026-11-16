/**
 * @file  uds.h
 * @brief UDS diagnostics (ISO 14229) over ISO-TP (ISO 15765-2) in the ECU firmware.
 *
 * Same services and answers as the Python ECU in 03_CAN/sim/uds.py:
 *   0x10 01/03, 0x22 F195 (SW version) / 0100 (window position), 0x19 02, 0x14 FFFFFF, 0x3E 00
 *   negative response 7F SID NRC: 11 service, 12 sub-function, 13 length, 31 out of range
 * Request 0x7E0, response 0x7E8, 8-byte frames padded with 0xAA.
 */
#ifndef UDS_H
#define UDS_H

#include <stdbool.h>
#include <stdint.h>

#define UDS_REQ_ID   (0x7E0U)
#define UDS_RESP_ID  (0x7E8U)

/** What diagnostics can see of the ECU (updated by main every 10 ms). */
typedef struct
{
    bool  dtc_switch_timeout;   /* U0140-00 */
    bool  dtc_motor_overrun;    /* B1310-00 */
    bool  dtc_switch_invalid;   /* U0422-00 */
    float pos_pct;
} UdsEcuData_t;

void Uds_Init(void);
void Uds_OnFrame(const uint8_t *data, uint8_t dlc, const UdsEcuData_t *ecu);  /* frame on 0x7E0 */
void Uds_Task1ms(void);         /* sends the next Consecutive Frame, if one is waiting */

/* Provided by main.c (CAN driver). */
bool Can_Send(uint32_t id, const uint8_t *data, uint8_t dlc);

#endif /* UDS_H */
