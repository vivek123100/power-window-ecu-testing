# Real-World CAN and Diagnostic Issues – a Field Guide

Problems that come up in real test and integration work, written for someone new to the job.
For each: **what you see**, **typical cause**, **how it is found**, **how it is prevented**, and where this
project already covers it.

_Started 14 Nov 2026 – add every new issue you meet at work._

---

## A. Messages that are wrong although they arrive

### A1. Frozen sender (stale data)
- **What you see:** frames keep arriving on time, but the content never changes. The receiver happily uses old values (for example "Up pressed" long after the driver let go).
- **Cause:** the sender's application software hangs, but its CAN controller keeps repeating the last frame from its transmit buffer.
- **How it's found:** look at the **AliveCounter** in the trace: it stays the same in every frame. A pure timeout check never notices, because frames do arrive.
- **Prevented by:** E2E protection (AUTOSAR E2E profiles): an alive counter and usually a CRC in every safety-relevant message; the receiver rejects frames whose counter hasn't moved on.
- **This project:** CR_04 (AliveCounter check, DTC U0422-00).

### A2. Wrong DBC version
- **What you see:** values look plausible but are wrong (window at 140 % or a temperature of −40 °C all the time), or signals are "missing".
- **Cause:** sender and receiver (or your test tool) use different versions of the DBC: a signal was moved, rescaled or added.
- **How it's found:** compare the DBC version in the tool with the software release notes; decode one frame by hand.
- **Prevented by:** versioned DBC files under configuration management; the DBC version in every test report.
- **This project:** one DBC in Git (`03_CAN/dbc/power_window.dbc`), used by both the ECU simulation and the tests.

### A3. Scaling, offset or byte order mistakes
- **What you see:** values off by a factor (2×, 10×), shifted by a constant, or nonsense when values exceed one byte.
- **Cause:** wrong factor/offset, signed vs. unsigned mix-up, Intel (little endian) vs. Motorola (big endian) byte order.
- **How it's found:** set a known physical value, look at the raw bytes, calculate by hand (raw × factor + offset).
- **Prevented by:** DBC conformance tests; boundary values (min, max, just over one byte).
- **This project:** `test_frames_match_dbc`; the frame builder exercise; WindowPos uses factor 0.5.

### A4. Wrong or missing default / initial values
- **What you see:** strange behaviour right after power-on, wake-up or reset, then everything is fine.
- **Cause:** a signal has no defined start value, or the receiver uses a value before the first frame arrived.
- **How it's found:** compare the first samples after start-up; back-to-back testing.
- **Prevented by:** a specified initial value for every signal and state.
- **This project:** back-to-back found the model starting at 50 % instead of the real position (defect 6).

---

## B. Messages that don't arrive (or arrive at the wrong time)

### B1. Message timeout
- **What you see:** a function stops working; a "lost communication" DTC (U0xxx).
- **Cause:** broken wire, loose connector, dead or sleeping sender, gateway not routing.
- **How it's found:** cycle-time measurement in the trace (`candump -ta` timestamps); gaps between frames.
- **Prevented by:** timeout monitoring with a specified detection window and safe reaction.
- **This project:** REQ_09, CR_01, TC_08, TC_37/38, TC_49–TC_53.

### B2. False timeouts at start-up or wake-up
- **What you see:** a "lost communication" DTC after every start, although nothing is broken.
- **Cause:** ECUs boot at different speeds; the receiver starts monitoring before the sender has sent anything.
- **How it's found:** DTCs that always appear at power-on, often with "fault not present now".
- **Prevented by:** a start-up delay before monitoring, or counting the age from power-on (CR_01 option A).
- **This project:** OP_06 (start-up delay, A + C) is an open improvement.

### B3. Cycle time jitter
- **What you see:** a cyclic message arrives sometimes after 18 ms, sometimes after 35 ms.
- **Cause:** sender CPU load, task scheduling, bus load, gateway delays.
- **How it's found:** statistics over many frames (min, max, average gap), not one sample.
- **Prevented by:** cycle time requirements with tolerances, tested over long runs.
- **This project:** TC_17 (100 ms ± 10 ms over 10 s); the bash `cansend` loop only reached 30–35 ms.

### B4. High bus load
- **What you see:** delays, low-priority messages arriving late or not at all.
- **Cause:** too many messages or too short cycles on one bus; a new ECU added to an old network.
- **How it's found:** bus load measurement in CANoe/CANalyzer (often kept below about 50–70 %, depending on the OEM).
- **Prevented by:** network design and load budgets; priority-aware ID assignment.
- **This project:** not covered (two messages only).

### B5. Message ID conflicts
- **What you see:** garbage values, error frames, two ECUs fighting.
- **Cause:** two ECUs configured to send the same ID (copy-paste in the network database, wrong variant).
- **How it's found:** the trace shows the same ID with two different content patterns or cycle times.
- **Prevented by:** one central communication matrix (DBC/ARXML) for the whole vehicle.

---

## C. The bus itself

