# Tools & Skills Log

Every tool and method used in this project, where it was used, and the evidence in the repo.
Status: ✅ used in the project · 🔧 set up, not used yet · 📅 planned

_Last updated: 5 Nov 2026 (MIL and SIL complete; CI green)_

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
| CAN / DBC | 📅 | – | – |
| SocketCAN, python-can, cantools | 📅 | – | – |
| UDS (udsoncan, ISO-TP) | 📅 | – | – |

## Hardware (PIL / HIL)
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| STM32 / STM32CubeIDE | 📅 | – | – |
| Mini-HIL (real-time plant ↔ MCU over CAN) | 📅 | – | – |

## Methods & standards
| Method | Status | Where I applied it |
|---|---|---|
| V-model / X-in-the-loop (MIL, SIL, PIL, HIL) | ✅ | Project structure; MIL complete |
| Requirements engineering (testable "shall" requirements) | ✅ | 14 requirements in `docs/requirements.md` |
| Requirements review | ✅ | Found an untestable requirement (REQ_06: physically impossible timing) and rewrote it |
| Test specification | ✅ | 36 test cases in `docs/test_specification.md` |
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
| Tool qualification ("test the test tool") | ✅ | Found that the MISRA check reported 0 findings because it was misconfigured; proved it with a known-bad file |
| Continuous integration with quality gates | ✅ | Build fails on new MISRA findings, test failures, model/code mismatch or coverage < 90 % |
| Functional safety awareness (ISO 26262) | ✅ basic | Anti-pinch treated as a safety function; no re-closing on a trapped obstacle |
