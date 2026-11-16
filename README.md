# Power Window ECU – End-to-End Verification

![SIL tests](https://github.com/vivek123100/power-window-ecu-testing/actions/workflows/sil-tests.yml/badge.svg)

A power window ECU with anti-pinch protection, verified along the **V-model**: from requirements through
**Model-in-the-Loop**, **Software-in-the-Loop**, a **CAN/UDS network**, **Processor-in-the-Loop** on an STM32 and a
**mini Hardware-in-the-Loop** bench, with automated tests, back-to-back comparison, coverage, static analysis and CI.
Personal portfolio project: MATLAB/Simulink for MIL, open-source tools for everything else.

> **Skills shown:** ECU software testing · test automation (Python/pytest) · MIL/SIL/PIL/HIL · requirements-based
> testing and traceability · Simulink/Stateflow · embedded C (STM32, bare metal) · CAN, DBC, UDS (ISO 14229), ISO-TP ·
> E2E protection · fault injection · code coverage · MISRA C:2012 · CI/CD (GitHub Actions) · change requests

> **About PIL/HIL:** the STM32 is **emulated** (Renode) and the bus is Linux SocketCAN (`vcan0`); there is no physical
> bench yet. The firmware is real ARM code built with the target compiler, and the HIL tests run in real time on the bus,
> but analog I/O is replaced by CAN messages and timing on the emulator is an estimate (see [`05_HIL/`](05_HIL)).

| | |
|---|---|
| Requirements | **18** (incl. two change requests, CR_01 and CR_04) |
| Test cases | **80**, traced to requirements |
| Automated tests | **103** on every push (SIL, back-to-back, CAN, UDS) + **12** real-time HIL tests + **23** MIL tests in MATLAB |
| Model vs. code | **100 % identical**, every signal every 10 ms: MIL vs. SIL **and** MIL vs. PIL (back-to-back) |
| On the target | same 103 tests on an **STM32F407** (Cortex-M4F, Renode emulator); worst step time < 1 µs of 10 ms |
| HIL | ECU firmware (bxCAN driver, UDS + ISO-TP in C) on vcan0, measured on the bus: reaction ≤ 50 ms, timeout 500–520 ms, cycle 100 ± 10 ms; **12 / 12 pass** |
| Code coverage | **96 % lines** (only defensive code uncovered) |
| Static analysis | cppcheck + MISRA C:2012 addon, 1 documented deviation |
| Defects found | **11** (design, code, model, test tool, requirements, robustness) |

## How it fits together

```mermaid
flowchart LR
  REQ["Requirements<br/>18 REQ · 80 TC"] --> MIL["MIL<br/>Simulink / Stateflow<br/>23 / 23 pass"]
  MIL --> SIL["SIL<br/>C99 + pytest<br/>48 tests"]
  MIL -. "back-to-back<br/>23 scenarios" .- SIL
  SIL --> CAN["CAN + UDS + E2E<br/>virtual bus + SocketCAN<br/>32 tests"]
  CAN --> PIL["PIL<br/>STM32F407 on Renode<br/>103 tests · 23/23 identical"]
  PIL --> HIL["Mini-HIL<br/>firmware as CAN node on vcan0<br/>12 / 12 real-time tests"]
```

The same test cases run at every level; only the "in-the-loop" part changes.

## The feature

The driver presses Up or Down; the switch request arrives over CAN from the body control module (BCM).
The door ECU drives the motor, stops at the end positions, and **reverses if something is trapped**
while the window closes.

| Function | Requirements |
|---|---|
| Up / down / stop / end positions | REQ_01 – REQ_04 |
| Anti-pinch: detect > 8 A between 4 and 96 %, reverse ≥ 20 %, no re-closing until released | REQ_05 – REQ_07, REQ_13, REQ_14 |
| Protection: voltage 9–16 V, CAN timeout > 500 ms (any state), motor overrun > 8 s, Up+Down | REQ_08 – REQ_11 |
| CAN status message every 100 ms | REQ_12 |
| UDS diagnostics (0x10, 0x22, 0x19, 0x14, 0x3E), DTCs U0140-00, B1310-00 and U0422-00 | REQ_15, REQ_16 |
| E2E protection: AliveCounter check on the switch message, frozen sender → U0422-00 | REQ_17, REQ_18 |

Controller states: `IDLE`, `MOVING_UP`, `MOVING_DOWN`, `PINCH_REVERSE`, `WAIT_RELEASE`, `ERROR`.

## Test levels

| Level | What runs | Where | Result |
|---|---|---|---|
| **MIL** | Stateflow controller + plant model, automated harness, fault injection | [`01_MIL/`](01_MIL) | 23 / 23 pass ([report](reports/MIL_test_report.md)) |
| **SIL** | Hand-written C99 controller via ctypes, Python plant, pytest | [`02_SIL/`](02_SIL) | 48 tests pass (40 controller + 8 E2E unit) |
| **Back-to-back** | MIL reference data vs. SIL, all signals every 10 ms | `02_SIL/tests/test_back_to_back.py` | 23 / 23 identical |
| **CAN** | DBC, 4-node virtual network (BCM, ECU, tester, logger), cycle times, timeouts | [`03_CAN/`](03_CAN) | 18 tests pass (incl. 7 frozen-sender tests) |
| **UDS** | ISO-TP + UDS server in the ECU: read data, read/clear DTCs, negative responses, P2 | [`03_CAN/`](03_CAN) | 14 tests pass |
| **Live** | ECU in real time on Linux SocketCAN `vcan0`: live BCM, pinch, frozen sender, UDS by hand | [`03_CAN/LIVE_DEMO.md`](03_CAN/LIVE_DEMO.md) | manual demos A–E |
| **PIL** | Same tests, controller cross-compiled for an STM32F407 (bare metal, UART link), run in the Renode emulator; execution time measured | [`04_PIL/`](04_PIL) | 103 tests pass, MIL vs. PIL 23 / 23 identical |
| **HIL** | ECU firmware runs on its own (1 ms clock, bxCAN, UDS in C) on SocketCAN; real-time plant, BCM and tester on the PC; bench health check (inconclusive instead of false results) | [`05_HIL/`](05_HIL) | 12 / 12 pass |

## What testing found

| # | Found by | Defect | Fix |
|---|---|---|---|
| 1 | Requirement × state matrix | No fault handling during pinch reversal | Added transitions, TC_20 |
| 2 | MIL test | Window re-closed on a trapped hand while Up was held | New state `WAIT_RELEASE`, REQ_13, TC_21 |
| 3 | MIL test | Pinch flag cleared too early | REQ_14 |
| 4 | Requirement review | REQ_06 physically impossible (20 % in 200 ms) | Reworded |
| 5 | Code review + SIL tests | ERROR recovery checked "Up pressed" instead of "released" | One missing `!` fixed, TC_22 |
| 6 | Back-to-back | Model initialised the position to 50 % at power-on | Unit Delay initial condition |
| 7 | Coverage | 9 transitions and 5 conditions never tested | TC_23 – TC_36, sensor fault injection |
| 8 | Tool self-test | MISRA check silently reported nothing (misconfigured) | `--enable=style`, self-test file |
| 9 | Live SocketCAN test | Dead BCM not detected while the window was idle | Change request **CR_01**, TC_49 – TC_53 |
| 10 | Scenario review | Frozen sender: stale "Up pressed" frames arriving on time kept the window moving (AliveCounter never checked) | Change request **CR_04**: E2E check, U0422-00, TC_54 – TC_67 |
| 11 | Live SocketCAN test | Two ECUs on one bus crashed the diagnostic receiver (duplicate ISO-TP frame) | Robust ISO-TP receiver, TC_68 |

Open points and out-of-scope items (CRC for E2E, start-up delay, engine-off / locking behaviour, crash behaviour) are
listed in [`docs/requirements.md`](docs/requirements.md).

## Run it

```bash
# Linux / WSL, from the repo root
python3 -m venv .venv && source .venv/bin/activate
pip install pytest gcovr cantools python-can
sudo apt install -y gcc cppcheck            # static analysis
bash run_all.sh                             # MISRA + 103 tests + coverage gate (>= 90 %)

python3 03_CAN/sim/run_demo.py              # lost CAN message -> ERROR after 510 ms
python3 03_CAN/sim/run_uds_demo.py          # UDS session frame by frame
bash 04_PIL/run_pil.sh                      # PIL: same tests on the emulated STM32 (needs arm-none-eabi-gcc + Renode)
bash 05_HIL/run_hil.sh                      # HIL: ECU firmware as a CAN node on vcan0, real-time tests
```

PIL and HIL also need the ARM compiler and Renode (`sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi`,
Renode 1.17 portable), see [`04_PIL/README.md`](04_PIL/README.md); HIL needs `vcan0` (set up by `run_hil.sh`).

MIL: open `01_MIL/model/PowerWindow_MIL.slx` in MATLAB/Simulink and run `run_mil_tests` from `01_MIL/tests/`.
The live SocketCAN demo (4 terminals) is described in [`03_CAN/LIVE_DEMO.md`](03_CAN/LIVE_DEMO.md).

CI (GitHub Actions) runs the MISRA check, all SIL/CAN/UDS tests, back-to-back and the coverage gate on every push.
PIL and HIL run locally (they need Renode).

## Documents

- [Requirements](docs/requirements.md) · [Test specification](docs/test_specification.md) · [Traceability](docs/traceability.md)
- [CAN / UDS guide with glossary and exercises](03_CAN/README.md) · [Live demo guide](03_CAN/LIVE_DEMO.md)
- [PIL guide](04_PIL/README.md) · [HIL guide](05_HIL/README.md)
- Reports: [MIL test report](reports/MIL_test_report.md) · [back-to-back MIL vs. SIL](reports/b2b/b2b_report.md) · [MIL vs. PIL](reports/b2b/b2b_pil_report.md)
- [Real-world CAN and diagnostic issues (field guide)](docs/real_world_issues.md): problems met while building this, and how they are found and prevented in practice
- [Tools and skills log](docs/tools_and_skills.md)

## Tools

MATLAB · Simulink · Stateflow · C99 · gcc · arm-none-eabi-gcc · STM32 (Cortex-M4F) · Renode · Python · pytest · ctypes · gcov / gcovr · cppcheck (MISRA C:2012) ·
CAN · DBC · E2E (AliveCounter) · cantools · python-can · SocketCAN · can-utils · ISO-TP · UDS (ISO 14229) · Git · GitHub Actions

## Project structure

```
docs/       requirements, test specification, traceability, field guide, tools log
01_MIL/     Simulink/Stateflow model + MATLAB test harness
02_SIL/     C controller (src/) + pytest harness, back-to-back (tests/)
03_CAN/     DBC, virtual CAN network, UDS, live SocketCAN demo, CAN/UDS tests
04_PIL/     PIL: STM32F407 firmware (startup, linker script, UART server), Renode script, host link
05_HIL/     mini-HIL: ECU firmware (bxCAN, UDS), Renode SocketCAN bridge, real-time bench and tests
reports/    MIL report, back-to-back reference data and report, static analysis
run_all.sh  local pipeline, same steps as CI
```
