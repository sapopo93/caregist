from pathlib import Path

from api.services.cqc_polling_policy import (
    MINIMUM_POLLS_IN_WINDOW,
    SCHEDULED_POLLS_IN_WINDOW,
    SIGNAL_POLL_CRON,
    SIGNAL_POLL_TIME_BUDGET_SECONDS,
    SIGNAL_POLL_TIMEOUT_MINUTES,
)
from tools.nightly_cqc_db_check import REQUIRED_WEEKLY_POLLS


def test_polling_consumers_share_one_minimum():
    assert MINIMUM_POLLS_IN_WINDOW == 24
    assert SCHEDULED_POLLS_IN_WINDOW == 28
    assert REQUIRED_WEEKLY_POLLS == MINIMUM_POLLS_IN_WINDOW


def test_workflow_matches_shared_cadence_and_budget():
    workflow = Path(".github/workflows/cqc-signal-poll.yml").read_text(encoding="utf-8")
    assert f'cron: "{SIGNAL_POLL_CRON}"' in workflow
    assert f"timeout-minutes: {SIGNAL_POLL_TIMEOUT_MINUTES}" in workflow
    assert SIGNAL_POLL_TIME_BUDGET_SECONDS < SIGNAL_POLL_TIMEOUT_MINUTES * 60
