/**
 * @file  e2e_counter.h
 * @brief E2E alive-counter check for BCM_WindowSwitch (0x200) - CR_04.
 *
 * Part of the communication layer, not the window logic: it decides whether a
 * received frame is fresh before its values reach window_ctrl.c.
 */
#ifndef E2E_COUNTER_H
#define E2E_COUNTER_H

#include <stdbool.h>
#include <stdint.h>

/** Result of checking one received frame. */
typedef enum
{
    E2E_STATUS_INITIAL  = 0,   /**< first frame after start: accepted          */
    E2E_STATUS_OK       = 1,   /**< counter changed: fresh frame, accepted      */
    E2E_STATUS_REPEATED = 2    /**< same counter as last time: stale, discarded */
} E2E_Status_t;

void         E2E_Init(void);
E2E_Status_t E2E_CheckCounter(uint8_t counter);
bool         E2E_DtcActive(void);     /* U0422-00 stored (REQ_18) */
void         E2E_ClearDtc(void);      /* UDS 0x14 */

#endif /* E2E_COUNTER_H */
