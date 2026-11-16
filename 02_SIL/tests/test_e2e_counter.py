"""Unit tests for the E2E alive-counter check (CR_04, REQ_17, REQ_18).

These call e2e_counter.c directly - no plant, no bus. Run:
    pytest 02_SIL/tests/test_e2e_counter.py -v
"""
import pytest
from sil_env import E2E_INITIAL, E2E_OK, E2E_REPEATED


@pytest.fixture
def e2e(ctrl):
    ctrl.E2E_Init()
    return ctrl


def feed(e2e, counters):
    return [e2e.E2E_CheckCounter(c) for c in counters]


def test_TC_54_first_frame_accepted(e2e):
    """REQ_17: the first frame after start-up is accepted"""
    assert feed(e2e, [7]) == [E2E_INITIAL]


def test_TC_55_incrementing_counter_accepted(e2e):
    """REQ_17: a normal sender (0, 1, 2, 3) is always accepted"""
    assert feed(e2e, [0, 1, 2, 3]) == [E2E_INITIAL, E2E_OK, E2E_OK, E2E_OK]
    assert not e2e.E2E_DtcActive()


def test_TC_56_repeated_counter_discarded(e2e):
    """REQ_17: same counter as the last accepted frame -> discarded"""
    assert feed(e2e, [4, 4]) == [E2E_INITIAL, E2E_REPEATED]


def test_TC_57_wrap_15_to_0_accepted(e2e):
    """REQ_17: the counter wraps 15 -> 0; that is a change, not a repeat"""
    assert feed(e2e, [14, 15, 0, 1]) == [E2E_INITIAL, E2E_OK, E2E_OK, E2E_OK]


def test_TC_58_dtc_after_3_repeats_not_2(e2e):
    """REQ_18 boundary: 2 discarded frames -> no DTC, the 3rd -> DTC"""
    feed(e2e, [5, 5, 5])                      # 2 repeats
    assert not e2e.E2E_DtcActive(), "DTC after only 2 discarded frames"
    feed(e2e, [5])                            # 3rd repeat
    assert e2e.E2E_DtcActive(), "no DTC after 3 discarded frames"


def test_TC_59_repeat_count_resets_on_fresh_frame(e2e):
    """REQ_18: repeats must be 3 IN A ROW - a fresh frame starts again from 0"""
    feed(e2e, [1, 1, 1, 2, 2, 2])             # 2 repeats, fresh, 2 repeats
    assert not e2e.E2E_DtcActive()


def test_TC_60_dtc_latched_until_cleared(e2e):
    """REQ_18: DTC stays after fresh frames return; UDS 0x14 clears it"""
    feed(e2e, [3, 3, 3, 3])                   # DTC
    assert feed(e2e, [4, 5]) == [E2E_OK, E2E_OK]
    assert e2e.E2E_DtcActive(), "DTC must stay stored"
    e2e.E2E_ClearDtc()
    assert not e2e.E2E_DtcActive()


def test_TC_60b_long_freeze_no_overflow(e2e):
    """Robustness: 300 identical frames - still REPEATED, no counter overflow"""
    results = feed(e2e, [9] * 301)
    assert set(results[1:]) == {E2E_REPEATED}
    assert e2e.E2E_DtcActive()
    assert feed(e2e, [10]) == [E2E_OK]


def test_TC_86_counter_jump_accepted(e2e):
    """REQ_17 (V&V F-08): lost frames make the counter jump (3 -> 11) - a change, accepted;
    only the same counter again is a repeat"""
    assert feed(e2e, [3, 11, 11]) == [E2E_INITIAL, E2E_OK, E2E_REPEATED]

