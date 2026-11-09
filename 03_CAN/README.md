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
| `sim/run_live.py` | Live demo on SocketCAN `vcan0`, I play BCM and tester |
| `tests/test_can.py` | 8 CAN tests (cycle time, content, timeout boundary, DBC conformance) |
| `tests/test_uds.py` | 13 UDS tests (services, DTCs, negative responses, P2 timing) |

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
| **E2E protection** | End-to-end checks (counter, CRC) that a message is fresh and correct. Not implemented yet |
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
bit 3 DTC_SwitchTimeout, bit 4 DTC_MotorOverrun · byte 2: CtrlState (0 IDLE … 5 ERROR).
Example `8C 06 03 00` = 70 %, Down, pinch, PINCH_REVERSE.

**Diagnostic IDs:** 0x7E0/0x7E8 are the OBD-II standard IDs, used here for simplicity. Real ECUs get their own
pair from the car maker's diagnostic description (ODX/CDD) or use 29-bit IDs like `0x18DA10F1`.

---

## Automated tests

```bash
pytest 03_CAN/tests -v        # 21 tests: 8 CAN + 13 UDS (virtual bus, simulated time)
python3 03_CAN/sim/run_demo.py
python3 03_CAN/sim/run_uds_demo.py
```
The tests use python-can's in-process virtual bus, so they are repeatable and run in GitHub Actions.

---

## Live demo on SocketCAN

**Setup** (once; again after every WSL restart):
```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan      # "File exists" = already there, fine
sudo ip link set up vcan0
ip link show vcan0                        # must show UP
```

| Terminal | Role | Command |
|---|---|---|
| 1 | ECU | `CAN_INTERFACE=socketcan python3 03_CAN/sim/run_live.py 600` |
| 2 | Bus monitor | `candump -ta vcan0` (diagnostics only: `candump -ta vcan0,7E0:7F0`) |
| 3 | Me: BCM + tester | `cangen` / `cansend` – these never print anything |

### Script

| # | Do (Terminal 3) | Expect | Why |
|---|---|---|---|
| 1 | `cangen vcan0 -I 200 -L 2 -D 0200 -g 20` | T1: `MOVING_DOWN`; T2: 210 byte 0 falls | Down pressed, REQ_02 |
| 2 | Ctrl+C within ~1.5 s | T1: `ERROR ... DTC timeout 1` after ~0.5 s; T2: 210 `xx 08 05 00` | Message lost while moving, REQ_09 |
| 3 | `cansend vcan0 7E0#031902FFAAAAAAAA` | T2: `7E8 07 59 02 09 C1 40 00 08` | Read DTCs → U0140-00 confirmed |
| 4 | `cansend vcan0 7E0#0414FFFFFFAAAAAA` | T2: `7E8 01 54`; T1: `DTC timeout 0` | Clear DTCs, REQ_16 |
| 5 | `cangen vcan0 -I 200 -L 2 -D 0000 -g 20` | T1: `IDLE` | Leaving ERROR needs both switches released |
| 6 | `cansend vcan0 7E0#0322F195AAAAAAAA` | T2: `7E8 10 0B 62 F1 95 50 57 2D`, then nothing | First Frame, ECU waits |
| 7 | `cansend vcan0 7E0#3000000000000000` | T2: `7E8 21 31 2E 30 2E 30 AA AA` | Flow Control → rest of "PW-1.0.0" |
| 8 | `cansend vcan0 7E0#0322123400000000` | T2: `7E8 03 7F 22 31` | Unknown DID → negative response |

`cangen` options: `-I` ID, `-L` length, `-D` data, `-g` gap in ms.

### Troubleshooting

| Problem | Fix |
|---|---|
| Terminal 3 prints nothing | Normal. Look at Terminals 1 and 2 |
| ECU reacts to nothing | Its run time is over: restart `run_live.py` |
| `Network is down` / `No such device` | Run the setup again (`vcan0` gone after WSL restart) |
| Up → Release gives ERROR | The gap between two `cangen` runs was > 500 ms; correct behaviour |
| `0060` does nothing | Byte 1 is the AliveCounter; only byte 0 bits 0–1 are switches |
| First Frame but no rest | Send the Flow Control `7E0#3000000000000000` |

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
