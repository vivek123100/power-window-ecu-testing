"""UDS diagnostic tests: a tester talks to the DCU over ISO-TP on the virtual bus.

Run from the repo root:   pytest 03_CAN/tests/test_uds.py -v
"""
import pytest
import uds
from can_network import run_network

SW_VERSION = bytes([0x22, 0xF1, 0x95])
WINDOW_POS = bytes([0x22, 0x01, 0x00])
READ_DTCS = bytes([0x19, 0x02, 0xFF])
CLEAR_DTCS = bytes([0x14, 0xFF, 0xFF, 0xFF])


def diag(ctrl, requests, **kwargs):
    tr = run_network(ctrl, diag_requests=requests, **kwargs)
    return tr, tr.tester


def dtcs_in(resp):
    """59 02 09 [3 bytes DTC + 1 byte status]... -> ['U0140-00', ...]"""
    assert resp[:2] == bytes([0x59, 0x02]), f"not a 0x19 response: {resp.hex(' ')}"
    body = resp[3:]
    return [uds.dtc_name(body[i:i + 3]) for i in range(0, len(body), 4)]


def test_TC_39_read_software_version(ctrl):
    """REQ_15: 22 F1 95 -> 62 F1 95 'PW-1.0.0' (11 bytes: multi-frame ISO-TP)"""
    tr, tester = diag(ctrl, [(0.5, SW_VERSION)], stop_time=1.0)
    resp = tester.response_to(SW_VERSION)
    assert resp == bytes([0x62, 0xF1, 0x95]) + b"PW-1.0.0", resp
    diag_frames = [d for t, i, d in tr.frames if i in (uds.REQ_ID, uds.RESP_ID)]
    kinds = [d[0] >> 4 for d in diag_frames]
    assert kinds == [0, 1, 3, 2], f"expected SF request, FF, FC, CF - got {kinds}"


def test_TC_40_read_window_position_live(ctrl):
    """REQ_15: 22 01 00 returns the current position while the window moves"""
    _, tester = diag(ctrl, [(1.4, WINDOW_POS)], init_pos=30, sw_up=((0, 0), (1, 1)))
    resp = tester.response_to(WINDOW_POS)
    assert resp[:3] == bytes([0x62, 0x01, 0x00])
    assert 38 <= resp[3] <= 42, f"position {resp[3]} %"


def test_TC_41_unknown_did(ctrl):
    """REQ_15: unknown DID -> negative response 7F 22 31 (request out of range)"""
    req = bytes([0x22, 0xF1, 0xFF])
    _, tester = diag(ctrl, [(0.5, req)], stop_time=1.0)
    assert tester.response_to(req) == bytes([0x7F, 0x22, 0x31])


def test_TC_42_no_dtcs_when_ok(ctrl):
    """REQ_15: 19 02 FF without any fault -> 59 02 09, no DTC records"""
    _, tester = diag(ctrl, [(2.0, READ_DTCS)], stop_time=3.0)
    assert tester.response_to(READ_DTCS) == bytes([0x59, 0x02, 0x09])


def test_TC_43_dtc_after_can_timeout(ctrl):
    """REQ_09, REQ_15: after a lost switch message, U0140-00 is stored and readable"""
    _, tester = diag(ctrl, [(4.0, READ_DTCS)], bcm_silent=(2.0, 3.0), stop_time=5.0)
    assert dtcs_in(tester.response_to(READ_DTCS)) == ["U0140-00"]


def test_TC_44_dtc_after_overrun(ctrl):
    """REQ_10, REQ_15: blocked motor -> B1310-00 stored and readable"""
    _, tester = diag(ctrl, [(10.0, READ_DTCS)], obstacle_active=True,
                     stall_current=7.9, stop_time=10.5)
    assert dtcs_in(tester.response_to(READ_DTCS)) == ["B1310-00"]


def test_TC_45_clear_dtcs(ctrl):
    """REQ_16: 14 FF FF FF -> 54; DTCs gone in 0x19 and in the status message"""
    requests = [(4.0, READ_DTCS), (4.5, CLEAR_DTCS), (5.0, READ_DTCS)]
    tr, tester = diag(ctrl, requests, bcm_silent=(2.0, 3.0), stop_time=6.0)
    reads = [resp for t_req, req, t_resp, resp in tester.log if req == READ_DTCS]
    assert dtcs_in(reads[0]) == ["U0140-00"], "DTC not stored before clearing"
    assert tester.response_to(CLEAR_DTCS) == bytes([0x54])
    assert dtcs_in(reads[1]) == [], "DTC still stored after clearing"
    last_status = tr.decoded("DCU_WindowStatus")[-1][1]
    assert last_status["DTC_SwitchTimeout"] == 0, "status message still shows the DTC"


@pytest.mark.parametrize("tc, req, expected", [
    ("TC_46 extended session", bytes([0x10, 0x03]), bytes([0x50, 0x03, 0x00, 0x32, 0x01, 0xF4])),
    ("TC_46 tester present", bytes([0x3E, 0x00]), bytes([0x7E, 0x00])),
    ("TC_47 unsupported service", bytes([0x31, 0x01, 0x02, 0x03]), bytes([0x7F, 0x31, 0x11])),
    ("TC_47 wrong length", bytes([0x22, 0xF1]), bytes([0x7F, 0x22, 0x13])),
    ("TC_47 unsupported session", bytes([0x10, 0x02]), bytes([0x7F, 0x10, 0x12])),
])
def test_service_responses(ctrl, tc, req, expected):
    """REQ_15: positive and negative responses"""
    _, tester = diag(ctrl, [(0.5, req)], stop_time=1.0)
    assert tester.response_to(req) == expected, tc


def test_response_time_p2(ctrl):
    """REQ_15: every response starts within P2 = 50 ms"""
    requests = [(0.5, SW_VERSION), (0.8, READ_DTCS), (1.1, bytes([0x3E, 0x00]))]
    tr, tester = diag(ctrl, requests, stop_time=1.5)
    assert len(tester.log) == 3
    for t_req, req, t_resp, resp in tester.log:
        first = min(t for t, i, d in tr.frames if i == uds.RESP_ID and t >= t_req - 1e-9)
        assert first - t_req <= 0.05, f"{req.hex(' ')}: response after {(first - t_req) * 1000:.0f} ms"
