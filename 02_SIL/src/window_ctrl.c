/**
 * @file  window_ctrl.c
 * @brief Power window controller - C version of the Stateflow chart.
 *
 * Rules used to translate the chart:
 *  - one 'case' per state in a switch statement
 *  - transitions = an if / else-if chain, in the SAME priority order as the chart
 *  - only ONE transition per step (like Stateflow)
 *  - entry actions live in enter_state()
 *  - after(8, sec) = a tick counter that counts 10 ms steps since state entry
 */
#include "window_ctrl.h"

/* ---- Calibration constants (no "magic numbers" in the logic) ---------- */
#define CYCLE_MS            (10U)
#define OVERRUN_TICKS       (8000U / CYCLE_MS)   /* REQ_10: 8 s            */
#define MSG_TIMEOUT_MS      (500.0f)             /* REQ_09                 */
#define VBAT_MIN_V          (9.0f)               /* REQ_08                 */
#define VBAT_MAX_V          (16.0f)              /* REQ_08                 */
#define PINCH_CURRENT_A     (8.0f)               /* REQ_05                 */
#define PINCH_ZONE_MIN_PCT  (4.0f)               /* REQ_05                 */
#define PINCH_ZONE_MAX_PCT  (96.0f)              /* REQ_05, REQ_07         */
#define REVERSE_PCT         (20.0f)              /* REQ_06                 */
#define POS_CLOSED_PCT      (100.0f)             /* REQ_04                 */
#define POS_OPEN_PCT        (0.0f)               /* REQ_04                 */

/* ---- Internal state (static = only visible in this file) ------------- */
static WindowState_t   s_state;
static uint16_t        s_ticks;          /* 10 ms steps since state entry */
static float           s_pos_at_pinch;
static WindowOutputs_t s_out;

/* ---- Helpers ---------------------------------------------------------- */
static bool voltage_ok(float vbat_v)
{
    return (vbat_v >= VBAT_MIN_V) && (vbat_v <= VBAT_MAX_V);
}

static bool msg_ok(float age_ms)
{
    return age_ms <= MSG_TIMEOUT_MS;
}

/** Change state and run its entry action (like 'entry:' in Stateflow). */
static void enter_state(WindowState_t next)
{
    s_state = next;
    s_ticks = 0U;

    switch (next)
    {
        case WS_IDLE:          s_out.motor_cmd = 0;  break;
        case WS_MOVING_UP:     s_out.motor_cmd = 1;  break;
        case WS_MOVING_DOWN:   s_out.motor_cmd = -1; break;
        case WS_PINCH_REVERSE: s_out.motor_cmd = -1; s_out.pinch_flag = true; break;
        case WS_WAIT_RELEASE:  s_out.motor_cmd = 0;  break;
        case WS_ERROR:         s_out.motor_cmd = 0;  break;
        default:               s_out.motor_cmd = 0;  break;
    }
}

/* ---- Public functions ------------------------------------------------- */
void WindowCtrl_Init(void)
{
    s_out.motor_cmd          = 0;
    s_out.pinch_flag         = false;
    s_out.dtc_switch_timeout = false;
    s_out.dtc_motor_overrun  = false;
    s_pos_at_pinch           = 0.0f;
    enter_state(WS_IDLE);                /* default transition */
}

void WindowCtrl_ClearDtcs(void)
{
    s_out.dtc_switch_timeout = false;    /* REQ_16: UDS 0x14 */
    s_out.dtc_motor_overrun  = false;
}

