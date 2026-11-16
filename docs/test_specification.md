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
| TC_14 | REQ_03 | Moving down, pos = 50 % | Release switch | Motor Stop within 50 ms |
| TC_15 | REQ_10 | Motor blocked (position not changing) | Hold Up for 7.9 s | Motor still running, no DTC |
| TC_16 | REQ_10 | Motor blocked | Hold Up for 8.1 s | Motor Stop, DTC_MOTOR_OVERRUN stored |
| TC_17 | REQ_12 | CAN level (virtual bus), ECU running | Record DCU_WindowStatus (0x210) for 10 s | Cycle time 100 ms ±10 ms for every frame |
| TC_18 | REQ_12 | CAN level, window moving up from 30 % | Read DCU_WindowStatus at 1.4 s | WindowPos = real position (±0.5 %, about 40 %), MotorState Up, PinchFlag 0, CtrlState MOVING_UP, no DTC |
| TC_19 | REQ_12, REQ_14 | Pinch detected (as in TC_04) | Read status message | Pinch flag = 1 |
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
| TC_33 | REQ_08 | Idle, Vbat 16.5 V from start | Press Up (and separately Down) | “Motor never starts; ERROR, DTC_SwitchTimeout stored (CR_01)” | 
| TC_32b | REQ_09 | Idle, switch message missing from start | Press Down | Motor never starts (Down variant of TC_32) |
| TC_33b | REQ_08 | Idle, Vbat 16.5 V from start | Press Down | Motor never starts (Down variant of TC_33) |
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
| TC_49 | REQ_09 | Window idle at 50 %, no switch pressed | Switch message age > 500 ms from 2 s | ERROR as soon as the age exceeds 500 ms, DTC_SwitchTimeout stored, motor stays off |
| TC_50 | REQ_09 | Pinch, Up still held (WAIT_RELEASE) | Switch message lost from 4 s | ERROR, DTC_SwitchTimeout stored, motor stays off |
| TC_51 | REQ_09 | Idle timeout from 2 s to 3 s, switches released | Message back at 3 s, Up pressed at 5 s | IDLE again, window moves at 5 s, DTC still stored |
| TC_52 | REQ_09 | CAN level, BCM never sends after power-on | – | DTC_SwitchTimeout stored about 510 ms after power-on |
| TC_53 | REQ_09 | CAN level, window idle | BCM pauses: frames 500 ms apart / 560 ms apart | 500 ms: no timeout · 560 ms: ERROR, DTC_SwitchTimeout (same boundary as TC_37/38, in IDLE) |
| TC_54 | REQ_17 | E2E unit, after E2E_Init | First frame, counter 5 | Accepted (INITIAL) |
| TC_55 | REQ_17 | E2E unit | Counters 0, 1, 2, 3 | All accepted (OK) |
| TC_56 | REQ_17 | E2E unit, counter 4 accepted | Counter 4 again | Discarded (REPEATED) |
| TC_57 | REQ_17 | E2E unit, counter 15 accepted | Counter 0 | Accepted: the wrap 15 → 0 is a change |
| TC_58 | REQ_18 | E2E unit | Same counter: 2 repeats, then a 3rd | After 2: no DTC · after the 3rd: DTC (boundary) |
| TC_59 | REQ_18 | E2E unit | 2 repeats, 1 fresh frame, 2 repeats | No DTC: repeats must be in a row |
| TC_60 | REQ_18, REQ_16 | E2E unit, DTC stored | Fresh frames, then E2E_ClearDtc | DTC stays with fresh frames; cleared only by the clear |
| TC_60b | REQ_18 | E2E unit | 300 identical frames | Still REPEATED, no counter overflow (robustness) |
| TC_61 | REQ_17, REQ_18, REQ_09 | CAN level, closing from 10 % | BCM frozen from 2 s (keeps sending, same frame) | U0422-00 at about 2.04 s (3rd stale frame); ERROR 500–520 ms after the last fresh frame |
| TC_62 | REQ_17 | As TC_61 | Frozen frames say "Up pressed" | Motor off from 2.55 s: stale frames do not keep the window moving |
| TC_63 | REQ_18 | CAN level, closing | BCM frozen for 2 frames only (2.00–2.04 s) | 2 frames discarded, no DTC, window keeps moving (boundary) |
| TC_64 | REQ_18 | As TC_61 | Read DCU_WindowStatus | DTC_SwitchInvalid (byte 1 bit 5) = 0 before, 1 after the freeze |
| TC_65 | REQ_18, REQ_15 | As TC_61 | Tester at 3 s: 19 02 FF | U0140-00 and U0422-00, 11 bytes → multi-frame (FF + FC + CF) |
| TC_66 | REQ_16, REQ_18 | Freeze 2.0–2.6 s, Up released at 2.8 s | Tester: 14 FF FF FF at 3 s, 19 02 FF at 3.5 s | 54, then no DTC; status bit 5 = 0 |
| TC_67 | REQ_17, REQ_09 | Freeze 2.0–2.6 s, Up held until 2.8 s | Fresh frames back at 2.6 s | ERROR at 2.7 s (Up still held), IDLE at 3.0 s; U0422-00 stays stored |
| TC_68 | REQ_15 | ISO-TP receiver | Same Consecutive Frame twice; unsolicited frames on 0x7E8 | Duplicate CF dropped (no crash), next message works; tester ignores frames it did not ask for |
| TC_69 | REQ_01 | HIL: ECU at 50 %, 12 V | Up pressed at 1.0 s | Motor Up frame (0x301) ≤ 50 ms after the switch frame, measured on the bus |
| TC_70 | REQ_03 | HIL: moving up | Up released at 1.5 s | Motor Stop ≤ 50 ms after the release frame; IDLE |
| TC_71 | REQ_05, REQ_06, REQ_13, REQ_14 | HIL: hand at 70 %, Up held 1.0–4.0 s | – | PinchFlag in 0x210, reversal to ≤ 50.5 %, WAIT_RELEASE, no movement while held; IDLE and PinchFlag 0 after release |
| TC_72 | REQ_09 | HIL: closing from 10 % | BCM silent from 2.0 s | ERROR 500–520 ms after the last switch frame; DTC_SwitchTimeout in 0x210 |
| TC_73 | REQ_17, REQ_18 | HIL: closing from 10 % | BCM frozen from 2.0 s (Up repeated, same counter) | DTC_SwitchInvalid before 2.2 s; motor stops before 2.6 s |
| TC_74 | REQ_08 | HIL: closing | Battery 8.5 V at 1.5 s (0x300) | Motor Stop ≤ 50 ms |
| TC_75 | REQ_12 | HIL: ECU running | Record 0x210 for 5 s | Every gap 100 ± 10 ms, ≥ 48 frames |
| TC_76 | REQ_11 | HIL: closing | Down also pressed at 1.5 s | Motor Stop ≤ 50 ms |
| TC_77 | Timing | HIL: moving + pinch | – | WindowCtrl_Step < 10 % of the 10 ms task (SysTick ticks in 0x301) |
| TC_78 | REQ_15, REQ_16 | HIL: BCM silent 1.0–1.7 s | 19 02 FF at 2.5 s, 14 FF FF FF at 3.0 s, 19 02 FF at 3.5 s | U0140-00, then 54, then no DTC (UDS in the firmware) |
| TC_79 | REQ_15, REQ_18 | HIL: frozen 1.0–1.7 s while closing | 19 02 FF at 2.5 s | U0140-00 + U0422-00 = 11 bytes as First Frame + Flow Control + Consecutive Frame |
| TC_80 | REQ_15 | HIL: ECU idle | 22 F1 95, 22 F1 FF, 31 01 02 03, 3E 00, 10 03 | "PW-1.0.0" (multi-frame), 7F 22 31, 7F 31 11, 7E 00, 50 03 00 32 01 F4; each first response ≤ 50 ms (P2) |
| TC_81 | REQ_07 | Window at 95 %, obstacle at 97 %, stall 9 A | Hold Up | Blocked at 97 %: no pinch, no reversal (V&V F-02: real upper-boundary test) |
| TC_82 | REQ_05 | Window at 90 %, obstacle at 95 %, stall 9 A | Hold Up | Pinch and reversal (just inside the zone) |
| TC_83 | REQ_16 | Blocked motor → B1310-00 stored | 19 02 FF at 10 s, 14 FF FF FF at 10.5 s, 19 02 FF at 11 s | B1310-00, then 54, then no DTC; status DTC_MotorOverrun 0 (V&V F-03) |
| TC_84 | REQ_05 | Closing, pos 50 % | Current exactly 8.0 A | No pinch ("more than 8 A"; V&V F-07) |
| TC_85 | REQ_08 | Battery exactly 16.0 V | Press Up | Motor Up within 50 ms (only above 16 V forbidden; V&V F-07) |
| TC_86 | REQ_17 | E2E unit | Counters 3, 11, 11 | INITIAL, OK (jump = lost frames, accepted), REPEATED (V&V F-08) |
| TC_87 | – (HIL robustness) | HIL: closing from 10 % | Sensor frames 0x300 stop at 1.5 s | Motor off ≤ 150 ms, sensor-timeout flag in 0x301, no CAN RX overruns (V&V F-09) |


