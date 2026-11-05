# Test Specification – Power Window ECU

Techniques used: requirements-based testing, boundary value analysis, equivalence classes.

| TC ID | Req | Precondition | Action | Expected result |
|---|---|---|---|---|
| TC_01 | REQ_01 | Pos = 50 %, 12 V | Press Up | Motor Up within 50 ms |
| TC_02 | REQ_04 | Moving up | Pos reaches 100 % | Motor Stop |
| TC_03 | REQ_05 | Closing, pos 50 % | Current = 7.9 A | No pinch detected |
| TC_04 | REQ_05, REQ_06 | Closing, pos 50 % | Current = 8.1 A | Pinch detected, reverse ≥ 20 % within 200 ms |
| TC_05 | REQ_07 | Closing, pos 97 % | Current = 9 A | No reversal |
| TC_06 | REQ_08 | Battery 8.9 V | Press Up | Motor stays off |
| TC_07 | REQ_08 | Battery 9.0 V | Press Up | Motor Up |
| TC_08 | REQ_09 | Moving | Switch message missing 600 ms | Motor Stop, DTC_SWITCH_TIMEOUT stored |
| TC_09 | REQ_11 | Idle | Up and Down together | Motor Stop |
| TC_10 | REQ_02 | Pos = 50 %, 12 V  | Press Down | Motor Down within 50 ms |
| TC_11 | REQ_02, REQ_04 | Pos = 0% | Press Down | Motor stays off |
| TC_12 | REQ_02 | Pos = 1 % | Press Down | Motor Down |
| TC_13 | REQ_03 | Moving up, Pos = 50 % | Release switch | Motor Stop within 50ms |
| TC_14	| REQ_03 | Moving down, pos = 50 % | Release switch |	Motor Stop within 50 ms |
| TC_15 | REQ_10 | Motor blocked (position not changing) |	Hold Up for 7.9 s |	Motor still running, no DTC |
| TC_16	| REQ_10 |	Motor blocked | Hold Up for 8.1 s |	Motor Stop, DTC_MOTOR_OVERRUN stored |
| TC_17 | REQ_12 | CAN level (virtual bus), ECU running | Record DCU_WindowStatus (0x210) for 10 s | Cycle time 100 ms ±10 ms for every frame |
| TC_18 | REQ_12 | CAN level, window moving up from 30 % | Read DCU_WindowStatus at 1.4 s | WindowPos = real position (±0.5 %, about 40 %), MotorState Up, PinchFlag 0, CtrlState MOVING_UP, no DTC |
| TC_19 | REQ_12, REQ_14 | Pinch detected (as in TC_04) | Read status message |	Pinch flag = 1 |
| TC_20 | REQ_09 | Pinch reversal active (current = 8.1 A, pos = 50 %) | Switch message missing for 600 ms | Motor Stop, DTC_SwitchTimeout stored |
| TC_21 | REQ_13, REQ_14 | Obstacle at = 70 %, pos = 50 % | Hold Up for the whole test | Pinch reversal to ~50 %, then motor stays 0 while Up is held; PinchFlag stays 1 |
| TC_22 | REQ_09 | ERROR after switch message lost (as TC_08), Up still held | Message returns at 5 s, Up released at 6 s | 5–6 s: motor stays 0 (no restart); after 6 s: state IDLE, no movement |
| TC_23 | REQ_08 | Moving up, pos 50 % | Vbat drops 12 V -> 8.5 V at 2 s | Motor stops within 50 ms, state IDLE | 
| TC_24 | REQ_11 | Moving up, pos 50 % | Down also pressed at 2 s | Motor stops within 50 ms, state IDLE | 
| TC_25 | REQ_09 | Moving down, pos 50 % | Switch message lost at 1.5 s (age 600 ms) | Motor stops, state ERROR, DTC_SwitchTimeout stored | 
| TC_26 | REQ_10 | Moving down; fault injection: position sensor stuck from 1.5 s | Hold Down | Still running at 8.9 s (7.9 s); stopped + DTC_MotorOverrun at 9.1 s (8.1 s) | 
| TC_27 | REQ_08 | Moving down, pos 50 % | Vbat rises 12 V -> 16.5 V at 2 s | Motor stops within 50 ms, state IDLE | 
| TC_28 | REQ_11 | Moving down, pos 50 % | Up also pressed at 2 s | Motor stops within 50 ms, state IDLE | 
| TC_29 | REQ_10 | Pinch reversal active; fault injection: position sensor stuck from 1.9 s | Hold Up | Still reversing 7.9 s after reversal start; stopped + DTC_MotorOverrun at 8.1 s | 
| TC_30 | REQ_08, REQ_14 | Pinch reversal active | Vbat drops to 8.5 V at 2.0 s | Motor stops within 50 ms, state IDLE, PinchFlag cleared | 
| TC_31 | REQ_13, REQ_14 | Pinch, Up held until 4 s | Release Up at 4 s, press again at 5 s | PinchFlag 1 at 3.9 s, 0 at 4.1 s, state IDLE; motor up again within 50 ms of new press | 
| TC_32 | REQ_09 | Idle, switch message missing from start | Press Up (and separately Down) | Motor never starts | 
| TC_33 | REQ_08 | Idle, Vbat 16.5 V from start | Press Up (and separately Down) | Motor never starts | 
| TC_34 | REQ_05 | Window at 2 %, obstacle at 3 % | Hold Up | Blocked at 3 % (below pinch zone): no pinch, no reversal | 
| TC_35 | REQ_06 | Window at 5 %, obstacle at 10 % | Hold Up | Pinch at 10 %, reversal ends at 0 % (less than 20 % available), motor stops | 
| TC_36 | REQ_03 | Moving down | At 2 s: Down released and Up pressed in the same cycle | Motor stops first (no direct reversal of direction) |
| TC_37 | REQ_09 | CAN level, window moving up | BCM pauses: switch frames 500 ms apart (max message age 490 ms) | No timeout, no DTC | 
| TC_38 | REQ_09 | CAN level, window moving up | BCM pauses: switch frames 560 ms apart (age reaches 510 ms) | Timeout, motor stops, DTC_SwitchTimeout set |
| TC_39 | REQ_15 | CAN level, ECU idle | Tester: 22 F1 95 | 62 F1 95 "PW-1.0.0"; transferred as ISO-TP SF request, FF, FC, CF | 
| TC_40 | REQ_15 | Window moving up from 30 % | Tester at 1.4 s: 22 01 00 | 62 01 00 + current position (about 40 %) | 
| TC_41 | REQ_15 | ECU idle | Tester: 22 F1 FF (unknown DID) | 7F 22 31 (request out of range) | 
| TC_42 | REQ_15 | No fault occurred | Tester: 19 02 FF | 59 02 09, no DTC records | 
| TC_43 | REQ_09, REQ_15 | Switch message lost 2–3 s while moving | Tester at 4 s: 19 02 FF | DTC U0140-00 with status 08 (confirmed) | 
| TC_44 | REQ_10, REQ_15 | Blocked motor (overrun) | Tester at 10 s: 19 02 FF | DTC B1310-00 with status 08 | 
| TC_45 | REQ_16 | DTC U0140-00 stored | Tester: 19 02 FF, 14 FF FF FF, 19 02 FF | DTC present, then 54, then no DTC; status message DTC bit 0 | 
| TC_46 | REQ_15 | ECU idle | 10 03 / 3E 00 | 50 03 00 32 01 F4 / 7E 00 | 
| TC_47 | REQ_15 | ECU idle | 31 01 02 03 / 22 F1 / 10 02 | 7F 31 11 / 7F 22 13 / 7F 10 12 | 
| TC_48 | REQ_15 | ECU idle | Three requests (22, 19, 3E) | Each response starts within 50 ms |


