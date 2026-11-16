/**
 * @file  main.c
 * @brief PIL server: runs the UNCHANGED controller code (02_SIL/src) on the
 *        STM32 and lets the PC call its functions over the UART.
 *
 * The PC (04_PIL/host/pil_target.py) plays the plant and the test harness,
 * exactly like in SIL; only the controller runs on the target processor.
 *
 * UART2 receive is interrupt-driven into a ring buffer; while waiting, the CPU
 * sleeps (WFI). Busy-polling a status register costs a lot in an emulator (and
 * power on a real ECU), so the firmware only wakes up when a byte arrives.
 *
 * Protocol (binary, little endian):
 *   request  = 0xA5, cmd, payload        response = 0x5A, cmd, payload
 *   'P' ping                       -> "PIL1"
 *   'I' WindowCtrl_Init            -> (nothing)
 *   'S' WindowCtrl_Step  18 bytes: u8 up, u8 down, f32 pos, f32 current, f32 vbat, f32 age
 *                        -> 9 bytes: i8 motor, u8 pinch, u8 dtc_timeout, u8 dtc_overrun,
 *                                    u8 state, u32 CPU cycles used by WindowCtrl_Step (SysTick)
 *   'C' WindowCtrl_ClearDtcs       -> (nothing)
 *   'e' E2E_Init                   -> (nothing)
 *   'K' E2E_CheckCounter  1 byte   -> 1 byte status
 *   'D' E2E_DtcActive              -> 1 byte
 *   'X' E2E_ClearDtc               -> (nothing)
 *   unknown cmd                    -> 0x5A, '?'
 */
#include <stdint.h>
#include <string.h>
#include "window_ctrl.h"
#include "e2e_counter.h"

#define REG(addr)       (*(volatile uint32_t *)(addr))

/* Clocks and pins (needed on a real board; Renode does not check them) */
#define RCC_AHB1ENR     REG(0x40023830U)
#define RCC_APB1ENR     REG(0x40023840U)
#define GPIOA_MODER     REG(0x40020000U)
#define GPIOA_AFRL      REG(0x40020020U)

/* USART2 on PA2 (TX) / PA3 (RX) - on Nucleo boards this is the ST-LINK virtual COM port */
#define USART2_SR       REG(0x40004400U)
#define USART2_DR       REG(0x40004404U)
#define USART2_BRR      REG(0x40004408U)
#define USART2_CR1      REG(0x4000440CU)
#define SR_RXNE         (1U << 5)
#define SR_TXE          (1U << 7)
#define CR1_RXNEIE      (1U << 5)
#define NVIC_ISER1      REG(0xE000E104U)            /* enable IRQs 32..63 */
#define IRQ_USART2      (38U)

#define RX_SIZE         (64U)                       /* power of 2 */
static volatile uint8_t  s_rx_buf[RX_SIZE];
static volatile uint32_t s_rx_head;                 /* written by the interrupt */
static uint32_t          s_rx_tail;                 /* read by main             */

/* SysTick: 24-bit down-counter on the CPU clock, used to measure execution time.
 * (Every Cortex-M has it. The DWT cycle counter is more common on real boards,
 * but Renode does not model it.) */
#define SYST_CSR        REG(0xE000E010U)
#define SYST_RVR        REG(0xE000E014U)
#define SYST_CVR        REG(0xE000E018U)
#define SYST_MASK       (0x00FFFFFFU)

#define SYNC_REQ        (0xA5U)
#define SYNC_RESP       (0x5AU)

static void uart_init(void)
{
    RCC_AHB1ENR |= (1U << 0);                       /* GPIOA clock  */
    RCC_APB1ENR |= (1U << 17);                      /* USART2 clock */
    GPIOA_MODER = (GPIOA_MODER & ~(0xFU << 4)) | (0xAU << 4);      /* PA2, PA3 = alternate function */
    GPIOA_AFRL  = (GPIOA_AFRL & ~(0xFFU << 8)) | (0x77U << 8);     /* AF7 = USART2 */
    USART2_BRR  = 0x8BU;                            /* 115200 baud at 16 MHz (HSI) */
    USART2_CR1  = (1U << 13) | (1U << 3) | (1U << 2) | CR1_RXNEIE;  /* UE, TE, RE, RX interrupt */
    NVIC_ISER1  = (1U << (IRQ_USART2 - 32U));
}