void WindowCtrl_Step(const WindowInputs_t *in, WindowOutputs_t *out)
{
    if (s_ticks < UINT16_MAX)
    {
        s_ticks++;                       /* time since state entry */
    }

    switch (s_state)
    {
        case WS_IDLE:
            if (!msg_ok(in->sw_msg_age_ms))                      /* REQ_09, CR_01 */
            {
                s_out.dtc_switch_timeout = true;
                enter_state(WS_ERROR);
            }
            else if (in->sw_up && !in->sw_down && (in->pos_pct < POS_CLOSED_PCT) &&
                voltage_ok(in->vbat_v) && msg_ok(in->sw_msg_age_ms))
            {
                enter_state(WS_MOVING_UP);                       /* REQ_01 */
            }
            else if (in->sw_down && !in->sw_up && (in->pos_pct > POS_OPEN_PCT) &&
                     voltage_ok(in->vbat_v) && msg_ok(in->sw_msg_age_ms))
            {
                enter_state(WS_MOVING_DOWN);                     /* REQ_02 */
            }
            else
            {
                /* stay in IDLE */
            }
            break;

        case WS_MOVING_UP:
            if (!msg_ok(in->sw_msg_age_ms))                      /* 1: REQ_09 */
            {
                s_out.dtc_switch_timeout = true;
                enter_state(WS_ERROR);
            }
            else if (s_ticks >= OVERRUN_TICKS)                   /* 2: REQ_10 */
            {
                s_out.dtc_motor_overrun = true;
                enter_state(WS_ERROR);
            }
            else if (!voltage_ok(in->vbat_v))                    /* 3: REQ_08 */
            {
                enter_state(WS_IDLE);
            }
            else if (in->sw_up && in->sw_down)                   /* 4: REQ_11 */
            {
                enter_state(WS_IDLE);
            }
            else if ((in->current_a > PINCH_CURRENT_A) &&        /* 5: REQ_05 */
                     (in->pos_pct > PINCH_ZONE_MIN_PCT) &&
                     (in->pos_pct < PINCH_ZONE_MAX_PCT))
            {
                s_pos_at_pinch = in->pos_pct;
                enter_state(WS_PINCH_REVERSE);
            }
            else if (!in->sw_up || (in->pos_pct >= POS_CLOSED_PCT)) /* 6: REQ_03, REQ_04 */
            {
                enter_state(WS_IDLE);
            }
            else
            {
                /* keep moving up */
            }
            break;

        case WS_MOVING_DOWN:
            if (!msg_ok(in->sw_msg_age_ms))                      /* 1: REQ_09 */
            {
                s_out.dtc_switch_timeout = true;
                enter_state(WS_ERROR);
            }
            else if (s_ticks >= OVERRUN_TICKS)                   /* 2: REQ_10 */
            {
                s_out.dtc_motor_overrun = true;
                enter_state(WS_ERROR);
            }
            else if (!voltage_ok(in->vbat_v))                    /* 3: REQ_08 */
            {
                enter_state(WS_IDLE);
            }
            else if (in->sw_up && in->sw_down)                   /* 4: REQ_11 */
            {
                enter_state(WS_IDLE);
            }
            else if (!in->sw_down || (in->pos_pct <= POS_OPEN_PCT)) /* 5: REQ_03, REQ_04 */
            {
                enter_state(WS_IDLE);
            }
            else
            {
                /* keep moving down */
            }
            break;

        case WS_PINCH_REVERSE:
            if (!msg_ok(in->sw_msg_age_ms))                          /* 1: REQ_09 */
            {
                s_out.dtc_switch_timeout = true;
                enter_state(WS_ERROR);
            }
            else if (s_ticks >= OVERRUN_TICKS)                       /* 2: REQ_10 */
            {
                s_out.dtc_motor_overrun = true;
                enter_state(WS_ERROR);
            }
            else if (!voltage_ok(in->vbat_v))                        /* 3: REQ_08 */
            {
                s_out.pinch_flag = false;                            /* REQ_14 */
                enter_state(WS_IDLE);
            }
            else if (((s_pos_at_pinch - in->pos_pct) >= REVERSE_PCT) ||
                     (in->pos_pct <= POS_OPEN_PCT))                  /* 4: REQ_06, REQ_13 */
            {
                enter_state(WS_WAIT_RELEASE);
            }
            else
            {
                /* keep reversing */
            }
            break;

        case WS_WAIT_RELEASE:
            if (!msg_ok(in->sw_msg_age_ms))                          /* REQ_09, CR_01 */
            {
                s_out.dtc_switch_timeout = true;
                enter_state(WS_ERROR);
            }
            else if (!in->sw_up)                                     /* REQ_13 */
            {
                s_out.pinch_flag = false;                            /* REQ_14 */
                enter_state(WS_IDLE);
            }
            else
            {
                /* wait until Up is released */
            }
            break;

        case WS_ERROR:
            if (msg_ok(in->sw_msg_age_ms) && !in->sw_up && !in->sw_down)   /* recovery */
            {
                s_out.pinch_flag = false;                                 /* REQ_14 */
                enter_state(WS_IDLE);
            }
            else
            {
                /* stay in ERROR until the fault is gone and both switches are released */
            }
            break;

        default:
            enter_state(WS_IDLE);        /* defensive: unknown state */
            break;
    }

    *out       = s_out;
    out->state = s_state;
}
