/**
 * @file  uds.c
 * @brief UDS server + ISO-TP transport for the window ECU (embedded C, no heap).
 *
 * ISO-TP frame types (first nibble of byte 0):
 *   0L Single Frame (<= 7 bytes)   1L LL First Frame (12-bit length + 6 bytes)
 *   2N Consecutive Frame (7 bytes) 30 Flow Control from the tester ("continue")
 * A long answer is sent as FF; the ECU then WAITS for the tester's Flow Control
 * and sends the CFs, one per millisecond (the bxCAN has only 3 TX mailboxes).
 */
#include <string.h>
#include "uds.h"
#include "window_ctrl.h"
#include "e2e_counter.h"

#define PAD             (0xAAU)
#define MAX_RESP        (32U)

#define NRC_SERVICE     (0x11U)
#define NRC_SUBFUNC     (0x12U)
#define NRC_LENGTH      (0x13U)
#define NRC_RANGE       (0x31U)
#define STATUS_AVAIL    (0x09U)                     /* testFailed + confirmedDTC */
#define STATUS_CONF     (0x08U)

static const uint8_t SW_VERSION[8]  = { 'P', 'W', '-', '1', '.', '0', '.', '0' };
static const uint8_t DTC_TIMEOUT[3] = { 0xC1U, 0x40U, 0x00U };   /* U0140-00 */
static const uint8_t DTC_OVERRUN[3] = { 0x93U, 0x10U, 0x00U };   /* B1310-00 */
static const uint8_t DTC_INVALID[3] = { 0xC4U, 0x22U, 0x00U };   /* U0422-00 */

static uint8_t  s_session;
static uint8_t  s_tx[MAX_RESP];                     /* long answer being sent   */
static uint32_t s_tx_len;
static uint32_t s_tx_pos;                           /* next byte to send        */
static uint8_t  s_tx_seq;                           /* next CF sequence number  */
static bool     s_wait_fc;                          /* FF sent, waiting for FC  */
static bool     s_sending_cf;                       /* FC received, CFs pending */

void Uds_Init(void)
{
    s_session    = 0x01U;
    s_tx_len     = 0U;
    s_wait_fc    = false;
    s_sending_cf = false;
}

/* ---------------------------------------------------------------- ISO-TP */
static bool send_padded(const uint8_t *bytes, uint32_t n)
{
    uint8_t f[8];
    for (uint32_t i = 0U; i < 8U; i++) { f[i] = (i < n) ? bytes[i] : PAD; }
    return Can_Send(UDS_RESP_ID, f, 8U);
}

static void isotp_send(const uint8_t *msg, uint32_t len)
{
    uint8_t f[8];
    if (len <= 7U)                                  /* Single Frame */
    {
        f[0] = (uint8_t)len;
        (void)memcpy(&f[1], msg, len);
        (void)send_padded(f, len + 1U);
        return;
    }
    (void)memcpy(s_tx, msg, len);                   /* First Frame, then wait for FC */
    s_tx_len = len;
    f[0] = (uint8_t)(0x10U | ((len >> 8) & 0x0FU));
    f[1] = (uint8_t)(len & 0xFFU);
    (void)memcpy(&f[2], msg, 6U);
    (void)send_padded(f, 8U);
    s_tx_pos = 6U;
    s_tx_seq = 1U;
    s_wait_fc = true;
    s_sending_cf = false;
}

void Uds_Task1ms(void)
{
    if (!s_sending_cf)
    {
        return;
    }
    uint8_t f[8];
    const uint32_t left = s_tx_len - s_tx_pos;
    const uint32_t n = (left > 7U) ? 7U : left;
    f[0] = (uint8_t)(0x20U | s_tx_seq);
    (void)memcpy(&f[1], &s_tx[s_tx_pos], n);
    if (send_padded(f, n + 1U))                     /* mailbox full: retry next ms */
    {
        s_tx_pos += n;
        s_tx_seq = (uint8_t)((s_tx_seq + 1U) & 0x0FU);
        if (s_tx_pos >= s_tx_len)
        {
            s_sending_cf = false;                   /* whole answer sent */
        }
    }
}

/* ---------------------------------------------------------------- services */
static uint32_t nrc(uint8_t *r, uint8_t sid, uint8_t code)
{
    r[0] = 0x7FU;
    r[1] = sid;
    r[2] = code;
    return 3U;
}

