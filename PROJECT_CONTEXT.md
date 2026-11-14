# Project Context – Handover for a New Chat

> **How to use:** start a new chat, attach this file (or paste its content), and write:
> *"I'm continuing my automotive testing learning project. Here is my project context. Continue from 'Next steps'."*
> Update this file at every milestone (or ask Claude to update it).

_Last updated: 14 Nov 2026 (CR_01 done)_

## 1. Who I am and what I want
- Automotive engineer, beginner–intermediate in testing theory.
- Goal: learn automotive ECU testing (MIL, SIL, PIL, HIL, CAN, UDS) with free resources and build **one GitHub portfolio project** for my CV. Target: test engineer roles (HIL/SIL/test automation). Long term: maybe an automotive testing startup in India (EV/BMS focus).
- Time: ~8–10 h/week. Project expected done ~March 2027.
- **How I like to learn:** hands-on, short explanations, see things working. Long paper exercises get boring; mix theory with building. Explain errors step by step; give exact commands.

## 2. My setup
| Item | Detail |
|---|---|
| GitHub repo | https://github.com/vivek123100/power-window-ecu-testing (public, branch `main`) |
| PC | Windows. Repo cloned locally, edited in VS Code. **Git commands from Windows only.** |
| MATLAB | MATLAB Online with license (MATLAB, Simulink, Stateflow). Onramps done (MATLAB, Simulink). |
| MATLAB repo copy | `MATLAB Drive/pw-ecu` (clone of the GitHub repo). Open the model ONLY from here. Git via `gitrepo`, `add`, `commit`, `push`, `pull`. |
| SIL tools | WSL Ubuntu: gcc, gcov/gcovr, cppcheck, Python venv (`.venv`) with pytest. Repo at `/mnt/c/Users/LENOVO/OneDrive/Desktop/github.repo/power-window-ecu-testing` (alias `pw` = cd + activate venv). Run `pytest 02_SIL/tests -v`. **Git only from Windows PowerShell, not WSL.** TODO: move repo out of OneDrive to `C:\Projects`. |
| Routine | Always `pull` before working (both copies), `push` after. GitHub = the backup. |

Lessons learned: don't delete and re-clone a MATLAB Drive folder under the same name (sync broke `.git`); never type values into model blocks, use variable names.

## 3. The project: Power Window ECU with anti-pinch
Repo structure: `docs/` (requirements, test spec, traceability, tools log, CV notes), `01_MIL/model`, `01_MIL/tests`, `02_SIL/src`, `02_SIL/tests`, `03_CAN/dbc`, `03_CAN/sim`, `04_PIL`, `05_HIL`, `reports/`, `.github/workflows/sil-tests.yml`.

### Requirements (summary – full text in `docs/requirements.md`)
REQ_01 Up → motor up ≤50 ms · REQ_02 Down → motor down ≤50 ms · REQ_03 release → stop ≤50 ms · REQ_04 stop at 0/100 % · REQ_05 pinch if current >8 A while closing, 4 % < pos < 96 % · REQ_06 start reversing ≤200 ms and reverse ≥20 % · REQ_07 no anti-pinch above 96 % · REQ_08 no motor if Vbat <9 or >16 V · REQ_09 switch CAN msg missing >500 ms → stop + DTC_SWITCH_TIMEOUT · REQ_10 motor running >8 s → stop + DTC_MOTOR_OVERRUN · REQ_11 Up+Down → stop · REQ_12 status on CAN every 100 ms · REQ_13 after pinch, no closing until Up released and pressed again · REQ_14 pinch flag stays set until Up released.

### Stateflow controller (`WindowController`, MATLAB action language, discrete 0.01 s)
Inputs: `SwUp`, `SwDown` (boolean), `Pos` [%], `Current` [A], `Vbat` [V], `SwMsgAge_ms`. Outputs: `MotorCmd` (int8: 1/−1/0), `PinchFlag`, `DTC_SwitchTimeout`, `DTC_MotorOverrun`. Local: `PosAtPinch`.

States: IDLE (0), MOVING_UP (1), MOVING_DOWN (−1), PINCH_REVERSE (−1, PinchFlag=true, no exit action), WAIT_RELEASE (0), ERROR (0).

Transition priorities (faults first): from moving states → 1 timeout→ERROR (+DTC), 2 `after(8,sec)`→ERROR (+DTC), 3 voltage→IDLE, 4 Up&&Down→IDLE, then normal (pinch → PINCH_REVERSE; release/end stop → IDLE). PINCH_REVERSE → WAIT_RELEASE when reversed ≥20 % or pos ≤0. WAIT_RELEASE → IDLE on `~SwUp` (clears PinchFlag). ERROR → IDLE when msg OK and both switches released. DTCs latch.

