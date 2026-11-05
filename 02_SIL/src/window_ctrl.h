/**
 * @file  window_ctrl.h
 * @brief Power window controller (SIL implementation of the Stateflow chart).
 *
 * Call WindowCtrl_Init() once at start-up, then WindowCtrl_Step() every 10 ms.
 */
#ifndef WINDOW_CTRL_H
#define WINDOW_CTRL_H

#include <stdbool.h>
#include <stdint.h>

/** Controller states - same as the Stateflow chart. */
typedef enum
{
    WS_IDLE = 0,
    WS_MOVING_UP,
    WS_MOVING_DOWN,
    WS_PINCH_REVERSE,
    WS_WAIT_RELEASE,
    WS_ERROR
} WindowState_t;

/** Inputs, read every cycle (same names as the chart inputs). */
typedef struct
{
    bool  sw_up;           /**< Up switch pressed */
    bool  sw_down;         /**< Down switch pressed */
    float pos_pct;         /**< Window position 0..100 % */
    float current_a;       /**< Motor current [A] */
    float vbat_v;          /**< Battery voltage [V] */
    float sw_msg_age_ms;   /**< Time since last switch CAN message [ms] */
} WindowInputs_t;

/** Outputs, written every cycle. */
typedef struct
{
    int8_t        motor_cmd;          /**< 1 = up, -1 = down, 0 = stop */
    bool          pinch_flag;         /**< Pinch detected (REQ_14) */
    bool          dtc_switch_timeout; /**< REQ_09, latched */
    bool          dtc_motor_overrun;  /**< REQ_10, latched */
    WindowState_t state;              /**< Active state (for testing/debugging) */
} WindowOutputs_t;

void WindowCtrl_Init(void);
void WindowCtrl_Step(const WindowInputs_t *in, WindowOutputs_t *out);
void WindowCtrl_ClearDtcs(void);   /* clear stored DTCs (UDS 0x14) */

#endif /* WINDOW_CTRL_H */
