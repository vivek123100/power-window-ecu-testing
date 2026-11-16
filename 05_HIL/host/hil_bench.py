"""Mini-HIL bench: the PC side of the HIL test.

The ECU firmware (05_HIL/target) runs on its own on an emulated STM32 and is a
node on a CAN bus. This bench plays everything around it, in REAL TIME:

  plant     window + motor model (same model as MIL/SIL), every 10 ms:
            reads the motor command (0x301), sends position/current/voltage (0x300)
  BCM       optional: the door switch, 0x200 every 20 ms with AliveCounter,
            with fault injection (silent = lost message, frozen = stale frames)
  logger    every frame on the bus with a host timestamp, like candump -ta

0x300 / 0x301 stand for the analog and PWM I/O of a real HIL bench (position
sensor, current measurement, battery supply, H-bridge output).

Bus (environment variable HIL_BUS):
  socketcan  (default) Linux SocketCAN, channel HIL_CAN (default vcan0): the ECU is
             connected by Renode's SocketCAN bridge, candump / bcm_live.py see everything
  tcp        TCP CAN bridge inside Renode (port 3457), for PCs without SocketCAN
"""
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
HIL = ROOT / "05_HIL"
ELF = HIL / "target" / "build" / "hil_fw.elf"
sys.path.insert(0, str(ROOT / "02_SIL" / "tests"))   # sil_env: plant model
sys.path.insert(0, str(ROOT / "04_PIL" / "host"))    # pil_target: find_renode
import sil_env      # noqa: E402
import pil_target   # noqa: E402

ID_SWITCH, ID_STATUS, ID_SENSORS, ID_ACTUATORS = 0x200, 0x210, 0x300, 0x301
UDS_REQ, UDS_RESP = 0x7E0, 0x7E8
FLOW_CONTROL = bytes([0x30, 0x00, 0x00]) + bytes([0xAA] * 5)   # continue, no limit, STmin 0
UDS_TIMEOUT_S = 0.5     # tester gives up after P2* (no answer = lost request or dead ECU)
TCP_PORT = 3457
STATE = ["IDLE", "MOVING_UP", "MOVING_DOWN", "PINCH_REVERSE", "WAIT_RELEASE", "ERROR"]


REALTIME_LIMIT_MS = 15.0     # allowed lateness of the test system before a result is not trusted


class HilError(RuntimeError):
    pass


class BenchNotRealTime(HilError):
    """The TEST SYSTEM (emulator or PC) was not real-time: the result says nothing about the ECU."""


# ---------------------------------------------------------------- buses
class Frame:
    def __init__(self, arbitration_id, data, timestamp=None):
        self.arbitration_id = arbitration_id
        self.data = bytes(data)
        self.timestamp = time.monotonic() if timestamp is None else timestamp


class SocketCanBus:
    """python-can on SocketCAN (vcan0)."""

    def __init__(self, channel):
        import can
        self._can = can
        self.bus = can.Bus(interface="socketcan", channel=channel, receive_own_messages=False)

    def send(self, fid, data):
        self.bus.send(self._can.Message(arbitration_id=fid, data=bytes(data), is_extended_id=False))

    def recv(self, timeout):
        """Frames that arrived within timeout, with the kernel's receive timestamp."""
        m = self.bus.recv(timeout=timeout)
        if m is None:
            return []
        mono = m.timestamp - (time.time() - time.monotonic())     # epoch -> monotonic
        return [Frame(m.arbitration_id, m.data, mono)]

    def close(self):
        self.bus.shutdown()


class TcpCanBus:
    """13-byte frames over TCP to tcp_can_bridge.py inside Renode."""

    def __init__(self, port, timeout_s=60):
        t_end = time.monotonic() + timeout_s
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
                break
            except OSError:
                if time.monotonic() > t_end:
                    raise HilError(f"no Renode TCP CAN bridge on port {port}")
                time.sleep(0.2)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.buf = b""
        self.lock = threading.Lock()

    def send(self, fid, data):
        data = bytes(data)
        with self.lock:
            self.sock.sendall(struct.pack("<IB", fid, len(data)) + data.ljust(8, b"\0"))

    def recv(self, timeout):
        self.sock.settimeout(timeout)
        try:
            d = self.sock.recv(65536)
            if d:
                self.buf += d
        except (socket.timeout, BlockingIOError):
            pass
        out = []
        while len(self.buf) >= 13:
            fid, n = struct.unpack("<IB", self.buf[:5])
            out.append(Frame(fid, self.buf[5:5 + n]))
            self.buf = self.buf[13:]
        return out

    def close(self):
        self.sock.close()