void USART2_IRQHandler(void);
void USART2_IRQHandler(void)
{
    while ((USART2_SR & SR_RXNE) != 0U)
    {
        s_rx_buf[s_rx_head & (RX_SIZE - 1U)] = (uint8_t)USART2_DR;
        s_rx_head++;
    }
}

static uint8_t uart_get(void)
{
    /* Interrupts off while checking, so a byte arriving between the check and
     * WFI cannot be missed: WFI still wakes up on a pending interrupt. */
    __asm volatile ("cpsid i" ::: "memory");
    while (s_rx_tail == s_rx_head)
    {
        __asm volatile ("wfi");                     /* sleep until the next interrupt */
        __asm volatile ("cpsie i\n isb\n cpsid i" ::: "memory");   /* let the ISR run */
    }
    __asm volatile ("cpsie i" ::: "memory");
    const uint8_t b = s_rx_buf[s_rx_tail & (RX_SIZE - 1U)];
    s_rx_tail++;
    return b;
}

static void uart_put(uint8_t b)
{
    while ((USART2_SR & SR_TXE) == 0U) { }
    USART2_DR = b;
}

static void uart_read(uint8_t *buf, uint32_t n)
{
    for (uint32_t i = 0U; i < n; i++) { buf[i] = uart_get(); }
}

static void uart_write(const uint8_t *buf, uint32_t n)
{
    for (uint32_t i = 0U; i < n; i++) { uart_put(buf[i]); }
}

static void respond(uint8_t cmd, const uint8_t *payload, uint32_t n)
{
    uart_put(SYNC_RESP);
    uart_put(cmd);
    uart_write(payload, n);
}

static void cycle_counter_init(void)
{
    SYST_RVR = SYST_MASK;                           /* count down from 2^24 - 1 */
    SYST_CVR = 0U;
    SYST_CSR = (1U << 2) | (1U << 0);               /* CPU clock, enable, no interrupt */
}

static void do_step(void)
{
    uint8_t rx[18];
    uint8_t tx[9];
    WindowInputs_t  in;
    WindowOutputs_t out;

    uart_read(rx, sizeof rx);
    in.sw_up   = (rx[0] != 0U);
    in.sw_down = (rx[1] != 0U);
    (void)memcpy(&in.pos_pct,       &rx[2],  4U);
    (void)memcpy(&in.current_a,     &rx[6],  4U);
    (void)memcpy(&in.vbat_v,        &rx[10], 4U);
    (void)memcpy(&in.sw_msg_age_ms, &rx[14], 4U);

    const uint32_t t0 = SYST_CVR;
    WindowCtrl_Step(&in, &out);                     /* the code under test */
    const uint32_t cycles = (t0 - SYST_CVR) & SYST_MASK;   /* down-counter, wraps */

    tx[0] = (uint8_t)out.motor_cmd;
    tx[1] = out.pinch_flag ? 1U : 0U;
    tx[2] = out.dtc_switch_timeout ? 1U : 0U;
    tx[3] = out.dtc_motor_overrun ? 1U : 0U;
    tx[4] = (uint8_t)out.state;
    (void)memcpy(&tx[5], &cycles, 4U);
    respond('S', tx, sizeof tx);
}

int main(void)
{
    uart_init();
    cycle_counter_init();
    WindowCtrl_Init();
    E2E_Init();

    for (;;)
    {
        if (uart_get() != SYNC_REQ)
        {
            continue;                               /* resynchronise on the next 0xA5 */
        }
        const uint8_t cmd = uart_get();
        uint8_t b;
        switch (cmd)
        {
            case 'P': respond('P', (const uint8_t *)"PIL1", 4U); break;
            case 'I': WindowCtrl_Init(); respond('I', NULL, 0U); break;
            case 'S': do_step(); break;
            case 'C': WindowCtrl_ClearDtcs(); respond('C', NULL, 0U); break;
            case 'e': E2E_Init(); respond('e', NULL, 0U); break;
            case 'K': b = (uint8_t)E2E_CheckCounter(uart_get()); respond('K', &b, 1U); break;
            case 'D': b = E2E_DtcActive() ? 1U : 0U; respond('D', &b, 1U); break;
            case 'X': E2E_ClearDtc(); respond('X', NULL, 0U); break;
            default:  respond('?', NULL, 0U); break;
        }
    }
}
