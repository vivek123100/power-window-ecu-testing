# 05_HIL – Mini Hardware-in-the-Loop

In PIL the PC calls the controller step by step. In HIL the ECU **runs on its own, in real time**,
like in the car: the firmware on the STM32 has its own 1 ms clock, reads real CAN frames, runs the controller
every 10 ms and sends its frames. The bench around it (plant, BCM, fault injection) also runs in real time,
and every result is **measured on the bus**.

```
             vcan0 (SocketCAN)  ──  candump · bcm_live.py · Wireshark
                 │
 ┌───────────────┴──────────────┐            ┌──────────────────────────────────────┐
 │ HIL bench (PC, 10 ms loop)   │            │ ECU: STM32F407 (Renode emulator)     │
 │  plant: window, motor, hand  │ 0x300 ───► │  bxCAN driver, SysTick 1 ms          │
 │  BCM: switch + AliveCounter  │ 0x200 ───► │  E2E check, message age              │
 │  fault injection             │            │  WindowCtrl_Step every 10 ms         │
 │  logger with timestamps      │ ◄─── 0x301 │  (unchanged code from 02_SIL/src)    │
 │  UDS tester (ISO-TP)         │ ◄─── 0x210 │  status every 100 ms                 │
 │                              │ ◄─► 7E0/7E8│  UDS server + ISO-TP in C (uds.c)    │
 └──────────────────────────────┘            └──────────────────────────────────────┘
```

`0x300` (sensors) and `0x301` (motor command) stand for the analog and PWM I/O of a real HIL bench
(position sensor, current measurement, battery supply, H-bridge). They are described in `dbc/hil_io.dbc`.
`0x200` and `0x210` are the real vehicle messages from `03_CAN/dbc/power_window.dbc`.

## What HIL adds over PIL

| | PIL | HIL |
|---|---|---|
| Who sets the pace | the PC, step by step | the ECU's own clock (SysTick) |
| Inputs | function arguments over UART | real CAN frames on a bus, arriving any time |
| Communication software | not tested | bxCAN driver, RX polling, TX mailboxes, E2E on received frames, UDS + ISO-TP in C |
| Timing requirements | simulated time | **measured in real time** on the bus (reaction ≤ 50 ms, timeout 500–520 ms, cycle 100 ms) |
| Other bus users | none | candump, bcm_live.py, any tool on vcan0 |

## Test-system health (important)

A PC emulator is **soft real-time**: when the PC is busy, Renode can stall for 100+ ms and then catch up.
Real benches (dSPACE, NI) use real-time hardware for that reason. Here every test checks the **bench
itself** during its measurement window: the ECU's 10 ms frames must arrive on time and the bench loop must
not be late (limit 15 ms). If not, the run says nothing about the ECU. It is repeated (up to 3 runs), and if
it never runs cleanly the test is reported **SKIPPED – INCONCLUSIVE**, never as a pass or fail of the ECU.

## Files

| File | What it is |
|---|---|
| `target/main.c` | ECU firmware: bxCAN driver, 1 ms SysTick, 10 ms task, E2E, status every 100 ms |
| `target/uds.c`, `uds.h` | UDS server (0x10, 0x22, 0x19, 0x14, 0x3E, NRCs) and ISO-TP (SF, FF → wait for FC → CF one per ms) |
| `target/Makefile` | Builds `target/build/hil_fw.elf` (startup + linker script shared with 04_PIL) |
| `renode/hil_board.resc` | The emulated STM32F4 board with the firmware |
| `renode/hil_socketcan.resc` | CAN1 ↔ `vcan0` with Renode's SocketCAN bridge |
| `renode/hil_tcp.resc`, `tcp_can_bridge.py` | CAN1 ↔ TCP port 3457, for PCs without SocketCAN (CI, containers) |
| `host/hil_bench.py` | The bench: real-time plant, BCM, fault injection, logger, health check |
| `host/hil_live.py` | Live mode: you drive the ECU by hand (with `bcm_live.py`) |
| `tests/test_hil.py` | TC_69–TC_80, automated real-time tests (incl. UDS on the target) |
| `dbc/hil_io.dbc` | HIL I/O messages 0x300, 0x301 |
| `run_hil.sh` | One command: vcan0 up, build, run the tests |

## Run the tests

Setup: same as `04_PIL` (arm-none-eabi-gcc, Renode) and `vcan0` from the CAN part. Stop `run_live.py` and
`bcm_live.py` first: only the bench may drive the bus during the tests.

```bash
pw
bash 05_HIL/run_hil.sh                      # 12 tests, about 2 minutes (each test = fresh ECU power-on)
HIL_BUS=tcp bash 05_HIL/run_hil.sh          # without vcan0
```

## Live: drive the ECU on the chip

| Terminal | Command | You do |
|---|---|---|
| 1 | `python3 05_HIL/host/hil_live.py` | the world: `p 70` hand, `p` remove, `v 8.5` battery, `v`, `w`, `q` |
| 2 | `candump -ta vcan0` | watch 0x200, 0x210, 0x300 (every 10 ms), 0x301 |
| 3 | `python3 03_CAN/sim/bcm_live.py` | the BCM: `u`, `d`, `r`, `u 0.8`, `f`, `s` (start right after Terminal 1) |

The same demos as in `03_CAN/LIVE_DEMO.md` work (partial opening, pinch, frozen sender, lost message), but the
ECU is now the firmware on the emulated chip. To hide the 10 ms HIL I/O frames: `candump -ta vcan0,200:7FF,210:7FF`
(only 0x200 and 0x210).

Diagnostics on the chip (Terminal 4, `candump -ta vcan0,7E8:7FF` shows the answers):

| Purpose | Command | Answer |
|---|---|---|
| Read DTCs | `cansend vcan0 7E0#031902FFAAAAAAAA` | none `03 59 02 09` · one `07 59 02 09 C1 40 00 08` · two: First Frame `10 0B …` |
| Flow control (after a First Frame) | `cansend vcan0 7E0#3000000000000000` | `21 …` |
| Clear DTCs | `cansend vcan0 7E0#0414FFFFFFAAAAAA` | `01 54` |
| SW version | `cansend vcan0 7E0#0322F195AAAAAAAA` | `10 0B 62 F1 95 …`, then flow control |

Remember the workshop order: repair (unfreeze / resume the BCM, `r`) → clear → read again.

## Lessons from building it

1. **A PC emulator is not a real-time system** – stalls of up to ~180 ms were measured on a busy 2-core PC. The
   fix is not to widen tolerances, but to monitor the test system and separate "bench problem" from "ECU problem".
2. **Measure on the bus, not inside the ECU.** Reaction times are taken from frame timestamps (switch frame →
   motor frame), like a HIL engineer does with CANoe or candump.
3. **Every test starts with a power-on.** Fresh ECU state per test, no hidden dependencies between tests.
