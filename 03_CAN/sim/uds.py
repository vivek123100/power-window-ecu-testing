"""UDS diagnostics (ISO 14229) over ISO-TP (ISO 15765-2) for the window ECU.

Kept small on purpose so every frame can be read in the trace:

ISO-TP frame types (first nibble of byte 0):
  0x0L  Single Frame       up to 7 data bytes, L = length
  0x1L  First Frame        start of a long message, 12-bit total length
  0x2N  Consecutive Frame  next 7 bytes, N = sequence number 1..F, 0, 1 ...
  0x30  Flow Control       receiver says "continue" (block size 0, STmin 0)

UDS services supported by the DCU (request -> positive response = SID + 0x40):
  0x10 DiagnosticSessionControl   10 01 / 10 03      -> 50 xx 00 32 01 F4
  0x22 ReadDataByIdentifier       22 F1 95 (SW ver)  -> 62 F1 95 'PW-1.0.0'
                                  22 01 00 (window position, live) -> 62 01 00 pp
  0x19 ReadDTCInformation         19 02 FF           -> 59 02 09 [DTC DTC DTC status]...
  0x14 ClearDiagnosticInformation 14 FF FF FF        -> 54
  0x3E TesterPresent              3E 00              -> 7E 00
Negative response: 7F SID NRC  (0x11 service not supported, 0x12 sub-function
not supported, 0x13 wrong length, 0x31 request out of range)
"""

REQ_ID = 0x7E0          # tester -> DCU (physical request)
RESP_ID = 0x7E8         # DCU -> tester
PAD = 0xAA              # padding byte for unused frame bytes

SW_VERSION = b"PW-1.0.0"
DID_SW_VERSION = 0xF195
DID_WINDOW_POS = 0x0100

# DTC numbers (3 bytes: 2 bytes code + 1 byte failure type, SAE J2012 style)
DTC_SWITCH_TIMEOUT = bytes([0xC1, 0x40, 0x00])   # U0140-00: lost communication with BCM
DTC_MOTOR_OVERRUN = bytes([0x93, 0x10, 0x00])    # B1310-00: window motor overrun
STATUS_MASK_AVAILABLE = 0x09                      # testFailed + confirmedDTC
STATUS_CONFIRMED = 0x08

NRC_SERVICE_NOT_SUPPORTED = 0x11
NRC_SUBFUNCTION_NOT_SUPPORTED = 0x12
NRC_WRONG_LENGTH = 0x13
NRC_OUT_OF_RANGE = 0x31


def dtc_name(code3):
    """C1 40 00 -> 'U0140-00' (first 2 bits = letter P/C/B/U)."""
    letter = "PCBU"[code3[0] >> 6]
    return f"{letter}{(code3[0] >> 4) & 0x3}{code3[0] & 0xF:X}{code3[1]:02X}-{code3[2]:02X}"


# ---------------------------------------------------------------- ISO-TP
def pad8(data):
    return bytes(data) + bytes([PAD] * (8 - len(data)))


def isotp_frames(payload):
    """Split a UDS message into ISO-TP frames. Returns (first_frames, consecutive)."""
    if len(payload) <= 7:
        return [pad8(bytes([len(payload)]) + payload)], []
    first = bytes([0x10 | (len(payload) >> 8), len(payload) & 0xFF]) + payload[:6]
    rest, cfs, seq = payload[6:], [], 1
    while rest:
        cfs.append(pad8(bytes([0x20 | seq]) + rest[:7]))
        rest, seq = rest[7:], (seq + 1) & 0xF
    return [first], cfs


class IsoTpReceiver:
    """Rebuilds a message from SF / FF + CF frames."""

    def __init__(self):
        self.buf, self.expected, self.next_seq = b"", 0, 1

    def feed(self, data):
        """Returns ('done', payload), ('send_fc', None) or (None, None)."""
        kind = data[0] >> 4
        if kind == 0:                                     # single frame
            return "done", bytes(data[1:1 + (data[0] & 0xF)])
        if kind == 1:                                     # first frame
            self.expected = ((data[0] & 0xF) << 8) | data[1]
            self.buf, self.next_seq = bytes(data[2:8]), 1
            return "send_fc", None
        if kind == 2:                                     # consecutive frame
            if (data[0] & 0xF) != self.next_seq:
                raise ValueError(f"ISO-TP sequence error: got {data[0] & 0xF}, "
                                 f"expected {self.next_seq}")
            self.next_seq = (self.next_seq + 1) & 0xF
            self.buf += bytes(data[1:8])
            if len(self.buf) >= self.expected:
                return "done", self.buf[:self.expected]
        return None, None


