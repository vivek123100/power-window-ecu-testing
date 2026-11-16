/**
 * @file  startup.c
 * @brief Minimal start-up code for the STM32F407 (Cortex-M4F), no vendor HAL.
 *
 * What happens after reset, before main():
 *  1. The CPU reads the first two words of flash: initial stack pointer and
 *     the address of Reset_Handler (the vector table below).
 *  2. Reset_Handler copies initialised variables (.data) from flash to RAM,
 *     fills .bss with zeros (static variables like s_state start at 0),
 *     switches on the floating-point unit, then calls main().
 */
#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;   /* from the linker script */
extern int main(void);

void Reset_Handler(void);
void Default_Handler(void);

/* Interrupt handlers used by the firmwares. "weak" = if a firmware does not
 * define one, Default_Handler is used. Shared by PIL (04_PIL) and HIL (05_HIL). */
void SysTick_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void USART2_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));
void CAN1_RX0_IRQHandler(void) __attribute__((weak, alias("Default_Handler")));

#define IRQ_CAN1_RX0 (20)                                /* STM32F4 interrupt numbers */
#define IRQ_USART2   (38)
#define N_VECTORS    (16 + 82)                           /* 16 core + 82 STM32F407 IRQs */

#define SCB_CPACR (*(volatile uint32_t *)0xE000ED88U)   /* coprocessor access control */

void Reset_Handler(void)
{
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) { *dst++ = *src++; }           /* .data: flash -> RAM */
    for (dst = &_sbss; dst < &_ebss; dst++) { *dst = 0U; } /* .bss = 0          */

    SCB_CPACR |= (0xFU << 20);                           /* FPU on (CP10, CP11) */
    __asm volatile ("dsb\n isb");

    (void)main();
    for (;;) { }                                         /* main never returns  */
}

void Default_Handler(void)
{
    for (;;) { }                                         /* unexpected interrupt: stop here */
}

/* Vector table: placed at the start of flash by the linker script.
 * Used: SysTick (HIL 1 ms tick), CAN1 RX FIFO 0 (HIL) and USART2 receive (PIL). */
__attribute__((section(".isr_vector"), used))
const void *const g_vectors[N_VECTORS] =
{
    &_estack,              /* 0  initial stack pointer */
    Reset_Handler,         /* 1  reset                 */
    Default_Handler,       /* 2  NMI                   */
    Default_Handler,       /* 3  HardFault             */
    Default_Handler,       /* 4  MemManage             */
    Default_Handler,       /* 5  BusFault              */
    Default_Handler,       /* 6  UsageFault            */
    0, 0, 0, 0,            /* 7-10 reserved            */
    Default_Handler,       /* 11 SVCall                */
    Default_Handler,       /* 12 DebugMonitor          */
    0,                     /* 13 reserved              */
    Default_Handler,       /* 14 PendSV                */
    SysTick_Handler,       /* 15 SysTick               */
    [16 ... (16 + IRQ_CAN1_RX0 - 1)] = Default_Handler, /* IRQs 0..19: unused       */
    [16 + IRQ_CAN1_RX0] = CAN1_RX0_IRQHandler,          /* IRQ 20: CAN1 RX FIFO 0   */
    [(16 + IRQ_CAN1_RX0 + 1) ... (16 + IRQ_USART2 - 1)] = Default_Handler,
    [16 + IRQ_USART2] = USART2_IRQHandler,              /* IRQ 38: USART2           */
    [(16 + IRQ_USART2 + 1) ... (N_VECTORS - 1)] = Default_Handler,
};
