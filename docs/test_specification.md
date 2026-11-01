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

<!-- TODO (homework): add test cases for REQ_02, REQ_03, REQ_10, REQ_12 -->
