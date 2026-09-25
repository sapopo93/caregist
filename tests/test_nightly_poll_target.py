"""Pin the poll-cadence arithmetic to the cron it claims to describe.

`REQUIRED_WEEKLY_POLLS` was hardcoded to 336 (48/day x 7) on 2026-09-19, four
days *after* the cron moved to a four-slot night window -- and its comment cited
the workflow it already disagreed with. Nothing gated on it, so the only symptom
was a nightly line reading "17 completed of 17 runs (required 336)".

`api/services/cqc_polling_policy` closes that by making the cron and the minimum
one shared source, and `test_cqc_polling_policy` pins `SIGNAL_POLL_CRON` to the
workflow file. The remaining hop is unchecked: `SCHEDULED_POLLS_PER_NIGHT` is an
independent literal. Move the cron to five slots and update `SIGNAL_POLL_CRON`
and every existing test still passes while the minimum stays quietly wrong --
the original defect, one level up. This closes that hop.
"""

import pytest

from api.services.cqc_polling_policy import (
    ALLOWED_MISSED_NIGHTS,
    MINIMUM_POLLS_IN_WINDOW,
    POLLING_WINDOW,
    SCHEDULED_POLLS_PER_NIGHT,
    SIGNAL_POLL_CRON,
)


def _slots_per_night(expression: str) -> int:
    """Nightly run count for one cron expression.

    Models only the subset this workflow uses -- a literal minute, a
    comma-separated hour list, wildcards elsewhere -- and raises on anything
    else, so an unmodelled edit fails loudly instead of quietly producing a
    plausible number.
    """
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"expected 5 cron fields, got {len(fields)}: {expression!r}")
    minute, hours, day_of_month, month, day_of_week = fields
    for name, value in (
        ("day-of-month", day_of_month),
        ("month", month),
        ("day-of-week", day_of_week),
    ):
        if value != "*":
            raise ValueError(f"unmodelled {name} field {value!r} in {expression!r}")
    for name, value in (("minute", minute), ("hour", hours)):
        if any(char in value for char in "/-"):
            raise ValueError(f"unmodelled step/range in {name} field {value!r}")
    if not minute.isdigit():
        raise ValueError(f"unmodelled minute field {minute!r} in {expression!r}")
    return len(hours.split(","))


def test_scheduled_polls_per_night_matches_the_cron():
    assert SCHEDULED_POLLS_PER_NIGHT == _slots_per_night(SIGNAL_POLL_CRON)


def test_minimum_is_the_stated_arithmetic_over_that_cadence():
    nights = int(POLLING_WINDOW.total_seconds() // 86400)
    expected = (nights - ALLOWED_MISSED_NIGHTS) * _slots_per_night(SIGNAL_POLL_CRON)
    assert MINIMUM_POLLS_IN_WINDOW == expected


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("37 18,21,0,3 * * *", 4),   # the live night window
        ("0 * * * *", 1),
        ("7 0,12 * * *", 2),
    ],
)
def test_slots_per_night(expression, expected):
    assert _slots_per_night(expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "*/30 * * * *",   # step -- the old 48/day cadence that caused the defect
        "0 9-17 * * *",   # range
        "0 0 1 * *",      # day-of-month constraint
        "15 2 * * 0",     # day-of-week constraint
        "0 0 * *",        # too few fields
    ],
)
def test_unmodelled_expressions_fail_loudly(expression):
    with pytest.raises(ValueError):
        _slots_per_night(expression)
