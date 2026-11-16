# tcp_can_bridge.py - runs INSIDE Renode (IronPython 2.7).
#
# A tiny CAN bridge over TCP for PCs without SocketCAN (GitHub Actions runners,
# containers, Windows). With SocketCAN (WSL/Linux + vcan0) use Renode's own
# CreateSocketCANBridge instead - see hil.resc.
#
# Each CAN frame on the TCP stream = 13 bytes:  u32 id (little endian), u8 dlc, 8 data bytes.
# Frames the ECU sends (can1.FrameSent) go to the client. Frames from the client are
# delivered to can1 at least FRAME_GAP_US apart in virtual time, like on a real bus
# (an 8-byte frame takes ~0.25 ms at 500 kbit/s). Without this, frames that queued up
# while the emulator was busy would all arrive in the same instant and overflow the
# 3-deep hardware FIFO - something a real bus can't do (V&V re-run, CR_05).
import clr
for _asm in ("System.Net.Primitives", "System.Net.Sockets", "System.Threading.Thread"):
    clr.AddReference(_asm)          # .NET assemblies are not loaded by default
from System import Array, Byte, Action, BitConverter
from System.Net import IPAddress
from System.Net.Sockets import TcpListener
from System.Threading import Thread, ThreadStart
from Antmicro.Renode.Core.CAN import CANMessageFrame
from Antmicro.Renode.Time import TimeStamp, TimeInterval

FRAME_LEN = 13
FRAME_GAP_US = 250


def start_tcp_can_bridge(machine, can_name, port):
    can = machine[can_name]
    state = {"stream": None}
    listener = TcpListener(IPAddress.Loopback, port)
    listener.Start()

    def on_sent(frame):
        stream = state["stream"]
        if stream is None:
            return
        buf = Array.CreateInstance(Byte, FRAME_LEN)
        idb = BitConverter.GetBytes(int(frame.Id))
        for i in range(4):
            buf[i] = idb[i]
        n = min(len(frame.Data), 8)
        buf[4] = n
        for i in range(n):
            buf[5 + i] = frame.Data[i]
        try:
            stream.Write(buf, 0, FRAME_LEN)
        except Exception:
            state["stream"] = None

    can.FrameSent += on_sent

    pace = {"next_us": 0.0}

    def schedule(frame):
        # runs in the emulation thread: place the frame on the virtual time line
        now = machine.LocalTimeSource.ElapsedVirtualTime.TotalMicroseconds
        at = max(now, pace["next_us"])
        pace["next_us"] = at + FRAME_GAP_US
        delay = TimeInterval.FromMicroseconds(int(at - now))
        machine.ScheduleAction(delay, Action[TimeInterval](lambda t: can.OnFrameReceived(frame)),
                               "tcp_can_rx")

    def deliver(frame):
        machine.LocalTimeSource.ExecuteInNearestSyncedState(
            Action[TimeStamp](lambda ts: schedule(frame)), False)

    def serve():
        while True:
            client = listener.AcceptTcpClient()
            client.NoDelay = True
            stream = client.GetStream()
            state["stream"] = stream
            buf = Array.CreateInstance(Byte, FRAME_LEN)
            try:
                while True:
                    got = 0
                    while got < FRAME_LEN:
                        r = stream.Read(buf, got, FRAME_LEN - got)
                        if r == 0:
                            raise IOError("closed")
                        got += r
                    fid = BitConverter.ToUInt32(buf, 0)
                    n = min(int(buf[4]), 8)
                    data = Array.CreateInstance(Byte, n)
                    for i in range(n):
                        data[i] = buf[5 + i]
                    deliver(CANMessageFrame(fid, data, False, False, False, False))
            except Exception:
                state["stream"] = None
                client.Close()

    t = Thread(ThreadStart(serve))
    t.IsBackground = True
    t.Start()
    print("TCP CAN bridge on port %d <-> %s" % (port, can_name))
