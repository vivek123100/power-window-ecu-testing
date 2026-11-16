# 04_PIL – Processor-in-the-Loop

The **unchanged** controller code (`02_SIL/src/window_ctrl.c`, `e2e_counter.c`) is cross-compiled for an
ARM Cortex-M4 and runs on an STM32F407. The PC keeps the plant model and the test cases, exactly as in SIL.
Every 10 ms the PC sends the inputs over a UART, the target runs `WindowCtrl_Step` and sends the outputs back.

```
 PC (pytest)                                    STM32F407 (Renode emulator, later a real board)
 ┌──────────────────────────────┐   UART2       ┌─────────────────────────────────────┐
 │ test cases (02_SIL, 03_CAN)  │  inputs  ──►  │ main.c: PIL server                  │
 │ plant model (window, motor)  │               │   WindowCtrl_Step()  ← code under   │
 │ pil_target.py (same API as   │  ◄── outputs  │   E2E_CheckCounter()   test         │
 │ the SIL ctypes library)      │   + cycles    │ startup.c, linker script, no HAL    │
 └──────────────────────────────┘               └─────────────────────────────────────┘
```

**What PIL adds over SIL**

| Risk | SIL (host gcc, x86-64) | PIL (arm-none-eabi-gcc, Cortex-M4F) |
|---|---|---|
| Different compiler and optimisation (-O2) | not covered | ✅ |
| Different processor: 32-bit, hardware single-precision FPU | not covered | ✅ |
| Enum / bool / struct sizes, alignment | not covered | ✅ (inputs packed byte by byte) |
| Code fits in flash and RAM | not covered | ✅ (`arm-none-eabi-size`) |
| Execution time per step | not covered | ✅ measured with SysTick (see note) |
| Start-up code, static variables start at 0 | not covered | ✅ (`startup.c` clears `.bss`) |

PIL is **not** real-time: each step waits for the UART round trip, so a 10 s test takes longer than 10 s.
That's normal; HIL is the level that runs in real time.

## Folder

| File | What it is |
|---|---|
| `target/startup.c` | Reset handler: copy `.data`, clear `.bss`, FPU on, call `main`; vector table |
| `target/stm32f407.ld` | Linker script: 1 MB flash at 0x08000000, 128 KB RAM at 0x20000000 |
| `target/main.c` | PIL server: UART2 protocol, calls the controller, measures execution time |
| `target/Makefile` | Builds `target/build/pil_fw.elf` with `-Werror` |
| `renode/pil.resc` | Renode script: STM32F4 Discovery board, UART2 → TCP port 3456 |
| `host/pil_target.py` | PC side: starts Renode, same functions as the SIL library |
| `run_pil.sh` | One command: build + all SIL and CAN tests on the target |

## Setup (once, Ubuntu / WSL)

```bash
sudo apt install -y gcc-arm-none-eabi libnewlib-arm-none-eabi make
arm-none-eabi-gcc --version

cd ~
wget https://github.com/renode/renode/releases/download/v1.17.0/renode-1.17.0.linux-portable.tar.gz
tar xzf renode-1.17.0.linux-portable.tar.gz
echo 'export PATH="$HOME/renode_1.17.0-portable:$PATH"' >> ~/.bashrc
source ~/.bashrc
renode --version                 # Renode v1.17.0
```

## Run

```bash
pw
bash 04_PIL/run_pil.sh                          # all tests on the target
bash 04_PIL/run_pil.sh -k "TC_04 or TC_61"      # a few tests (fast check)
TARGET=pil pytest 02_SIL/tests/test_e2e_counter.py -v
```

The end of the pytest output shows the measured execution time of `WindowCtrl_Step`.
`reports/b2b/b2b_pil_report.md` is the back-to-back comparison **MIL vs. PIL**.

## Protocol (UART2, binary, little endian)

| Request | Payload | Response |
|---|---|---|
| `A5 'P'` ping | – | `5A 'P' "PIL1"` |
| `A5 'I'` WindowCtrl_Init | – | `5A 'I'` |
| `A5 'S'` WindowCtrl_Step | u8 up, u8 down, f32 pos, f32 current, f32 vbat, f32 age | `5A 'S'` i8 motor, u8 pinch, u8 dtc_timeout, u8 dtc_overrun, u8 state, u32 ticks |
| `A5 'C'` WindowCtrl_ClearDtcs | – | `5A 'C'` |
| `A5 'e'` / `'K'` / `'D'` / `'X'` | E2E_Init / CheckCounter (u8) / DtcActive / ClearDtc | `5A` + cmd (+ 1 byte) |

## Lessons from building it

1. **Busy-polling a register is expensive.** The first firmware polled the UART status register in a loop:
   110 ms per step, virtual time 40× slower than real time. With a receive interrupt and `WFI` (sleep until
   the next interrupt): 8 ms per step. On a real ECU the same change saves power.
2. **Race condition before `WFI`.** A byte can arrive between "buffer empty?" and `WFI`; the CPU would then
   sleep with data waiting. Fix: interrupts off while checking (`cpsid i`); `WFI` still wakes on a pending interrupt.
3. **The emulator is not the chip.** Renode does not model the DWT cycle counter (it reads 0), and its timing
   is based on instruction counts, not real clock cycles. SysTick works, but the numbers are an estimate:
   real execution time needs a real board.

## Moving to a real board (later)

Nucleo boards connect USART2 (PA2/PA3) to the ST-LINK USB virtual COM port, so the same protocol works over
`/dev/ttyACM0`. Steps then: flash with `st-flash` or STM32CubeProgrammer, set the real clock, use DWT for
exact cycles, and add a serial link in `pil_target.py` (pyserial) instead of the Renode TCP socket.
For an STM32G4 (e.g. Nucleo-G431RB) the startup, linker script and register addresses change; the
controller code and the tests stay the same.
