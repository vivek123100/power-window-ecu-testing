"""Live BCM on SocketCAN: sends BCM_WindowSwitch (0x200) every 20 ms with a real AliveCounter.

Since CR_04 the ECU rejects frames whose AliveCounter does not change, so `cangen` with
fixed data now acts as a FROZEN sender. Use this script to be a healthy BCM - and press
f to freeze it on purpose.

Run (Terminal 3, with vcan0 up and run_live.py running in Terminal 1):
    python3 03_CAN/sim/bcm_live.py

Commands (type the letter, then Enter):
    u  Up held             d  Down held           r  release (= stop the window)
    u 0.8 / d 0.4   hold for 0.8 s / 0.4 s, then release by itself
                    (window speed 25 %/s: 0.4 s = 10 %, 0.8 s = 20 %, 4 s = full travel)
    b  both pressed        f  freeze / unfreeze   s  stop / resume sending (cut wire)
    q  quit
The ECU is hold-to-move: it moves only while the switch is held.
"""
import os
import pathlib
import sys
import threading
import time

import can

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import can_network as net  # noqa: E402

SWITCH = {"u": (1, 0, "Up"), "d": (0, 1, "Down"), "r": (0, 0, "release"), "b": (1, 1, "both")}


def main():
    channel = os.environ.get("CAN_CHANNEL", "vcan0")
    msg = net.load_dbc().get_message_by_name("BCM_WindowSwitch")
    bus = can.Bus(interface=os.environ.get("CAN_INTERFACE", "socketcan"), channel=channel)
    state = {"up": 0, "down": 0, "frozen": False, "sending": True, "counter": 0, "last": None,
             "run": True}

    def sender():
        next_t = time.monotonic()
        while state["run"]:
            if state["sending"]:
                if state["frozen"] and state["last"] is not None:
                    data = state["last"]                         # same frame, same counter
                else:
                    data = msg.encode({"SwUp": state["up"], "SwDown": state["down"],
                                       "AliveCounter": state["counter"]})
                    state["counter"] = (state["counter"] + 1) % 16
                    state["last"] = data
                bus.send(can.Message(arbitration_id=msg.frame_id, data=data, is_extended_id=False))
            next_t += 0.020
            time.sleep(max(0.0, next_t - time.monotonic()))

    threading.Thread(target=sender, daemon=True).start()
    print(f"BCM sending 0x200 on {channel} every 20 ms (switches released).")
    print("Commands: u Up, d Down, r release, u 0.8 = hold 0.8 s, b both, f freeze, "
          "s stop/resume, q quit")
    press = {"id": 0}                    # newer command cancels a pending auto-release

    def auto_release(press_id):
        if press["id"] == press_id:
            state["up"], state["down"] = 0, 0
            print("-> released (hold time over)")

    try:
        for line in sys.stdin:
            parts = line.strip().lower().split()
            cmd = parts[0][:1] if parts else ""
            if cmd in SWITCH:
                press["id"] += 1
                state["up"], state["down"], name = SWITCH[cmd]
                hold = None
                if len(parts) > 1 and cmd in "ud":
                    try:
                        hold = float(parts[1])
                    except ValueError:
                        print("   use: u 0.8  (hold Up for 0.8 s)")
                if hold is not None:
                    threading.Timer(hold, auto_release, args=(press["id"],)).start()
                    name = f"{name} for {hold:g} s (about {hold * 25:.0f} %)"
                if state["frozen"]:
                    print(f"-> {name} (but the sender is FROZEN: frames still repeat the old content)")
                else:
                    print(f"-> {name}")
            elif cmd == "f":
                state["frozen"] = not state["frozen"]
                print("-> FROZEN: same frame and same AliveCounter every 20 ms" if state["frozen"]
                      else "-> unfrozen: counter moves again")
            elif cmd == "s":
                state["sending"] = not state["sending"]
                print("-> sending resumed" if state["sending"] else "-> STOPPED sending (lost message)")
            elif cmd == "q":
                break
            elif cmd:
                print("unknown command - use u, d, r, b, f, s or q")
    except KeyboardInterrupt:
        pass
    finally:
        state["run"] = False
        time.sleep(0.05)
        bus.shutdown()
        print("BCM stopped.")


if __name__ == "__main__":
    main()
