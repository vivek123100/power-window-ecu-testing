"""Back-to-back test: MIL (Simulink model) vs. SIL (C code).

For every test case, MATLAB saved the complete MIL run in reports/b2b/mil/TC_xx.csv
(see run_mil_tests.m). Here the same scenario runs on the C code and every
signal is compared sample by sample (every 10 ms).

Two results per signal:
  exact      - same value at the same time step
  tolerant   - same value within +-1 time step (10 ms). A 1-step offset can come
               from where a signal is logged (before/after a Unit Delay) and is
               reported, not hidden.
Pos/Current are floats, compared with a small value tolerance.

Writes reports/b2b/b2b_report.md and reports/b2b/sil/TC_xx.csv.

Run:  pytest 02_SIL/tests/test_back_to_back.py -v
"""
import csv
import pathlib

import pytest
from sil_env import ROOT, simulate

MIL_DIR = ROOT / "reports" / "b2b" / "mil"
SIL_DIR = ROOT / "reports" / "b2b" / "sil"
REPORT = ROOT / "reports" / "b2b" / "b2b_report.md"

SIGNALS = ["motor_cmd", "pinch_flag", "dtc_switch_timeout", "dtc_motor_overrun", "pos", "current"]
VALUE_TOL = {"pos": 1e-3, "current": 1e-3}      # floats; others must be equal
TIME_TOL_STEPS = 1                               # +-10 ms

DOWN = ((0, 0), (1, 1))
NEVER = ((0, 0),)

# Same scenarios as defineTests() in run_mil_tests.m (TC_17/18 have no MIL run).
SCENARIOS = {
    "TC_01": {},
    "TC_02": {},
    "TC_03": dict(obstacle_active=True, stall_current=7.9),
    "TC_04": dict(obstacle_active=True, stall_current=8.1),
    "TC_05": dict(init_pos=97, obstacle_active=True, obstacle_pos=98, stall_current=9),
    "TC_06": dict(vbat=((0, 8.9),)),
    "TC_07": dict(vbat=((0, 9.0),)),
    "TC_08": dict(msg_age=((0, 0), (3, 600))),
    "TC_09": dict(sw_down=DOWN),
    "TC_10": dict(sw_up=NEVER, sw_down=DOWN),
    "TC_11": dict(sw_up=NEVER, sw_down=DOWN, init_pos=0),
    "TC_12": dict(sw_up=NEVER, sw_down=DOWN, init_pos=1),
    "TC_13": dict(sw_up=((0, 0), (1, 1), (2, 0))),
    "TC_14": dict(sw_up=NEVER, sw_down=((0, 0), (1, 1), (2, 0))),
    "TC_15": dict(obstacle_active=True, stall_current=7.9),
    "TC_16": dict(obstacle_active=True, stall_current=7.9),
    "TC_19": dict(obstacle_active=True),
    "TC_20": dict(obstacle_active=True, msg_age=((0, 0), (2, 600))),
    "TC_21": dict(obstacle_active=True),
    "TC_22": dict(sw_up=((0, 0), (1, 1), (6, 0)), msg_age=((0, 0), (3, 600), (5, 0))),
    "TC_49": dict(sw_up=NEVER, msg_age=((0, 0), (2, 600))),
    "TC_50": dict(obstacle_active=True, msg_age=((0, 0), (4, 600))),
    "TC_51": dict(sw_up=((0, 0), (5, 1)), msg_age=((0, 0), (2, 600), (3, 0))),
}


