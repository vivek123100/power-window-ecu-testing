# CV Notes

Ready-to-use CV text, updated after each milestone. Copy the latest version into your CV.

_Last updated: 4 Nov 2026 (MIL complete)_

## Project entry (current version)

**Power Window ECU – End-to-End Verification (MIL / SIL / PIL / HIL)** · personal project · [GitHub link]

- Derived 14 testable requirements for a power window ECU with anti-pinch protection and maintained full requirements-to-test traceability.
- Built a Simulink/Stateflow controller model with a closed-loop plant model (window position, motor current, obstacle, end stops).
- Developed an automated, requirements-based MIL test harness in MATLAB: 21 test cases including boundary values and fault injection (CAN timeout, motor overrun, under-voltage, pinch), with auto-generated test reports. Result: 19/19 executed tests pass.
- Found and fixed 3 design defects through testing (missing fault handling during pinch reversal, repeated pinching while the switch is held, status flag cleared too early) and 1 untestable requirement in review.

_Planned bullets (add when done):_
- SIL: controller implemented in C; same test cases reused via pytest; back-to-back comparison with MIL; X % branch coverage (gcov); MISRA checks (cppcheck); CI on GitHub Actions.
- CAN/UDS: DBC-based network, simulated ECUs with python-can, UDS services 0x22/0x19.
- PIL: code verified on STM32, execution time measured.
- HIL: real-time plant ↔ MCU over CAN, automated fault-injection tests.

## Skills line (current version)

**Testing:** V-model, MIL, requirements-based testing, test specification, traceability, boundary value analysis, fault injection, regression testing
**Tools:** MATLAB, Simulink, Stateflow, Git, GitHub, VS Code
**Domain:** body electronics (power window, anti-pinch), basic functional safety awareness

_To add as the project goes on:_ C, Python, pytest, gcov, cppcheck/MISRA, GitHub Actions, CAN, DBC, UDS, STM32, SIL, PIL, HIL

## Certificates
- MATLAB Onramp (MathWorks)
- Simulink Onramp (MathWorks)
- _Optional to add:_ Stateflow Onramp (free)

## Interview stories (STAR: situation, task, action, result)

1. **Repeated pinch bug.** Situation: automated test of the anti-pinch function. Action: noticed the window re-closed on the obstacle every ~1.6 s while the switch was held; added a WAIT_RELEASE state, a new requirement (REQ_13) and a regression test (TC_21). Result: safety issue fixed and covered by a test.
2. **Gap found with the requirement × state matrix.** The pinch-reversal state ignored CAN timeout and overrun faults. Added the missing transitions and test case TC_20.
3. **Untestable requirement.** REQ_06 demanded 20 % reversal within 200 ms, physically impossible at 25 %/s motor speed. Rewrote it as "start reversing within 200 ms and reverse ≥ 20 %".
4. **Test setup vs. product bug.** A failing test was caused by a hard-coded Constant block in the model, not by the controller. Lesson: always check the test setup first; keep inputs as variables so one model serves all test cases.