## Coverage justifications
| Code | Reason not covered |
|---|---|
| `default:` in `enter_state()` and `WindowCtrl_Step()` | Defensive code for an invalid state value; unreachable in normal operation. |

Coverage results (SIL, gcov)

After TC_23–TC_36: 96 % line coverage, 97 % branch coverage (gcovr). Before: 81 % lines.

Re-measured in the V&V review with gcov: CR_01 had left 2 branches that could never be taken (F-01, 94.8 % branches taken). After CR_05: **96.3 % lines, 96.7 % branches taken** (`window_ctrl.c`), 100 % / 100 % (`e2e_counter.c`).

Not covered:
default: in enter_state() and WindowCtrl_Step() 
Reason: Defensive code for an invalid state value (e.g. memory corruption). Unreachable in normal operation.
Not covered: s_ticks saturation (s_ticks < UINT16_MAX false branch) 
Reason: Only reached after > 655 s in one state (e.g. long IDLE). Protects against counter overflow. Candidate for a long-duration test later.

Note: TC_26 and TC_29 use sensor fault injection that exists only in the SIL plant (pos_stuck_from). They are SIL-only until the MIL plant gets the same fault input.



## Static analysis
- cppcheck (`--enable=all`): no findings except `unusedFunction` for WindowCtrl_Init/Step (called from the test harness; expected).
- cppcheck MISRA C:2012 addon (`--enable=style`), on `window_ctrl.c` and `e2e_counter.c`: only Rule 8.7 (advisory) findings for the public interface functions -> deviation below. Addon verified with a self-test file containing known violations (Rules 7.1, 8.4, 14.4, 15.1, 15.6).
- Note: cppcheck covers a subset of MISRA rules; a full compliance claim would need a commercial tool (e.g. Polyspace, QA-C) would be needed for a full compliance claim.

