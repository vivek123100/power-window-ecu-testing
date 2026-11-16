"""CR_04: frozen sender on the CAN bus (REQ_17, REQ_18).

The BCM keeps sending on time, but repeats the same frame (same AliveCounter).
Run:  pytest 03_CAN/tests/test_can_e2e.py -v
"""
import uds
from can_network import run_network

ERROR, MOVING_UP, IDLE = 5, 1, 0
READ_DTCS = bytes([0x19, 0x02, 0xFF])
CLEAR_DTCS = bytes([0x14, 0xFF, 0xFF, 0xFF])


def first(rows, cond):
    return next((r for r in rows if cond(r)), None)


def dtcs_in(resp):
    body = resp[3:]
    return [uds.dtc_name(body[i:i + 3]) for i in range(0, len(body), 4)]


def last_accepted_before(tr, t_freeze):
    return max(t for t, _ in tr.frames_of("BCM_WindowSwitch") if t < t_freeze)


def test_TC_61_frozen_sender_while_moving(ctrl):
    """REQ_17/18: BCM frozen at 2 s while closing -> U0422 after 3 frames, ERROR after 510 ms"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1)), bcm_frozen=(2.0, 4.0), stop_time=4.0)
    frozen_frames = [t for t, _ in tr.frames_of("BCM_WindowSwitch") if 2.0 <= t < 4.0]
    assert len(frozen_frames) > 50, "the BCM must keep sending while frozen"
    t_dtc = first(tr.e2e, lambda r: r[1])[0]
    assert 2.03 <= t_dtc <= 2.07, f"U0422 stored at {t_dtc:.2f} s (3rd stale frame expected ~2.04 s)"
    t_err = first(tr.ecu, lambda r: r[2] == ERROR)[0]
    detect = t_err - last_accepted_before(tr, 2.0)
    assert 0.50 < detect <= 0.52, f"ERROR {detect * 1000:.0f} ms after last fresh frame"


def test_TC_62_frozen_up_does_not_keep_motor_running(ctrl):
    """REQ_17: stale 'Up pressed' frames must not keep the window moving"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1)), bcm_frozen=(2.0, 4.0), stop_time=4.0)
    assert all(cmd == 0 for t, cmd, *_ in tr.ecu if t > 2.55), "motor still running on stale frames"


def test_TC_63_two_stale_frames_no_dtc(ctrl):
    """REQ_18 boundary: only 2 stale frames -> no U0422, window keeps moving"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1)), bcm_frozen=(2.0, 2.04), stop_time=3.0)
    assert tr.e2e[-1][2] == 2, f"expected 2 discarded frames, got {tr.e2e[-1][2]}"
    assert not any(dtc for _, dtc, _ in tr.e2e)
    assert tr.ecu_at(2.5)[2] == MOVING_UP


def test_TC_64_status_message_shows_u0422(ctrl):
    """REQ_18: DTC_SwitchInvalid bit (0x210 byte 1 bit 5) set after the freeze"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1)), bcm_frozen=(2.0, 4.0), stop_time=4.0)
    before = [s for t, s in tr.decoded("DCU_WindowStatus") if t < 2.0]
    after = [s for t, s in tr.decoded("DCU_WindowStatus") if t > 2.1]
    assert all(s["DTC_SwitchInvalid"] == 0 for s in before)
    assert all(s["DTC_SwitchInvalid"] == 1 for s in after)


def test_TC_65_uds_reports_both_dtcs(ctrl):
    """REQ_18: 19 02 FF lists U0140-00 and U0422-00 (11 bytes -> multi-frame)"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1)), bcm_frozen=(2.0, 4.0),
                     stop_time=3.5, diag_requests=[(3.0, READ_DTCS)])
    assert dtcs_in(tr.tester.response_to(READ_DTCS)) == ["U0140-00", "U0422-00"]


def test_TC_66_clear_removes_u0422(ctrl):
    """REQ_16/18: 14 FF FF FF clears U0422-00 too (after the BCM is healthy again)"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1), (2.8, 0)), bcm_frozen=(2.0, 2.6),
                     stop_time=4.0, diag_requests=[(3.0, CLEAR_DTCS), (3.5, READ_DTCS)])
    assert tr.tester.response_to(CLEAR_DTCS) == bytes([0x54])
    assert dtcs_in(tr.tester.response_to(READ_DTCS)) == []
    assert tr.decoded("DCU_WindowStatus")[-1][1]["DTC_SwitchInvalid"] == 0


def test_TC_67_recovery_after_freeze(ctrl):
    """REQ_17/09: fresh frames return at 2.6 s, Up released at 2.8 s -> IDLE; U0422 stays"""
    tr = run_network(ctrl, init_pos=10, sw_up=((0, 0), (1, 1), (2.8, 0)), bcm_frozen=(2.0, 2.6),
                     stop_time=4.0)
    assert tr.ecu_at(2.7)[2] == ERROR, "must stay in ERROR while Up is still held"
    assert tr.ecu_at(3.0)[2] == IDLE, "no recovery after fresh frames and release"
    assert tr.e2e[-1][1], "U0422 must stay stored until cleared"
