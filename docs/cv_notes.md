# CV Notes

Ready-to-use CV text, updated after each milestone. Copy the latest version into your CV.

_Last updated: 16 Nov 2026 (MIL, SIL, CAN/UDS, CR_01, CR_04 E2E, PIL on Renode)_

> **Rule for every milestone (Claude keeps this up to date):** add each task as a bullet in the
> bullet bank below: **what I did → problem I hit → how I solved it → measurable result**, plus new
> ATS keywords. Only things really done in this project, nothing invented. The final CV is written
> only when I ask for it.

## 10-second summary (top of CV / profile)

Automotive engineer focused on **ECU software testing**. Built a complete verification project for a power
window ECU along the **V-model: MIL → SIL → PIL → HIL**, with **CAN, UDS diagnostics, E2E protection**, back-to-back
testing, **96 % code coverage, MISRA C:2012** and **CI (GitHub Actions)**: 115 automated tests (incl. 12 real-time
HIL tests on embedded firmware), 11 defects found and fixed, 2 change requests handled end to end.

## Bullet bank: problem → action → result (pick the best 5–7 for the CV)

**Requirements and design**
- Wrote 18 testable requirements and 68 test cases with full traceability; found an untestable requirement in review (20 % reversal in 200 ms was physically impossible) and rewrote it.
- Found missing fault handling in the pinch-reversal state with a requirement × state matrix; added transitions and a regression test.

**MIL (MATLAB/Simulink/Stateflow)**
- Built a Stateflow controller with a closed-loop plant model and an automated MIL harness (23 test cases, auto-generated report); testing exposed a safety defect: the window re-closed on a trapped hand → new state WAIT_RELEASE, 23/23 pass.

**SIL (C99, Python/pytest)**
- Implemented the controller in C99 and reused the MIL test cases in pytest (ctypes); a regression test caught a recovery bug that code review missed (one missing `!`: the window would restart by itself after a fault).
- Back-to-back MIL vs. SIL every 10 ms on all signals: 100 % identical; found a power-on initialisation defect that all functional tests missed.
- Raised code coverage from 81 % to 96 % lines / 97 % branches (gcov) with 14 targeted tests incl. sensor fault injection.
- Found that the MISRA C:2012 check silently reported 0 findings (misconfigured tool); proved it with a known-bad file and fixed the configuration (tool qualification mindset).
- Set up CI with quality gates (MISRA, 103 tests, back-to-back, coverage ≥ 90 %) on every push in GitHub Actions.

**CAN, UDS, E2E**
- Designed a DBC and a virtual CAN network (BCM, ECU, tester, logger); automated tests for cycle time, signal content and timeout boundaries (500 vs. 560 ms, detection 510 ms).
- Implemented UDS (ISO 14229) over ISO-TP: 0x10, 0x22, 0x19, 0x14, 0x3E, negative responses, P2 timing; DTCs U0140-00, B1310-00, U0422-00.
- Live testing on Linux SocketCAN (candump, cansend) revealed that a dead BCM went undetected while the window was idle → change request CR_01 with impact analysis, tests written first, model and code updated.
- Scenario review: a frozen sender (frames on time, stale content) kept the window moving → CR_04: E2E AliveCounter check, new DTC, 15 tests; developed on a feature branch and merged via pull request with green CI.
- Found a robustness bug during live testing: two ECUs on one bus crashed the ISO-TP receiver → receiver now drops bad frames, regression test added.

**PIL (STM32, ARM)**
- Cross-compiled the unchanged controller for an STM32F407 (Cortex-M4F, bare metal, own startup code and linker script, 2.4 KB flash) and ran all 103 SIL/CAN tests on the target in the Renode emulator: MIL vs. PIL 100 % identical; worst-case step time < 1 µs of the 10 ms budget.
- Cut PIL runtime 12× (110 → 8 ms per step) by replacing UART busy-polling with a receive interrupt and WFI sleep; fixed the race condition before WFI.

**Verification & validation**
- Ran an independent V&V review of the whole project: re-ran every level from a fresh clone, audited traceability by script and used **mutation testing** (21 planted bugs): 16 caught at first; the 5 survivors exposed real gaps (untested exact boundaries, a pinch-zone limit that could shift unnoticed, "clear all DTCs" only tested for one DTC). Closed them with 7 new tests; branch coverage 94.8 → 96.7 %.
- Found dead code left by an earlier change request (always-true condition, MISRA C:2012 Rule 14.3) that the MISRA tool did not report; and validated the requirements against FMVSS 118: documented that a current threshold is not yet a proven force limit (< 100 N) and that the reversal distance must be specified in mm.

