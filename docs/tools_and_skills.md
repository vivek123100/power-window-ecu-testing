# Tools & Skills Log

Every tool and method used in this project, where it was used, and the evidence in the repo.
Status: ✅ used in the project · 🔧 set up, not used yet · 📅 planned

_Last updated: 14 Nov 2026 (MIL, SIL, CAN/UDS complete; CR_01 implemented, 87 tests)_

## Modelling & simulation
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| MATLAB | ✅ | Test automation scripts, data analysis of simulation results | `01_MIL/tests/` |
| Simulink | ✅ | Closed-loop MIL model: controller + plant, fixed-step 10 ms, From/To Workspace interfaces | `01_MIL/model/PowerWindow_MIL.slx` |
| Stateflow | ✅ | ECU state machine with 6 states, transition priorities, temporal logic (`after`) | `01_MIL/model/` |
| MATLAB Function block | ✅ | Plant model: window position, motor current, obstacle, end stops | `01_MIL/model/` |
| MATLAB Online | ✅ | Model development in the browser | – |

## Test automation
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| MATLAB test harness (`Simulink.SimulationInput`, `sim`) | ✅ | Automated 21 requirements-based test cases, auto-generated report | `01_MIL/tests/run_mil_tests.m`, `reports/MIL_test_report.md` |
| Python | ✅ | SIL test environment: closed-loop simulation, plant model, C interface via `ctypes` | `02_SIL/tests/sil_env.py` |
| pytest | ✅ | 22 test cases (parametrised), fixtures that build the C library; 20/20 executed pass | `02_SIL/tests/test_window_ctrl.py` |

## Embedded software (SIL)
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| WSL (Ubuntu on Windows) | ✅ | Linux build and test environment (same OS as CI) | – |
| gcc | ✅ | Compiled the controller as a shared library with `-Wall -Wextra -Werror` | `02_SIL/tests/sil_env.py` |
| gcov / gcovr (code coverage) | ✅ | Line and branch coverage of the C controller: 81 % → 96 % lines, 97 % branches; HTML report | `reports/coverage/` |
| cppcheck (static analysis, MISRA C:2012 addon) | ✅ | Static analysis of the controller; verified the MISRA addon with a self-test file; 2 findings (Rule 8.7) handled as a documented deviation | `reports/static/`, `02_SIL/misra_suppressions.txt` |
| Embedded C (C99) | ✅ | Hand-coded the Stateflow state machine: switch/case, priority-ordered transitions, tick-based timer, named calibration constants | `02_SIL/src/window_ctrl.c/.h` |

## Version control & CI
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| Git | ✅ | Daily commits from Windows and from MATLAB (`gitclone`, `gitrepo`, `commit`, `push`) | Commit history |
| GitHub | ✅ | Public portfolio repository, personal access tokens | Repo |
| GitHub Actions | ✅ | CI pipeline on every push: MISRA check, 36 SIL tests, 20 back-to-back comparisons, coverage gate (≥ 90 %), report artifacts. Green. | `.github/workflows/sil-tests.yml` |
| VS Code | ✅ | Editing docs and code | – |
| Markdown | ✅ | Requirements, test specification, traceability, reports | `docs/`, `reports/` |