FLOW_CONTROL_CTS = pad8([0x30, 0x00, 0x00])      # continue, no block limit, STmin 0


# ---------------------------------------------------------------- UDS server (in the DCU)
class UdsServer:
    def __init__(self, dcu):
        self.dcu = dcu                     # gives access to outputs, position, C library
        self.session = 0x01                # default session
        self.pending_cf = []               # consecutive frames waiting for flow control
        self.rx = IsoTpReceiver()

    def on_frame(self, data):
        """Handle one frame on REQ_ID. Returns the list of frames to send now."""
        if data[0] >> 4 == 3:                              # flow control from tester
            out, self.pending_cf = self.pending_cf, []
            return out
        status, payload = self.rx.feed(data)
        if status != "done":
            return []
        first, self.pending_cf = isotp_frames(self.handle(payload))
        return first

    def handle(self, req):
        sid = req[0]
        if sid == 0x10:
            if len(req) != 2:
                return self.nrc(sid, NRC_WRONG_LENGTH)
            if req[1] not in (0x01, 0x03):
                return self.nrc(sid, NRC_SUBFUNCTION_NOT_SUPPORTED)
            self.session = req[1]
            return bytes([0x50, req[1], 0x00, 0x32, 0x01, 0xF4])   # P2 50 ms, P2* 5 s
        if sid == 0x22:
            if len(req) != 3:
                return self.nrc(sid, NRC_WRONG_LENGTH)
            did = (req[1] << 8) | req[2]
            if did == DID_SW_VERSION:
                return bytes([0x62, req[1], req[2]]) + SW_VERSION
            if did == DID_WINDOW_POS:
                return bytes([0x62, req[1], req[2], int(round(self.dcu.pos_prev))])
            return self.nrc(sid, NRC_OUT_OF_RANGE)
        if sid == 0x19:
            if len(req) != 3:
                return self.nrc(sid, NRC_WRONG_LENGTH)
            if req[1] != 0x02:
                return self.nrc(sid, NRC_SUBFUNCTION_NOT_SUPPORTED)
            resp = bytes([0x59, 0x02, STATUS_MASK_AVAILABLE])
            out = self.dcu.out
            for active, code in ((out.dtc_switch_timeout, DTC_SWITCH_TIMEOUT),
                                 (out.dtc_motor_overrun, DTC_MOTOR_OVERRUN)):
                if active and (STATUS_CONFIRMED & req[2]):
                    resp += code + bytes([STATUS_CONFIRMED])
            return resp
        if sid == 0x14:
            if len(req) != 4:
                return self.nrc(sid, NRC_WRONG_LENGTH)
            if bytes(req[1:4]) != b"\xFF\xFF\xFF":
                return self.nrc(sid, NRC_OUT_OF_RANGE)
            self.dcu.clear_dtcs()
            return bytes([0x54])
        if sid == 0x3E:
            if len(req) != 2 or req[1] != 0x00:
                return self.nrc(sid, NRC_SUBFUNCTION_NOT_SUPPORTED)
            return bytes([0x7E, 0x00])
        return self.nrc(sid, NRC_SERVICE_NOT_SUPPORTED)

    @staticmethod
    def nrc(sid, code):
        return bytes([0x7F, sid, code])


# ---------------------------------------------------------------- Tester (the workshop tool)
class Tester:
    """Sends UDS requests at given times and collects the responses."""

    def __init__(self, requests):
        self.queue = sorted(requests)      # [(time, request_bytes), ...]
        self.rx = IsoTpReceiver()
        self.current = None                # (t_sent, request)
        self.log = []                      # (t_req, request, t_resp, response)

    def step(self, t, received):
        """received: frames on RESP_ID this step. Returns frames to send."""
        out = []
        for data in received:
            status, payload = self.rx.feed(data)
            if status == "send_fc":
                out.append(FLOW_CONTROL_CTS)
            elif status == "done" and self.current is not None:
                self.log.append((*self.current, t, payload))
                self.current = None
        if self.current is None and self.queue and self.queue[0][0] <= t + 1e-9:
            _, req = self.queue.pop(0)
            frames, _ = isotp_frames(req)  # requests are short: single frame
            out += frames
            self.current = (t, req)
        return out

    def response_to(self, request):
        """Last response to a given request (bytes), or None."""
        for t_req, req, t_resp, resp in reversed(self.log):
            if req == request:
                return resp
        return None
