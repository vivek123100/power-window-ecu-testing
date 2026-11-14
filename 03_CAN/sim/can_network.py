"""Virtual CAN network for the power window ECU.

Three nodes on a python-can *virtual* bus (no hardware needed):

  BCM     body control module - sends BCM_WindowSwitch every 20 ms
  DCU     the door control unit = YOUR C CONTROLLER (02_SIL/src/window_ctrl.c)
          + the window plant. It decodes the switch message, works out
          SwMsgAge_ms from when the last message really arrived, runs the
          controller every 10 ms and sends DCU_WindowStatus every 100 ms.
  tester  diagnostic tester (UDS over ISO-TP on 0x7E0 / 0x7E8), like a workshop tool
  logger  listens to everything, like candump / CANalyzer trace

Time is simulated (10 ms steps), so every run is exactly repeatable.
Messages are encoded/decoded with cantools from 03_CAN/dbc/power_window.dbc.

Bus choice (environment variables):
  default                    python-can "virtual" bus inside this program (tests, CI)
  CAN_INTERFACE=socketcan    Linux SocketCAN, channel CAN_CHANNEL (default vcan0):
                             candump / cansend / Wireshark see the traffic
"""
import itertools
import os
import pathlib
import sys
import time

import can
import cantools

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_SIL" / "tests"))
import sil_env  # noqa: E402  (C library, plant model, DT)
import uds      # noqa: E402  (UDS server, tester, ISO-TP)

DBC_FILE = ROOT / "03_CAN" / "dbc" / "power_window.dbc"
DT = sil_env.DT
MOTOR_STATE = {0: 0, 1: 1, -1: 2}             # motor_cmd -> DBC MotorState
_channels = itertools.count()


def make_buses(n):
    """Create n bus connections that all see each other's frames."""
    interface = os.environ.get("CAN_INTERFACE", "virtual")
    if interface == "virtual":
        channel = f"pw_vcan_{next(_channels)}"    # own channel per run: no cross-talk
    else:
        channel = os.environ.get("CAN_CHANNEL", "vcan0")
    return [can.Bus(interface=interface, channel=channel) for _ in range(n)]


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
        self.last_rx_t = 0.0                  # option A (CR_01): age counts from power-on
        self.next_tx = 0.0
        self.inp, self.out = sil_env.Inputs(), sil_env.Outputs()
        self.pos_prev, self.cur_prev = plant.p, 0.0
        self.uds = uds.UdsServer(self)
        lib.WindowCtrl_Init()

    def clear_dtcs(self):
        """Called by UDS 0x14: clears the stored DTCs in the C controller."""
        self.lib.WindowCtrl_ClearDtcs()

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
            elif m.arbitration_id == uds.REQ_ID:                  # diagnostics
                for frame in self.uds.on_frame(bytes(m.data)):
                    self.bus.send(can.Message(arbitration_id=uds.RESP_ID, data=frame,
                                              is_extended_id=False))

        age_ms = (t - self.last_rx_t) * 1000.0

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
                obstacle_pos=70.0, stall_current=10.0, diag_requests=(),
                bcm_enabled=True, realtime=False, on_status=None):
    """Run the virtual network.

    bcm_silent:    (t_start, t_end) - the BCM stops sending in this window
                   (fault injection: lost CAN message, REQ_09).
    diag_requests: [(time, request_bytes), ...] sent by the diagnostic tester,
                   e.g. [(1.0, bytes([0x22, 0xF1, 0x95]))]. Responses: tr.tester.log
    bcm_enabled:   False = no simulated BCM; switch frames must come from outside
                   (e.g. cansend on vcan0)
    realtime:      True = wait 10 ms per step (for live SocketCAN demos)
    on_status:     optional callback(t, decoded_status) for every status frame sent
    """
    db = load_dbc()
    status_msg = db.get_message_by_name("DCU_WindowStatus")
    buses = make_buses(4)
    bcm_bus, dcu_bus, log_bus, tester_bus = buses
    try:
        plant = sil_env.WindowPlant(init_pos, obstacle_active, obstacle_pos, stall_current)
        bcm, dcu = BCM(bcm_bus, db), DCU(dcu_bus, db, lib, plant)
        tester = uds.Tester(list(diag_requests))
        tr = CanTrace(db)
        tr.tester = tester

        t_start = time.monotonic()
        for k in range(int(round(stop_time / DT)) + 1):
            t = round(k * DT, 2)
            if realtime:                      # keep pace with the wall clock
                time.sleep(max(0.0, t_start + t - time.monotonic()))
            silent = (not bcm_enabled or
                      (bcm_silent is not None and bcm_silent[0] <= t < bcm_silent[1]))
            bcm.step(t, value_at(sw_up, t) > 0.5, value_at(sw_down, t) > 0.5, silent)

            responses = []                    # tester: read 0x7E8, send 0x7E0
            while True:
                m = tester_bus.recv(timeout=0)
                if m is None:
                    break
                if m.arbitration_id == uds.RESP_ID:
                    responses.append(bytes(m.data))
            for frame in tester.step(t, responses):
                tester_bus.send(can.Message(arbitration_id=uds.REQ_ID, data=frame,
                                            is_extended_id=False))

            age = dcu.step(t, vbat)

            while True:                       # logger: record all frames
                m = log_bus.recv(timeout=0)
                if m is None:
                    break
                tr.frames.append((t, m.arbitration_id, bytes(m.data)))
                if on_status is not None and m.arbitration_id == status_msg.frame_id:
                    on_status(t, status_msg.decode(bytes(m.data), decode_choices=False))
            tr.ecu.append((t, dcu.out.motor_cmd, dcu.out.state, dcu.pos_prev, age))
        return tr
    finally:
        for b in buses:
            b.shutdown()
