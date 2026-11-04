"""pytest setup: build the C library once per test session and give it to every test."""
import os
import pytest
import sil_env


@pytest.fixture(scope="session")
def ctrl():
    sil_env.build_library(coverage=os.environ.get("COVERAGE") == "1")
    return sil_env.load_library()
