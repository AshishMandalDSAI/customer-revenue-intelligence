"""Shared pytest fixtures. Tests run against the processed data already
produced by `python scripts/run_pipeline.py` -- run the pipeline once
before running the test suite (CI does this automatically; see Makefile's
`test` target which depends on `pipeline`)."""
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).resolve().parent.parent
