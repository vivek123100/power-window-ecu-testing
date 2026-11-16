/**
 * @file  main.c
 * @brief HIL firmware: the power window ECU as a real CAN node on the STM32F407.
 *
 * Unlike PIL (the PC calls the controller step by step), here the ECU runs on
 * its own, in real time, like in the car:
 *   - SysTick interrupt every 1 ms = the ECU's clock
 *   - every 10 ms: read CAN, run WindowCtrl_Step, send the motor command
 *   - every 100 ms: send DCU_WindowStatus (REQ_12)
 *
 * CAN (bxCAN, CAN1, 500 kbit/s):
 *   RX 0x200 BCM_WindowSwitch  switches + AliveCounter (E2E check, CR_04)
 *   RX 0x300 HIL_Sensors       from the HIL simulator: position, current, battery
 *   TX 0x301 HIL_Actuators     to the HIL simulator: motor command (every 10 ms)
 *   TX 0x210 DCU_WindowStatus  same layout as in 03_CAN/dbc/power_window.dbc
 *   RX 0x7E0 / TX 0x7E8        UDS diagnostics over ISO-TP (uds.c)
 * 0x300/0x301 replace the analog/PWM I/O of a real HIL bench (sensors, H-bridge).
 * The controller code (02_SIL/src) is unchanged.
 */
#include <stdint.h>
#include <stdbool.h>
#include "window_ctrl.h"
#include "e2e_counter.h"
#include "uds.h"

#define REG(addr)       (*(volatile uint32_t *)(addr))

/* ---- Clock (SysTick input). Renode's STM32F4 model: 72 MHz. Real F407 after
 *      reset (HSI): 16 MHz - change this when moving to a board. ---------- */
#define CPU_HZ          (72000000U)
#define TICK_HZ         (1000U)                     /* 1 ms tick */

#define SYST_CSR        REG(0xE000E010U)
#define SYST_RVR        REG(0xE000E014U)
#define SYST_CVR        REG(0xE000E018U)

#define RCC_AHB1ENR     REG(0x40023830U)
#define RCC_APB1ENR     REG(0x40023840U)
#define GPIOB_MODER     REG(0x40020400U)
#define GPIOB_AFRH      REG(0x40020424U)

/* ---- bxCAN registers (RM0090, chapter 32) ------------------------------- */
#define CAN1_BASE       (0x40006400U)
#define CAN_MCR         REG(CAN1_BASE + 0x000U)
#define CAN_MSR         REG(CAN1_BASE + 0x004U)
#define CAN_TSR         REG(CAN1_BASE + 0x008U)
#define CAN_RF0R        REG(CAN1_BASE + 0x00CU)
#define CAN_BTR         REG(CAN1_BASE + 0x01CU)
#define CAN_TIR(n)      REG(CAN1_BASE + 0x180U + (0x10U * (n)))
#define CAN_TDTR(n)     REG(CAN1_BASE + 0x184U + (0x10U * (n)))
#define CAN_TDLR(n)     REG(CAN1_BASE + 0x188U + (0x10U * (n)))
#define CAN_TDHR(n)     REG(CAN1_BASE + 0x18CU + (0x10U * (n)))
#define CAN_RI0R        REG(CAN1_BASE + 0x1B0U)
#define CAN_RDT0R       REG(CAN1_BASE + 0x1B4U)
#define CAN_RDL0R       REG(CAN1_BASE + 0x1B8U)
#define CAN_RDH0R       REG(CAN1_BASE + 0x1BCU)
#define CAN_FMR         REG(CAN1_BASE + 0x200U)
#define CAN_FM1R        REG(CAN1_BASE + 0x204U)
#define CAN_FS1R        REG(CAN1_BASE + 0x20CU)
#define CAN_FFA1R       REG(CAN1_BASE + 0x214U)
#define CAN_FA1R        REG(CAN1_BASE + 0x21CU)
#define CAN_F0R1        REG(CAN1_BASE + 0x240U)
#define CAN_F0R2        REG(CAN1_BASE + 0x244U)

#define MCR_INRQ        (1U << 0)
#define MCR_SLEEP       (1U << 1)
#define MSR_INAK        (1U << 0)
#define TSR_TME0        (1U << 26)
#define RF0R_FMP0       (3U << 0)
#define RF0R_RFOM0      (1U << 5)
#define TIR_TXRQ        (1U << 0)
#define WAIT_LIMIT      (100000U)                   /* never hang forever on a register */

/* ---- Message IDs ------------------------------------------------------- */
#define ID_SWITCH       (0x200U)
#define ID_STATUS       (0x210U)
#define ID_SENSORS      (0x300U)
#define ID_ACTUATORS    (0x301U)