## Vehicle networks & diagnostics
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| CAN / DBC | ✅ | Wrote a DBC (2 messages, signals with scaling, value tables, cycle times); decoded frames by hand (Intel byte order) | `03_CAN/dbc/power_window.dbc` |
| python-can (virtual bus) | ✅ | 4-node virtual network: BCM, DCU (my C controller), diagnostic tester, logger; deterministic simulated time | `03_CAN/sim/can_network.py` |
| cantools | ✅ | Encoding/decoding all frames from the DBC; DBC conformance test | `03_CAN/tests/test_can.py` |
| candump log format | ✅ | Bus traces exported for CAN tools (e.g. SavvyCAN) | `reports/can/demo.log` |
| ISO-TP (ISO 15765-2) | ✅ | Implemented single, first, consecutive and flow-control frames by hand | `03_CAN/sim/uds.py` |
| UDS (ISO 14229) | ✅ | Diagnostic server in the ECU: 0x10, 0x22 (F195, 0100), 0x19 02, 0x14, 0x3E, negative responses; DTCs U0140-00 / B1310-00 | `03_CAN/sim/uds.py`, `03_CAN/tests/test_uds.py` |
| SocketCAN (vcan0) | ✅ | Ran the ECU in real time on a Linux SocketCAN interface (WSL) | `03_CAN/sim/run_live.py` |
| can-utils (candump, cansend, cangen) | ✅ | Watched live traffic, measured cycle times from timestamps, injected switch frames, sent UDS requests and ISO-TP flow control by hand | – |
| udsoncan | 📅 | Planned for the HIL bench | – |

## Hardware (PIL / HIL)
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| STM32 / STM32CubeIDE | 📅 | – | – |
| Mini-HIL (real-time plant ↔ MCU over CAN) | 📅 | – | – |

## PIL tools (added 16 Nov 2026)
| Tool | Used for |
|---|---|
| arm-none-eabi-gcc 13 | Cross-compiler for ARM Cortex-M (`-mcpu=cortex-m4 -mfpu=fpv4-sp-d16 -mfloat-abi=hard`) |
| arm-none-eabi-size, map file | Flash/RAM usage of the firmware (2.4 KB flash) |
| Make | Firmware build (`04_PIL/target/Makefile`) |
| Renode 1.17 | Emulated STM32F4 Discovery board, UART → TCP socket, headless in tests |

