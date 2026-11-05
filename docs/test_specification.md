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
| TC_17 | REQ_12 |	ECU running | Measure status message for 10 s |	Cycle time 100 ms ±10 ms |
| TC_18 | REQ_12 |	Moving up, pos =  40 % | Read status message |	Position = 40 %, state = Up, pinch flag = 0 |
| TC_19 | REQ_12 | Pinch detected (as in TC_04) | Read status message |	Pinch flag = 1 |
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