#define TASK_MS         (10U)                       /* controller cycle  */
#define STATUS_MS       (100U)                      /* REQ_12            */

typedef struct
{
    uint32_t id;
    uint8_t  dlc;
    uint8_t  data[8];
} CanFrame_t;

static volatile uint32_t s_ms;                      /* ms since power-on (SysTick) */

static bool     s_sw_up, s_sw_down;                 /* last ACCEPTED switch frame  */
static uint32_t s_last_switch_ms;                   /* CR_01 option A: 0 = power-on */
static float    s_pos_pct, s_current_a, s_vbat_v;   /* last sensor frame (0 = safe: no voltage) */
static uint32_t s_rx_discarded;                     /* stale frames (E2E)          */

void SysTick_Handler(void);
void SysTick_Handler(void)
{
    s_ms++;
}

/* ---------------------------------------------------------------- bxCAN */
static bool wait_msr(uint32_t mask, uint32_t value)
{
    for (uint32_t i = 0U; i < WAIT_LIMIT; i++)
    {
        if ((CAN_MSR & mask) == value) { return true; }
    }
    return false;
}

static void can_init(void)
{
    RCC_AHB1ENR |= (1U << 1);                       /* GPIOB clock */
    RCC_APB1ENR |= (1U << 25);                      /* CAN1 clock  */
    GPIOB_MODER = (GPIOB_MODER & ~(0xFU << 16)) | (0xAU << 16);      /* PB8 RX, PB9 TX: AF */
    GPIOB_AFRH  = (GPIOB_AFRH & ~0xFFU) | 0x99U;                     /* AF9 = CAN1 */

    CAN_MCR = (CAN_MCR & ~MCR_SLEEP) | MCR_INRQ;    /* leave sleep, enter init mode */
    (void)wait_msr(MSR_INAK, MSR_INAK);
    /* 500 kbit/s at 42 MHz APB1: prescaler 6, 1 + 11 + 2 = 14 time quanta */
    CAN_BTR = (1U << 20) | (10U << 16) | (6U - 1U);

    CAN_FMR  |= 1U;                                 /* filter init mode            */
    CAN_FM1R &= ~1U;                                /* filter 0: mask mode         */
    CAN_FS1R |= 1U;                                 /* 32-bit                      */
    CAN_FFA1R &= ~1U;                               /* -> FIFO 0                   */
    CAN_F0R1 = 0U;                                  /* id 0, mask 0 = accept all   */
    CAN_F0R2 = 0U;
    CAN_FA1R |= 1U;                                 /* activate filter 0           */
    CAN_FMR  &= ~1U;

    CAN_MCR &= ~MCR_INRQ;                           /* normal mode */
    (void)wait_msr(MSR_INAK, 0U);
}

static bool can_receive(CanFrame_t *f)
{
    if ((CAN_RF0R & RF0R_FMP0) == 0U) { return false; }
    const uint32_t rir = CAN_RI0R;
    const uint32_t lo = CAN_RDL0R;
    const uint32_t hi = CAN_RDH0R;
    f->id  = rir >> 21;                             /* standard 11-bit id */
    f->dlc = (uint8_t)(CAN_RDT0R & 0xFU);
    for (uint32_t i = 0U; i < 4U; i++)
    {
        f->data[i]      = (uint8_t)(lo >> (8U * i));
        f->data[i + 4U] = (uint8_t)(hi >> (8U * i));
    }
    CAN_RF0R |= RF0R_RFOM0;                         /* release the FIFO entry */
    return true;
}

bool Can_Send(uint32_t id, const uint8_t *data, uint8_t dlc)
{
    for (uint32_t box = 0U; box < 3U; box++)
    {
        if ((CAN_TSR & (TSR_TME0 << box)) != 0U)    /* mailbox empty? */
        {
            uint32_t lo = 0U, hi = 0U;
            for (uint32_t i = 0U; i < 4U; i++)
            {
                if (i < dlc)        { lo |= (uint32_t)data[i] << (8U * i); }
                if ((i + 4U) < dlc) { hi |= (uint32_t)data[i + 4U] << (8U * i); }
            }
            CAN_TDTR(box) = dlc;
            CAN_TDLR(box) = lo;
            CAN_TDHR(box) = hi;
            CAN_TIR(box)  = (id << 21) | TIR_TXRQ;  /* request transmission */
            return true;
        }
    }
    return false;                                   /* all 3 mailboxes busy */
}

/* ---------------------------------------------------------------- signals */
static uint16_t get_u16(const uint8_t *d) { return (uint16_t)(d[0] | ((uint16_t)d[1] << 8)); }

