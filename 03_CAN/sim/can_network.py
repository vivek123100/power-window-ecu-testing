"""Virtual CAN network for the power window ECU.

Three nodes on a python-can *virtual* bus (no hardware needed):

  BCM     body control module - sends BCM_WindowSwitch every 20 ms
  DCU     the door control unit = YOUR C CONTROLLER (02_SIL/src/window_ctrl.c)
          + the window plant. It decodes the switch message, works out
          SwMsgAge_ms from when the last message really arrived, runs the
          controller every 10 ms and sends DCU_WindowStatus every 100 ms.
  logger  listens to everything, like candump / CANalyzer trace

Time is simulated (10 ms steps), so every run is exactly repeatable.
Messages are encoded/decoded with cantools from 03_CAN/dbc/power_window.dbc.
"""
import itertools
import pathlib
import sys

import can
import cantools

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_SIL" / "tests"))
import sil_env  # noqa: E402  (C library, plant model, DT)

DBC_FILE = ROOT / "03_CAN" / "dbc" / "power_window.dbc"
DT = sil_env.DT
NEVER_RECEIVED_MS = 1.0e6                     # before the first switch message
MOTOR_STATE = {0: 0, 1: 1, -1: 2}             # motor_cmd -> DBC MotorState
_channels = itertools.count()


def load_dbc():
    return cantools.database.load_file(str(DBC_FILE))


def cycle_time_s(msg):
    """Cycle time from the DBC attribute GenMsgCycleTime (ms -> s)."""
    return msg.dbc.attributes["GenMsgCycleTime"].value / 1000.0


def value_at(table, t):
    return sil_env.value_at(table, t)


# ---------------------------------------------------------------- nodes
class BCM:
    """Sends the driver's switch request every 20 ms (unless silenced)."""

    def __init__(self, bus, db):
        self.bus = bus
        self.msg = db.get_message_by_name("BCM_WindowSwitch")
        self.cycle = cycle_time_s(self.msg)
        self.counter = 0
        self.next_tx = 0.0

    def step(self, t, sw_up, sw_down, silent):
        if silent:
            self.next_tx = t                  # send again as soon as silence ends
            return
        if t >= self.next_tx - 1e-9:
            data = self.msg.encode({"SwUp": int(sw_up), "SwDown": int(sw_down),
                                    "AliveCounter": self.counter})
            self.bus.send(can.Message(arbitration_id=self.msg.frame_id, data=data,
                                      is_extended_id=False))
            self.counter = (self.counter + 1) % 16
            self.next_tx += self.cycle


class DCU:
    """Door control unit: C controller + plant, connected to the bus."""

    def __init__(self, bus, db, lib, plant):
        self.bus, self.lib, self.plant = bus, lib, plant
        self.rx_switch = db.get_message_by_name("BCM_WindowSwitch")
        self.tx_status = db.get_message_by_name("DCU_WindowStatus")
        self.cycle = cycle_time_s(self.tx_status)
        self.sw_up = self.sw_down = False     # last received values
        self.last_rx_t = None
        self.next_tx = 0.0
        self.inp, self.out = sil_env.Inputs(), sil_env.Outputs()
        self.pos_prev, self.cur_prev = plant.p, 0.0
        lib.WindowCtrl_Init()

    def step(self, t, vbat):
        # 1. receive: decode every switch message that arrived
        while True:
            m = self.bus.recv(timeout=0)
            if m is None:
                break
            if m.arbitration_id == self.rx_switch.frame_id:
                sig = self.rx_switch.decode(m.data)
                self.sw_up, self.sw_down = bool(sig["SwUp"]), bool(sig["SwDown"])
                self.last_rx_t = t

        age_ms = (NEVER_RECEIVED_MS if self.last_rx_t is None
                  else (t - self.last_rx_t) * 1000.0)

        # 2. 10 ms task: run the C controller, then the plant
        self.inp.sw_up, self.inp.sw_down = self.sw_up, self.sw_down
        self.inp.pos_pct, self.inp.current_a = self.pos_prev, self.cur_prev
        self.inp.vbat_v, self.inp.sw_msg_age_ms = vbat, age_ms
        self.lib.WindowCtrl_Step(self.inp, self.out)
        pos, cur = self.plant.step(self.out.motor_cmd)
        self.pos_prev, self.cur_prev = pos, cur

        # 3. send the status message every 100 ms (REQ_12)
        if t >= self.next_tx - 1e-9:
            data = self.tx_status.encode({
                "WindowPos": round(pos * 2) / 2,   # DBC resolution 0.5 %
                "MotorState": MOTOR_STATE[self.out.motor_cmd],
                "PinchFlag": int(self.out.pinch_flag),
                "DTC_SwitchTimeout": int(self.out.dtc_switch_timeout),
                "DTC_MotorOverrun": int(self.out.dtc_motor_overrun),
                "CtrlState": self.out.state,
            })
            self.bus.send(can.Message(arbitration_id=self.tx_status.frame_id, data=data,
                                      is_extended_id=False))
            self.next_tx += self.cycle
        return age_ms


