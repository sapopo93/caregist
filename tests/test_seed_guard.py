"""Tests for the destructive-truncate guard in db/seed.py (F-32)."""

import importlib.util
from pathlib import Path

import pytest

# db/seed.py is a script, not a package module — load it directly.
_SEED_PATH = Path(__file__).resolve().parents[1] / "db" / "seed.py"
_spec = importlib.util.spec_from_file_location("caregist_seed", _SEED_PATH)
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://user:pw@localhost:5432/caregist",
        "postgresql://127.0.0.1/caregist",
        "postgresql://db:5432/caregist",
    ],
)
def test_local_database_truncate_allowed(url):
    # Local hosts never require the confirmation flag.
    seed.guard_truncate(url, i_understand=False)


def test_remote_truncate_blocked_without_flag():
    with pytest.raises(SystemExit):
        seed.guard_truncate("postgresql://user:pw@prod.rds.amazonaws.com/caregist", i_understand=False)


def test_remote_truncate_allowed_with_flag():
    seed.guard_truncate("postgresql://user:pw@prod.rds.amazonaws.com/caregist", i_understand=True)