**HIL (real-time, CAN)**
- Built a mini-HIL bench: the ECU firmware (own bxCAN driver, 1 ms scheduler, UDS + ISO-TP in C, 3.9 KB) runs as a real-time node on SocketCAN; the PC runs plant, BCM and diagnostic tester in a 10 ms loop. 12 automated tests measured on the bus: reaction ≤ 50 ms, timeout detection 500–520 ms, status cycle 100 ± 10 ms, pinch, frozen sender, UDS read/clear incl. multi-frame – 12 / 12 pass.
- Found that the emulator stalled up to 183 ms on a loaded PC, which made timing tests fail randomly; added a test-system health check that repeats or reports a run as inconclusive instead of blaming the ECU.

## ATS keywords (use the ones that match the job ad)

**English:** ECU testing, verification and validation (V&V), mutation testing, PIL testing, cross-compilation, bare-metal firmware, linker script, interrupts, software testing, test automation, V-model, MIL, SIL, PIL, HIL, real-time testing, CAN driver, embedded UDS,
requirements-based testing, test specification, traceability, back-to-back testing, regression testing,
fault injection, boundary value analysis, code coverage, static analysis, MISRA C, CI/CD, GitHub Actions,
MATLAB, Simulink, Stateflow, C, Python, pytest, embedded C, STM32, ARM Cortex-M, Renode, CAN, DBC,
SocketCAN, UDS, ISO 14229, ISO-TP, ISO 15765, DTC, diagnostics, E2E protection, AUTOSAR concepts,
ISO 26262 awareness, change management, Git, Linux

**German (often in ads):** Steuergeräte-Test, Softwaretest, Testautomatisierung, Testspezifikation,
Anforderungsanalyse, Rückverfolgbarkeit, Fehlerinjektion, Regressionstest, Diagnose (UDS), Fehlerspeicher,
Embedded-Software, Restbussimulation (concept), funktionale Sicherheit (ISO 26262, Grundlagen)

**Not used in this project (don't claim):** CANoe/CANalyzer, dSPACE, Vector tools, AUTOSAR stack, real HIL bench.
Say instead: "open-source equivalents: python-can, SocketCAN, can-utils, Renode".


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


## Skills line (current version)

**Testing:** V-model, MIL, requirements-based testing, test specification, traceability, boundary value analysis, fault injection, regression testing
**Tools:** MATLAB, Simulink, Stateflow, C (C99), Python, pytest, gcc, gcov/gcovr, cppcheck, GitHub Actions, Linux (WSL), Git, GitHub, VS Code
**Networks & diagnostics:** CAN, DBC, E2E protection (AliveCounter), SocketCAN, can-utils (candump/cansend/cangen), python-can, cantools, ISO-TP, UDS (0x10, 0x22, 0x19, 0x14, 0x3E), DTCs
**Domain:** body electronics (power window, anti-pinch), basic functional safety awareness

**Testing levels:** MIL, SIL, PIL, HIL (emulated target), back-to-back (model vs. code / target)
**Quality:** code coverage (gcov), static analysis (cppcheck, MISRA C:2012), CI/CD (GitHub Actions)

_Embedded:_ STM32 (Cortex-M4F), bare-metal C, bxCAN, Renode, arm-none-eabi-gcc

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
10. **Frozen sender (E2E).** Scenario review: what if the BCM's software hangs but its CAN controller keeps repeating the last frame? The frames arrive on time, so the timeout check never fires, and a stale "Up pressed" would keep the window moving. Raised CR_04 on a feature branch: a separate E2E module checks the AliveCounter, discards stale frames and stores U0422-00 after 3 in a row. I put it in the communication layer, so the window state machine and the Simulink model did not change. 15 new tests (unit + CAN level, boundaries 2 vs. 3 frames), shown live by freezing a BCM on vcan0. Merged through a pull request with green CI.
11. **Robustness bug found by accident.** During the live demo an old ECU process was still running, so two ECUs answered on the same diagnostic ID. My ISO-TP receiver saw a duplicate consecutive frame and crashed the whole ECU. A real receiver must drop the message and wait, not die. Fixed it, added regression test TC_68, and wrote the "two ECUs on one ID" pattern into my field guide. Lesson: test with unexpected input, not only the happy path; and check the bench (who else is on the bus?) before blaming the ECU.
4. **Test setup vs. product bug.** A failing test was caused by a hard-coded Constant block in the model, not by the controller. Lesson: always check the test setup first; keep inputs as variables so one model serves all test cases.
