"""PIL host side: talks to the controller running on the (emulated) STM32.

PilTarget has the SAME functions as the ctypes library used in SIL
(WindowCtrl_Init, WindowCtrl_Step, WindowCtrl_ClearDtcs, E2E_*). So the existing
SIL and CAN tests run unchanged - only the controller now executes on the
target processor, compiled by the target compiler (arm-none-eabi-gcc).

    TARGET=pil pytest 02_SIL/tests 03_CAN/tests

Renode is started automatically (headless) and stopped after the tests.
Settings (environment variables):
    RENODE      path to the renode program        (default: "renode" on PATH)
    PIL_PORT    TCP port of the emulated UART     (default: 3456)
    PIL_HOST    connect to an already running target instead of starting Renode
                (e.g. a real board through a serial-to-TCP bridge) - later, real hardware
"""
import atexit
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PIL = ROOT / "04_PIL"
ELF = PIL / "target" / "build" / "pil_fw.elf"
RESC = PIL / "renode" / "pil.resc"

SYNC_REQ, SYNC_RESP = 0xA5, 0x5A


class PilError(RuntimeError):
    pass


class PilTarget:
    """Drop-in replacement for the SIL ctypes library, executed on the target."""

    def __init__(self, sock):
        self.sock = sock
        self.cycles = []                 # CPU cycles of every WindowCtrl_Step call
        self.calls = 0

    # ------------------------------------------------------------ transport
    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise PilError("target closed the connection")
            buf += chunk
        return buf

    def _call(self, cmd, payload=b"", resp_len=0):
        self.calls += 1
        self.sock.sendall(bytes([SYNC_REQ, ord(cmd)]) + payload)
        head = self._recv(2)
        if head[0] != SYNC_RESP or head[1] != ord(cmd):
            raise PilError(f"bad response {head.hex(' ')} to command {cmd!r}")
        return self._recv(resp_len)

    # ------------------------------------------------------------ same API as the C library
    def ping(self):
        return self._call("P", resp_len=4)

    def WindowCtrl_Init(self):
        self._call("I")

    def WindowCtrl_Step(self, inp_ref, out_ref):
        inp = getattr(inp_ref, "_obj", inp_ref)      # accept ctypes.byref(...) like SIL
        out = getattr(out_ref, "_obj", out_ref)
        payload = struct.pack("<BBffff", int(bool(inp.sw_up)), int(bool(inp.sw_down)),
                              inp.pos_pct, inp.current_a, inp.vbat_v, inp.sw_msg_age_ms)
        r = self._call("S", payload, resp_len=9)
        motor, pinch, dto, dov, state, cycles = struct.unpack("<bBBBBI", r)
        out.motor_cmd, out.pinch_flag = motor, bool(pinch)
        out.dtc_switch_timeout, out.dtc_motor_overrun = bool(dto), bool(dov)
        out.state = state
        self.cycles.append(cycles)

    def WindowCtrl_ClearDtcs(self):
        self._call("C")

    def E2E_Init(self):
        self._call("e")

    def E2E_CheckCounter(self, counter):
        return self._call("K", bytes([int(counter) & 0xFF]), resp_len=1)[0]

    def E2E_DtcActive(self):
        return bool(self._call("D", resp_len=1)[0])

    def E2E_ClearDtc(self):
        self._call("X")


# ---------------------------------------------------------------- start / connect
def build_firmware():
    """Build the firmware with make (needs arm-none-eabi-gcc)."""
    if shutil.which("arm-none-eabi-gcc") is None:
        raise PilError("arm-none-eabi-gcc not found: sudo apt install gcc-arm-none-eabi")
    subprocess.run(["make", "-s", "-C", str(PIL / "target")], check=True)


def find_renode():
    """Renode from $RENODE, the PATH, or ~/renode_*-portable/ (portable install)."""
    if os.environ.get("RENODE"):
        return os.environ["RENODE"]
    if shutil.which("renode"):
        return "renode"
    found = sorted(pathlib.Path.home().glob("renode_*-portable/renode"))
    if found:
        return str(found[-1])                     # newest version if several
    raise PilError("Renode not found: install it (04_PIL/README.md) or set RENODE=/path/to/renode")


def _connect(host, port, timeout_s):
    t_end = time.monotonic() + timeout_s
    while True:
        try:
            s = socket.create_connection((host, port), timeout=10)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return s
        except OSError:
            if time.monotonic() > t_end:
                raise PilError(f"no target on {host}:{port}")
            time.sleep(0.2)


def start_target():
    """Build the firmware, start Renode headless, connect and check with a ping."""
    port = int(os.environ.get("PIL_PORT", "3456"))
    host = os.environ.get("PIL_HOST")
    proc = None
    if host is None:
        build_firmware()
        renode = find_renode()
        host = "127.0.0.1"
        proc = subprocess.Popen(
            [renode, "--disable-gui", "--plain", "--hide-log", "-P", "-1",
             "-e", f"$elf=@{ELF}; $port={port}; include @{RESC}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def stop():
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        atexit.register(stop)

    target = PilTarget(_connect(host, port, timeout_s=60))
    if target.ping() != b"PIL1":
        raise PilError("target did not answer the ping")
    return target


_target = None


def get_target():
    """One target for the whole test session (SIL and CAN tests share it)."""
    global _target
    if _target is None:
        _target = start_target()
    return _target


SYSTICK_HZ = int(os.environ.get("PIL_SYSTICK_HZ", "72000000"))   # Renode stm32f4: 72 MHz


def summary(target=None):
    """Execution time of WindowCtrl_Step measured on the target with SysTick."""
    target = target or _target
    if target is None or not target.cycles:
        return "PIL: no WindowCtrl_Step calls"
    c = target.cycles
    worst_us = max(c) / SYSTICK_HZ * 1e6
    return (f"PIL: {target.calls} calls to the target, WindowCtrl_Step {len(c)} times. "
            f"SysTick ticks min {min(c)}, avg {sum(c) / len(c):.0f}, max {max(c)} "
            f"= worst {worst_us:.2f} us of the 10 ms budget ({worst_us / 100:.4f} %). "
            f"Renode is not cycle-accurate: real timing needs a real board.")
