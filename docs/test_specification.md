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