### Plant (`WindowPlant`, MATLAB Function block)
Inputs: `MotorCmd, ObstacleActive, ObstaclePos, InitPos, StallCurrent`. 25 %/s, end stops 0/100 %, current 0 A off / 2 A free / StallCurrent when blocked. Feedback `Pos` and `Current` to the chart via Unit Delay (IC `InitPos` and 0) to avoid an algebraic loop.

### MIL test harness
- Inputs via From Workspace blocks: `SwUp_in`, `SwDown_in`, `Vbat_in`, `MsgAge_in` (format `[time value]`, no interpolation, sample time 0.01). Plant constants use variables. Outputs via To Workspace (Timeseries): `MotorCmd, PinchFlag, DTC_SwitchTimeout, DTC_MotorOverrun, Pos, Current`.
- `01_MIL/tests/run_mil_tests.m`: 21 test cases (TC_01–TC_21), checks with measured values, writes `reports/MIL_test_report.md`. `mil_defaults.m` for manual runs.
- **Result: 19/19 executed PASS; TC_17/TC_18 N/A (CAN status message, tested later).** TC_22 (ERROR recovery needs switch release) added; MIL now 20/20. Model fix: Pos Unit Delay IC = `InitPos`; Pos/Current logged before the Unit Delays.

Bugs found so far: missing fault handling in PINCH_REVERSE (→ TC_20), repeated pinch while Up held (→ REQ_13, WAIT_RELEASE, TC_21), PinchFlag cleared too early (→ REQ_14), untestable REQ_06 (reworded).

## 4. Progress
- [x] Roadmap, skills overview, career paths, startup timeline discussed
- [x] GitHub repo set up, docs written
- [x] MIL: Stateflow model, plant, automated harness, 19/19 pass
- [x] **SIL complete:** C controller (`02_SIL/src/`), pytest harness 36 tests (`02_SIL/tests/`, sensor fault `pos_stuck_from`), back-to-back vs. MIL 100 % identical, coverage 95 % lines (only defensive `default:` uncovered), cppcheck + MISRA (addon needs `--enable=style`; DEV_01 Rule 8.7 in `02_SIL/misra_suppressions.txt`), GitHub Actions green with quality gates.
- [x] **CAN + UDS complete:** DBC `03_CAN/dbc/power_window.dbc` (0x200 BCM_WindowSwitch 20 ms, 0x210 DCU_WindowStatus 100 ms); `03_CAN/sim/can_network.py` (virtual bus, BCM/DCU/tester/logger, simulated time, `bcm_silent`, `diag_requests`); `03_CAN/sim/uds.py` (ISO-TP by hand, UDS 0x10/0x22 F195+0100/0x19 02/0x14/0x3E on 0x7E0/0x7E8, DTCs U0140-00, B1310-00); tests `03_CAN/tests/test_can.py` (8) and `test_uds.py` (13); C API `WindowCtrl_ClearDtcs`. REQ_15/REQ_16, TC_37–TC_48 added. Total 77 passed locally (`bash run_all.sh`). Open question: REQ_09 timeout only detected while moving.
- [ ] PIL (STM32 Nucleo)
- [ ] Mini-HIL with fault injection
- [ ] README polish + demo video
- Parked for later: Jira (free) + Xray trial; Polarion/codeBeamer/Jama trial; Doorstop or sphinx-needs; seat heater Stateflow exercise.

## 5. Next steps
- **CR_01 DONE (14 Nov 2026):** REQ_09 timeout now detected in every state (new transitions IDLE→ERROR and WAIT_RELEASE→ERROR, priority 1, in Stateflow and `window_ctrl.c`); option A start-up rule (message age counts from power-on, `can_network.py` `last_rx_t = 0.0`); tests TC_32 updated, TC_49–TC_53 added; MIL 23/23, `bash run_all.sh` 87 passed / 1 skipped, coverage 96 %. Since CR_01, `run_live.py` stores U0140-00 if `cangen` doesn't start within 0.5 s.
- My computer's repo folder is connected to the chat: Claude can write files directly into it.
1. Open points left: OP_03 AliveCounter / E2E (open), OP_06 start-up delay (A + C) improvement. Out of scope: OP_04 engine off / locking (CR_02), OP_05 crash behaviour (CR_03).
2. Next options: README + demo video (job-ready), PIL on a board (ask which board), or E2E (OP_03). Try a feature branch + pull request for the next change.
3. Housekeeping: move the repo out of OneDrive to `C:\Projects`; add TC_23–TC_36 to the MIL harness.
