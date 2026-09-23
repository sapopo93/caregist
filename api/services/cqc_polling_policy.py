"""Single source of truth for CQC signal-poll operational expectations."""

from __future__ import annotations

from datetime import timedelta


# :37 avoids the start-of-hour Actions scheduling peak. The former :07 cadence
# missed whole slots despite completed jobs being far shorter than three hours.
SIGNAL_POLL_CRON = "37 18,21,0,3 * * *"
SIGNAL_POLL_TIMEOUT_MINUTES = 50
SIGNAL_POLL_TIME_BUDGET_SECONDS = 45 * 60

POLLING_WINDOW = timedelta(days=7)
SCHEDULED_POLLS_PER_NIGHT = 4
ALLOWED_MISSED_NIGHTS = 1
SCHEDULED_POLLS_IN_WINDOW = (
    int(POLLING_WINDOW.total_seconds() // 86400) * SCHEDULED_POLLS_PER_NIGHT
)
MINIMUM_POLLS_IN_WINDOW = (
    int(POLLING_WINDOW.total_seconds() // 86400) - ALLOWED_MISSED_NIGHTS
) * SCHEDULED_POLLS_PER_NIGHT
MINIMUM_SUCCESS_RATIO = 0.90
LATEST_COMPLETED_POLL_SLA = timedelta(hours=16)