### C1. Error frames and bus-off
- **What you see:** error frames in the trace; an ECU suddenly disappears from the bus.
- **Cause:** electrical problems (bad wiring, missing termination, interference); after too many errors, a CAN controller goes **bus-off** and stops sending.
- **How it's found:** error counters and error frames in CANoe; an oscilloscope on CAN-H/CAN-L.
- **Prevented by:** correct wiring and termination; bus-off recovery strategy in the ECU software.
- **This project:** not covered (virtual bus has no electrical errors). A real HIL bench would add it.

### C2. Missing or double termination
- **What you see:** communication works on the bench but fails in the car, or only at certain speeds.
- **Cause:** CAN needs exactly two 120 Ω resistors at the bus ends (≈ 60 Ω measured between CAN-H and CAN-L when powered off).
- **How it's found:** a multimeter measurement between CAN-H and CAN-L.
- **Prevented by:** a checklist for every new bench setup.

### C3. Babbling idiot
- **What you see:** one ECU floods the bus with frames, others can't send.
- **Cause:** a software bug sending in a loop, often with a low (high-priority) ID.
- **How it's found:** one ID dominates the trace; bus load near 100 %.
- **Prevented by:** bus guardians, software watchdogs, rate limits.

---

## D. Diagnostics

### D1. DTC flooding
- **What you see:** dozens of DTCs after one event (for example low voltage during cranking).
- **Cause:** every ECU reports its own symptom; missing preconditions for fault monitoring.
- **How it's found:** look for the **first** DTC in time (and its freeze frame data), not the longest list.
- **Prevented by:** fault preconditions (only monitor at stable voltage), DTC suppression rules.
- **This project:** low voltage deliberately stores **no** DTC (REQ_08).

### D2. Intermittent faults
- **What you see:** DTC stored (status 08) but "not present now"; the problem can't be reproduced in the workshop.
- **Cause:** loose contacts, temperature, vibration, rare software timing.
- **How it's found:** wiggle tests, long-term logging in the vehicle, freeze frame data, reproduction on a HIL bench.
- **Prevented by:** robust connectors; fault injection tests for exactly these patterns.
- **This project:** fault injection on the live bus (cutting the BCM messages).

### D3. Wrong diagnostic IDs or session
- **What you see:** the tester gets no answer, or only negative responses.
- **Cause:** wrong request ID for that ECU or vehicle variant; service not allowed in the current session; security access needed.
- **How it's found:** check the diagnostic description (ODX/CDD); look at the NRC (7F xx 7F = not in this session, 33 = security).
- **Prevented by:** using the official diagnostic database in the tester.
- **This project:** 0x7E0/0x7E8 used for simplicity; NRCs 11/12/13/31 tested.

### D4. Flashing interrupted
- **What you see:** an ECU that doesn't start after a software update ("bricked"), or only answers in boot mode.
- **Cause:** voltage drop, lost connection or tester timeout during reprogramming (UDS 0x34/0x36/0x37).
- **How it's found:** the ECU only answers in programming session; the bootloader reports an invalid application.
- **Prevented by:** stable power supply during flashing, a bootloader that can always restart the download.
- **This project:** not covered (no flashing).

---

## E. Test setup problems (the test is wrong, not the ECU)

### E1. Test bench differs from the car
- **What you see:** passes on HIL, fails in the vehicle (or the other way round).
- **Cause:** different software or DBC version, simplified plant model, missing ECUs (restbus simulation incomplete), different wiring.
- **How it's found:** compare configurations line by line; record the vehicle and replay on the bench.
- **Prevented by:** documented bench configuration in every test report.

### E2. Silent or misconfigured tools
- **What you see:** "0 findings" or "all passed" although something is wrong.
- **Cause:** a tool option missing, a filter too strict, tests not actually running.
- **How it's found:** feed the tool a known bad input (tool qualification / self-test).
- **This project:** the MISRA check reported nothing until `--enable=style` (defect 8).

### E3. Hard-coded values and stale files in the setup
- **What you see:** many tests fail at once after a "small" change, or a fix that doesn't seem to work.
- **Cause:** a value typed into a model block, an old file version in the test folder, editing the wrong copy.
- **How it's found:** check the setup first (versions, `grep`, `git diff`) before suspecting the ECU.
- **This project:** the hard-coded Constant block (18 → 15 passing); new test files that never reached the repo.

### E4. Flaky tests (timing)
- **What you see:** a test passes sometimes and fails sometimes, with no code change.
- **Cause:** real-time timing on a PC or bench, uninitialised state between tests, test order dependencies.
- **How it's found:** run the same test many times; check for shared state.
- **Prevented by:** simulated time where possible, a clean reset before each test, tolerances on timing checks.
- **This project:** automated tests use simulated time (repeatable); only the live SocketCAN demo runs in real time.

---

## Quick checklist when something "doesn't work"

1. **Is the setup right?** Versions (software, DBC, test files), wiring, termination, power supply.
2. **Is the message there?** Trace: ID present, cycle time OK, length OK.
3. **Is the content fresh and correct?** AliveCounter moving, CRC OK, values decode sensibly.
4. **What does the ECU say?** Read DTCs and their status; look at the first one in time.
5. **Can I reproduce it?** Same inputs on the bench, with fault injection if needed.