# ---------------------------------------------------------------- run
class CanTrace:
    """Everything that happened in one run."""

    def __init__(self, db):
        self.db = db
        self.frames = []          # (t, can_id, bytes) - like a candump log
        self.ecu = []             # (t, motor_cmd, state, pos, sw_msg_age_ms) every 10 ms

    def frames_of(self, name):
        frame_id = self.db.get_message_by_name(name).frame_id
        return [(t, d) for t, i, d in self.frames if i == frame_id]

    def decoded(self, name):
        msg = self.db.get_message_by_name(name)
        return [(t, msg.decode(d, decode_choices=False)) for t, d in self.frames_of(name)]

    def ecu_at(self, t):
        return max((row for row in self.ecu if row[0] <= t + 1e-6), key=lambda r: r[0])

    def write_candump(self, path):
        """Save in candump format: (time) vcan0 ID#DATA"""
        with open(path, "w") as f:
            for t, i, d in self.frames:
                f.write(f"({t:010.3f}) vcan0 {i:03X}#{d.hex().upper()}\n")


def run_network(lib, stop_time=5.0, sw_up=((0, 0), (1, 1)), sw_down=((0, 0),),
                vbat=12.0, bcm_silent=None, init_pos=50.0, obstacle_active=False,
                obstacle_pos=70.0, stall_current=10.0):
    """Run the virtual network.

    bcm_silent: (t_start, t_end) - the BCM stops sending in this window
                (fault injection: lost CAN message, REQ_09).
    """
    db = load_dbc()
    channel = f"pw_vcan_{next(_channels)}"    # own channel per run: no cross-talk
    buses = [can.Bus(interface="virtual", channel=channel) for _ in range(3)]
    bcm_bus, dcu_bus, log_bus = buses
    try:
        plant = sil_env.WindowPlant(init_pos, obstacle_active, obstacle_pos, stall_current)
        bcm, dcu = BCM(bcm_bus, db), DCU(dcu_bus, db, lib, plant)
        tr = CanTrace(db)

        for k in range(int(round(stop_time / DT)) + 1):
            t = round(k * DT, 2)
            silent = bcm_silent is not None and bcm_silent[0] <= t < bcm_silent[1]
            bcm.step(t, value_at(sw_up, t) > 0.5, value_at(sw_down, t) > 0.5, silent)
            age = dcu.step(t, vbat)

            while True:                       # logger: record all frames
                m = log_bus.recv(timeout=0)
                if m is None:
                    break
                tr.frames.append((t, m.arbitration_id, bytes(m.data)))
            tr.ecu.append((t, dcu.out.motor_cmd, dcu.out.state, dcu.pos_prev, age))
        return tr
    finally:
        for b in buses:
            b.shutdown()
