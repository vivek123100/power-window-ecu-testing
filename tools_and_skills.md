# Tools & Skills Log

Every tool and method used in this project, where it was used, and the evidence in the repo.
Status: ✅ used in the project · 🔧 set up, not used yet · 📅 planned

_Last updated: 4 Nov 2026 (MIL complete, SIL setup started)_

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
| Python | 🔧 | – | – |
| pytest | 🔧 | – | – |

## Embedded software (SIL)
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| WSL (Ubuntu on Windows) | 🔧 | Linux build and test environment | – |
| gcc / make | 🔧 | – | – |
| gcov / gcovr (code coverage) | 🔧 | – | – |
| cppcheck (static analysis, MISRA) | 🔧 | – | – |
| Embedded C | 📅 | – | – |

## Version control & CI
| Tool | Status | What I did with it | Evidence |
|---|---|---|---|
| Git | ✅ | Daily commits from Windows and from MATLAB (`gitclone`, `gitrepo`, `commit`, `push`) | Commit history |
| GitHub | ✅ | Public portfolio repository, personal access tokens | Repo |
| GitHub Actions | 🔧 | CI workflow prepared for SIL tests | `.github/workflows/sil-tests.yml` |
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
| Test specification | ✅ | 21 test cases in `docs/test_specification.md` |
| Traceability (requirement ↔ test ↔ result) | ✅ | `docs/traceability.md` |
| Boundary value analysis | ✅ | 7.9 / 8.1 A, 8.9 / 9.0 V, 7.9 / 8.1 s |
| Fault injection | ✅ | CAN message timeout, motor overrun, low voltage, obstacle (pinch) |
| Requirement × state matrix (model completeness) | ✅ | Found missing fault handling in PINCH_REVERSE |
| Regression testing | ✅ | Full test suite rerun after every model change |
| Debugging / root cause analysis | ✅ | Test setup errors (wrong Step block, hard-coded Constant), 3 design defects |
| Plant modelling (closed loop) | ✅ | Window, motor current, stall, end stops |
| Back-to-back testing (model vs. code) | 📅 | – |
| Code coverage (statement, branch, MC/DC) | 📅 | – |
| MISRA C | 📅 | – |
| Functional safety awareness (ISO 26262) | ✅ basic | Anti-pinch treated as a safety function; no re-closing on a trapped obstacle |
