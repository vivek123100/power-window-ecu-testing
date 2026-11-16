"""Live HIL: the ECU firmware on the emulated STM32 is a node on vcan0, and you drive it.

Same 4-terminal demo as 03_CAN/LIVE_DEMO.md - but now the ECU is the FIRMWARE on the
(emulated) chip, not Python. This terminal starts the ECU and plays the plant.

Terminal 1:  python3 05_HIL/host/hil_live.py          (ECU + plant, type commands here)
Terminal 2:  candump -ta vcan0                        (you see 0x200, 0x210, 0x300, 0x301)
Terminal 3:  python3 03_CAN/sim/bcm_live.py           (you are the BCM: u d r f s ...)

Commands here (the real world around the ECU):
    p 70   hand (obstacle) at 70 %      p      remove the hand
    v 8.5  battery voltage 8.5 V        v      back to 12 V
    w      where is the window?         q      quit (switches the ECU off)
"""
import os
import sys
import threading

import hil_bench as hb

MOTOR = {0: "Stop", 1: "Up", 2: "Down"}


def main():
    vbat = {"v": 12.0}
    bench = hb.HilBench(bcm=False, vbat=lambda t: vbat["v"], init_pos=50.0)
    last = {"key": None, "t": -1.0}

    def show(t, s):
        key = (s["MotorState"], s["CtrlState"], s["PinchFlag"], s["DTC_SwitchTimeout"],
               s["DTC_MotorOverrun"], s["DTC_SwitchInvalid"])
        moving = s["MotorState"] != 0 and t - last["t"] >= 0.5 - 1e-6
        if key != last["key"] or moving:
            last["key"], last["t"] = key, t
            print(f"{t:7.2f} s  pos {s['WindowPos']:5.1f} %  motor {MOTOR[s['MotorState']]:4}  "
                  f"state {hb.STATE[s['CtrlState']]:13} pinch {s['PinchFlag']}  "
                  f"DTC timeout {s['DTC_SwitchTimeout']} overrun {s['DTC_MotorOverrun']} "
                  f"invalid {s['DTC_SwitchInvalid']}", flush=True)

    bench.on_status = show
    print(__doc__)
    print("Powering on the ECU (Renode)... start bcm_live.py in Terminal 3 now.")
    if os.environ.get("HIL_BUS", "socketcan") != "socketcan":
        print("Note: HIL_BUS is not socketcan - candump/bcm_live.py will not see this bus.")
    bench.start()
    print("ECU is running on the emulated STM32.\n")
    try:
        for line in sys.stdin:
            parts = line.split()
            if not parts:
                continue
            cmd, arg = parts[0].lower(), (parts[1] if len(parts) > 1 else None)
            plant = bench.plant
            if cmd == "p" and arg:
                plant.obstacle_pos, plant.obstacle_active = float(arg), True
                print(f"   [world] hand at {float(arg):.0f} % (window at {plant.p:.1f} %)")
            elif cmd == "p":
                plant.obstacle_active = False
                print("   [world] hand removed")
            elif cmd == "v":
                vbat["v"] = float(arg) if arg else 12.0
                print(f"   [world] battery {vbat['v']:.1f} V")
            elif cmd == "w":
                print(f"   [world] window at {plant.p:.1f} %, battery {vbat['v']:.1f} V, hand "
                      f"{'at %.0f %%' % plant.obstacle_pos if plant.obstacle_active else 'none'}, "
                      f"worst step {bench.max_step_ticks()} ticks")
            elif cmd == "q":
                break
            else:
                print("   commands: p 70, p, v 8.5, v, w, q")
    except KeyboardInterrupt:
        pass
    finally:
        bench.stop()
        print("ECU switched off.")


if __name__ == "__main__":
    threading.current_thread().name = "hil_live"
    main()
