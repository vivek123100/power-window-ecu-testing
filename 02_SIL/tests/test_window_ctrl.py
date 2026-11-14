"""SIL tests for the power window ECU - same test cases as the MIL harness.

Run from the repo root:   pytest 02_SIL/tests -v
"""
import pytest
from sil_env import simulate, ERROR, IDLE, PINCH_REVERSE, WAIT_RELEASE

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


# ------------------------------------------------------------------------
# TC_23 - TC_31: added after coverage analysis (Step 2e). Each one tests a
# fault in a state where no earlier test reached it.
# ------------------------------------------------------------------------
DOWN_FROM_1 = dict(sw_up=NEVER, sw_down=DOWN_AT_1)


def assert_stops_at(tr, t_fault, state=None):
    """Motor running just before the fault, stopped within 50 ms after it."""
    assert tr.val_at("motor_cmd", t_fault - 0.05) != 0, "motor not running before the fault"
    t = tr.first_t("motor_cmd", lambda v: v == 0, t_fault)
    assert t is not None and t - t_fault <= 0.05, f"stopped {t} (fault at {t_fault})"
    if state is not None:
        assert tr.val_at("state", t_fault + 0.1) == state


def test_TC_23_undervoltage_while_moving_up(ctrl):
    """REQ_08: Vbat drops to 8.5 V at 2 s while closing"""
    tr = simulate(ctrl, vbat=((0, 12.0), (2, 8.5)))
    assert_stops_at(tr, 2.0, IDLE)


def test_TC_24_up_and_down_while_moving_up(ctrl):
    """REQ_11: Down also pressed at 2 s while closing"""
    tr = simulate(ctrl, sw_down=((0, 0), (2, 1)))
    assert_stops_at(tr, 2.0, IDLE)


def test_TC_25_msg_lost_while_moving_down(ctrl):
    """REQ_09: switch message lost at 1.5 s while opening"""
    tr = simulate(ctrl, msg_age=((0, 0), (1.5, 600)), **DOWN_FROM_1)
    assert_stops_at(tr, 1.5, ERROR)
    assert tr.val_at("dtc_switch_timeout", 1.6) == 1


def test_TC_26_overrun_while_moving_down(ctrl):
    """REQ_10: position sensor stuck at 1.5 s (fault injection) -> motor runs on -> overrun"""
    tr = simulate(ctrl, pos_stuck_from=1.5, **DOWN_FROM_1)
    assert tr.val_at("motor_cmd", 8.9) == -1, "stopped before 8 s"
    assert tr.val_at("dtc_motor_overrun", 8.9) == 0
    assert tr.val_at("motor_cmd", 9.1) == 0
    assert tr.val_at("dtc_motor_overrun", 9.1) == 1


def test_TC_27_overvoltage_while_moving_down(ctrl):
    """REQ_08: Vbat rises to 16.5 V at 2 s while opening"""
    tr = simulate(ctrl, vbat=((0, 12.0), (2, 16.5)), **DOWN_FROM_1)
    assert_stops_at(tr, 2.0, IDLE)


def test_TC_28_up_and_down_while_moving_down(ctrl):
    """REQ_11: Up also pressed at 2 s while opening"""
    tr = simulate(ctrl, sw_up=((0, 0), (2, 1)), sw_down=DOWN_AT_1)
    assert_stops_at(tr, 2.0, IDLE)


def test_TC_29_overrun_during_pinch_reversal(ctrl):
    """REQ_10: position sensor stuck during reversal -> reversal never ends -> overrun"""
    tr = simulate(ctrl, obstacle_active=True, pos_stuck_from=1.9)
    t_rev = tr.first_t("state", lambda v: v == PINCH_REVERSE)
    assert t_rev is not None, "no pinch reversal"
    assert tr.val_at("motor_cmd", t_rev + 7.9) == -1, "stopped before 8 s"
    assert tr.val_at("motor_cmd", t_rev + 8.1) == 0
    assert tr.val_at("dtc_motor_overrun", t_rev + 8.1) == 1


def test_TC_30_undervoltage_during_pinch_reversal(ctrl):
    """REQ_08, REQ_14: Vbat drops to 8.5 V at 2.0 s while reversing"""
    tr = simulate(ctrl, obstacle_active=True, vbat=((0, 12.0), (2, 8.5)))
    assert_stops_at(tr, 2.0, IDLE)
    assert tr.val_at("pinch_flag", 2.1) == 0, "pinch flag must be cleared when leaving to IDLE"


def test_TC_31_release_after_pinch_unlocks_window(ctrl):
    """REQ_13, REQ_14: Up released at 4 s after pinch, pressed again at 5 s"""
    tr = simulate(ctrl, obstacle_active=True, sw_up=((0, 0), (1, 1), (4, 0), (5, 1)))
    assert tr.val_at("pinch_flag", 3.9) == 1
    assert tr.val_at("pinch_flag", 4.1) == 0, "flag not cleared on release"
    assert tr.val_at("state", 4.1) == IDLE
    t = tr.first_t("motor_cmd", lambda v: v == 1, 5.0)
    assert t is not None and t - 5.0 <= 0.05, "window does not close again after a new press"


