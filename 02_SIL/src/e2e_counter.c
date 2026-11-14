/**
 * @file  e2e_counter.c
 * @brief E2E alive-counter check (REQ_17, REQ_18) - CR_04.
 *
 * Rules:
 *  - first frame after E2E_Init(): accept, remember its counter (INITIAL)
 *  - counter equal to the last accepted one: discard (REPEATED), count it
 *  - any other counter: accept (OK), remember it, reset the repeat count
 *  - 3 discarded frames in a row: store the DTC (stays until E2E_ClearDtc)
 */
#include "e2e_counter.h"

#define E2E_COUNTER_MASK  (0x0FU)   /* AliveCounter is 4 bits (0..15)  */
#define E2E_MAX_REPEATS   (3U)      /* REQ_18: 3 discarded frames      */

static uint8_t s_last_counter;      /* counter of the last accepted frame */
static bool    s_has_last;          /* false until the first frame         */
static uint8_t s_repeat_count;      /* discarded frames in a row           */
static bool    s_dtc;               /* U0422-00 stored                     */

void E2E_Init(void)
{
    s_last_counter = 0U;
    s_has_last     = false;
    s_repeat_count = 0U;
    s_dtc          = false;
}

E2E_Status_t E2E_CheckCounter(uint8_t counter)
{
    /* TODO (your task, CR_04): implement the four rules from the file header.
       Hints:
         - first mask the counter:  counter & E2E_COUNTER_MASK
         - three cases: no frame yet / same counter / different counter
         - only count repeats up to E2E_MAX_REPEATS (no overflow)
         - set s_dtc when s_repeat_count reaches E2E_MAX_REPEATS
       Remove the two lines below when you are done. */
    (void)counter;
    return E2E_STATUS_OK;
}

bool E2E_DtcActive(void)
{
    return s_dtc;
}

void E2E_ClearDtc(void)
{
    s_dtc = false;
}
