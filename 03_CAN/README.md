# 03_CAN – CAN, UDS and SocketCAN

The power window ECU (my C controller from `02_SIL/src`) on a CAN bus: a DBC file,
a virtual 4-node network, automated CAN and UDS tests, and a live demo on Linux SocketCAN.

| Folder / file | What it is |
|---|---|
| `dbc/power_window.dbc` | CAN database: messages 0x200 and 0x210, their signals and cycle times |
| `sim/can_network.py` | Virtual network: BCM, DCU (my ECU), diagnostic tester, logger |
| `sim/uds.py` | UDS server (in the ECU) and tester, ISO-TP framing by hand |
| `sim/run_demo.py` | Demo: lost switch message → ERROR after 510 ms |
| `sim/run_uds_demo.py` | Demo: read SW version, read and clear DTCs, frame by frame |
| `sim/run_live.py` | Live demo on SocketCAN `vcan0`: the ECU + window model (obstacle commands) |
| `sim/bcm_live.py` | Live BCM with a real AliveCounter (hold, timed hold, freeze, cut wire) |
| `LIVE_DEMO.md` | Step-by-step guide for the 4-terminal live demo |
| `tests/test_can.py` | 11 CAN tests (cycle time, content, timeout boundary, DBC conformance) |
| `tests/test_can_e2e.py` | 7 frozen-sender tests (CR_04: discard, U0422-00, recovery) |
| `tests/test_uds.py` | 15 UDS tests (services, DTCs, clear of all DTCs, negative responses, P2 timing, ISO-TP robustness) |

---

## Glossary – the words that matter

| Term | Meaning in one line |
|---|---|
| **CAN** | Two-wire bus where every ECU hears every message |
| **Frame** | One CAN message: ID + length + up to 8 data bytes |
| **ID** (identifier) | The message's "name" and priority. Lower ID wins when two ECUs send at once |
| **Arbitration** | How CAN decides who sends first: bit by bit, a 0 beats a 1 |
| **DLC** | Data Length Code = number of data bytes (0–8) |
| **Signal** | One value inside the data, e.g. WindowPos. Defined by start bit, length, factor, offset |
| **DBC** | File that describes which bits of which ID are which signal |
| **Factor / offset** | physical value = raw × factor + offset (WindowPos: raw × 0.5) |
| **Intel byte order** | Little endian: bit 0 is the rightmost bit of byte 0 |
| **Cycle time** | How often a message repeats (0x200: 20 ms, 0x210: 100 ms) |
| **Cyclic message** | Sent automatically on a fixed cycle; nobody asks for it |
| **Timeout** | A cyclic message stops arriving for too long (here > 500 ms) |
| **Message age** | Time since the last frame of a message arrived; the ECU compares it with the limit |
| **AliveCounter** | Number that changes every frame, so a receiver can spot a frozen sender (E2E) |
| **E2E protection** | End-to-end checks (counter, CRC) that a message is fresh and correct. Here: AliveCounter check (CR_04), no CRC yet |
| **Frozen sender** | Sender keeps repeating its last frame on time (application hung); the content is stale, the counter does not move |
| **Stale frame** | A frame whose AliveCounter equals the last accepted one; the ECU discards it (REQ_17) |
| **U0422-00** | DTC "invalid data received from BCM" (`C4 22 00`): 3 stale frames in a row (REQ_18) |
| **Latched DTC** | Stays stored after the fault is gone, until UDS 0x14 clears it |
| **BCM** | Body Control Module, here: sends the window switch request |
| **DCU** | Door Control Unit = my power window ECU |
| **UDS** | Unified Diagnostic Services (ISO 14229): the language of diagnostic testers |
| **Service / SID** | First byte of a UDS request, e.g. 0x22 = read data |
| **Positive response** | Answer = SID + 0x40 (0x22 → 0x62) |
| **Negative response** | `7F` + SID + reason code (NRC) |
| **NRC** | Negative Response Code: 11 not supported, 12 sub-function, 13 length, 31 out of range |
| **DID** | Data Identifier: number of a value you can read, e.g. F195 = software version |
| **DTC** | Diagnostic Trouble Code: a stored fault, 3 bytes code + 1 byte status |
| **U / B / C / P code** | DTC letter from the first 2 bits: U network, B body, C chassis, P powertrain |
| **Status byte** | 8 flags per DTC; 08 = confirmed (stored), 01 = failing right now |
| **Session** | UDS mode: 01 default, 03 extended (more services allowed) |
| **TesterPresent** | `3E 00`: "I'm still connected", keeps a session alive |
| **P2** | Time the ECU has to start its answer (50 ms here) |
| **ISO-TP** | Transport layer (ISO 15765-2) that splits long UDS messages into frames |
| **SF / FF / CF / FC** | Single Frame, First Frame, Consecutive Frame, Flow Control |
| **Physical / functional request** | To one ECU (0x7E0) / to all ECUs at once (OBD: 0x7DF) |
| **SocketCAN** | Linux's built-in CAN support: CAN interfaces look like network cards |
| **vcan0** | Virtual CAN interface in the Linux kernel, no hardware needed |
| **can0** | A real CAN interface, e.g. a USB-CAN adapter |
| **can-utils** | Command-line tools: `candump`, `cansend`, `cangen` |

