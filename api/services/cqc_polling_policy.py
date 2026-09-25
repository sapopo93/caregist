"""Single source of truth for CQC signal-poll operational expectations."""

from __future__ import annotations

from datetime import timedelta


# :37 is an operational hypothesis intended to avoid the earlier part of the
# Actions scheduling window. It is not a proven fix: readiness still requires
# observing at least 24 starts in seven days at >=90% completion.
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
