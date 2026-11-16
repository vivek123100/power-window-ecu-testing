"""pytest setup for the HIL tests (05_HIL).

Every test powers on a fresh ECU (Renode + HIL firmware), runs its scenario in
real time on the bench, then evaluates the CAN log.

Test-system health: if the bench or the emulator was not real-time during the
measurement (BenchNotRealTime), the run says nothing about the ECU. It is repeated
up to HIL_RETRIES times; if it never runs cleanly the test is reported as SKIPPED
"INCONCLUSIVE" - never as an ECU pass or fail.
"""
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "05_HIL" / "host"))
import hil_bench  # noqa: E402

RETRIES = int(os.environ.get("HIL_RETRIES", "3"))
_stats = {"runs": 0, "retries": 0, "max_ticks": 0}


@pytest.fixture
def hil():
    """hil(check, duration, **bench_settings): run a scenario and check it."""
    def run(check, duration, **settings):
        last = None
        for attempt in range(RETRIES):
            bench = hil_bench.HilBench(**settings)
            with bench:
                bench.run_for(duration)
            _stats["runs"] += 1
            _stats["max_ticks"] = max(_stats["max_ticks"], bench.max_step_ticks())
            try:
                return check(bench)
            except hil_bench.BenchNotRealTime as e:
                last = e
                _stats["retries"] += 1
        pytest.skip(f"INCONCLUSIVE after {RETRIES} runs: {last}")
    return run


def pytest_report_header(config):
    return f"HIL bus: {os.environ.get('HIL_BUS', 'socketcan')} (set HIL_BUS=tcp without vcan0)"


def pytest_terminal_summary(terminalreporter):
    if _stats["runs"]:
        ticks = _stats["max_ticks"]
        terminalreporter.write_line(
            f"HIL: {_stats['runs']} ECU power-ons, {_stats['retries']} repeated because the test bench "
            f"was not real-time. Worst WindowCtrl_Step on the ECU: {ticks} SysTick ticks "
            f"= {ticks / 72:.2f} us of the 10 ms task (Renode estimate).")