def load_mil(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return {
        "t": [round(float(r["t"]), 2) for r in rows],
        **{s: [float(r[s]) for r in rows] for s in SIGNALS},
    }


def equal(sig, a, b):
    return abs(a - b) <= VALUE_TOL.get(sig, 0.0)


def compare(mil, sil):
    """Compare one signal set. Returns per-signal stats."""
    sil_index = {t: i for i, t in enumerate(sil.t)}
    stats = {}
    for sig in SIGNALS:
        s_vals = sil.sig[sig]
        exact = tol = 0
        first_exact_diff = first_tol_diff = None
        for t, m in zip(mil["t"], mil[sig]):
            i = sil_index.get(t)
            if i is None:
                continue
            if equal(sig, m, s_vals[i]):
                exact += 1
                tol += 1
                continue
            if first_exact_diff is None:
                first_exact_diff = (t, m, s_vals[i])
            lo, hi = max(0, i - TIME_TOL_STEPS), min(len(s_vals), i + TIME_TOL_STEPS + 1)
            if any(equal(sig, m, s_vals[j]) for j in range(lo, hi)):
                tol += 1
            elif first_tol_diff is None:
                first_tol_diff = (t, m, s_vals[i])
        n = len(mil["t"])
        stats[sig] = dict(n=n, exact=exact, tol=tol,
                          first_exact_diff=first_exact_diff, first_tol_diff=first_tol_diff)
    return stats


def save_sil_csv(tc, tr):
    SIL_DIR.mkdir(parents=True, exist_ok=True)
    with open(SIL_DIR / f"{tc}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t"] + SIGNALS)
        for k, t in enumerate(tr.t):
            w.writerow([t] + [tr.sig[s][k] for s in SIGNALS])


# ---------------------------------------------------------------- report
_results = {}


@pytest.fixture(scope="module", autouse=True)
def b2b_report():
    yield
    if not _results:
        return
    lines = ["# Back-to-Back Report: MIL (Simulink) vs. SIL (C code)", "",
             f"Compared every 10 ms. Tolerance: value {VALUE_TOL} for floats, "
             f"time +-{TIME_TOL_STEPS} step.", "",
             "| TC | Result | Exact match | Notes |", "|---|---|---|---|"]
    for tc in sorted(_results):
        stats = _results[tc]
        ok = all(s["tol"] == s["n"] for s in stats.values())
        total = sum(s["n"] for s in stats.values())
        exact = sum(s["exact"] for s in stats.values())
        notes = []
        for sig, s in stats.items():
            if s["first_tol_diff"]:
                t, m, v = s["first_tol_diff"]
                notes.append(f"**{sig} differs at {t:.2f} s (MIL {m:g}, SIL {v:g})**")
            elif s["first_exact_diff"]:
                t, m, v = s["first_exact_diff"]
                notes.append(f"{sig}: 1-step offset from {t:.2f} s")
        lines.append(f"| {tc} | {'PASS' if ok else 'FAIL'} | {100 * exact / total:.1f} % | "
                     f"{'; '.join(notes) or 'identical'} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------- tests
MIL_FILES = sorted(MIL_DIR.glob("TC_*.csv")) if MIL_DIR.exists() else []


@pytest.mark.skipif(not MIL_FILES, reason="no MIL reference data: run run_mil_tests in MATLAB "
                                          "and commit reports/b2b/mil/")
@pytest.mark.parametrize("mil_file", MIL_FILES, ids=[p.stem for p in MIL_FILES])
def test_back_to_back(ctrl, mil_file):
    tc = mil_file.stem
    assert tc in SCENARIOS, f"{tc}: no SIL scenario defined in SCENARIOS"
    mil = load_mil(mil_file)
    stop = mil["t"][-1]
    tr = simulate(ctrl, stop_time=stop, **SCENARIOS[tc])
    save_sil_csv(tc, tr)

    stats = compare(mil, tr)
    _results[tc] = stats

    problems = []
    for sig, s in stats.items():
        if s["tol"] != s["n"]:
            t, m, v = s["first_tol_diff"]
            problems.append(f"{sig}: {s['n'] - s['tol']} samples differ, first at {t:.2f} s "
                            f"(MIL {m:g}, SIL {v:g})")
    assert not problems, f"{tc} MIL vs SIL mismatch:\n  " + "\n  ".join(problems)