static uint32_t add_dtc(uint8_t *r, uint32_t n, bool active, const uint8_t *code, uint8_t mask)
{
    if (active && ((STATUS_CONF & mask) != 0U))
    {
        (void)memcpy(&r[n], code, 3U);
        r[n + 3U] = STATUS_CONF;
        n += 4U;
    }
    return n;
}

static uint32_t handle(const uint8_t *q, uint32_t len, const UdsEcuData_t *ecu, uint8_t *r)
{
    const uint8_t sid = q[0];
    switch (sid)
    {
        case 0x10U:                                 /* DiagnosticSessionControl */
            if (len != 2U) { return nrc(r, sid, NRC_LENGTH); }
            if ((q[1] != 0x01U) && (q[1] != 0x03U)) { return nrc(r, sid, NRC_SUBFUNC); }
            s_session = q[1];
            r[0] = 0x50U; r[1] = q[1]; r[2] = 0x00U; r[3] = 0x32U; r[4] = 0x01U; r[5] = 0xF4U;
            return 6U;                              /* P2 50 ms, P2* 5 s */

        case 0x22U:                                 /* ReadDataByIdentifier */
            if (len != 3U) { return nrc(r, sid, NRC_LENGTH); }
            r[0] = 0x62U; r[1] = q[1]; r[2] = q[2];
            if ((q[1] == 0xF1U) && (q[2] == 0x95U))
            {
                (void)memcpy(&r[3], SW_VERSION, sizeof SW_VERSION);
                return 3U + sizeof SW_VERSION;
            }
            if ((q[1] == 0x01U) && (q[2] == 0x00U))
            {
                r[3] = (uint8_t)(ecu->pos_pct + 0.5f);
                return 4U;
            }
            return nrc(r, sid, NRC_RANGE);

        case 0x19U:                                 /* ReadDTCInformation */
        {
            if (len != 3U) { return nrc(r, sid, NRC_LENGTH); }
            if (q[1] != 0x02U) { return nrc(r, sid, NRC_SUBFUNC); }
            uint32_t n = 3U;
            r[0] = 0x59U; r[1] = 0x02U; r[2] = STATUS_AVAIL;
            n = add_dtc(r, n, ecu->dtc_switch_timeout, DTC_TIMEOUT, q[2]);
            n = add_dtc(r, n, ecu->dtc_motor_overrun,  DTC_OVERRUN, q[2]);
            n = add_dtc(r, n, ecu->dtc_switch_invalid, DTC_INVALID, q[2]);
            return n;
        }

        case 0x14U:                                 /* ClearDiagnosticInformation */
            if (len != 4U) { return nrc(r, sid, NRC_LENGTH); }
            if ((q[1] != 0xFFU) || (q[2] != 0xFFU) || (q[3] != 0xFFU)) { return nrc(r, sid, NRC_RANGE); }
            WindowCtrl_ClearDtcs();                 /* REQ_16 */
            E2E_ClearDtc();
            r[0] = 0x54U;
            return 1U;

        case 0x3EU:                                 /* TesterPresent */
            if ((len != 2U) || (q[1] != 0x00U)) { return nrc(r, sid, NRC_SUBFUNC); }
            r[0] = 0x7EU; r[1] = 0x00U;
            return 2U;

        default:
            return nrc(r, sid, NRC_SERVICE);
    }
}

void Uds_OnFrame(const uint8_t *data, uint8_t dlc, const UdsEcuData_t *ecu)
{
    if (dlc < 1U)
    {
        return;
    }
    const uint8_t kind = (uint8_t)(data[0] >> 4);
    if (kind == 3U)                                 /* Flow Control from the tester */
    {
        if (s_wait_fc)
        {
            s_wait_fc = false;
            s_sending_cf = true;                    /* CFs go out from Uds_Task1ms */
        }
        return;
    }
    if (kind != 0U)                                 /* only Single Frame requests are needed */
    {
        return;
    }
    const uint32_t len = data[0] & 0x0FU;
    if ((len == 0U) || (len > 7U) || (len >= dlc))
    {
        return;                                     /* invalid SF: ignore (ISO 15765-2) */
    }
    uint8_t resp[MAX_RESP];
    const uint32_t n = handle(&data[1], len, ecu, resp);
    isotp_send(resp, n);
}
