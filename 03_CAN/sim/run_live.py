"""Live demo on SocketCAN: the window ECU runs in real time on vcan0 and YOU are the BCM.

Terminal 1:  CAN_INTERFACE=socketcan python3 03_CAN/sim/run_live.py
Terminal 2:  candump -ta vcan0                       (watch all frames)
Terminal 3:  send switch frames / diagnostic requests with cansend (see below)

The ECU only prints when its status changes.
Since CR_01 the ECU stores U0140-00 if no switch frame arrives within 500 ms of
start-up: start cangen right away, or clear the DTC with UDS afterwards.
"""
import os
import sys

import can_network as net
import sil_env

STATE = ["IDLE", "MOVING_UP", "MOVING_DOWN", "PINCH_REVERSE", "WAIT_RELEASE", "ERROR"]
MOTOR = {0: "Stop", 1: "Up", 2: "Down"}
HELP = """
Window ECU running on {ch} for {dur:.0f} s.
Note: no switch frame within 0.5 s -> ERROR + DTC (CR_01). Start cangen now, or clear the DTC later.
Try in another terminal:

  Press Up (BCM sends every 20 ms - stop with Ctrl+C = lost message!):
    while true; do cansend {ch} 200#0100; sleep 0.02; done
  Release (both switches 0):
    while true; do cansend {ch} 200#0000; sleep 0.02; done
  Read stored DTCs (UDS 19 02 FF):         cansend {ch} 7E0#031902FFAAAAAAAA
  Clear DTCs (UDS 14 FF FF FF):            cansend {ch} 7E0#0414FFFFFFAAAAAA
  Read SW version (multi-frame!):          cansend {ch} 7E0#0322F195AAAAAAAA
    ... then send the flow control:        cansend {ch} 7E0#3000000000000000
"""


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
    ch = os.environ.get("CAN_CHANNEL", "vcan0")
    if os.environ.get("CAN_INTERFACE") != "socketcan":
        sys.exit("Run with CAN_INTERFACE=socketcan (and vcan0 up), see the docstring.")
    print(HELP.format(ch=ch, dur=duration))

    import inspect
    if "bcm_enabled" not in inspect.signature(net.run_network).parameters:
        sys.exit("03_CAN/sim/can_network.py is the old version - replace it with the new one.")

    sil_env.build_library()
    lib = sil_env.load_library()
    last = {}

    def show(t, s):
        key = (s["MotorState"], s["CtrlState"], s["PinchFlag"],
               s["DTC_SwitchTimeout"], s["DTC_MotorOverrun"])
        if key != last.get("key"):
            last["key"] = key
            print(f"{t:7.2f} s  pos {s['WindowPos']:5.1f} %  motor {MOTOR[s['MotorState']]:4}  "
                  f"state {STATE[s['CtrlState']]:13} pinch {s['PinchFlag']}  "
                  f"DTC timeout {s['DTC_SwitchTimeout']} overrun {s['DTC_MotorOverrun']}")

    try:
        net.run_network(lib, stop_time=duration, bcm_enabled=False, realtime=True,
                        on_status=show)
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