# ---------------------------------------------------------------- the ECU (Renode)
def build_firmware():
    if shutil.which("arm-none-eabi-gcc") is None:
        raise HilError("arm-none-eabi-gcc not found: sudo apt install gcc-arm-none-eabi")
    subprocess.run(["make", "-s", "-C", str(HIL / "target")], check=True)


def start_ecu(bus_kind):
    """Power on the ECU: start Renode with the HIL firmware. Returns the process."""
    renode = pil_target.find_renode()
    resc = HIL / "renode" / ("hil_tcp.resc" if bus_kind == "tcp" else "hil_socketcan.resc")
    cmd = (f"$elf=@{ELF}; $board=@{HIL / 'renode' / 'hil_board.resc'}; "
           f"$bridge=@{HIL / 'renode' / 'tcp_can_bridge.py'}; ")
    if bus_kind != "tcp":
        cmd += f'$canif="{os.environ.get("HIL_CAN", "vcan0")}"; '
    cmd += f"include @{resc}"
    return subprocess.Popen([renode, "--disable-gui", "--plain", "--hide-log", "-P", "-1", "-e", cmd],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop_ecu(proc):
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------- the bench
def _at(schedule, t, default):
    """schedule: [(t, value), ...] - hold the last value (MIL format), or a function of t."""
    if schedule is None:
        return default
    if callable(schedule):
        return schedule(t)
    v = default
    for t_i, v_i in schedule:
        if t >= t_i - 1e-9:
            v = v_i
    return v


class HilBench:
    """Real-time plant + BCM + logger around the ECU.

    Times in schedules are seconds since bench start (= ECU power-on).
    """

    def __init__(self, sw_up=((0, 0),), sw_down=((0, 0),), vbat=((0, 12.0),),
                 bcm=True, bcm_silent=None, bcm_frozen=None, init_pos=50.0,
                 obstacle_pos=None, stall_current=10.0, bus=None, ecu=True, verbose=False,
                 diag=(), sensors_silent=None):
        self.sw_up, self.sw_down, self.vbat = sw_up, sw_down, vbat
        self.bcm, self.bcm_silent, self.bcm_frozen = bcm, bcm_silent, bcm_frozen
        self.plant = sil_env.WindowPlant(init_pos, obstacle_pos is not None,
                                         obstacle_pos if obstacle_pos is not None else 70.0,
                                         stall_current)
        self.bus_kind = bus or os.environ.get("HIL_BUS", "socketcan")
        self.with_ecu, self.verbose = ecu, verbose
        self.motor_cmd, self.ecu_state = 0, None
        self.frames = []            # (t, id, data) - everything seen on the bus
        self.sent = []              # (t, id, data) - what the bench sent
        self.jitter_ms = []         # lateness of each 10 ms cycle
        self.counter, self.last_bcm = 0, None
        self._run, self._thread, self.proc, self.bus, self.t0 = False, None, None, None, None
        self.on_status = None       # optional callback(t, decoded 0x210)
        self.diag = sorted(diag)    # [(t, request bytes)] - UDS tester requests
        self.sensors_silent = sensors_silent   # (t0, t1): no 0x300 frames (sensor wire cut)
        self.uds_log = []           # (t_request, request, t_first_response_frame, response)
        self._uds_cur = None        # [t_req, req, t_first, expected_len, buffer]

    # ------------------------------------------------------------ start / stop
    def start(self, wait_for_ecu=True, timeout_s=60):
        if self.with_ecu:
            build_firmware()
            self.proc = start_ecu(self.bus_kind)
        if self.bus_kind == "tcp":
            self.bus = TcpCanBus(TCP_PORT, timeout_s)
        else:
            self.bus = SocketCanBus(os.environ.get("HIL_CAN", "vcan0"))
        if self.with_ecu and wait_for_ecu:
            self._wait_for_first_frame(timeout_s)
        self.t0 = time.monotonic()  # t = 0: the ECU has just started
        self._run = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _wait_for_first_frame(self, timeout_s):
        t_end = time.monotonic() + timeout_s
        while time.monotonic() < t_end:
            if any(f.arbitration_id == ID_ACTUATORS for f in self.bus.recv(0.05)):
                return
        raise HilError("the ECU sends nothing (no 0x301 frame): is Renode running and the bus up?")

    def stop(self):
        self._run = False
        for th in (self._thread, getattr(self, "_reader", None)):
            if th is not None:
                th.join(timeout=2)
        stop_ecu(self.proc)
        if self.bus is not None:
            self.bus.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def now(self):
        return time.monotonic() - self.t0

    def run_for(self, seconds):
        t_end = self.t0 + seconds
        while time.monotonic() < t_end:
            time.sleep(0.01)

    # ------------------------------------------------------------ 10 ms real-time loop
    def _send(self, t, fid, data):
        self.bus.send(fid, data)
        self.sent.append((t, fid, bytes(data)))

    def _read_loop(self):
        """Receive thread: timestamps every frame as soon as it arrives (like candump -ta)."""
        while self._run:
            for f in self.bus.recv(0.05):
                ft = f.timestamp - self.t0
                self.frames.append((ft, f.arbitration_id, f.data))
                if f.arbitration_id == ID_ACTUATORS and len(f.data) >= 2:
                    self.motor_cmd = struct.unpack("<b", f.data[:1])[0]
                    self.ecu_state = f.data[1]
                elif f.arbitration_id == ID_STATUS and self.on_status is not None:
                    self.on_status(ft, decode_status(f.data))
                elif f.arbitration_id == UDS_RESP:
                    self._uds_rx(ft, f.data)

    # ------------------------------------------------------------ UDS tester (ISO-TP)
    def _uds_rx(self, t, d):
        cur = self._uds_cur
        if cur is None or not d:
            return                                   # not waiting: ignore (TC_68 lesson)
        if cur[2] is None:
            cur[2] = t                               # first response frame -> P2 time
        kind = d[0] >> 4
        if kind == 0:                                # Single Frame
            self._uds_done(bytes(d[1:1 + (d[0] & 0x0F)]))
        elif kind == 1:                              # First Frame -> send Flow Control
            cur[3] = ((d[0] & 0x0F) << 8) | d[1]
            cur[4] = bytes(d[2:8])
            self._send(t, UDS_REQ, FLOW_CONTROL)
        elif kind == 2 and cur[3]:                   # Consecutive Frame
            cur[4] += bytes(d[1:8])
            if len(cur[4]) >= cur[3]:
                self._uds_done(cur[4][:cur[3]])

    def _uds_done(self, payload):
        t_req, req, t_first = self._uds_cur[:3]
        self.uds_log.append((t_req, req, t_first, payload))
        self._uds_cur = None

    def uds_response(self, request):
        """Last complete answer to a request (bytes) or None."""
        for t_req, req, t_first, resp in reversed(self.uds_log):
            if req == bytes(request):
                return resp
        return None

    def uds_timeouts(self):
        """Requests that got no complete answer within UDS_TIMEOUT_S."""
        return [(t, req) for t, req, t_first, resp in self.uds_log if resp is None]

    def _loop(self):
        k = 0
        while self._run:
            target = self.t0 + k * 0.010
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            t = time.monotonic() - self.t0
            self.jitter_ms.append(max(0.0, (t - k * 0.010) * 1000.0))

            pos, cur = self.plant.step(self.motor_cmd)    # 1. plant, 10 ms (latest motor command)
            vbat = float(_at(self.vbat, t, 12.0))
            if not (self.sensors_silent and self.sensors_silent[0] <= t < self.sensors_silent[1]):
                self._send(t, ID_SENSORS, struct.pack(    # 2. sensors to the ECU
                    "<HHH", int(round(pos * 100)), int(round(cur * 100)), int(round(vbat * 100))))

            cur = self._uds_cur                           # 4. tester: timeout first
            if cur is not None and t - cur[0] > UDS_TIMEOUT_S:
                self.uds_log.append((cur[0], cur[1], cur[2], None))   # None = no (complete) answer
                self._uds_cur = None
            if self._uds_cur is None and self.diag and self.diag[0][0] <= t:
                _, req = self.diag.pop(0)
                req = bytes(req)
                self._uds_cur = [t, req, None, 0, b""]
                self._send(t, UDS_REQ, bytes([len(req)]) + req + bytes([0xAA] * (7 - len(req))))

            if self.bcm and k % 2 == 0:                   # 3. BCM, every 20 ms
                silent = self.bcm_silent is not None and self.bcm_silent[0] <= t < self.bcm_silent[1]
                frozen = self.bcm_frozen is not None and self.bcm_frozen[0] <= t < self.bcm_frozen[1]
                if not silent:
                    if frozen and self.last_bcm is not None:
                        data = self.last_bcm               # same frame, same counter
                    else:
                        up = int(_at(self.sw_up, t, 0) > 0.5)
                        down = int(_at(self.sw_down, t, 0) > 0.5)
                        data = bytes([up | (down << 1), self.counter & 0x0F])
                        self.counter = (self.counter + 1) % 16
                        self.last_bcm = data
                    self._send(t, ID_SWITCH, data)
            k += 1

    # ------------------------------------------------------------ evaluation helpers
    def of(self, fid, t_from=0.0):
        return [(t, d) for t, i, d in self.frames if i == fid and t >= t_from]

    def actuators(self, t_from=0.0):
        """[(t, motor_cmd, state, step_ticks)] from 0x301."""
        return [(t, struct.unpack("<b", d[:1])[0], d[1], d[2] | (d[3] << 8))
                for t, d in self.of(ID_ACTUATORS, t_from)]

    def statuses(self, t_from=0.0):
        return [(t, decode_status(d)) for t, d in self.of(ID_STATUS, t_from)]

    def first(self, rows, cond, t_from=0.0):
        return next((r for r in rows if r[0] >= t_from and cond(r)), None)

    def rx_overruns(self):
        """Lost CAN frames reported by the ECU (0x301 byte 4)."""
        return max((d[4] for _, d in self.of(ID_ACTUATORS) if len(d) >= 5), default=0)

    def max_step_ticks(self):
        return max((r[3] for r in self.actuators()), default=0)

    # ------------------------------------------------------------ test-system health
    def stall_ms(self, t_from, t_to):
        """Worst real-time violation of the TEST SYSTEM in [t_from, t_to]:
        - the ECU's 10 ms frames (0x301) arrive late -> the emulator stalled
        - the bench's own 10 ms loop ran late         -> the PC stalled
        Returns the extra delay in ms beyond the 10 ms cycle (0 = perfect)."""
        ts = [t for t, _ in self.of(ID_ACTUATORS) if t_from - 0.05 <= t <= t_to + 0.05]
        gaps = [(b - a) * 1000.0 - 10.0 for a, b in zip(ts, ts[1:])]
        k0, k1 = int(t_from / 0.010), int(t_to / 0.010) + 1
        late = self.jitter_ms[k0:k1]
        if not ts:
            return float("inf")
        return max(gaps + late + [0.0])

    def require_realtime(self, t_from, t_to, limit_ms=REALTIME_LIMIT_MS):
        """Raise BenchNotRealTime if the test system stalled during the measurement."""
        s = self.stall_ms(t_from, t_to)
        if s > limit_ms:
            raise BenchNotRealTime(f"test bench not real-time in {t_from:.2f}-{t_to:.2f} s: "
                                   f"{s:.0f} ms stall (limit {limit_ms} ms)")
        return s


def dtc_names(resp):
    """59 02 09 [C1 40 00 08]... -> ['U0140-00', ...]"""
    out, body = [], resp[3:]
    for i in range(0, len(body) - 3, 4):
        c = body[i:i + 3]
        out.append(f"{'PCBU'[c[0] >> 6]}{(c[0] >> 4) & 3}{c[0] & 0xF:X}{c[1]:02X}-{c[2]:02X}")
    return out


def decode_status(d):
    """DCU_WindowStatus 0x210, same layout as 03_CAN/dbc/power_window.dbc."""
    return {
        "WindowPos": d[0] * 0.5,
        "MotorState": d[1] & 0x03,
        "PinchFlag": (d[1] >> 2) & 1,
        "DTC_SwitchTimeout": (d[1] >> 3) & 1,
        "DTC_MotorOverrun": (d[1] >> 4) & 1,
        "DTC_SwitchInvalid": (d[1] >> 5) & 1,
        "CtrlState": d[2] & 0x07,
    }
