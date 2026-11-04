"""SIL tests for the power window ECU - same test cases as the MIL harness.

Run from the repo root:   pytest 02_SIL/tests -v
"""
import pytest
from sil_env import simulate, ERROR, IDLE

UP_AT_1 = ((0, 0), (1, 1))
DOWN_AT_1 = ((0, 0), (1, 1))
NEVER = ((0, 0),)


def test_TC_01_up_starts_motor_within_50ms(ctrl):
    """REQ_01"""
    tr = simulate(ctrl)
    t = tr.first_t("motor_cmd", lambda v: v == 1, 1.0)
    assert t is not None and t - 1.0 <= 0.05, f"motor up at {t}"


def test_TC_02_stops_at_100_percent(ctrl):
    """REQ_04"""
    tr = simulate(ctrl)
    assert tr.val_at("pos", 4.0) >= 99.9
    assert tr.val_at("motor_cmd", 4.0) == 0


def test_TC_03_stall_7_9A_no_pinch(ctrl):
    """REQ_05 (just below the 8 A limit)"""
    tr = simulate(ctrl, obstacle_active=True, stall_current=7.9)
    assert max(tr.values("pinch_flag")) == 0
    assert -1 not in tr.values("motor_cmd")


def test_TC_04_stall_8_1A_pinch_and_reverse(ctrl):
    """REQ_05, REQ_06 (just above the 8 A limit)"""
    tr = simulate(ctrl, obstacle_active=True, stall_current=8.1)
    t_stall = tr.first_t("current", lambda v: v > 8)
    t_rev = tr.first_t("motor_cmd", lambda v: v == -1)
    assert t_rev is not None, "no reversal"
    assert t_rev - t_stall <= 0.2, f"reversal {1000 * (t_rev - t_stall):.0f} ms after stall"
    reversed_pct = 70.0 - tr.val_at("pos", 4.0)
    assert reversed_pct >= 20.0, f"reversed only {reversed_pct:.1f} %"
    assert max(tr.values("pinch_flag")) == 1


def test_TC_05_no_reversal_above_96_percent(ctrl):
    """REQ_07"""
    tr = simulate(ctrl, init_pos=97, obstacle_active=True, obstacle_pos=98, stall_current=9)
    assert -1 not in tr.values("motor_cmd")
    assert max(tr.values("pinch_flag")) == 0


@pytest.mark.parametrize("tc, kwargs", [
    ("TC_06 Vbat 8.9 V (REQ_08)", dict(vbat=((0, 8.9),))),
    ("TC_09 Up+Down (REQ_11)", dict(sw_down=DOWN_AT_1)),
    ("TC_11 Pos 0 %, Down (REQ_02, REQ_04)", dict(sw_up=NEVER, sw_down=DOWN_AT_1, init_pos=0)),
])
def test_motor_never_runs(ctrl, tc, kwargs):
    tr = simulate(ctrl, **kwargs)
    assert set(tr.values("motor_cmd")) == {0}, tc


def test_TC_07_vbat_9_0V_motor_runs(ctrl):
    """REQ_08 (exactly at the limit)"""
    tr = simulate(ctrl, vbat=((0, 9.0),))
    t = tr.first_t("motor_cmd", lambda v: v == 1, 1.0)
    assert t is not None and t - 1.0 <= 0.05


def test_TC_08_msg_lost_stop_and_dtc(ctrl):
    """REQ_09"""
    tr = simulate(ctrl, msg_age=((0, 0), (3, 600)))
    assert tr.val_at("dtc_switch_timeout", 2.9) == 0
    assert tr.val_at("motor_cmd", 3.1) == 0
    assert tr.val_at("dtc_switch_timeout", 3.1) == 1
    assert tr.val_at("dtc_switch_timeout", 11.0) == 1, "DTC must stay stored"


@pytest.mark.parametrize("tc, init_pos", [("TC_10 Pos 50 %", 50), ("TC_12 Pos 1 %", 1)])
def test_down_starts_motor_within_50ms(ctrl, tc, init_pos):
    """REQ_02"""
    tr = simulate(ctrl, sw_up=NEVER, sw_down=DOWN_AT_1, init_pos=init_pos)
    t = tr.first_t("motor_cmd", lambda v: v == -1, 1.0)
    assert t is not None and t - 1.0 <= 0.05, tc


@pytest.mark.parametrize("tc, kwargs", [
    ("TC_13 Up released", dict(sw_up=((0, 0), (1, 1), (2, 0)))),
    ("TC_14 Down released", dict(sw_up=NEVER, sw_down=((0, 0), (1, 1), (2, 0)))),
])
def test_release_stops_within_50ms(ctrl, tc, kwargs):
    """REQ_03"""
    tr = simulate(ctrl, **kwargs)
    assert tr.val_at("motor_cmd", 1.9) != 0, f"{tc}: not running before release"
    t = tr.first_t("motor_cmd", lambda v: v == 0, 2.0)
    assert t is not None and t - 2.0 <= 0.05, tc


def test_TC_15_blocked_7_9s_still_running(ctrl):
    """REQ_10 (just below 8 s)"""
    tr = simulate(ctrl, obstacle_active=True, stall_current=7.9)
    assert tr.val_at("motor_cmd", 8.9) == 1
    assert tr.val_at("dtc_motor_overrun", 8.9) == 0


def test_TC_16_blocked_8_1s_stop_and_dtc(ctrl):
    """REQ_10 (just above 8 s)"""
    tr = simulate(ctrl, obstacle_active=True, stall_current=7.9)
    assert tr.val_at("motor_cmd", 9.1) == 0
    assert tr.val_at("dtc_motor_overrun", 9.1) == 1


@pytest.mark.skip(reason="TC_17/TC_18: CAN status message - tested in the CAN/HIL step")
def test_TC_17_18_status_message():
    """REQ_12"""


def test_TC_19_pinch_flag_set(ctrl):
    """REQ_12, REQ_14"""
    tr = simulate(ctrl, obstacle_active=True)
    assert tr.val_at("pinch_flag", 2.0) == 1


def test_TC_20_msg_lost_during_reversal(ctrl):
    """REQ_09"""
    tr = simulate(ctrl, obstacle_active=True, msg_age=((0, 0), (2, 600)))
    assert tr.val_at("motor_cmd", 1.95) == -1, "not reversing at 1.95 s"
    assert tr.val_at("motor_cmd", 2.1) == 0
    assert tr.val_at("dtc_switch_timeout", 2.1) == 1


def test_TC_21_no_reclosing_after_pinch(ctrl):
    """REQ_13, REQ_14"""
    tr = simulate(ctrl, obstacle_active=True)
    assert 1 not in tr.values("motor_cmd", after=2.7), "window closed again on the obstacle"
    assert tr.val_at("pinch_flag", 5.0) == 1, "pinch flag cleared too early"


def test_TC_22_error_recovery_needs_release(ctrl):
    """REQ_09 recovery: message back at 5 s while Up held, Up released at 6 s"""
    tr = simulate(ctrl, sw_up=((0, 0), (1, 1), (6, 0)), msg_age=((0, 0), (3, 600), (5, 0)))
    assert tr.val_at("state", 5.5) == ERROR, "left ERROR while Up still held"
    assert 1 not in tr.values("motor_cmd", after=3.1), "window moved again after the fault"
    assert tr.val_at("state", 6.1) == IDLE, "stuck in ERROR after release"
