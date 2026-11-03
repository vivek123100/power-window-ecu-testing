# Requirements – Power Window ECU

## Interfaces
**Inputs:** switch (Up/Down/Neutral, via CAN), motor current [A], window position [0–100 %],
vehicle speed [km/h, via CAN], battery voltage [V]
**Outputs:** motor command (Up/Down/Stop), status message on CAN, DTCs

## Requirements
| ID | Requirement |
|---|---|
| REQ_01 | When the Up switch is pressed and position < 100 %, the ECU shall drive the motor up within 50 ms. |
| REQ_02 | When the Down switch is pressed and position > 0 %, the ECU shall drive the motor down within 50 ms. |
| REQ_03 | When the switch is released, the motor shall stop within 50 ms. |
| REQ_04 | The motor shall stop when the position reaches 100 % (fully closed) or 0 % (fully open). |
| REQ_05 | If motor current > 8 A while closing, between 4 % and 96 % position, the ECU shall detect a pinch. |
| REQ_06 | After a pinch is detected, the window shall start moving down within 200 ms and reverse by at least 20 %. |
| REQ_07 | Anti-pinch shall be inactive above 96 % position. |
| REQ_08 | If battery voltage < 9 V or > 16 V, the motor shall not run. |
| REQ_09 | If the switch CAN message is missing for > 500 ms, the motor shall stop and DTC_SWITCH_TIMEOUT shall be stored. |
| REQ_10 | If the motor runs continuously for > 8 s, it shall stop and DTC_MOTOR_OVERRUN shall be stored. |
| REQ_11 | If Up and Down are both active at the same time, the motor shall stop. |
| REQ_12 | The ECU shall send its status (position, motor state, pinch flag) on CAN every 100 ms. |
| REQ_13 | After a pinch reversal, the ECU shall not drive the window up until the Up switch has been released and pressed again. |
| REQ_14 | The pinch flag in the status message shall stay set until the Up switch is released. |