# MIL Test Report - Power Window ECU

Generated: 05-Nov-2026 00:10:29  
Model: PowerWindow_MIL.slx

**20 of 20 executed test cases passed.**

| TC | Requirement | Description | Result | Details |
|---|---|---|---|---|
| TC_01 | REQ_01 | Up pressed -> motor up within 50 ms | PASS | motor up after 0 ms (limit 50 ms) |
| TC_02 | REQ_04 | Window stops at 100 % | PASS | at 4 s: Pos = 100.0 %, MotorCmd = 0 |
| TC_03 | REQ_05 | Stall current 7.9 A -> no pinch | PASS | PinchFlag max = 0, reversal seen = 0 |
| TC_04 | REQ_05, REQ_06 | Stall current 8.1 A -> pinch, reverse >= 20 % | PASS | reversal started 0 ms after stall (limit 200 ms), reversed 20.0 % |
| TC_05 | REQ_07 | Blocked above 96 % -> no reversal | PASS | reversal seen = 0 |
| TC_06 | REQ_08 | Vbat 8.9 V -> motor stays off | PASS | MotorCmd min/max = 0 / 0 |
| TC_07 | REQ_08 | Vbat 9.0 V -> motor up | PASS | motor up after 0 ms (limit 50 ms) |
| TC_08 | REQ_09 | Switch message lost at 3 s -> stop + DTC | PASS | DTC before = 0, at 3.1 s: MotorCmd = 0, DTC = 1, DTC at 11 s = 1 |
| TC_09 | REQ_11 | Up and Down together -> motor stays off | PASS | MotorCmd min/max = 0 / 0 |
| TC_10 | REQ_02 | Down pressed -> motor down within 50 ms | PASS | motor down after 0 ms (limit 50 ms) |
| TC_11 | REQ_02, REQ_04 | Pos 0 %, Down -> motor stays off | PASS | MotorCmd min/max = 0 / 0 |
| TC_12 | REQ_02 | Pos 1 %, Down -> motor down | PASS | motor down after 0 ms (limit 50 ms) |
| TC_13 | REQ_03 | Up released at 2 s -> stop within 50 ms | PASS | running before release = 1, stopped 0 ms after release (limit 50 ms) |
| TC_14 | REQ_03 | Down released at 2 s -> stop within 50 ms | PASS | running before release = 1, stopped 0 ms after release (limit 50 ms) |
| TC_15 | REQ_10 | Blocked motor, 7.9 s -> still running, no DTC | PASS | at 8.9 s (7.9 s running): MotorCmd = 1, DTC = 0 |
| TC_16 | REQ_10 | Blocked motor, 8.1 s -> stop + DTC | PASS | at 9.1 s (8.1 s running): MotorCmd = 0, DTC = 1 |
| TC_17 | REQ_12 | Status message cycle time | N/A | No CAN at MIL level - tested in CAN/HIL step |
| TC_18 | REQ_12 | Status message content | N/A | No CAN at MIL level - tested in CAN/HIL step |
| TC_19 | REQ_12, REQ_14 | Pinch flag set during pinch | PASS | PinchFlag at 2.0 s = 1 |
| TC_20 | REQ_09 | Message lost during pinch reversal -> stop + DTC | PASS | reversing at 1.95 s = 1, at 2.1 s: MotorCmd = 0, DTC = 1 |
| TC_21 | REQ_13, REQ_14 | Up held after pinch -> no re-closing | PASS | re-closing after pinch = 0, PinchFlag at 5 s = 1 |
| TC_22 | REQ_09 | Message back while Up held -> no restart | PASS | motor moved after fault = 0, DTC at 11 s = 1 |
