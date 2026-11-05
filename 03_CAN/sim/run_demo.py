"""Demo: the window ECU on a virtual CAN bus.

Scenario: driver presses Up at 0.5 s. From 1.5 s to 2.5 s the BCM stops
sending (lost CAN message). Expected: the ECU stops the window after 500 ms
without a message (REQ_09) and stores DTC_SwitchTimeout.

Run from the repo root:   python3 03_CAN/sim/run_demo.py
"""
import pathlib

import can_network as net
import sil_env

STATE = ["IDLE", "MOVING_UP", "MOVING_DOWN", "PINCH_REVERSE", "WAIT_RELEASE", "ERROR"]
MOTOR = {0: "Stop", 1: "Up", 2: "Down"}


def main():
    sil_env.build_library()
    lib = sil_env.load_library()
    tr = net.run_network(lib, stop_time=3.5, sw_up=((0, 0), (0.5, 1)), bcm_silent=(1.5, 2.5))

    sw = tr.frames_of("BCM_WindowSwitch")
    st = tr.decoded("DCU_WindowStatus")
    print(f"{len(tr.frames)} frames on the bus: {len(sw)} x BCM_WindowSwitch (0x200), "
          f"{len(st)} x DCU_WindowStatus (0x210)\n")

    gaps = [(t1, t2) for (t1, _), (t2, _) in zip(sw, sw[1:]) if t2 - t1 > 0.05]
    for t1, t2 in gaps:
        print(f"BCM silent: no 0x200 between {t1:.2f} s and {t2:.2f} s ({(t2 - t1) * 1000:.0f} ms)\n")

    print("  time   ID   data         WindowPos  Motor  Pinch  DTC_Timeout  State")
    raw = dict((t, d) for t, d in tr.frames_of("DCU_WindowStatus"))
    for t, s in st:
        print(f"{t:6.2f}  210  {raw[t].hex(' ').upper():11}  {s['WindowPos']:6.1f} %  "
              f"{MOTOR[s['MotorState']]:5}  {s['PinchFlag']:5}  {s['DTC_SwitchTimeout']:11}  "
              f"{STATE[s['CtrlState']]}")

    t_err = next((t for t, cmd, state, pos, age in tr.ecu if state == 5), None)
    if t_err is not None and gaps:
        t_last = gaps[0][0]
        print(f"\nECU entered ERROR at {t_err:.2f} s, "
              f"{(t_err - t_last) * 1000:.0f} ms after the last switch message (limit 500 ms).")

    log = pathlib.Path(__file__).resolve().parents[2] / "reports" / "can" / "demo.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    tr.write_candump(log)
    print(f"candump log written to {log}")


if __name__ == "__main__":
    main()