# TC_32 - TC_36: branch coverage (each condition inside a transition both ways)
@pytest.mark.parametrize("tc, kwargs", [
    ("TC_32 switch message missing from start (REQ_09)", dict(msg_age=((0, 600),))),
    ("TC_33 Vbat 16.5 V from start (REQ_08)", dict(vbat=((0, 16.5),))),
    ("TC_33b Vbat 16.5 V, Down (REQ_08)", dict(vbat=((0, 16.5),), **DOWN_FROM_1)),
    ("TC_32b message missing, Down (REQ_09)", dict(msg_age=((0, 600),), **DOWN_FROM_1)),
])
def test_no_start_with_fault_present(ctrl, tc, kwargs):
    tr = simulate(ctrl, **kwargs)
    assert set(tr.values("motor_cmd")) == {0}, tc


def test_TC_34_no_pinch_below_4_percent(ctrl):
    """REQ_05 lower limit: blocked at 3 % while closing -> no pinch (seal zone)"""
    tr = simulate(ctrl, init_pos=2, obstacle_active=True, obstacle_pos=3)
    assert max(tr.values("pinch_flag")) == 0
    assert -1 not in tr.values("motor_cmd")


def test_TC_35_pinch_near_bottom_reverses_to_0(ctrl):
    """REQ_06: pinch at 10 % -> reversal ends at 0 % (less than 20 % available)"""
    tr = simulate(ctrl, init_pos=5, obstacle_active=True, obstacle_pos=10)
    assert max(tr.values("pinch_flag")) == 1
    assert tr.val_at("pos", 4.0) == 0.0
    assert tr.val_at("motor_cmd", 4.0) == 0, "motor must stop at 0 %"


def test_TC_36_switch_from_down_to_up(ctrl):
    """REQ_03: Down released and Up pressed in the same cycle -> stop first"""
    tr = simulate(ctrl, sw_up=((0, 0), (2, 1)), sw_down=((0, 0), (1, 1), (2, 0)))
    assert tr.val_at("motor_cmd", 2.0) == 0, "must stop before changing direction"


# ------------------------------------------------------------------------
# TC_49 - TC_51 and updated TC_32: CR_01 (REQ_09 timeout in every state)
# ------------------------------------------------------------------------
def test_TC_32_message_missing_from_start_stores_dtc(ctrl):
    """REQ_09 (CR_01): no switch message from power-on -> ERROR + DTC, motor never runs"""
    tr = simulate(ctrl, msg_age=((0, 600),))
    assert set(tr.values("motor_cmd")) == {0}
    assert tr.val_at("state", 0.1) == ERROR
    assert tr.val_at("dtc_switch_timeout", 0.1) == 1


def test_TC_49_msg_lost_while_idle(ctrl):
    """REQ_09 (CR_01): message lost at 2 s while idle -> ERROR + DTC"""
    tr = simulate(ctrl, sw_up=NEVER, msg_age=((0, 0), (2, 600)))
    assert tr.val_at("state", 1.95) == IDLE
    assert tr.val_at("state", 2.1) == ERROR, "lost message not detected while idle"
    assert tr.val_at("dtc_switch_timeout", 2.1) == 1
    assert set(tr.values("motor_cmd")) == {0}


def test_TC_50_msg_lost_in_wait_release(ctrl):
    """REQ_09 (CR_01): message lost while waiting for Up release after a pinch"""
    tr = simulate(ctrl, obstacle_active=True, msg_age=((0, 0), (4, 600)))
    assert tr.val_at("state", 3.9) == WAIT_RELEASE, "precondition: not in WAIT_RELEASE"
    assert tr.val_at("state", 4.1) == ERROR, "lost message not detected in WAIT_RELEASE"
    assert tr.val_at("dtc_switch_timeout", 4.1) == 1


def test_TC_51_idle_timeout_recovery(ctrl):
    """REQ_09 (CR_01): idle timeout 2-3 s, message back, Up at 5 s -> works again, DTC stays"""
    tr = simulate(ctrl, sw_up=((0, 0), (5, 1)), msg_age=((0, 0), (2, 600), (3, 0)))
    assert tr.val_at("state", 2.5) == ERROR
    assert tr.val_at("state", 3.1) == IDLE
    t = tr.first_t("motor_cmd", lambda v: v == 1, 5.0)
    assert t is not None and t - 5.0 <= 0.05, "window does not work after recovery"
    assert tr.val_at("dtc_switch_timeout", 11.0) == 1, "DTC must stay stored"
