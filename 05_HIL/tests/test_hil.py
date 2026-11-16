"""HIL tests: the ECU firmware runs on its own (emulated STM32, real CAN frames),
the bench plays plant + BCM in real time. Everything is measured on the bus.

Run (Ubuntu, vcan0 up):   bash 05_HIL/run_hil.sh
Without SocketCAN:        HIL_BUS=tcp pytest 05_HIL/tests -v
Times: bench start = ECU power-on = 0 s. Tolerances are the requirement limits;
the bench itself must be real-time within 15 ms during each measurement.
"""
from hil_bench import ID_SWITCH, dtc_names

IDLE, MOVING_UP, MOVING_DOWN, PINCH_REVERSE, WAIT_RELEASE, ERROR = range(6)
READ_DTCS = bytes([0x19, 0x02, 0xFF])
CLEAR_DTCS = bytes([0x14, 0xFF, 0xFF, 0xFF])


def switch_frames(b, cond, t_from=0.0):
    """Times the BCM sent a 0x200 frame matching cond(data)."""
    return [t for t, i, d in b.sent if i == ID_SWITCH and t >= t_from and cond(d)]


def test_TC_69_up_reaction_time(hil):
    """REQ_01: Up pressed at 1.0 s -> motor Up on the bus within 50 ms"""
    def check(b):
        t_press = switch_frames(b, lambda d: d[0] & 1)[0]
        b.require_realtime(t_press, t_press + 0.1)
        t_motor = b.first(b.actuators(), lambda r: r[1] == 1, t_press)[0]
        dt = (t_motor - t_press) * 1000
        assert dt <= 50, f"motor Up {dt:.0f} ms after the switch frame"
        return dt
    hil(check, 1.5, sw_up=((0, 0), (1.0, 1)))


def test_TC_70_release_reaction_time(hil):
    """REQ_03: Up released at 1.5 s -> motor Stop within 50 ms"""
    def check(b):
        t_rel = switch_frames(b, lambda d: d[0] == 0, 1.5)[0]
        b.require_realtime(t_rel, t_rel + 0.1)
        t_stop = b.first(b.actuators(), lambda r: r[1] == 0, t_rel)[0]
        assert (t_stop - t_rel) * 1000 <= 50
        assert b.statuses()[-1][1]["CtrlState"] == IDLE
    hil(check, 2.0, sw_up=((0, 0), (1.0, 1), (1.5, 0)))


def test_TC_71_pinch_reversal_and_wait_release(hil):
    """REQ_05/06/13/14: hand at 70 %, Up held -> pinch, reverse >= 20 %, wait for release"""
    def check(b):
        act = b.actuators()
        t_pinch = b.first(act, lambda r: r[2] == PINCH_REVERSE)[0]
        b.require_realtime(t_pinch - 0.1, t_pinch + 0.3)
        st = b.statuses(t_pinch)
        assert any(s["PinchFlag"] == 1 for _, s in st), "PinchFlag never set in 0x210"
        t_wait = b.first(act, lambda r: r[2] == WAIT_RELEASE, t_pinch)[0]
        pos_at_wait = min(s["WindowPos"] for t, s in st if t <= t_wait + 0.1)
        assert pos_at_wait <= 50.5, f"reversed only to {pos_at_wait} % (needs >= 20 %)"
        assert all(r[1] == 0 for r in act if t_wait + 0.02 < r[0] < 3.9), "window moved while Up held"
        t_idle = b.first(act, lambda r: r[2] == IDLE, 4.0)[0]
        assert t_idle - 4.0 < 0.1, "no IDLE after release"
        assert b.statuses(t_idle + 0.15)[0][1]["PinchFlag"] == 0
    hil(check, 4.5, sw_up=((0, 0), (1.0, 1), (4.0, 0)), obstacle_pos=70.0)


def test_TC_72_lost_switch_message_detection_window(hil):
    """REQ_09 (CR_01): BCM silent from 2.0 s while closing -> ERROR 500-520 ms after the last frame"""
    def check(b):
        t_last = max(switch_frames(b, lambda d: True))
        b.require_realtime(t_last, t_last + 0.6)
        t_err = b.first(b.actuators(), lambda r: r[2] == ERROR, t_last)[0]
        dt = (t_err - t_last) * 1000
        assert 500 <= dt <= 520, f"ERROR {dt:.0f} ms after the last switch frame"
        assert b.statuses(t_err + 0.15)[0][1]["DTC_SwitchTimeout"] == 1
        return dt
    hil(check, 3.0, sw_up=((0, 0), (0.5, 1)), init_pos=10.0, bcm_silent=(2.0, 99.0))


def test_TC_73_frozen_sender(hil):
    """REQ_17/18 (CR_04): BCM frozen from 2.0 s ('Up' repeated, same counter) -> U0422 bit, motor stops"""
    def check(b):
        b.require_realtime(1.9, 2.7)
        assert all(s["DTC_SwitchInvalid"] == 0 for t, s in b.statuses() if t < 2.0)
        t_dtc = b.first(b.statuses(2.0), lambda r: r[1]["DTC_SwitchInvalid"] == 1)[0]
        assert t_dtc < 2.2, f"U0422 bit only at {t_dtc:.2f} s"
        t_stop = b.first(b.actuators(2.0), lambda r: r[1] == 0)[0]
        assert t_stop < 2.6, "stale 'Up' frames kept the motor running"
    hil(check, 3.0, sw_up=((0, 0), (0.5, 1)), init_pos=10.0, bcm_frozen=(2.0, 99.0))


