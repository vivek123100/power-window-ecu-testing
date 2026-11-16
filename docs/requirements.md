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
| REQ_09 | If the switch CAN message is missing for more than 500 ms **in any state**, the ECU shall stop the motor (if running), enter ERROR and store DTC_SWITCH_TIMEOUT; detection shall happen within 500–520 ms. Until the first message is received, the message age shall count from power-on. |
| REQ_10 | If the motor runs continuously for > 8 s, it shall stop and DTC_MOTOR_OVERRUN shall be stored. |
| REQ_11 | If Up and Down are both active at the same time, the motor shall stop. |
| REQ_12 | The ECU shall send its status (position, motor state, pinch flag) on CAN every 100 ms. |
| REQ_13 | After a pinch reversal, the ECU shall not drive the window up until the Up switch has been released and pressed again. |
| REQ_14 | The pinch flag in the status message shall stay set until the Up switch is released.. |
| REQ_15 | The ECU shall support UDS diagnostics (ISO 14229) over ISO-TP on CAN IDs 0x7E0 (request) / 0x7E8 (response): 0x10 sessions 01/03, 0x22 DIDs F195 (software version) and 0100 (window position), 0x19 sub-function 02, 0x14, 0x3E. Unsupported requests shall get a negative response (7F). Responses shall start within P2 = 50 ms. | 
| REQ_16 | UDS 0x14 FF FF FF shall clear all stored DTCs (U0140-00, B1310-00, U0422-00), both in the diagnostic memory and in the status message. |
| REQ_17 | The ECU shall check the AliveCounter of every received BCM_WindowSwitch frame (0x200). A frame whose counter equals the counter of the last accepted frame shall be discarded: its switch values shall not be used and it shall not count as a received message for REQ_09. The first frame after start-up and every changed counter (including the wrap 15 → 0) shall be accepted. _(CR_04)_ |
| REQ_18 | If 3 consecutive 0x200 frames are discarded (REQ_17), the ECU shall store DTC_SWITCH_INVALID (U0422-00), shown in DCU_WindowStatus (0x210 byte 1 bit 5) and reported by UDS 0x19. The DTC shall stay stored after fresh frames return, until cleared with UDS 0x14. _(CR_04)_ |


## Open points and out-of-scope items

| ID | Type | Description | Status |
|---|---|---|---|
| OP_01 | Gap | REQ_09: lost switch message only detected while the window moves, not in IDLE | Fixed by CR_01|
| OP_02 | Gap | REQ_09: detection window not specified (measured 510 ms; proposal 500–520 ms) | Fixed by CR_01 |
| OP_03 | Gap | AliveCounter in 0x200 is never checked (no E2E protection against a frozen sender) | Fixed by CR_04 (REQ_17, REQ_18) |
| OP_04 | Out of scope | Behaviour at engine off and car locking not specified (no ignition, door or lock inputs; window stays where it is). Real cars: retained power, comfort closing with anti-pinch active, block while locked | Not implemented; possible future CR_02 |
| OP_05 | Out of scope | No emergency behaviour: the ECU has no crash input, so after an accident or fire the window stays where it is. Real cars react to a crash message from the airbag ECU (unlock doors, hazard lights, sometimes open windows); this needs E2E-protected CAN signals and ISO 26262 safety analysis (false trigger at speed) | Not implemented; possible future CR_03 |
| OP_06 | Improvement | Start-up delay for timeout monitoring (option A + C), to avoid false DTCs when the BCM wakes up slower than 500 ms | Open |
| OP_07 | Improvement | The E2E check covers only the AliveCounter. There is no CRC or data ID (as in an AUTOSAR E2E profile), so a frame with corrupted content but a moving counter is still accepted | Open |

## Change requests

| CR | Date | Change | Requirements | Tests |
|---|---|---|---|---|
| CR_01 | 14 Nov 2026 | Switch message timeout detected in every state, detection window 500–520 ms, age counts from power-on | REQ_09 | TC_32 (changed), TC_49–TC_53 |
| CR_04 | 16 Nov 2026 | E2E AliveCounter check on 0x200, new DTC U0422-00 (frozen sender) | REQ_16 (extended), REQ_17, REQ_18 | TC_54–TC_67 |