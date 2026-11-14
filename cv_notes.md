# CV Notes

Ready-to-use CV text, updated after each milestone. Copy the latest version into your CV.

_Last updated: 14 Nov 2026 (MIL, SIL, CAN/UDS, CR_01)_

## Project entry (current version)

**Power Window ECU – End-to-End Verification (MIL / SIL / PIL / HIL)** · personal project · [GitHub link]

- Derived 14 testable requirements for a power window ECU with anti-pinch protection and maintained full requirements-to-test traceability.
- Built a Simulink/Stateflow controller model with a closed-loop plant model (window position, motor current, obstacle, end stops).
- Developed an automated, requirements-based MIL test harness in MATLAB: 21 test cases including boundary values and fault injection (CAN timeout, motor overrun, under-voltage, pinch), with auto-generated test reports. Result: 19/19 executed tests pass.
- Found and fixed 3 design defects through testing (missing fault handling during pinch reversal, repeated pinching while the switch is held, status flag cleared too early) and 1 untestable requirement in review.

- Implemented the controller in C99 (state machine with priority-ordered transitions, tick-based timers, named calibration constants) and verified it in a Python/pytest SIL environment (closed-loop plant model, C library via ctypes) with the same 22 test cases as MIL: 20/20 executed tests pass.

- Set up automated back-to-back testing (MIL reference data exported from MATLAB vs. SIL, every 10 ms, all signals): 100 % identical across 20 scenarios; uncovered a one-sample power-on initialisation defect missed by all functional tests.

- Raised code coverage from 81 % to 96 % lines / 97 % branches (gcov) by analysing uncovered code and adding 14 targeted test cases, including sensor fault injection (stuck position sensor); remaining gaps justified as defensive code.

- Ran static analysis with cppcheck incl. the MISRA C:2012 addon (verified with a known-bad self-test); handled findings through a documented deviation process.
- Built a GitHub Actions CI pipeline with quality gates on every push: MISRA check, 36 SIL tests, 20 back-to-back comparisons and a ≥ 90 % coverage gate, with downloadable reports.

- Designed a DBC for the window ECU and built a virtual CAN network (python-can, cantools) with BCM, the ECU under test, a diagnostic tester and a bus logger; automated CAN tests for cycle time, signal content, DBC conformance and message-timeout boundaries.
- Ran the ECU in real time on Linux SocketCAN (vcan0) and tested it manually with can-utils: live traces (candump), frame injection (cansend/cangen), message-loss fault injection, UDS requests and ISO-TP flow control by hand.
- Implemented UDS diagnostics (ISO 14229) over ISO-TP (ISO 15765-2): sessions, ReadDataByIdentifier, ReadDTCInformation, ClearDiagnosticInformation, TesterPresent and negative responses; 13 automated diagnostic tests incl. P2 response time.

- Handled a requirement change request (CR_01) through the full V-model: impact analysis (2 states, ~10 files, affected tests), REQ update incl. start-up rule, Stateflow and C changes, 6 new tests written first; 87 automated tests green, coverage 96 %.

_Planned bullets (add when done):_
- PIL: code verified on STM32, execution time measured.
- HIL: real-time plant ↔ MCU over CAN, automated fault-injection tests.

## Skills line (current version)

**Testing:** V-model, MIL, requirements-based testing, test specification, traceability, boundary value analysis, fault injection, regression testing
**Tools:** MATLAB, Simulink, Stateflow, C (C99), Python, pytest, gcc, gcov/gcovr, cppcheck, GitHub Actions, Linux (WSL), Git, GitHub, VS Code
**Networks & diagnostics:** CAN, DBC, SocketCAN, can-utils (candump/cansend/cangen), python-can, cantools, ISO-TP, UDS (0x10, 0x22, 0x19, 0x14, 0x3E), DTCs
**Domain:** body electronics (power window, anti-pinch), basic functional safety awareness

**Testing levels:** MIL, SIL, back-to-back (model vs. code)
**Quality:** code coverage (gcov), static analysis (cppcheck, MISRA C:2012), CI/CD (GitHub Actions)

_To add as the project goes on:_ STM32, PIL, HIL

## Certificates
- MATLAB Onramp (MathWorks)
- Simulink Onramp (MathWorks)
- _Optional to add:_ Stateflow Onramp (free)

## Interview stories (STAR: situation, task, action, result)

1. **Repeated pinch bug.** Situation: automated test of the anti-pinch function. Action: noticed the window re-closed on the obstacle every ~1.6 s while the switch was held; added a WAIT_RELEASE state, a new requirement (REQ_13) and a regression test (TC_21). Result: safety issue fixed and covered by a test.
2. **Gap found with the requirement × state matrix.** The pinch-reversal state ignored CAN timeout and overrun faults. Added the missing transitions and test case TC_20.
3. **Untestable requirement.** REQ_06 demanded 20 % reversal within 200 ms, physically impossible at 25 %/s motor speed. Rewrote it as "start reversing within 200 ms and reverse ≥ 20 %".
5. **Regression tests catch what reviews miss.** In code review I found that the ERROR recovery checked "Up pressed" instead of "Up released" (one missing `!`): the window would restart on its own after a fault. The comment was updated but the condition was not. The automated SIL tests (TC_16, TC_22) failed and pointed to it. Lesson: when code and comment disagree, trust the code, and never rely on review alone.
6. **Back-to-back finds what functional tests miss.** Comparing every sample of MIL vs. SIL failed only for the 3 tests where the window did not start at 50 %, and only at t = 0. Cause: the model's feedback Unit Delay was still initialised to 50 % instead of the start position, so for the first 10 ms the controller saw the wrong window position (it could have driven a fully open window into the end stop at power-on). Fixed the initial condition and the logging point; result 100 % identical.
7. **Test the test tool.** The MISRA check reported 0 findings on my code. Instead of trusting it, I ran it on a file with known violations: still 0. The addon's findings were hidden by default (severity "style" not enabled). After fixing the configuration it found 5 violations in the test file and 2 in my code (Rule 8.7, handled as a documented deviation). In ISO 26262 terms: tool confidence matters, a silent tool is not proof.
8. **A requirement gap found while building a demo.** For the UDS demo I needed a stored "lost communication" DTC, but none appeared: the timeout is only checked while the window moves. Real ECUs usually store U0140 in any state. I documented it as an open requirement question for REQ_09 instead of quietly changing the code.
9. **A change request done properly.** Live testing showed a dead BCM went unnoticed while the window was idle. I raised CR_01, did the impact analysis (IDLE and WAIT_RELEASE affected, ~10 files, TC_32 behaviour changes), chose a start-up rule (age counts from power-on, so a BCM that never starts is also detected), wrote the tests first (6 red), changed model and code, and back-to-back confirmed both match. Lesson: committing from MATLAB and the PC separately broke main for a while; a feature branch with a pull request avoids that.
4. **Test setup vs. product bug.** A failing test was caused by a hard-coded Constant block in the model, not by the controller. Lesson: always check the test setup first; keep inputs as variables so one model serves all test cases.