## Coverage justifications
| Code | Reason not covered |
|---|---|
| `default:` in `enter_state()` and `WindowCtrl_Step()` | Defensive code for an invalid state value; unreachable in normal operation. |

Coverage results (SIL, gcov)

After TC_23–TC_36: 96 % line coverage, 97 % branch coverage. Before: 81 % lines.

Not covered:
default: in enter_state() and WindowCtrl_Step()	
Reason: Defensive code for an invalid state value (e.g. memory corruption). Unreachable in normal operation.
Not covered: s_ticks saturation (s_ticks < UINT16_MAX false branch)	
Reason: Only reached after > 655 s in one state (e.g. long IDLE). Protects against counter overflow. Candidate for a long-duration test later.

Note: TC_26 and TC_29 use sensor fault injection that exists only in the SIL plant (pos_stuck_from). They are SIL-only until the MIL plant gets the same fault input.



## Static analysis
- cppcheck (`--enable=all`): no findings except `unusedFunction` for WindowCtrl_Init/Step (called from the test harness; expected).
- cppcheck MISRA C:2012 addon (`--enable=style`): 2 findings, both Rule 8.7 (advisory) -> deviation below. Addon verified with a self-test file containing known violations (Rules 7.1, 8.4, 14.4, 15.1, 15.6).
- Note: cppcheck covers a subset of MISRA rules; a full compliance claim would need a commercial tool (e.g. Polyspace, QA-C) would be needed for a full compliance claim.

### MISRA deviations
| ID | Rule | Location | Justification |
|---|---|---|---|
| DEV_01 | 8.7 (advisory) | `WindowCtrl_Init`, `WindowCtrl_Step` | Public module interface declared in `window_ctrl.h`, called from other translation units (test harness, later the main loop). Making them `static` would break the module. Suppressed in `02_SIL/misra_suppressions.txt`. |

Test levels per test case
| Level	| Where |	Test cases | 
|---|---|---|
| MIL |	01_MIL/tests/run_mil_tests.m |	TC_01–TC_16, TC_19–TC_22 |
| SIL	| 02_SIL/tests/test_window_ctrl.py	| TC_01–TC_16, TC_19–TC_36 |
| Back-to-back	| 02_SIL/tests/test_back_to_back.py	| all MIL test cases |
| CAN (virtual bus)	| 03_CAN/tests/test_can.py | TC_08, TC_17, TC_18, TC_19, TC_37, TC_38 + DBC conformance + AliveCounter |
| UDS (virtual bus) | 03_CAN/tests/test_uds.py | TC_39–TC_48 |

Timing note (REQ_09): the timeout is detected 510 ms after the last message (first 10 ms check with age > 500 ms). Recommended requirement update: "detected within 500–520 ms".
