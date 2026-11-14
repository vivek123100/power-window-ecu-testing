"""CAN-level tests: the C controller on the virtual CAN bus.

Every check uses only what a tester would see on the bus (decoded frames
from the logger), plus the ECU state for diagnosis messages.

Run from the repo root:   pytest 03_CAN/tests -v
"""
import pytest
from can_network import run_network

ERROR, MOVING_UP, PINCH_REVERSE = 5, 1, 3
UP, DOWN = 1, 2                      # DBC MotorState values


def status(tr):
    return tr.decoded("DCU_WindowStatus")


def status_at(tr, t):
    """Last status frame sent at or before t."""
    return max((x for x in status(tr) if x[0] <= t + 1e-6), key=lambda x: x[0])[1]


def test_TC_17_status_cycle_time(ctrl):
    """REQ_12: DCU_WindowStatus every 100 ms (+-10 ms) for 10 s"""
    tr = run_network(ctrl, stop_time=10.0)
    times = [t for t, _ in status(tr)]
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert len(times) >= 100, f"only {len(times)} status frames in 10 s"
    assert all(0.09 <= g <= 0.11 for g in gaps), \
        f"cycle time out of range: min {min(gaps) * 1000:.0f} ms, max {max(gaps) * 1000:.0f} ms"


def test_TC_18_status_content_while_moving(ctrl):
    """REQ_12: status shows real position, motor state, pinch flag and state"""
    tr = run_network(ctrl, init_pos=30, sw_up=((0, 0), (1, 1)))
    s = status_at(tr, 1.4)
    ecu_pos = tr.ecu_at(1.4)[3]
    assert abs(s["WindowPos"] - ecu_pos) <= 0.5, f"WindowPos {s['WindowPos']} vs real {ecu_pos:.2f}"
    assert 38 <= s["WindowPos"] <= 42, f"expected about 40 %, got {s['WindowPos']}"
    assert s["MotorState"] == UP
    assert s["PinchFlag"] == 0
    assert s["CtrlState"] == MOVING_UP
    assert s["DTC_SwitchTimeout"] == 0 and s["DTC_MotorOverrun"] == 0


def test_TC_19_pinch_visible_on_can(ctrl):
    """REQ_12, REQ_14: pinch flag and reversal visible in the status message"""
    tr = run_network(ctrl, obstacle_active=True)
    s = status_at(tr, 2.0)
    assert s["PinchFlag"] == 1
    assert s["MotorState"] == DOWN
    assert s["CtrlState"] == PINCH_REVERSE


def test_TC_08_can_message_lost(ctrl):
    """REQ_09: BCM stops sending at 3 s -> stop + DTC, visible on CAN"""
    tr = run_network(ctrl, sw_up=((0, 0), (1, 1)), init_pos=10, bcm_silent=(3.0, 5.0))
    t_err = next(t for t, cmd, state, pos, age in tr.ecu if state == ERROR)
    t_last = max(t for t, _ in tr.frames_of("BCM_WindowSwitch") if t < 3.0)
    detect = t_err - t_last
    assert 0.50 < detect <= 0.52, f"timeout detected after {detect * 1000:.0f} ms (allowed 500-520 ms)"
    s = status_at(tr, t_err + 0.1)
    assert s["DTC_SwitchTimeout"] == 1 and s["MotorState"] == 0 and s["CtrlState"] == ERROR


@pytest.mark.parametrize("tc, silent, expect_error", [
    ("TC_37 frames 500 ms apart (max age 490 ms) -> no timeout", (1.5, 1.98), False),
    ("TC_38 frames 560 ms apart (age reaches 510 ms) -> timeout", (1.5, 2.04), True),
])
def test_timeout_boundary(ctrl, tc, silent, expect_error):
    """REQ_09 boundary: real message gaps just below / above 500 ms"""
    tr = run_network(ctrl, sw_up=((0, 0), (1, 1)), init_pos=10, bcm_silent=silent, stop_time=3.0)
    sw = [t for t, _ in tr.frames_of("BCM_WindowSwitch")]
    max_gap = max(b - a for a, b in zip(sw, sw[1:]))
    entered_error = any(state == ERROR for t, cmd, state, pos, age in tr.ecu)
    assert entered_error == expect_error, f"{tc}: max gap {max_gap * 1000:.0f} ms, error={entered_error}"


def test_frames_match_dbc(ctrl):
    """Every frame on the bus has the ID, length and value ranges from the DBC"""
    tr = run_network(ctrl, obstacle_active=True, stop_time=6.0)
    for name, dlc in (("BCM_WindowSwitch", 2), ("DCU_WindowStatus", 4)):
        frames = tr.frames_of(name)
        assert frames, f"no {name} frames"
        assert all(len(d) == dlc for _, d in frames), f"{name}: wrong length"
        for _, s in tr.decoded(name):
            if name == "DCU_WindowStatus":
                assert 0 <= s["WindowPos"] <= 100
                assert s["MotorState"] in (0, 1, 2)
                assert 0 <= s["CtrlState"] <= 5


def test_alive_counter_increments(ctrl):
    """BCM AliveCounter counts 0..15 and wraps (needed later for E2E checks)"""
    tr = run_network(ctrl, stop_time=1.0)
    counters = [s["AliveCounter"] for _, s in tr.decoded("BCM_WindowSwitch")]
    assert counters[:17] == list(range(16)) + [0]


def test_TC_52_bcm_never_sends_after_power_on(ctrl):
    """REQ_09 (CR_01, option A): no switch message at all -> DTC ~510 ms after power-on"""
    tr = run_network(ctrl, bcm_enabled=False, stop_time=2.0)
    t_err = next((t for t, cmd, state, pos, age in tr.ecu if state == ERROR), None)
    assert t_err is not None, "dead BCM never detected"
    assert 0.50 < t_err <= 0.52, f"detected after {t_err * 1000:.0f} ms (allowed 500-520 ms)"
    assert status_at(tr, t_err + 0.1)["DTC_SwitchTimeout"] == 1


@pytest.mark.parametrize("tc, silent, expect_error", [
    ("TC_53 idle, frames 500 ms apart -> no timeout", (1.5, 1.98), False),
    ("TC_53 idle, frames 560 ms apart -> timeout", (1.5, 2.04), True),
])
def test_TC_53_timeout_boundary_while_idle(ctrl, tc, silent, expect_error):
    """REQ_09 (CR_01): the same boundary as TC_37/38, but with the window idle"""
    tr = run_network(ctrl, sw_up=((0, 0),), bcm_silent=silent, stop_time=3.0)
    entered_error = any(state == ERROR for t, cmd, state, pos, age in tr.ecu)
    assert entered_error == expect_error, tc
