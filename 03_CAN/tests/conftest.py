"""pytest setup for the CAN tests: same C library as the SIL tests.

TARGET=pil: the ECU's controller runs on the STM32 instead (PIL), see 02_SIL/tests/conftest.py.
"""
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_SIL" / "tests"))   # sil_env
sys.path.insert(0, str(ROOT / "03_CAN" / "sim"))     # can_network
sys.path.insert(0, str(ROOT / "04_PIL" / "host"))    # pil_target

import sil_env  # noqa: E402

PIL = os.environ.get("TARGET") == "pil"


@pytest.fixture(scope="session")
def ctrl():
    if PIL:
        import pil_target
        return pil_target.get_target()
    sil_env.build_library(coverage=os.environ.get("COVERAGE") == "1")
    return sil_env.load_library()
