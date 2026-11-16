# Live Demo on SocketCAN – 4 Terminals

The power window ECU runs in real time on the virtual CAN bus `vcan0`. I play the BCM
(the door switch), the "real world" (a hand in the window) and the workshop tester.

| Terminal | Role | What I type there |
|---|---|---|
| **1** | ECU + window model (the real world) | `p 70`, `p`, `w` |
| **2** | Bus monitor (like CANalyzer trace) | nothing, only watch |
| **3** | BCM = the door switch | `u`, `d`, `r`, `u 0.8`, `f`, `s`, `b`, `q` |
| **4** | Diagnostic tester (workshop tool) | `cansend` UDS requests |

---

## 1. Setup

**Once after every WSL restart** (Terminal 1):
```bash
pw
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan 2>/dev/null   # no output = fine
sudo ip link set up vcan0
ip -details link show vcan0                        # must show "vcan" and UP / UNKNOWN
```

**Make sure no old ECU is still running** (only one ECU may be on the bus):
```bash
pkill -f run_live.py
candump -ta vcan0,210:7FF      # wait 3 s: no lines = bus is free → Ctrl+C
```

**Start the four terminals:**

| Terminal | Command |
|---|---|
| 1 ECU | `pw` → `CAN_INTERFACE=socketcan python3 03_CAN/sim/run_live.py 1800` |
| 2 monitor | `pw` → `candump -ta vcan0,200:7FF` (switch frames) or `candump -ta vcan0` (everything) |
| 3 BCM | `pw` → `python3 03_CAN/sim/bcm_live.py` (start right after Terminal 1) |
| 4 tester | `pw` → `candump -ta vcan0,7E8:7FF &` (shows the ECU's diagnostic answers) |

Start the BCM within 0.5 s… a few seconds of the ECU; otherwise U0140-00 is stored at power-on
(CR_01 option A). Not a problem: clear it with UDS.

---

## 2. Command reference

### Terminal 1 – the real world (window model)
| Type | Effect |
|---|---|
| `p 70` | Put a hand (obstacle) at 70 % |
| `p` | Remove the hand |
| `w` | Show where the window is and where the obstacle is |

The ECU prints a line when its status changes, and every 0.5 s while the motor runs.

### Terminal 3 – the BCM (door switch)
| Type | Effect |
|---|---|
| `u` | Hold Up (window closes while held) |
| `d` | Hold Down (window opens while held) |
| `r` | Release the switch = **stop the window** |
| `u 0.8` / `d 0.4` | Hold for 0.8 s / 0.4 s, then release by itself (25 %/s: 0.4 s ≈ 10 %, 0.8 s ≈ 20 %, 4 s = full) |
| `b` | Both pressed (implausible input → stop, REQ_11) |
| `f` | **Freeze** / unfreeze: repeat the same frame, same AliveCounter (frozen sender, CR_04) |
| `s` | Stop / resume sending = **cut the wire** (lost message, REQ_09) |
| `q` | Quit |

`f` and `s` are **fault injection**, not normal operation. Each `f` toggles – check the reply says
`unfrozen` before going on.

### Terminal 4 – diagnostics (UDS over ISO-TP, request 0x7E0, answer 0x7E8)
| Purpose | Command | Answer (0x7E8) |
|---|---|---|
| Read DTCs (19 02 FF) | `cansend vcan0 7E0#031902FFAAAAAAAA` | no DTC: `03 59 02 09` · one: `07 59 02 09 C1 40 00 08` · two or more: First Frame `10 0B …` |
| Flow control (after a First Frame) | `cansend vcan0 7E0#3000000000000000` | Consecutive Frame `21 …` |
| Clear DTCs (14 FF FF FF) | `cansend vcan0 7E0#0414FFFFFFAAAAAA` | `01 54` |
| SW version (22 F1 95, multi-frame) | `cansend vcan0 7E0#0322F195AAAAAAAA` | `10 0B 62 F1 95 …`, then flow control |
| Window position (22 01 00) | `cansend vcan0 7E0#03220100AAAAAAAA` | `04 62 01 00 pp` (pp = position in hex) |
| Unknown DID (negative test) | `cansend vcan0 7E0#0322123400000000` | `03 7F 22 31` (request out of range) |

DTC codes: `C1 40 00` = **U0140-00** lost communication with BCM · `93 10 00` = **B1310-00** motor
overrun · `C4 22 00` = **U0422-00** invalid data from BCM (frozen AliveCounter). Status `08` = confirmed.

---

## 3. Demos

### A. Partial opening (hold-to-move)
| Where | Type | Expect (Terminal 1) |
|---|---|---|
| T3 | `d 0.8` | `MOVING_DOWN`, 50 % → about 30 %, then `IDLE` |
| T3 | `u` … wait … `r` | moves up while held, stops where you release |

### B. Anti-pinch (REQ_05, REQ_06, REQ_13)
Pinch = something trapped while the window **closes** (a child's hand). The ECU has no sensor for the
hand – it watches the **motor current**: free ≈ 2 A, blocked = 10 A, limit **8 A**. Above the limit it
reverses 20 % and waits until Up is released. Only while closing, only between 4 % and 96 %
(near the top the glass must press into the seal).

The hand must be **above** the glass, in its path:

| Where | Type | Expect (Terminal 1) |
|---|---|---|
| T3 | `d`, wait ~3 s, `r` | window at 0 %, `IDLE` |
| T1 | `p 70` | `[world] obstacle at 70 % (window now at 0.0 %)` |
| T3 | `u` (hold) | pos 12, 25, 37 … `MOVING_UP` |
| – | (automatic) | at 70 %: **`PINCH_REVERSE pinch 1`**, motor Down |
| – | (automatic) | down to 50 %, then **`WAIT_RELEASE`**, motor Stop |
| T3 | `r` | `IDLE`, `pinch 0` |
| T1 | `p` | hand removed – now `u` closes fully |

### C. Frozen sender (CR_04, REQ_17/18)
| Where | Type | Expect |
|---|---|---|
| T3 | `u` | T2: second byte of 0x200 counts 0…F · T1: `MOVING_UP` |
| T3 | `f` | T2: bytes stop changing · T1: `invalid 1` (~60 ms), then `ERROR`, `timeout 1` (~0.5 s) |
| T4 | read DTCs + flow control | `10 0B 59 02 09 C1 40 00` then `21 08 C4 22 00 08 AA AA` = U0140-00 + U0422-00 |
| T3 | `f` (→ "unfrozen"), then `r` | T2: counter moves again · T1: `IDLE`, DTCs still stored |
| T4 | clear DTCs, read DTCs | `01 54`, then `03 59 02 09` (empty) · T1: all DTCs 0 |

The frozen frames still said "Up pressed" and arrived on time – without the AliveCounter check the
window would have kept moving.

### D. Lost message (REQ_09, CR_01)
| Where | Type | Expect |
|---|---|---|
| T3 | `d` | `MOVING_DOWN` |
| T3 | `s` | ~0.5 s later: `ERROR`, motor Stop, `timeout 1` |
| T3 | `s` (resume), `r` | `IDLE`, DTC stays stored |
| T4 | read DTCs | `07 59 02 09 C1 40 00 08` = U0140-00 |

### E. Repair → clear → verify (the workshop order)
| Step | Where | Command |
|---|---|---|
| 1. Repair the cause | T3 | `f` until "unfrozen" / `s` until "resumed" |
| 2. Release the switch | T3 | `r` → ECU leaves ERROR |
| 3. Clear the fault memory | T4 | `cansend vcan0 7E0#0414FFFFFFAAAAAA` |
| 4. Verify | T4 | `cansend vcan0 7E0#031902FFAAAAAAAA` → `03 59 02 09` = no DTCs |

Clearing does **not** repair anything. Clear while the fault is still there → the DTC comes straight
back. That's the sign "fault still present".

---

## 4. Rules worth remembering

| Behaviour | Why |
|---|---|
| ECU stays in ERROR until `r`, even after the fault is gone | Safety: the window must not start moving by itself when the fault disappears |
| A stored DTC does not block the window | Only the ERROR state blocks; the DTC is just memory for the workshop |
| DTCs are latched | They stay stored after the fault is gone, until UDS 0x14 |
| A restarted ECU has no DTCs | The simulation keeps fault memory in RAM (a real ECU stores it in EEPROM/flash) |
| `cangen` with fixed data = frozen sender | Since CR_04 the AliveCounter must change; use `bcm_live.py` instead |

---

## 5. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Terminal 1 stopped, last line long ago | Run time over (it only prints on changes) | Restart with ↑ + Enter |
| Lines alternate between two positions (e.g. 100 % ERROR and a moving window) | **Two ECUs on the bus** (old `run_live.py` still running) – ID conflict | `pkill -f run_live.py`; check with `candump vcan0,210:7FF`; if it persists: `wsl --shutdown` in PowerShell |
| Every BCM command says "but the sender is FROZEN" | `f` toggles; it's still frozen | `f` once more until "unfrozen" |
| `invalid 1` comes back after clearing | Still frozen, or cleared before unfreezing (DTC is latched) | Unfreeze first, then clear again |
| Nothing moves after ERROR | Switch still held in the frames | `r` |
| Pinch does nothing | Hand below the glass, or above 96 % / below 4 % | Open the window first, then `p 70`, then `u` |
| `Network is down` / `No such device` | `vcan0` gone after WSL restart | Setup again |
| First Frame but no rest | ECU waits for flow control | `cansend vcan0 7E0#3000000000000000` |
| `No module named can` | Wrong Python / venv not active | `source .venv/bin/activate` (or run from where `run_all.sh` works) |