def test_TC_74_undervoltage_stops_motor(hil):
    """REQ_08: battery drops to 8.5 V at 1.5 s while closing -> motor Stop within 50 ms"""
    def check(b):
        t_low = next(t for t, i, d in b.sent if i == 0x300 and t >= 1.5)
        b.require_realtime(t_low, t_low + 0.1)
        t_stop = b.first(b.actuators(), lambda r: r[1] == 0, t_low)[0]
        assert (t_stop - t_low) * 1000 <= 50
    hil(check, 2.0, sw_up=((0, 0), (0.5, 1)), init_pos=10.0, vbat=((0, 12.0), (1.5, 8.5)))


def test_TC_75_status_cycle_time(hil):
    """REQ_12: DCU_WindowStatus every 100 ms +-10 ms, measured on the bus for 5 s"""
    def check(b):
        b.require_realtime(0.5, 5.5)
        ts = [t for t, _ in b.statuses(0.5)]
        gaps = [(y - x) * 1000 for x, y in zip(ts, ts[1:])]
        assert len(ts) >= 48
        assert all(90 <= g <= 110 for g in gaps), f"gaps {min(gaps):.0f}-{max(gaps):.0f} ms"
    hil(check, 5.5)


def test_TC_76_up_and_down_together(hil):
    """REQ_11: Down also pressed at 1.5 s while closing -> motor Stop within 50 ms"""
    def check(b):
        t_both = switch_frames(b, lambda d: (d[0] & 3) == 3)[0]
        b.require_realtime(t_both, t_both + 0.1)
        t_stop = b.first(b.actuators(), lambda r: r[1] == 0, t_both)[0]
        assert (t_stop - t_both) * 1000 <= 50
    hil(check, 2.0, sw_up=((0, 0), (0.5, 1)), sw_down=((0, 0), (1.5, 1)), init_pos=10.0)


def test_TC_77_execution_time_budget(hil):
    """Timing: WindowCtrl_Step on the ECU uses far less than its 10 ms task (moving + pinch)"""
    def check(b):
        ticks = b.max_step_ticks()
        assert 0 < ticks < 0.1 * 720000, f"{ticks} ticks (10 ms = 720000 ticks at 72 MHz)"
    hil(check, 2.5, sw_up=((0, 0), (0.5, 1)), obstacle_pos=70.0)


# ---------------------------------------------------------------- UDS on the ECU firmware
def test_TC_78_read_and_clear_dtc_on_target(hil):
    """REQ_15/16: lost switch message -> U0140-00 readable by UDS, 14 FF FF FF clears it"""
    def check(b):
        reads = [r for r in b.uds_log if r[1] == READ_DTCS]
        assert len(reads) == 2, f"answers: {[r[3].hex(' ') for r in b.uds_log]}"
        assert dtc_names(reads[0][3]) == ["U0140-00"]
        assert b.uds_response(CLEAR_DTCS) == bytes([0x54])
        assert dtc_names(reads[1][3]) == []
        assert b.statuses()[-1][1]["DTC_SwitchTimeout"] == 0
    hil(check, 4.0, bcm_silent=(1.0, 1.7),
        diag=[(2.5, READ_DTCS), (3.0, CLEAR_DTCS), (3.5, READ_DTCS)])


def test_TC_79_two_dtcs_multi_frame(hil):
    """REQ_18/15: frozen sender -> U0140-00 + U0422-00 = 11 bytes, sent as FF + FC + CF"""
    def check(b):
        resp = b.uds_response(READ_DTCS)
        assert resp is not None, "no complete answer (ISO-TP multi-frame failed?)"
        assert dtc_names(resp) == ["U0140-00", "U0422-00"]
        frames = [d for t, i, d in b.frames if i == 0x7E8]
        assert frames[0][0] == 0x10 and frames[0][1] == 11, "expected a First Frame, length 11"
        assert any(d[0] == 0x21 for d in frames), "no Consecutive Frame"
    hil(check, 3.0, sw_up=((0, 0), (0.5, 1), (1.8, 0)), init_pos=10.0, bcm_frozen=(1.0, 1.7),
        diag=[(2.5, READ_DTCS)])


def test_TC_80_uds_services_and_p2(hil):
    """REQ_15: SW version (multi-frame), unknown DID, unknown service, TesterPresent; P2 <= 50 ms"""
    requests = [bytes([0x22, 0xF1, 0x95]), bytes([0x22, 0xF1, 0xFF]), bytes([0x31, 0x01, 0x02, 0x03]),
                bytes([0x3E, 0x00]), bytes([0x10, 0x03])]

    def check(b):
        assert b.uds_response(requests[0]) == bytes([0x62, 0xF1, 0x95]) + b"PW-1.0.0"
        assert b.uds_response(requests[1]) == bytes([0x7F, 0x22, 0x31])
        assert b.uds_response(requests[2]) == bytes([0x7F, 0x31, 0x11])
        assert b.uds_response(requests[3]) == bytes([0x7E, 0x00])
        assert b.uds_response(requests[4]) == bytes([0x50, 0x03, 0x00, 0x32, 0x01, 0xF4])
        for t_req, req, t_first, resp in b.uds_log:
            b.require_realtime(t_req, t_first + 0.01)
            assert (t_first - t_req) * 1000 <= 50, f"{req.hex(' ')}: P2 {(t_first - t_req) * 1000:.0f} ms"
    hil(check, 2.5, diag=[(1.0 + 0.2 * i, r) for i, r in enumerate(requests)])