### MISRA deviations
| ID | Rule | Location | Justification |
|---|---|---|---|
| DEV_01 | 8.7 (advisory) | `WindowCtrl_Init`, `WindowCtrl_Step`; `E2E_Init`, `E2E_CheckCounter`, `E2E_DtcActive`, `E2E_ClearDtc` (CR_04) | Public module interface declared in `window_ctrl.h`, called from other translation units (test harness, later the main loop). Making them `static` would break the module. Suppressed in `02_SIL/misra_suppressions.txt`. |

Test levels per test case
| Level | Where | Test cases | 
|---|---|---|
| MIL | 01_MIL/tests/run_mil_tests.m | TC_01–TC_16, TC_19–TC_22 |
| SIL | 02_SIL/tests/test_window_ctrl.py | TC_01–TC_16, TC_19–TC_36, TC_49–TC_51, TC_81, TC_82, TC_84, TC_85 |
| SIL unit (E2E module) | 02_SIL/tests/test_e2e_counter.py | TC_54–TC_60b, TC_86 |
| Back-to-back | 02_SIL/tests/test_back_to_back.py | all MIL test cases |
| CAN (virtual bus) | 03_CAN/tests/test_can.py | TC_08, TC_17, TC_18, TC_19, TC_37, TC_38, TC_52, TC_53 + DBC conformance + AliveCounter |
| CAN E2E (virtual bus) | 03_CAN/tests/test_can_e2e.py | TC_61–TC_67 |
| UDS (virtual bus) | 03_CAN/tests/test_uds.py | TC_39–TC_48, TC_68, TC_83 |
| Live (manual) | 03_CAN/LIVE_DEMO.md | demos A–E on SocketCAN vcan0 |
| HIL (firmware as CAN node on vcan0) | 05_HIL/tests/test_hil.py (`bash 05_HIL/run_hil.sh`) | TC_69–TC_80, TC_87, real time, measured on the bus |
| PIL (STM32F407 in Renode) | `TARGET=pil` + 02_SIL/tests, 03_CAN/tests (`bash 04_PIL/run_pil.sh`) | all SIL, CAN, E2E and UDS test cases (103 tests); back-to-back MIL vs. PIL |

Timing note (REQ_09): the timeout is detected 510 ms after the last message (first 10 ms check with age > 500 ms). Recommended requirement update: "detected within 500–520 ms".

## PIL notes
- Same test cases and limits as SIL; only the controller moves to the target (cross-compiled with `arm-none-eabi-gcc -O2 -Werror`, hardware FPU).
- Execution time of `WindowCtrl_Step` measured with SysTick on every call: worst 56–57 ticks (< 1 µs at Renode's 72 MHz SysTick) of the 10 ms budget. Renode is instruction-based, not cycle-accurate: the real value must be measured on a board (DWT cycle counter).
- Result: 103 passed, 1 skipped (same as SIL); MIL vs. PIL 23/23 identical (`reports/b2b/b2b_pil_report.md`).

## HIL notes
- Every test powers on a fresh ECU; the bench (plant, BCM, tester) runs a 10 ms real-time loop; results come from CAN frame timestamps.
- Test-system health: the ECU's 10 ms frames and the bench loop must be on time (≤ 15 ms late) during each measurement. Otherwise the run is repeated (up to 3 times) and finally reported SKIPPED "INCONCLUSIVE", never as an ECU result.
- Result on my laptop (vcan0, 16 Nov 2026): 12 / 12 passed, no repetitions needed. TC_87 added in CR_05.