---

## Message reference

| ID | Name | Sender → receiver | Cycle | Bytes |
|---|---|---|---|---|
| 0x200 | BCM_WindowSwitch | BCM → ECU | 20 ms | 2 |
| 0x210 | DCU_WindowStatus | ECU → all | 100 ms | 4 |
| 0x7E0 | UDS request | tester → ECU | on request | 8 |
| 0x7E8 | UDS response | ECU → tester | on request | 8 |

**0x200** – byte 0: bit 0 SwUp, bit 1 SwDown; byte 1 bits 0–3: AliveCounter.
`0000` release · `0100` Up · `0200` Down · `0300` both (invalid → stop)

**0x210** – byte 0: WindowPos (× 0.5 %) · byte 1: bits 0–1 MotorState (0 Stop, 1 Up, 2 Down), bit 2 PinchFlag,
bit 3 DTC_SwitchTimeout, bit 4 DTC_MotorOverrun, bit 5 DTC_SwitchInvalid (U0422-00, CR_04) · byte 2: CtrlState (0 IDLE … 5 ERROR).
Example `8C 06 03 00` = 70 %, Down, pinch, PINCH_REVERSE.

**Diagnostic IDs:** 0x7E0/0x7E8 are the OBD-II standard IDs, used here for simplicity. Real ECUs get their own
pair from the car maker's diagnostic description (ODX/CDD) or use 29-bit IDs like `0x18DA10F1`.

---

## Automated tests

```bash
pytest 03_CAN/tests -v        # 33 tests: 11 CAN + 7 E2E + 15 UDS (virtual bus, simulated time)
python3 03_CAN/sim/run_demo.py
python3 03_CAN/sim/run_uds_demo.py
```
The tests use python-can's in-process virtual bus, so they are repeatable and run in GitHub Actions.

---

## Live demo on SocketCAN

Full guide with setup, all commands for the 4 terminals, demos and troubleshooting:
**[LIVE_DEMO.md](LIVE_DEMO.md)**

| Terminal | Role | Command |
|---|---|---|
| 1 | ECU + window model (`p 70` = hand at 70 %) | `CAN_INTERFACE=socketcan python3 03_CAN/sim/run_live.py 1800` |
| 2 | Bus monitor | `candump -ta vcan0` |
| 3 | BCM = door switch (`u` `d` `r` `u 0.8` `f` `s`) | `python3 03_CAN/sim/bcm_live.py` |
| 4 | Diagnostic tester | `cansend vcan0 7E0#031902FFAAAAAAAA` (read DTCs) |

Demos: partial opening, anti-pinch, frozen sender (CR_04), lost message, repair → clear → verify.

**Quick reference: frozen sender result and clearing**