static UdsEcuData_t s_diag;                         /* what UDS sees, updated every 10 ms */

static void handle_frame(const CanFrame_t *f)
{
    if ((f->id == ID_SWITCH) && (f->dlc >= 2U))
    {
        if (E2E_CheckCounter((uint8_t)(f->data[1] & 0x0FU)) == E2E_STATUS_REPEATED)
        {
            s_rx_discarded++;                       /* stale frame (REQ_17) */
            return;
        }
        s_sw_up   = (f->data[0] & 0x01U) != 0U;
        s_sw_down = (f->data[0] & 0x02U) != 0U;
        s_last_switch_ms = s_ms;
    }
    else if ((f->id == ID_SENSORS) && (f->dlc >= 6U))
    {
        s_pos_pct   = (float)get_u16(&f->data[0]) * 0.01f;
        s_current_a = (float)get_u16(&f->data[2]) * 0.01f;
        s_vbat_v    = (float)get_u16(&f->data[4]) * 0.01f;
    }
    else if (f->id == UDS_REQ_ID)
    {
        Uds_OnFrame(f->data, f->dlc, &s_diag);
    }
    else
    {
        /* other IDs: not for this ECU */
    }
}

static void send_actuators(const WindowOutputs_t *out, uint32_t step_ticks)
{
    uint8_t d[4];
    d[0] = (uint8_t)out->motor_cmd;                 /* int8: 1 up, -1 down, 0 stop */
    d[1] = (uint8_t)out->state;
    d[2] = (uint8_t)step_ticks;                     /* execution time of the step  */
    d[3] = (uint8_t)(step_ticks >> 8);
    (void)Can_Send(ID_ACTUATORS, d, 4U);
}

static void send_status(const WindowOutputs_t *out)
{
    uint8_t d[4];
    const uint8_t motor_state = (out->motor_cmd > 0) ? 1U : ((out->motor_cmd < 0) ? 2U : 0U);
    float raw = (s_pos_pct * 2.0f) + 0.5f;          /* WindowPos: factor 0.5 % */
    if (raw > 255.0f) { raw = 255.0f; }
    d[0] = (uint8_t)raw;
    d[1] = (uint8_t)(motor_state
                     | (out->pinch_flag ? 0x04U : 0U)
                     | (out->dtc_switch_timeout ? 0x08U : 0U)
                     | (out->dtc_motor_overrun ? 0x10U : 0U)
                     | (E2E_DtcActive() ? 0x20U : 0U));
    d[2] = (uint8_t)out->state;                     /* CtrlState */
    d[3] = 0U;
    (void)Can_Send(ID_STATUS, d, 4U);
}

/* ---------------------------------------------------------------- main */
int main(void)
{
    WindowInputs_t  in;
    WindowOutputs_t out = { 0 };
    uint32_t next_task_ms = 0U;
    uint32_t next_status_ms = 0U;

    can_init();
    WindowCtrl_Init();
    E2E_Init();
    Uds_Init();

    SYST_RVR = (CPU_HZ / TICK_HZ) - 1U;
    SYST_CVR = 0U;
    SYST_CSR = 7U;                                  /* CPU clock, interrupt, enable */

    for (;;)
    {
        CanFrame_t f;
        while (can_receive(&f))                     /* empty the RX FIFO every 1 ms */
        {
            handle_frame(&f);
        }
        Uds_Task1ms();                              /* next ISO-TP Consecutive Frame */

        const uint32_t now = s_ms;
        if ((int32_t)(now - next_task_ms) >= 0)     /* 10 ms task */
        {
            next_task_ms += TASK_MS;
            in.sw_up = s_sw_up;
            in.sw_down = s_sw_down;
            in.pos_pct = s_pos_pct;
            in.current_a = s_current_a;
            in.vbat_v = s_vbat_v;
            in.sw_msg_age_ms = (float)(now - s_last_switch_ms);

            const uint32_t t0 = SYST_CVR;
            WindowCtrl_Step(&in, &out);
            const uint32_t t1 = SYST_CVR;
            send_actuators(&out, (t0 >= t1) ? (t0 - t1) : 0U);   /* down-counter */

            s_diag.dtc_switch_timeout = out.dtc_switch_timeout;
            s_diag.dtc_motor_overrun  = out.dtc_motor_overrun;
            s_diag.dtc_switch_invalid = E2E_DtcActive();
            s_diag.pos_pct            = s_pos_pct;

            if ((int32_t)(now - next_status_ms) >= 0)
            {
                next_status_ms += STATUS_MS;
                send_status(&out);
            }
        }
        __asm volatile ("wfi");                     /* sleep until the next tick */
    }
}
