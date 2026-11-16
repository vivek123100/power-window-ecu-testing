"""pytest setup: build the C library once per test session and give it to every test.

TARGET=pil: the same tests run against the controller on the STM32 instead (PIL,
04_PIL/host/pil_target.py). The fixture returns an object with the same functions.
"""
import os
import pathlib
import sys

import pytest
import sil_env

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "04_PIL" / "host"))
PIL = os.environ.get("TARGET") == "pil"


@pytest.fixture(scope="session")
def ctrl():
    if PIL:
        import pil_target
        return pil_target.get_target()
    sil_env.build_library(coverage=os.environ.get("COVERAGE") == "1")
    return sil_env.load_library()


def pytest_report_header(config):
    return "target: PIL (controller on the emulated STM32)" if PIL else "target: SIL (host gcc)"


def pytest_terminal_summary(terminalreporter):
    if PIL:
        import pil_target
        terminalreporter.write_line(pil_target.summary())
