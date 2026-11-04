<<<<<<< HEAD
# Power Window ECU – End-to-End Verification (MIL / SIL / PIL / HIL)

Learning and portfolio project: verifying a power window ECU with anti-pinch
protection across all test levels of the V-model.
  **MIL status:** 19/19 executed test cases pass ([report](reports/MIL_test_report.md))
## Feature under test
The driver operates the window via a switch (CAN). The ECU drives the motor
up/down, stops at the end positions, and reverses the window if a pinch is
detected while closing.

## Project structure
| Folder     | Test level                                              | Status      |
| ---------- | ------------------------------------------------------- | ----------- |
| `docs/`    | Requirements, test specification, traceability          | Done        |
| `01_MIL/`  | Model-in-the-Loop (Simulink/Stateflow)                  | In progress |
| `02_SIL/`  | Software-in-the-Loop (C code + pytest/Unity)            | Planned     |
| `03_CAN/`  | DBC file, ECU simulation (SocketCAN, python-can), UDS   | Planned     |
| `04_PIL/`  | Processor-in-the-Loop (STM32)                           | Planned     |
| `05_HIL/`  | Mini-HIL with real-time plant model and fault injection | Planned     |
| `reports/` | Test reports                                            | Planned     |

## Tools
MATLAB/Simulink/Stateflow · C · Python · pytest · Unity · gcov · cppcheck (MISRA) ·
SocketCAN · python-can · cantools · udsoncan · STM32 · GitHub Actions

## Documents
- [Requirements](docs/requirements.md)
- [Test specification](docs/test_specification.md)
- [Traceability matrix](docs/traceability.md)

## Progress log
- [x] Feature defined, 12 requirements written
- [x] Test specification complete
- [x] MIL model + test harness
- [ ] SIL C implementation + back-to-back tests
- [ ] CAN network + UDS diagnostics
- [ ] PIL on STM32
- [ ] Mini-HIL with fault injection
=======
# power-window-ecu-testing
>>>>>>> 4fcd30d3200a94a28ba73058049c07065730fd35