## Methods & standards
| Method | Status | Where I applied it |
|---|---|---|
| V-model / X-in-the-loop (MIL, SIL, PIL, HIL) | ✅ | Project structure; MIL complete |
| Requirements engineering (testable "shall" requirements) | ✅ | 18 requirements in `docs/requirements.md` (2 change requests) |
| Requirements review | ✅ | Found an untestable requirement (REQ_06: physically impossible timing) and rewrote it |
| Test specification | ✅ | 68 test cases across MIL, SIL, CAN, E2E and UDS in `docs/test_specification.md` |
| Change request process (CR_01) | ✅ | Impact analysis, requirement update, model + code change, tests written first (red), then green; back-to-back kept model and code in step |
| Scenario review / requirement gap analysis | ✅ | Found gaps (idle timeout, E2E, detection window) and out-of-scope items (engine off/locking, crash); documented with decisions |
| Test-driven development | ✅ | UDS clear-DTC test written first (red), then the C function `WindowCtrl_ClearDtcs` (green) |
| Manual fault injection on a live bus | ✅ | Stopped the BCM sender with cangen/Ctrl+C -> timeout, DTC U0140-00, read and cleared via UDS by hand |
| Hardware-in-the-Loop (mini-HIL) | ✅ | ECU firmware runs on its own as a CAN node on vcan0 (Renode SocketCAN bridge); real-time plant, BCM and UDS tester on the PC; 12 tests measured on the bus |
| CAN driver (bxCAN, register level) | ✅ | Init, bit timing 500 kbit/s, acceptance filter, RX FIFO, 3 TX mailboxes |
| UDS + ISO-TP in embedded C | ✅ | Server with 0x10/0x22/0x19/0x14/0x3E and NRCs; FF → wait for Flow Control → CF one per ms |
| Real-time test measurement | ✅ | Reaction times and cycle times from frame timestamps; test-system health check, inconclusive results |
| Processor-in-the-Loop (PIL) | ✅ | Unchanged controller cross-compiled for STM32F407; all 103 SIL/CAN tests re-run on the target in Renode; MIL vs. PIL back-to-back 23/23 identical |
| Bare-metal embedded C | ✅ | Own startup code (vector table, .data/.bss init, FPU on), linker script, register-level UART, interrupt + WFI, SysTick timing, no HAL |
| Execution time measurement | ✅ | SysTick around `WindowCtrl_Step` on every call; worst < 1 µs of 10 ms (emulator estimate); learned DWT isn't modelled in Renode |
| Test harness abstraction | ✅ | `pil_target.py` has the same API as the SIL ctypes library, so one test suite runs on PC and target (`TARGET=pil`) |
| E2E protection (AliveCounter) | ✅ | CR_04: C module `e2e_counter.c` discards stale frames, U0422-00 after 3 in a row; check placed in the communication layer, so the window logic stayed unchanged |
| Frozen-sender fault injection | ✅ | Live BCM (`bcm_live.py`) frozen on purpose: frames on time but stale; watched the counter stop in candump |
| Robustness testing (unexpected input) | ✅ | Two ECUs on one bus crashed the ISO-TP receiver; fixed to drop bad frames, regression test TC_68 |
| Git feature branch + pull request | ✅ | CR_04 developed on `cr04-e2e-alive-counter`, merged into `main` through a PR with green CI |
| Workshop diagnostic flow (repair → clear → verify) | ✅ | Saw a cleared DTC come straight back while the fault was still present |
| Communication fault testing | ✅ | Real message gaps on the bus: timeout boundary 500 vs 560 ms, 510 ms detection time measured |
| Traceability (requirement ↔ test ↔ result) | ✅ | `docs/traceability.md` |
| Boundary value analysis | ✅ | 7.9 / 8.1 A, 8.9 / 9.0 V, 7.9 / 8.1 s |
| Fault injection | ✅ | CAN message timeout, motor overrun, low voltage, obstacle (pinch) |
| Requirement × state matrix (model completeness) | ✅ | Found missing fault handling in PINCH_REVERSE |
| Regression testing | ✅ | Full test suite rerun after every model change |
| Debugging / root cause analysis | ✅ | Test setup errors (wrong Step block, hard-coded Constant), 3 design defects |
| Plant modelling (closed loop) | ✅ | Window, motor current, stall, end stops |
| Same test cases reused across test levels (MIL → SIL) | ✅ | 22 test cases with identical inputs and limits in MATLAB and pytest |
| Code review | ✅ | Reviewed my own C code against the chart; found ERROR recovery bug (missing `!`) |
| Back-to-back testing (model vs. code) | ✅ | All 20 scenarios compared every 10 ms: 100 % identical; found a one-sample initialisation defect in the model (`reports/b2b/b2b_report.md`) |
| Golden reference data | ✅ | MIL runs exported as CSV and committed, so CI can compare without MATLAB |
| Code coverage analysis (statement, branch) | ✅ | Found 9 untested transitions + 5 untested conditions; added TC_23–TC_36; justified defensive code |
| Sensor fault injection | ✅ | Stuck position sensor in the SIL plant to reach overrun protection while opening and during pinch reversal |
| MISRA C:2012 | ✅ | Coding style followed (named constants, braces, `else` on every chain, `break` on every case); deviation process (DEV_01) |
| Mutation testing | ✅ | Planted 21 bugs in the C code one at a time; 16 killed at first, 5 survivors showed real test gaps (exact boundaries, pinch-zone limit, clear of all DTCs, counter jump); closed with TC_81–TC_87 |
| Independent V&V review | ✅ | Fresh-clone re-run of all levels, scripted traceability audit, gcov branch analysis (found dead code left by a change request), requirement validation against FMVSS 118 (force vs. current, reversal distance, block detection) |
| Tool qualification ("test the test tool") | ✅ | Found that the MISRA check reported 0 findings because it was misconfigured; proved it with a known-bad file |
| Continuous integration with quality gates | ✅ | Build fails on new MISRA findings, test failures, model/code mismatch or coverage < 90 % |
| Functional safety awareness (ISO 26262) | ✅ basic | Anti-pinch treated as a safety function; no re-closing on a trapped obstacle |
