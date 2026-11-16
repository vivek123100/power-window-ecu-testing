# Verification & Validation Report – Power Window ECU

| | |
|---|---|
| Object under review | `main` at commit `85a2943` (16 Nov 2026), all levels: requirements, MIL, SIL, CAN/UDS/E2E, PIL, HIL |
| Method | independent re-run from a fresh clone of GitHub, scripted traceability audit, code coverage (gcov), mutation testing, code review, requirement validation against FMVSS 118 |
| Reviewer | Claude (AI assistant), on request of the project owner, not part of the implementation of this review's findings |
| Verdict | **Verification passed with findings. Validation: suitable as a test-engineering demonstrator, not as a product specification** (see section 4) |

**Verification** = did we build it right (code and tests match the requirements, results reproducible)?
**Validation** = did we build the right thing (are the requirements right for a real power window)?

---

## 1. Re-run from a fresh clone (reproducibility)

| Level | Command | Result |
|---|---|---|
| SIL + CAN + UDS + back-to-back | `pytest 02_SIL/tests 03_CAN/tests` | **103 passed, 1 skipped** (matches README) |
| Coverage (gcov, `window_ctrl.c`) | `COVERAGE=1 …` | **96.3 % lines**, 100 % branches executed, **94.8 % branches taken** |
| Coverage (gcov, `e2e_counter.c`) | | **100 % lines, 100 % branches** |
| PIL (STM32F407, Renode) | `TARGET=pil …`, sample of 17 tests incl. back-to-back | **17 / 17 passed**, worst step 57 SysTick ticks |
| Firmware build | `make` in 04_PIL / 05_HIL | identical sizes to the committed state (2384 / 3936 bytes text) |
| HIL (TCP bridge, this reviewer's PC) | `HIL_BUS=tcp pytest 05_HIL/tests` | see section 1.1 |
| HIL (vcan0, owner's laptop) | `bash 05_HIL/run_hil.sh` | **12 / 12 passed** (`reports/junit_hil.xml`) |
| MISRA C:2012 (cppcheck) | in `run_all.sh` / CI | passed (cppcheck not available on the reviewer PC; evidence: owner's `run_all.sh` completed, CI green on PR #1–#3) |

### 1.1 HIL re-run
On the reviewer's PC (2 cores, mutation tests running in parallel): **11 passed, 1 INCONCLUSIVE** (TC_75, 5 s cycle-time
window; the emulator stalled up to 180 ms in all 3 runs; 7 of 18 power-ons were repeated by the health check).
On the owner's laptop with vcan0: **12 / 12 passed** without repeats. Conclusion: the ECU results are consistent;
TC_75 needs a quiet, reasonably fast PC – a known limit of an emulated bench (field guide E8), correctly reported.

---

## 2. Traceability and consistency audit (scripted)

Checked automatically: requirements ↔ test specification ↔ test code ↔ traceability matrix ↔ README numbers.

| Check | Result |
|---|---|
| Every requirement has at least one test case | ✅ 18 / 18 |
| Every test case in the specification has an automated test | ✅ 81 / 81 (TC_01–TC_80 + TC_60b); 6 of them only as parametrised IDs (TC_33, TC_37, TC_38, TC_46, TC_47) or without ID in the test name (TC_48 = `test_response_time_p2`) |
| Tests in code that are not in the specification | ⚠️ `TC_32b`, `TC_33b` (Down variants) |
| Traceability matrix complete | ⚠️ 6 links missing: TC_11→REQ_04, TC_19→REQ_14, TC_21→REQ_13/14, TC_43→REQ_09, TC_44→REQ_10 |
| README numbers | ⚠️ SIL has **49** tests (41 controller + 8 E2E), README says 48 (40 + 8); specification has **81** rows, README says 80 |
| Coverage numbers in docs | ⚠️ test specification still says "97 % branch coverage" (measured before CR_01); now 94.8 % (see F-01) |
| Permanently skipped test | ⚠️ `test_window_ctrl.py` skips TC_17/TC_18 ("tested in the CAN step") – they are tested in `test_can.py`; the placeholder is noise |

---

## 3. Test quality: mutation testing

21 bugs were planted in the C code one at a time (thresholds, comparison operators, removed checks, missing
resets). For each one, the SIL/CAN/UDS suite was run. A **killed** mutant means at least one test failed.

**Mutation score: 16 / 21 killed (76 %).**

| # | Planted bug | Result |
|---|---|---|
| M01 | pinch threshold 8.0 → 8.5 A | killed (back-to-back TC_04) |
| M02 | pinch `>` → `>=` (exactly 8.0 A) | **survived** |
| M03 | timeout 500 → 520 ms | killed (TC_08) |
| M04 | message age `<=` → `<` (exactly 500 ms) | killed (TC_08) |
| M05 | Vbat min 9.0 → 9.1 V | killed (TC_07) |
| M06 | Vbat max `<=` → `<` (exactly 16.0 V) | **survived** |
| M07 | reversal 20 % → 15 % | killed (TC_04) |
| M08 | pinch zone upper limit 96 → 98 % | **survived** |
| M09 | pinch zone lower limit 4 → 2 % | killed (TC_34) |
| M10 | overrun 8 s → 9 s | killed (TC_03) |
| M11 | no Up+Down check while moving down | killed (TC_28) |
| M12 | WAIT_RELEASE skipped | killed (TC_04) |
| M13 | ERROR recovery ignores the switches | killed (TC_03) |
| M14 | ClearDtcs forgets the overrun DTC | **survived** |
| M15 | pinch flag not cleared on release | killed (TC_31) |
| M16 | idle timeout check removed (CR_01 undone) | killed (TC_49) |
| M17 | end stop at 100 % ignored | killed (TC_01) |
| M18 | E2E: 3 repeats → 4 | killed (TC_58) |
| M19 | E2E: repeat count not reset on a fresh frame | killed (TC_59) |
| M20 | E2E_ClearDtc does nothing | killed (TC_60) |
| M21 | E2E counter mask 0x0F → 0x07 | **survived** |

---

## 4. Findings

Severity: **High** = could hide a safety or functional defect · **Medium** = real gap in test or requirement ·
**Low** = documentation / maintainability.

| ID | Sev. | Finding | Evidence | Recommendation |
|---|---|---|---|---|
| F-01 | Medium | **Dead code after CR_01**: in `IDLE`, the timeout check comes first, so `&& msg_ok(...)` in the Up and Down conditions is always true. MISRA C:2012 Rule 14.3 (required) / 2.2 (invariant condition, dead code); it also lowers branch coverage (2 branches can never be taken). The cppcheck MISRA addon did **not** report it – it checks only a subset of the rules. | gcov: lines 95 and 100, branch 3 "taken 0" | Remove the two redundant `msg_ok()` terms; regression + back-to-back (model has the same structure: check the Stateflow guard too) |
| F-02 | Medium | **Pinch zone upper limit not really tested**: TC_05 blocks the window at 98 %, so a zone of 96 → 98 % still passes. A real defect like this makes the window reverse at the seal and **never close**. | M08 survived | New test: block at 97 % with 9 A → no reversal; and at 95 % → reversal |
| F-03 | Medium | **REQ_16 "clear all DTCs" only tested for U0140** | M14 survived | Test: overrun → B1310 → 14 FF FF FF → no DTC |
| F-04 | Medium | **Validation – force vs. current**: REQ_05 detects a pinch at 8 A; the regulation limits the squeezing **force** to < 100 N (FMVSS 118 S5.1, test rods 4–200 mm). The 8 A ↔ 100 N relation is assumed, not shown. Current also depends on battery voltage (9–16 V) and temperature. | requirements vs. FMVSS 118 | State the assumption in REQ_05; on real hardware: force measurement on a 65 N/mm rod, voltage-compensated threshold |
| F-05 | Medium | **Validation – reversal distance**: REQ_06 asks for ≥ 20 % of travel. FMVSS 118 S5.2 needs the window to reverse to its start position, or ≥ 125 mm, or a 200 mm opening. 20 % is ≥ 125 mm only for a travel of ≥ 625 mm. | requirements vs. FMVSS 118 | Specify the reversal in mm (or "to the start position") once the glass travel is known |
| F-06 | Medium | **Validation – stall at the top**: above 96 % anti-pinch is off (correct, the seal), but there is no block detection: a motor stalled at 97–99 % (e.g. position drift, ice) runs at stall current until the **8 s overrun**. Real ECUs stop on block within ~100–300 ms. | REQ_07 + REQ_10 only | New requirement: block detection (current high + position not changing) in every zone |
| F-07 | Low | Boundary **exactly at the threshold** not tested: 8.0 A (REQ_05 says "> 8 A") and 16.0 V (REQ_08: motor allowed) | M02, M06 survived | Add TC with exactly 8.0 A (no pinch) and 16.0 V (motor runs) |
| F-08 | Low | E2E: no test with a **counter jump** (lost frames, e.g. 3 → 11); a wrong mask (0x07) would discard valid frames | M21 survived | Test: jump of 8 → accepted (OK) |
| F-09 | Low | HIL firmware: no timeout on the **sensor frame 0x300** and no check of the CAN **RX FIFO overrun** flag; on a bench stall the ECU would use old sensor values. (Bench artefact: on a real ECU the sensors are analog.) | code review `05_HIL/target/main.c` | Check FOVR0, count lost frames; or RX interrupt |
| F-10 | Low | Documentation: README test counts (48 → 49, 80 → 81), stale "97 % branch", 6 missing traceability links, `TC_32b/33b` not in the spec, skipped placeholder test, REQ_14 typo ("released.."), tab characters in TC_14/TC_16 rows | section 2 | Fix in one docs commit |
| F-11 | Low | REQ_01–03 "within 50 ms" does not say **from when** (switch press, CAN frame received, or frame sent). HIL measures frame sent → frame sent. | requirements review | Define the measurement points |

No **High** findings: no test was found that passes while the requirement is violated in normal operation, and every
safety-relevant mutant that changes normal behaviour (pinch threshold, reversal, WAIT_RELEASE, recovery, timeouts) was killed.

---

## 5. What is solid (keep as it is)

- Results are **reproducible** from a fresh clone, and the numbers in the README are correct within ±1.
- **Back-to-back** MIL vs. SIL vs. PIL is the strongest evidence in the project: it kills 9 of the 16 mutants on its own.
- The **E2E module** has 100 % line and branch coverage and 4 of 5 E2E mutants were killed.
- The **HIL health check** is good practice: a stalled test system is reported as inconclusive, not as an ECU result.
- Change requests (CR_01, CR_04) are traceable from the requirement to the tests.

## 6. Recommended next steps (in this order)

1. F-01 code fix + regression (small change request, CR_05).
2. F-02, F-03, F-07, F-08: four to five new test cases; re-run mutation testing (target: all non-equivalent mutants killed).
3. F-10 documentation commit.
4. F-04, F-05, F-06: record as open validation points (they need real hardware or a product decision).
