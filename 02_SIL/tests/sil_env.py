"""SIL test environment for the power window ECU.

- builds the C controller as a shared library (gcc)
- loads it with ctypes so Python can call WindowCtrl_Init / WindowCtrl_Step
- contains a Python copy of the MIL plant model (window, motor current, obstacle)
- runs a closed-loop simulation and returns a trace of all signals

The loop works exactly like the MIL model: every 10 ms the controller reads
Pos/Current from the previous step (Unit Delay), then the plant moves.
"""
import ctypes
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]          # repo root
SRC = ROOT / "02_SIL" / "src"
BUILD = ROOT / "build"
LIB = BUILD / "libwindow_ctrl.so"
DT = 0.01                                                    # 10 ms cycle

# State numbers - same order as the enum in window_ctrl.h
IDLE, MOVING_UP, MOVING_DOWN, PINCH_REVERSE, WAIT_RELEASE, ERROR = range(6)


# ---------------------------------------------------------------- C interface
class Inputs(ctypes.Structure):
    """Must match WindowInputs_t in window_ctrl.h (same order, same types)."""
    _fields_ = [
        ("sw_up", ctypes.c_bool),
        ("sw_down", ctypes.c_bool),
        ("pos_pct", ctypes.c_float),
        ("current_a", ctypes.c_float),
        ("vbat_v", ctypes.c_float),
        ("sw_msg_age_ms", ctypes.c_float),
    ]


class Outputs(ctypes.Structure):
    """Must match WindowOutputs_t in window_ctrl.h."""
    _fields_ = [
        ("motor_cmd", ctypes.c_int8),
        ("pinch_flag", ctypes.c_bool),
        ("dtc_switch_timeout", ctypes.c_bool),
        ("dtc_motor_overrun", ctypes.c_bool),
        ("state", ctypes.c_int),
    ]


_built = False


def build_library(coverage=False):
    """Compile window_ctrl.c into a shared library. Warnings are errors.

    Builds only once per test session: SIL and CAN tests share the library
    (rebuilding a library that is already loaded could crash the process).
    """
    global _built
    if _built:
        return
    _built = True
    BUILD.mkdir(exist_ok=True)
    cmd = ["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror",
           "-shared", "-fPIC", f"-I{SRC}", str(SRC / "window_ctrl.c"),
           "-o", str(LIB)]
    if coverage:
        cmd[1:1] = ["--coverage", "-O0"]
    subprocess.run(cmd, check=True)


def load_library():
    lib = ctypes.CDLL(str(LIB))
    lib.WindowCtrl_Init.argtypes = []
    lib.WindowCtrl_Init.restype = None
    lib.WindowCtrl_Step.argtypes = [ctypes.POINTER(Inputs), ctypes.POINTER(Outputs)]
    lib.WindowCtrl_Step.restype = None
    return lib


# ---------------------------------------------------------------- Plant model
class WindowPlant:
    """Python copy of the MIL plant (MATLAB Function block WindowPlant)."""

    SPEED = 25.0          # % per second -> full travel in 4 s
    FREE_CURRENT = 2.0    # A

    def __init__(self, init_pos=50.0, obstacle_active=False,
                 obstacle_pos=70.0, stall_current=10.0):
        self.p = float(init_pos)
        self.obstacle_active = obstacle_active
        self.obstacle_pos = obstacle_pos
        self.stall_current = stall_current

    def step(self, motor_cmd):
        cmd = float(motor_cmd)
        p_new = self.p + cmd * self.SPEED * DT
        blocked = False

        if (cmd > 0 and self.obstacle_active and self.p <= self.obstacle_pos
                and p_new >= self.obstacle_pos):
            p_new, blocked = self.obstacle_pos, True       # hand in the window

        if p_new >= 100.0:
            p_new, blocked = 100.0, cmd > 0                # top end stop
        elif p_new <= 0.0:
            p_new, blocked = 0.0, cmd < 0                  # bottom end stop

        if cmd == 0:
            current = 0.0
        elif blocked:
            current = self.stall_current
        else:
            current = self.FREE_CURRENT

        self.p = p_new
        return self.p, current


# ---------------------------------------------------------------- Simulation
def value_at(table, t):
    """Input tables use the MIL format [(time, value), ...]: hold last value."""
    v = table[0][1]
    for t_i, v_i in table:
        if t >= t_i - 1e-9:
            v = v_i
    return v


def simulate(lib, stop_time=12.0, sw_up=((0, 0), (1, 1)), sw_down=((0, 0),),
             vbat=((0, 12.0),), msg_age=((0, 0.0),), init_pos=50.0,
             obstacle_active=False, obstacle_pos=70.0, stall_current=10.0,
             pos_stuck_from=None):
    """Run one closed-loop test and return a Trace.

    pos_stuck_from: fault injection - from this time on, the position sensor
    freezes at its last value (the window still moves physically).
    """
    plant = WindowPlant(init_pos, obstacle_active, obstacle_pos, stall_current)
    pos_prev, cur_prev = float(init_pos), 0.0               # Unit Delay states
    inp, out = Inputs(), Outputs()
    tr = Trace()
    stuck_value = None

    lib.WindowCtrl_Init()
    for k in range(int(round(stop_time / DT)) + 1):
        t = round(k * DT, 2)
        inp.sw_up = value_at(sw_up, t) > 0.5
        inp.sw_down = value_at(sw_down, t) > 0.5
        inp.vbat_v = value_at(vbat, t)
        inp.sw_msg_age_ms = value_at(msg_age, t)
        inp.pos_pct = pos_prev
        if pos_stuck_from is not None and t >= pos_stuck_from - 1e-9:
            if stuck_value is None:
                stuck_value = pos_prev
            inp.pos_pct = stuck_value                       # sensor stuck
        inp.current_a = cur_prev

        lib.WindowCtrl_Step(ctypes.byref(inp), ctypes.byref(out))
        pos, cur = plant.step(out.motor_cmd)

        tr.add(t, out, pos, cur)
        pos_prev, cur_prev = pos, cur
    return tr


class Trace:
    """Logged signals of one run, plus helpers like valAt / firstT in MIL."""

    NAMES = ("motor_cmd", "pinch_flag", "dtc_switch_timeout",
             "dtc_motor_overrun", "state", "pos", "current")

    def __init__(self):
        self.t = []
        self.sig = {n: [] for n in self.NAMES}

    def add(self, t, out, pos, cur):
        self.t.append(t)
        self.sig["motor_cmd"].append(out.motor_cmd)
        self.sig["pinch_flag"].append(int(out.pinch_flag))
        self.sig["dtc_switch_timeout"].append(int(out.dtc_switch_timeout))
        self.sig["dtc_motor_overrun"].append(int(out.dtc_motor_overrun))
        self.sig["state"].append(out.state)
        self.sig["pos"].append(pos)
        self.sig["current"].append(cur)

    def val_at(self, name, t):
        """Value at time t (last sample at or before t)."""
        idx = max(i for i, ti in enumerate(self.t) if ti <= t + 1e-6)
        return self.sig[name][idx]

    def first_t(self, name, cond, t0=0.0):
        """First time >= t0 where cond(value) is true, or None."""
        for ti, v in zip(self.t, self.sig[name]):
            if ti >= t0 - 1e-6 and cond(v):
                return ti
        return None

    def values(self, name, after=-1.0):
        return [v for ti, v in zip(self.t, self.sig[name]) if ti > after]
