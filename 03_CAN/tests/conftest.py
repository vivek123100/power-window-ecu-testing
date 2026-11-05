"""pytest setup for the CAN tests: same C library as the SIL tests."""
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "02_SIL" / "tests"))   # sil_env
sys.path.insert(0, str(ROOT / "03_CAN" / "sim"))     # can_network

import sil_env  # noqa: E402


@pytest.fixture(scope="session")
def ctrl():
    sil_env.build_library(coverage=os.environ.get("COVERAGE") == "1")
    return sil_env.load_library()
