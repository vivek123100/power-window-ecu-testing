# Traceability Matrix

| Req | Test cases | MIL | SIL | PIL | HIL |
|---|---|---|---|---|---|
| REQ_01 | TC_01, TC_69 | Pass | Pass | Pass | Pass |
| REQ_02 | TC_10, TC_11, TC_12 | Pass | Pass | Pass | – |
| REQ_03 | TC_13, TC_14, TC_36, TC_70 | Pass | Pass | Pass | Pass |
| REQ_04 | TC_02 | Pass | Pass | Pass | – |
| REQ_05 | TC_03, TC_04, TC_34, TC_71 | Pass | Pass | Pass | Pass |
| REQ_06 | TC_04, TC_35, TC_71 | Pass | Pass | Pass | Pass |
| REQ_07 | TC_05 | Pass | Pass | Pass | – |
| REQ_08 | TC_06, TC_07, TC_23, TC_27, TC_30, TC_33, TC_74 | Pass | Pass | Pass | Pass |
| REQ_09 | TC_08, TC_20, TC_22, TC_25, TC_32, TC_37, TC_38, TC_49–TC_53, TC_61, TC_67, TC_72 | Pass | Pass | Pass | Pass |
| REQ_10 | TC_15, TC_16, TC_26, TC_29 | Pass | Pass | Pass | – |
| REQ_11 | TC_09, TC_24, TC_28, TC_76 | Pass | Pass | Pass | Pass |
| REQ_12 | TC_17, TC_18, TC_19, TC_75 | Pass | Pass | Pass | Pass |
| REQ_13 | TC_31, TC_71 | Pass | Pass | Pass | Pass |
| REQ_14 | TC_30, TC_31, TC_71 | Pass | Pass | Pass | Pass |
| REQ_15 | TC_39, TC_40, TC_41, TC_42, TC_43, TC_44, TC_46, TC_47, TC_48, TC_65, TC_68, TC_78, TC_79, TC_80 | n/a | Pass | Pass | Pass |
| REQ_16 | TC_45, TC_60, TC_66, TC_78 | n/a | Pass | Pass | Pass |
| REQ_17 | TC_54, TC_55, TC_56, TC_57, TC_61, TC_62, TC_67, TC_73 | n/a | Pass | Pass | Pass |
| REQ_18 | TC_58, TC_59, TC_60, TC_60b, TC_61, TC_63, TC_64, TC_65, TC_66, TC_73, TC_79 | n/a | Pass | Pass | Pass |

Legend: Pass / Fail / – (not yet run) / n/a (not part of that level)

- **MIL:** Simulink/Stateflow (`01_MIL`), 23 test cases. CAN, UDS and E2E (REQ_15–18) are not modelled in MIL.
- **SIL:** C code on the PC (gcc): `02_SIL/tests` + `03_CAN/tests` (virtual CAN bus), 103 automated tests.
- **PIL:** the same 103 tests with the controller on an STM32F407 (arm-none-eabi-gcc, Renode emulator), `04_PIL`. MIL vs. PIL back-to-back: 23/23 identical.
- **HIL:** ECU firmware as a real-time CAN node on vcan0 (`05_HIL`), 12 tests (TC_69–TC_80) measured on the bus. Not yet at HIL level: REQ_02 (down), REQ_04 (end stops), REQ_07 (no anti-pinch above 96 %), REQ_10 (8 s overrun) – covered in MIL/SIL/PIL.