| What you see | Meaning |
|---|---|
| `state ERROR   DTC timeout 1   invalid 1` | the final state after a freeze |
| `invalid 1` | the ECU saw the AliveCounter frozen and stored **U0422-00** |
| `timeout 1` | then no fresh frame for 0.5 s → **U0140-00** and ERROR; the motor stopped although the frozen frames still said "Up" |
| `10 0B 59 02 09 C1 40 00`, then `21 08 C4 22 00 08 AA AA` (in `candump -ta vcan0,7E8:7FF`) | read DTCs answer: U0140-00 and U0422-00 (First Frame + Consecutive Frame) |

Repair → clear → verify:
1. Repair first: in Terminal 3 unfreeze or resume the BCM, then `r`.
2. Clear: `cansend vcan0 7E0#0414FFFFFFAAAAAA` → answer `01 54`.
3. Check: `cansend vcan0 7E0#031902FFAAAAAAAA` → answer `03 59 02 09` = empty.

> Since CR_04, `cangen` with fixed data repeats the same AliveCounter, so the ECU treats it as a
> **frozen sender**. Use `bcm_live.py` as the healthy BCM.

---

## Practice exercises

Do these without looking at the answers, then check with the live demo.

1. Decode `210 [4] AE 08 05 00`.
2. Which `cansend` presses Up once? Which `cangen` keeps Up pressed?
3. Decode the DTC answer `07 59 02 09 93 10 00 08`.
4. The ECU answers `03 7F 19 13`. What went wrong?
5. Why is the timeout detected after 510 ms and not 500 ms?
6. Two ECUs send 0x200 and 0x210 at the same moment. Which one goes first, and why?
7. What's the difference between status `08` and `09`?
8. You stop `cangen` while the window is idle. What happens, and why is that a requirement gap?

<details>
<summary>Answers</summary>

1. 87 % (0xAE = 174 × 0.5), motor Stop, DTC_SwitchTimeout = 1 (byte 1 bit 3), state ERROR.
2. `cansend vcan0 200#0100` (one frame) · `cangen vcan0 -I 200 -L 2 -D 0100 -g 20` (every 20 ms).
3. Positive answer to 0x19, DTC `93 10 00` = 10|01|0011 → B, 1, 3, then 10 → **B1310-00** (motor overrun), status 08 confirmed.
4. Negative response to service 0x19, NRC 13 = wrong message length.
5. The ECU checks every 10 ms; at 500 ms the age is not yet *more than* 500 ms, so the first failing check is at 510 ms.
6. 0x200: both IDs are equal until bit 4, where 0x200 has a 0 and 0x210 a 1; a 0 wins.
7. 08 = confirmed (stored in memory); 09 = confirmed and failing right now.
8. Nothing: the timeout is only checked while the window moves. A dead BCM goes unnoticed while idle → open point for REQ_09.

</details>

---

## Open requirement points found in live testing

1. REQ_09: the timeout is only detected while the window moves, not in IDLE.
2. The AliveCounter is never checked: no E2E protection against a frozen sender.
3. REQ_09 does not specify the detection window (measured: 510 ms; proposal 500–520 ms).

Points 1 and 3 were fixed by **CR_01**, point 2 by **CR_04** (AliveCounter check, U0422-00).
Still open: no CRC in the E2E check (OP_07), start-up delay for timeout monitoring (OP_06).

## Out of scope (found during scenario review, not implemented)

4. **Behaviour at engine off and car locking is not specified.** The ECU has no ignition, door or lock inputs,
   so after engine off the window simply stays where it is. Real cars usually add retained power (windows
   still work for a while after engine off), comfort closing (locking closes the windows fully), and blocking
   while locked. Comfort closing moves the window with nobody at the switch, so anti-pinch must stay active
   (see regulations such as ECE R21 / FMVSS 118).
   **Decision:** not implemented in this project, because it needs new CAN signals (DBC), new requirements,
   new model states, C code and tests across all levels. Documented as a possible future **CR_02**.

5. **No emergency behaviour (crash, fire).** The ECU has no crash input, so after an accident the window
   stays where it is. Real cars react to a crash message from the airbag ECU (unlock doors, hazard lights,
   sometimes open windows). This needs an E2E-protected crash signal and an ISO 26262 safety analysis
   (a false trigger at speed is dangerous).
   **Decision:** not implemented; documented as OP_05, a possible future **CR_03**.
