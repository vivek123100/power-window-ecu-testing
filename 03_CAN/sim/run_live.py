"""Live demo on SocketCAN: the window ECU runs in real time on vcan0 and YOU are the BCM.

Terminal 1:  CAN_INTERFACE=socketcan python3 03_CAN/sim/run_live.py
Terminal 2:  candump -ta vcan0                       (watch all frames)
Terminal 3:  python3 03_CAN/sim/bcm_live.py  (you are the BCM), cansend for diagnostics

The ECU prints when its status changes, and every 0.5 s while the motor runs.
Commands typed here (Terminal 1) change the window model - the "real world":
    p 70   put an obstacle (a hand) at 70 %      p   remove the obstacle
    w      show where the window is now
Since CR_01 the ECU stores U0140-00 if no switch frame arrives within 500 ms of
start-up: start bcm_live.py right away, or clear the DTC with UDS afterwards.
"""
import os
import sys
import threading

import can_network as net
import sil_env

STATE = ["IDLE", "MOVING_UP", "MOVING_DOWN", "PINCH_REVERSE", "WAIT_RELEASE", "ERROR"]
MOTOR = {0: "Stop", 1: "Up", 2: "Down"}
PRINT_WHILE_MOVING_S = 0.5
HELP = """
Window ECU running on {ch} for {dur:.0f} s.
Note: no fresh switch frame within 0.5 s -> ERROR + U0140 (CR_01). Start the BCM right away.

Here (Terminal 1) - the window model / real world:
    p 70  obstacle (hand) at 70 %    p  remove obstacle    w  where is the window?
  Pinch demo: p 70, then hold Up below 70 % -> PINCH_REVERSE, back 20 %, WAIT_RELEASE (then r)

Terminal 3 - be the BCM (real AliveCounter, CR_04):
    python3 03_CAN/sim/bcm_live.py        then type u / d / r / b / f / s + Enter
  r = let go of the switch (stops the window).  u 0.8 = hold Up for 0.8 s (= 20 %)
  f = freeze (frozen sender): after 3 frames U0422-00, after 0.5 s ERROR + U0140-00
  s = stop sending (cut wire / lost message): after 0.5 s ERROR + U0140-00
  Leave ERROR: fresh frames AND both switches released (r). DTCs stay stored until cleared.

Diagnostics (a 4th terminal):
  Read stored DTCs (UDS 19 02 FF):         cansend {ch} 7E0#031902FFAAAAAAAA
    (two or more DTCs = 11+ bytes: ECU sends a First Frame, then send the flow control)
  Flow control:                            cansend {ch} 7E0#3000000000000000
  Clear DTCs (UDS 14 FF FF FF):            cansend {ch} 7E0#0414FFFFFFAAAAAA
  Read SW version (multi-frame):           cansend {ch} 7E0#0322F195AAAAAAAA
"""


def world_commands(holder):
    """Read obstacle commands from stdin (Terminal 1) while the ECU runs."""
    for line in sys.stdin:
        parts = line.split()
        plant = holder.get("plant")
        if not parts or plant is None:
            continue
        cmd = parts[0].lower()
        if cmd == "p" and len(parts) > 1:
            try:
                pos = float(parts[1])
            except ValueError:
                print("   use: p 70  (obstacle at 70 %)")
                continue
            plant.obstacle_pos, plant.obstacle_active = pos, True
            print(f"   [world] obstacle at {pos:.0f} % (window now at {plant.p:.1f} %)")
        elif cmd == "p":
            plant.obstacle_active = False
            print("   [world] obstacle removed")
        elif cmd == "w":
            print(f"   [world] window at {plant.p:.1f} %, obstacle "
                  f"{'at %.0f %%' % plant.obstacle_pos if plant.obstacle_active else 'none'}")
        else:
            print("   commands here: p 70 (obstacle), p (remove), w (where)")


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
    ch = os.environ.get("CAN_CHANNEL", "vcan0")
    if os.environ.get("CAN_INTERFACE") != "socketcan":
        sys.exit("Run with CAN_INTERFACE=socketcan (and vcan0 up), see the docstring.")
    print(HELP.format(ch=ch, dur=duration))

    import inspect
    if "on_plant" not in inspect.signature(net.run_network).parameters:
        sys.exit("03_CAN/sim/can_network.py is the old version - replace it with the new one.")

    sil_env.build_library()
    lib = sil_env.load_library()
    last = {"key": None, "t": -1.0}
    holder = {}
    threading.Thread(target=world_commands, args=(holder,), daemon=True).start()

    def show(t, s):
        key = (s["MotorState"], s["CtrlState"], s["PinchFlag"],
               s["DTC_SwitchTimeout"], s["DTC_MotorOverrun"], s.get("DTC_SwitchInvalid", 0))
        moving = s["MotorState"] != 0 and t - last["t"] >= PRINT_WHILE_MOVING_S - 1e-6
        if key != last["key"] or moving:
            last["key"], last["t"] = key, t
            print(f"{t:7.2f} s  pos {s['WindowPos']:5.1f} %  motor {MOTOR[s['MotorState']]:4}  "
                  f"state {STATE[s['CtrlState']]:13} pinch {s['PinchFlag']}  "
                  f"DTC timeout {s['DTC_SwitchTimeout']} overrun {s['DTC_MotorOverrun']} "
                  f"invalid {s.get('DTC_SwitchInvalid', 0)}")

    try:
        net.run_network(lib, stop_time=duration, bcm_enabled=False, realtime=True,
                        on_status=show, on_plant=lambda p: holder.update(plant=p))
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
