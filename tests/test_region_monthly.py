"""Region Monthly stage 1: month rules, coverage, planning, purchase refusals,
the flag-gated preview route, the build CLI and the workflow guards.

The Postgres-backed counts and immutability checks are in
tests/integration/test_region_monthly_pg.py.
"""

from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from api.config import Settings
from api.main import app
from api.middleware import ip_rate_limit
from api.service_taxonomy import resolve_service_filter, taxonomy
from api.services import region_monthly as svc
from api.services.region_monthly import RegionMonthlyError
from tools import build_region_monthly as cli
from tools.evidence_language_guard import scan_paths

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)  # latest buildable month is October 2026


def d(y: int, m: int, day: int = 1) -> date:
    return date(y, m, day)


def code_of(callable_, *args, **kwargs) -> str:
    with pytest.raises(RegionMonthlyError) as raised:
        callable_(*args, **kwargs)
    return raised.value.code


# --- UK month boundaries ----------------------------------------------------


def hours(period_month: date) -> float:
    start, end = svc.uk_month_bounds(period_month)
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600


def test_month_bounds_follow_the_2026_clock_changes():
    # 29 March 2026: clocks go forward, so March is an hour short and April starts at 23:00Z.
    assert svc.uk_month_bounds(d(2026, 3))[1].astimezone(UTC) == datetime(2026, 3, 31, 23, 0, tzinfo=UTC)
    assert hours(d(2026, 3)) == 31 * 24 - 1
    assert svc.uk_month_bounds(d(2026, 4))[0].astimezone(UTC) == datetime(2026, 3, 31, 23, 0, tzinfo=UTC)
    # 25 October 2026: clocks go back, so October is an hour long and November starts at 00:00Z.
    assert svc.uk_month_bounds(d(2026, 10))[0].astimezone(UTC) == datetime(2026, 9, 30, 23, 0, tzinfo=UTC)
    assert svc.uk_month_bounds(d(2026, 10))[1].astimezone(UTC) == datetime(2026, 11, 1, 0, 0, tzinfo=UTC)
    assert hours(d(2026, 10)) == 31 * 24 + 1
    # Ordinary months are whole days.
    assert hours(d(2026, 7)) == 31 * 24
    assert hours(d(2026, 11)) == 30 * 24


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        # BST ends 25 Oct 2026, so 31 Oct 23:30Z is 23:30 GMT on 31 October: October.
        (datetime(2026, 10, 31, 23, 30, tzinfo=UTC), d(2026, 10)),
        (datetime(2026, 11, 1, 0, 0, tzinfo=UTC), d(2026, 11)),
        # 31 March 23:30Z is 00:30 BST on 1 April: April.
        (datetime(2026, 3, 31, 23, 30, tzinfo=UTC), d(2026, 4)),
        (datetime(2026, 3, 31, 22, 59, 59, tzinfo=UTC), d(2026, 3)),
        (datetime(2026, 3, 31, 23, 0, tzinfo=UTC), d(2026, 4)),
        # Midsummer: 30 June 23:00Z is 00:00 BST on 1 July.
        (datetime(2026, 6, 30, 22, 59, 59, tzinfo=UTC), d(2026, 6)),
        (datetime(2026, 6, 30, 23, 0, tzinfo=UTC), d(2026, 7)),
        # The repeated hour on 25 October stays in October.
        (datetime(2026, 10, 25, 0, 30, tzinfo=UTC), d(2026, 10)),
        (datetime(2026, 10, 25, 1, 30, tzinfo=UTC), d(2026, 10)),
        # New year: December has no offset, so UTC and UK agree.
        (datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC), d(2026, 12)),
        (datetime(2027, 1, 1, 0, 0, tzinfo=UTC), d(2027, 1)),
        # 2028 is a leap year.
        (datetime(2028, 2, 29, 23, 30, tzinfo=UTC), d(2028, 2)),
        (datetime(2028, 3, 1, 0, 0, tzinfo=UTC), d(2028, 3)),
        (datetime(2028, 2, 1, 0, 0, tzinfo=UTC), d(2028, 2)),
        (datetime(2028, 1, 31, 23, 59, 59, tzinfo=UTC), d(2028, 1)),
    ],
)
def test_month_for_timestamp_uses_london_calendar(instant, expected):
    assert svc.month_for_timestamp(instant) == expected


def test_month_for_timestamp_converts_other_offsets():
    from datetime import timedelta

    plus_two = timezone(timedelta(hours=2))
    assert svc.month_for_timestamp(datetime(2026, 11, 1, 1, 0, tzinfo=plus_two)) == d(2026, 10)  # 23:00Z on 31 Oct
    with pytest.raises(ValueError):
        svc.month_for_timestamp(datetime(2026, 10, 31, 12, 0))  # naive instants are ambiguous


def test_leap_february_2028_is_29_days():
    assert hours(d(2028, 2)) == 29 * 24
    assert svc.uk_month_bounds(d(2028, 2))[1].astimezone(UTC) == datetime(2028, 3, 1, 0, 0, tzinfo=UTC)
    assert svc.available_on(d(2028, 2)) == d(2028, 3, 7)
    assert svc.add_months(d(2028, 1), 1) == d(2028, 2)
    assert svc.add_months(d(2026, 12), 1) == d(2027, 1)
    assert svc.add_months(d(2026, 1), -1) == d(2025, 12)


def test_bounds_need_a_first_of_month_date():
    with pytest.raises(RegionMonthlyError) as raised:
        svc.uk_month_bounds(d(2026, 10, 2))
    assert raised.value.code == "months_malformed"


# --- the seventh-day rule ---------------------------------------------------


@pytest.mark.parametrize(
    ("period_month", "refused_at", "allowed_at"),
    [
        # October: BST has ended, 00:00 London on 7 Nov is 00:00Z.
        (d(2026, 10), datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC), datetime(2026, 11, 7, 0, 0, tzinfo=UTC)),
        # September: BST still applies on 7 Oct, so 00:00 London is 23:00Z on the 6th.
        (d(2026, 9), datetime(2026, 10, 6, 22, 59, 59, tzinfo=UTC), datetime(2026, 10, 6, 23, 0, tzinfo=UTC)),
        # March: the clocks went forward on 29 March, so 7 April 00:00 London is 23:00Z on the 6th.
        (d(2026, 3), datetime(2026, 4, 6, 22, 59, 59, tzinfo=UTC), datetime(2026, 4, 6, 23, 0, tzinfo=UTC)),
        # December into January.
        (d(2026, 12), datetime(2027, 1, 6, 23, 59, 59, tzinfo=UTC), datetime(2027, 1, 7, 0, 0, tzinfo=UTC)),
        # Leap February.
        (d(2028, 2), datetime(2028, 3, 6, 23, 59, 59, tzinfo=UTC), datetime(2028, 3, 7, 0, 0, tzinfo=UTC)),
    ],
)
def test_a_month_is_buildable_from_midnight_london_on_the_seventh(period_month, refused_at, allowed_at):
    assert svc.is_buildable(period_month, refused_at) is False
    assert svc.is_buildable(period_month, allowed_at) is True
    assert svc.is_buildable(period_month, allowed_at.replace(year=allowed_at.year + 1)) is True


def test_the_month_itself_and_the_sixth_are_never_buildable():
    assert svc.is_buildable(d(2026, 10), datetime(2026, 10, 31, 23, 0, tzinfo=UTC)) is False
    assert svc.is_buildable(d(2026, 10), datetime(2026, 11, 6, 12, 0, tzinfo=UTC)) is False
    assert svc.is_buildable(d(2026, 10), datetime(2026, 11, 7, 12, 0, tzinfo=UTC)) is True


def test_buildable_rule_refuses_a_naive_clock():
    with pytest.raises(ValueError):
        svc.is_buildable(d(2026, 10), datetime(2026, 11, 20, 12, 0))


def test_latest_buildable_month_tracks_the_seventh():
    assert svc.latest_buildable_month(NOW) == d(2026, 10)
    assert svc.latest_buildable_month(datetime(2026, 11, 6, 23, 59, tzinfo=UTC)) == d(2026, 9)
    assert svc.latest_buildable_month(datetime(2026, 11, 7, 0, 0, tzinfo=UTC)) == d(2026, 10)
    assert svc.latest_buildable_month(datetime(2027, 1, 3, 9, 0, tzinfo=UTC)) == d(2026, 11)


# --- coverage ---------------------------------------------------------------


def test_coverage_by_month_states_what_the_data_can_say():
    april = svc.metric_coverage(d(2026, 4))
    assert april["new_registrations"]["status"] == "available"
    assert april["ratings_published"]["status"] == "available"
    assert april["closures_observed"]["text"] == "not captured before 10 August 2026"
    assert april["reinstatements_observed"]["status"] == "not_captured_before"

    july = svc.metric_coverage(d(2026, 7))
    assert july["closures_observed"]["status"] == "not_captured_before"
    assert july["ratings_published"]["status"] == "available"

    august = svc.metric_coverage(d(2026, 8))
    assert august["ratings_published"]["status"] == "partial"
    assert august["ratings_published"]["boundary"] == "2026-08-11"
    assert august["closures_observed"]["status"] == "partial"
    assert august["closures_observed"]["boundary"] == "2026-08-10"

    september = svc.metric_coverage(d(2026, 9))
    assert september["ratings_published"]["text"] == "not available from the rating history table after 11 August 2026"
    assert september["ratings_published"]["status"] == "not_available_after"
    assert september["closures_observed"]["status"] == "available"
    assert svc.metric_coverage(d(2027, 3))["ratings_published"]["status"] == "not_available_after"


def test_coverage_refuses_months_before_the_first_supported_month():
    assert code_of(svc.metric_coverage, d(2026, 3)) == "month_before_earliest"


def test_the_ratings_window_matches_the_rating_vocabulary():
    # The SQL buckets four published values; they must be the repo's published set.
    from api.services.rating_states import PUBLISHED_RATING_VALUES
    from api.queries import region_monthly as q

    for value in PUBLISHED_RATING_VALUES:
        assert f"'{value}'" in q.MONTH_COUNTS


# --- hashing ----------------------------------------------------------------

ROW = {
    "new_registrations": 5,
    "outstanding": 1,
    "good": 2,
    "requires_improvement": 1,
    "inadequate": 1,
    "no_published_rating_value": 2,
    "ratings_total": 7,
    "closures_observed": 2,
    "reinstatements_observed": 1,
}


def test_hash_ignores_key_order_and_generation_time():
    a = svc._assemble(d(2026, 9), "London", None, ROW, datetime(2026, 10, 7, 6, 30, tzinfo=UTC))
    b = svc._assemble(d(2026, 9), "London", None, dict(reversed(list(ROW.items()))), datetime(2027, 5, 1, tzinfo=UTC))
    assert a.content_sha256 == b.content_sha256
    assert re.fullmatch(r"[0-9a-f]{64}", a.content_sha256)
    content = svc.canonical_content(d(2026, 9), "London", None, a.metrics, a.coverage, a.limits)
    shuffled = json.loads(json.dumps(content))
    assert svc.canonical_json(content) == svc.canonical_json(dict(reversed(list(shuffled.items()))))
    assert svc.content_sha256(content) == a.content_sha256
    assert "built_at" not in content and "build_version" not in content


def test_hash_changes_with_any_count_region_service_or_month():
    base = svc._assemble(d(2026, 9), "London", None, ROW, NOW)
    for changed in (
        svc._assemble(d(2026, 9), "London", None, {**ROW, "new_registrations": 6}, NOW),
        svc._assemble(d(2026, 9), "East", None, ROW, NOW),
        svc._assemble(d(2026, 9), "London", "home-care", ROW, NOW),
        svc._assemble(d(2026, 10), "London", None, ROW, NOW),
    ):
        assert changed.content_sha256 != base.content_sha256


def test_unavailable_metrics_are_null_not_zero():
    april = svc._assemble(d(2026, 4), "London", None, ROW, NOW)
    assert april.metrics["closures_observed"] is None
    assert april.metrics["reinstatements_observed"] is None
    assert april.metrics["ratings_published"]["total"] == 7
    september = svc._assemble(d(2026, 9), "London", None, ROW, NOW)
    assert september.metrics["ratings_published"] is None
    assert september.metrics["closures_observed"] == 2


# --- regions and services ---------------------------------------------------


def test_only_the_nine_england_regions_are_supported():
    assert len(svc.REGIONS) == 9
    assert svc.normalise_region("london") == "London"
    assert svc.normalise_region("  Yorkshire and Humberside ") == "Yorkshire & Humberside"
    assert svc.normalise_region("yorkshire & humberside") == "Yorkshire & Humberside"
    for bad in ("", "  ", "Wales", "Scotland", "England", "South", None):
        assert code_of(svc.normalise_region, bad) == "region_unsupported"


def test_services_are_the_site_taxonomy_slugs_and_nothing_else():
    slugs = svc.supported_services()
    assert slugs == tuple(e["slug"] for e in taxonomy())
    assert "home-care" in slugs and "residential-care-homes" in slugs and "dental-services" in slugs
    assert svc.normalise_service(None) is None and svc.normalise_service("  ") is None
    assert svc.normalise_service("home-care") == "home-care"
    for bad in ("homecare", "Domiciliary care service", "dentists", "all"):
        assert code_of(svc.normalise_service, bad) == "service_unsupported"
    # Raw CQC wording reaches a slug only through the shared alias map.
    assert "domiciliary care service" in resolve_service_filter("home-care")
    assert "supported living" in resolve_service_filter("supported-living")


# --- backfill planning ------------------------------------------------------


def test_backfill_plan_is_the_full_cross_product_in_a_fixed_order():
    plan = svc.plan_backfill(d(2026, 4), d(2026, 10), NOW)
    assert len(plan) == 7 * 9 * (1 + len(svc.supported_services()))
    assert plan[0] == svc.BuildTarget(d(2026, 4), "East", None)
    assert plan[1] == svc.BuildTarget(d(2026, 4), "East", sorted(svc.supported_services())[0])
    assert plan == sorted(plan, key=lambda t: (t.period_month, t.region, t.service_slug or ""))
    assert plan == svc.plan_backfill(d(2026, 4), d(2026, 10), NOW)
    assert {t.region for t in plan} == set(svc.REGIONS)


def test_backfill_plan_can_be_narrowed_and_deduplicates():
    plan = svc.plan_backfill(
        d(2026, 9), d(2026, 10), NOW, regions=["london", "London", "East"], services=[None, "home-care", "home-care"]
    )
    assert [(t.period_month, t.region, t.service_slug) for t in plan] == [
        (d(2026, 9), "East", None),
        (d(2026, 9), "East", "home-care"),
        (d(2026, 9), "London", None),
        (d(2026, 9), "London", "home-care"),
        (d(2026, 10), "East", None),
        (d(2026, 10), "East", "home-care"),
        (d(2026, 10), "London", None),
        (d(2026, 10), "London", "home-care"),
    ]


def test_backfill_refusals():
    assert code_of(svc.plan_backfill, d(2026, 3), d(2026, 10), NOW) == "month_before_earliest"
    assert code_of(svc.plan_backfill, d(2010, 4), d(2026, 10), NOW) == "month_before_earliest"
    assert code_of(svc.plan_backfill, d(2026, 4), d(2026, 11), NOW) == "month_not_yet_buildable"
    assert code_of(svc.plan_backfill, d(2026, 10), d(2026, 9), NOW) == "range_invalid"
    assert code_of(svc.plan_backfill, d(2026, 4), d(2026, 5), NOW, regions=["Wales"]) == "region_unsupported"
    assert code_of(svc.plan_backfill, d(2026, 4), d(2026, 5), NOW, regions=[""]) == "region_unsupported"
    assert code_of(svc.plan_backfill, d(2026, 4), d(2026, 5), NOW, services=["nonsense"]) == "service_unsupported"
    assert code_of(svc.plan_backfill, d(2026, 4, 2), d(2026, 5), NOW) == "months_malformed"


def test_backfill_obeys_the_seventh_day_rule_at_the_boundary():
    just_before = datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC)
    at_seventh = datetime(2026, 11, 7, 0, 0, tzinfo=UTC)
    assert code_of(svc.plan_backfill, d(2026, 10), d(2026, 10), just_before, regions=["London"]) == "month_not_yet_buildable"
    assert svc.plan_backfill(d(2026, 10), d(2026, 10), at_seventh, regions=["London"], services=[None])


# --- purchases --------------------------------------------------------------

BUILT_TO_OCT = [svc.add_months(d(2026, 4), i) for i in range(7)]  # April to October 2026


def buy(kind, first, **kw):
    kw.setdefault("region", "London")
    kw.setdefault("built_months", BUILT_TO_OCT)
    return svc.resolve_purchase(kind, first, NOW, **kw)


def test_prices_and_lengths_live_in_one_place():
    assert {k: (v.months, v.price_pence) for k, v in svc.PURCHASE_KINDS.items()} == {
        "single": (1, 4900),
        "six": (6, 24500),
        "twelve": (12, 44500),
    }
    literals = re.compile(r"\b(4900|24500|44500)\b")
    offenders = [
        str(path.relative_to(ROOT))
        for folder in ("api", "tools")
        for path in (ROOT / folder).rglob("*.py")
        if path.name != "region_monthly.py" and literals.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_single_six_and_twelve_month_purchases():
    one = buy("single", d(2026, 10))
    assert (one.price_pence, [m.period_month for m in one.months], one.future_months) == (4900, [d(2026, 10)], ())
    six = buy("six", d(2026, 5))
    assert six.price_pence == 24500
    assert [m.period_month for m in six.months] == [d(2026, m) for m in range(5, 11)]
    assert all(m.status == "built" and m.available_from is None for m in six.months)
    twelve = buy("twelve", d(2026, 11), region="East", accept_future_months=True)
    assert twelve.price_pence == 44500 and len(twelve.months) == 12
    assert twelve.months[0].period_month == d(2026, 11) and twelve.months[-1].period_month == d(2027, 10)
    assert all(m.status == "future" for m in twelve.months)


def test_future_months_are_listed_with_the_day_each_will_be_available():
    purchase = buy("six", d(2026, 8), accept_future_months=True)
    assert [(m.period_month, m.status, m.available_from) for m in purchase.months] == [
        (d(2026, 8), "built", None),
        (d(2026, 9), "built", None),
        (d(2026, 10), "built", None),
        (d(2026, 11), "future", d(2026, 12, 7)),
        (d(2026, 12), "future", d(2027, 1, 7)),
        (d(2027, 1), "future", d(2027, 2, 7)),
    ]
    assert [m.period_month for m in purchase.future_months] == [d(2026, 11), d(2026, 12), d(2027, 1)]


def test_future_months_need_explicit_acceptance():
    with pytest.raises(RegionMonthlyError) as raised:
        buy("six", d(2026, 8))
    assert raised.value.code == "future_months_not_accepted"
    assert "November 2026" in raised.value.message and "January 2027" in raised.value.message
    assert code_of(buy, "single", d(2026, 11)) == "future_months_not_accepted"


def test_a_purchase_cannot_reach_beyond_twelve_months_after_the_latest_buildable_month():
    twelve_ok = buy("twelve", d(2026, 11), accept_future_months=True)  # ends October 2027
    assert twelve_ok.months[-1].period_month == d(2027, 10)
    assert code_of(buy, "twelve", d(2026, 12), accept_future_months=True) == "future_months_too_far"
    assert code_of(buy, "single", d(2027, 11), accept_future_months=True) == "future_months_too_far"
    assert buy("single", d(2027, 10), accept_future_months=True).months[0].status == "future"
    # The horizon moves on the seventh: after 7 Dec, November is buildable too.
    later = datetime(2026, 12, 7, 0, 0, tzinfo=UTC)
    assert svc.resolve_purchase(
        "twelve", d(2026, 12), later, region="East", built_months=BUILT_TO_OCT + [d(2026, 11)], accept_future_months=True
    )


def test_a_past_month_that_can_be_built_but_is_not_built_is_refused():
    assert code_of(buy, "single", d(2026, 10), built_months=[]) == "month_not_built"
    assert code_of(buy, "six", d(2026, 5), built_months=[m for m in BUILT_TO_OCT if m != d(2026, 7)]) == "month_not_built"
    # A gap blocks the sale even when future months are accepted.
    assert code_of(buy, "six", d(2026, 7), built_months=[], accept_future_months=True) == "month_not_built"


def test_months_before_the_first_supported_month_are_refused():
    assert code_of(buy, "single", d(2026, 3)) == "month_before_earliest"
    assert code_of(buy, "six", d(2025, 12)) == "month_before_earliest"
    assert code_of(buy, "twelve", d(2010, 4), accept_future_months=True) == "month_before_earliest"
    assert buy("single", d(2026, 4)).months[0].status == "built"


def test_unsupported_region_service_and_kind_are_refused_before_anything_else():
    for region in ("Wales", "", "Northern Ireland"):
        assert code_of(buy, "single", d(2026, 10), region=region) == "region_unsupported"
    assert code_of(buy, "single", d(2026, 10), service_slug="spa") == "service_unsupported"
    for kind in ("", "monthly", "SIX", "3", None):
        assert code_of(buy, kind, d(2026, 10)) == "kind_unsupported"


def test_malformed_and_non_consecutive_requests_are_refused():
    assert code_of(buy, "single", d(2026, 10, 15)) == "months_malformed"
    assert code_of(buy, "single", "2026-10") == "months_malformed"
    assert code_of(buy, "single", datetime(2026, 10, 1, tzinfo=UTC)) == "months_malformed"
    run = [d(2026, 4), d(2026, 5), d(2026, 6), d(2026, 7), d(2026, 8), d(2026, 9)]
    assert buy("six", d(2026, 4), months=run).price_pence == 24500
    assert code_of(buy, "six", d(2026, 4), months=[d(2026, 4), d(2026, 6), d(2026, 7), d(2026, 8), d(2026, 9), d(2026, 10)]) == "months_not_consecutive"
    assert code_of(buy, "six", d(2026, 4), months=list(reversed(run))) == "months_not_consecutive"
    assert code_of(buy, "six", d(2026, 5), months=run) == "months_not_consecutive"
    assert code_of(buy, "six", d(2026, 4), months=run[:5]) == "months_count_mismatch"
    assert code_of(buy, "single", d(2026, 4), months=run[:2]) == "months_count_mismatch"
    assert code_of(buy, "six", d(2026, 4), months=[*run[:5], d(2026, 9, 2)]) == "months_malformed"


def test_months_parameter_parsing():
    assert svc.parse_months_param("2026-04") == [d(2026, 4)]
    assert svc.parse_months_param("2026-04, 2026-05") == [d(2026, 4), d(2026, 5)]
    for bad in ("", "2026-4", "2026-13", "2026-00", "April 2026", "2026-04,", ",2026-04", "1999-01", ",".join(["2026-04"] * 13)):
        assert code_of(svc.parse_months_param, bad) == "months_malformed"


def test_every_refusal_code_has_a_plain_message_and_a_status():
    triggered = {
        code_of(svc.normalise_region, "Wales"),
        code_of(svc.normalise_service, "x"),
        code_of(svc.require_kind, "x"),
        code_of(svc.parse_month, "x"),
        code_of(svc.plan_backfill, d(2026, 10), d(2026, 9), NOW),
        code_of(buy, "six", d(2026, 4), months=[d(2026, 4), d(2026, 6)] + [d(2026, 7)] * 4),
        code_of(buy, "six", d(2026, 4), months=[d(2026, 4)]),
        code_of(buy, "single", d(2026, 3)),
        code_of(buy, "single", d(2026, 10), built_months=[]),
        code_of(buy, "single", d(2026, 11)),
        code_of(buy, "single", d(2028, 1), accept_future_months=True),
        code_of(svc.plan_backfill, d(2026, 4), d(2026, 11), NOW),
        "source_unavailable",
    }
    assert triggered == set(svc.REFUSAL_MESSAGES) == set(svc.REFUSAL_STATUS)
    for code in svc.REFUSAL_MESSAGES:
        err = RegionMonthlyError(code, regions="East", expected=6, month="June 2026", earliest="April 2026", months="June 2026",
                                 latest="October 2027", limit=12, available="7 December 2026")
        assert err.message and "{" not in err.message and err.code == code
        assert 400 <= err.status_code < 600


async def test_build_month_refuses_before_reading_when_a_source_table_is_missing_or_too_early():
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=False)
    with pytest.raises(RegionMonthlyError) as raised:
        await svc.build_month(conn, d(2026, 10), "London", None, NOW)
    assert raised.value.code == "source_unavailable"
    conn.fetchrow.assert_not_called()
    for month, as_of, code in (
        (d(2026, 10), datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC), "month_not_yet_buildable"),
        (d(2026, 3), NOW, "month_before_earliest"),
    ):
        with pytest.raises(RegionMonthlyError) as raised:
            await svc.build_month(conn, month, "London", None, as_of)
        assert raised.value.code == code
    with pytest.raises(RegionMonthlyError) as raised:
        await svc.build_month(conn, d(2026, 10), "Wales", None, NOW)
    assert raised.value.code == "region_unsupported"
    conn.fetchrow.assert_not_called()


# --- the preview and the words it uses --------------------------------------


def test_coverage_preview_lists_months_future_dates_coverage_and_limits():
    preview = svc.coverage_preview(
        "six", d(2026, 8), NOW, region="london", service_slug="home-care", built_months=BUILT_TO_OCT, accept_future_months=True
    )
    assert (preview["region"], preview["service"], preview["kind"]) == ("London", "home-care", "six")
    assert preview["price_pence"] == 24500 and preview["currency"] == "gbp" and preview["month_count"] == 6
    assert [m["month"] for m in preview["months"]] == ["2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01"]
    assert [m["status"] for m in preview["months"]] == ["built"] * 3 + ["future"] * 3
    assert preview["future_months"] == ["2026-11", "2026-12", "2027-01"]
    assert [m["available_from"] for m in preview["months"]][3:] == ["2026-12-07", "2027-01-07", "2027-02-07"]
    assert preview["months"][0]["coverage"]["ratings_published"]["status"] == "partial"
    assert preview["months"][1]["coverage"]["ratings_published"]["text"] == "not available from the rating history table after 11 August 2026"
    assert preview["limits"] == list(svc.LIMITS)
    assert preview["future_month_notice"] == svc.FUTURE_MONTH_NOTICE
    assert preview["summary"] == "August 2026 to January 2027: 3 built, 3 to be built (first on 7 December 2026)."
    assert [m["key"] for m in preview["metrics"]] == list(svc.METRICS)


def test_coverage_preview_for_built_months_only_has_no_future_notice():
    preview = svc.coverage_preview("single", d(2026, 10), NOW, region="East", built_months=BUILT_TO_OCT)
    assert preview["future_months"] == [] and preview["future_month_notice"] is None
    assert preview["summary"] == "October 2026: 1 built."


def test_coverage_preview_raises_the_same_refusals():
    assert code_of(svc.coverage_preview, "six", d(2026, 8), NOW, region="London", built_months=BUILT_TO_OCT) == "future_months_not_accepted"


FORBIDDEN_WORDS = re.compile(r"\bcomplete(?:ly|ness)?\b|\bevery\b|all history|\btrends?\b|\blikely\b|\bforecasts?\b", re.IGNORECASE)


def customer_strings(preview) -> list[str]:
    strings = [*svc.LIMITS, svc.FUTURE_MONTH_NOTICE, *svc.METRIC_DEFINITIONS.values(), *svc.METRIC_LABELS.values()]
    strings += [m.format(regions="East", expected=1, month="May 2026", earliest="April 2026", months="May 2026",
                         latest="October 2027", limit=12, available="7 June 2026") for m in svc.REFUSAL_MESSAGES.values()]
    strings.append(preview["summary"])
    for row in preview["months"]:
        strings += [c["text"] for c in row["coverage"].values()]
    return strings


def test_customer_text_makes_no_completeness_or_trend_claims():
    preview = svc.coverage_preview(
        "six", d(2026, 8), NOW, region="London", built_months=BUILT_TO_OCT, accept_future_months=True
    )
    for text in customer_strings(preview):
        assert not FORBIDDEN_WORDS.search(text), text
    joined = " ".join(svc.LIMITS)
    assert "only the locations CareGist holds" in joined
    assert "once under each of its service types" in joined
    assert "Do not add the service figures together" in joined
    assert "10 August 2026" in joined and "31 March 2026" in joined and "11 August 2026" in joined
    assert "not the date CQC removed or restored the registration" in joined


def test_the_design_note_carries_the_limits_and_every_refusal_code_verbatim():
    note = (ROOT / "docs/region-monthly-v1.md").read_text(encoding="utf-8")
    for limit in svc.LIMITS:
        assert limit in note
    assert svc.FUTURE_MONTH_NOTICE in note
    for code, template in svc.REFUSAL_MESSAGES.items():
        assert f"| `{code}` | {svc.REFUSAL_STATUS[code]} | {template} |" in note
    for label in svc.METRIC_LABELS.values():
        assert label in note
    assert "074_region_monthly_builds.sql" in note and "4900" in note and "24500" in note and "44500" in note


def test_repo_language_guard_accepts_the_new_customer_facing_files():
    paths = [
        ROOT / "api/services/region_monthly.py",
        ROOT / "api/routers/region_monthly.py",
        ROOT / "api/queries/region_monthly.py",
        ROOT / "tools/build_region_monthly.py",
    ]
    assert scan_paths(paths) == []


# --- the flag-gated route ---------------------------------------------------

BASE = "/api/v1/region-monthly/coverage"


def conn_factory(*, table_present=True, built=BUILT_TO_OCT):
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=table_present)
    conn.fetch = AsyncMock(return_value=[{"period_month": m} for m in built])

    @asynccontextmanager
    async def get_connection():
        yield conn

    return conn, get_connection


async def get(path, factory, *, enabled=True):
    with patch("api.routers.region_monthly.get_connection", factory), patch(
        "api.routers.region_monthly.settings.region_monthly_enabled", enabled
    ), patch("api.routers.region_monthly._now", return_value=NOW):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            return await client.get(path)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    ip_rate_limit._public_ip_requests.clear()
    yield
    ip_rate_limit._public_ip_requests.clear()


def test_the_flag_defaults_off():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert cfg.region_monthly_enabled is False


async def test_flag_off_is_the_same_plain_404_as_an_unknown_route_and_reads_nothing():
    conn, factory = conn_factory()
    off = await get(f"{BASE}?region=London&kind=single&first_month=2026-10", factory, enabled=False)
    unknown = await get("/api/v1/no-such-route", factory, enabled=False)
    assert off.status_code == 404 == unknown.status_code
    assert off.json() == unknown.json() == {"detail": "Not Found"}
    conn.fetchval.assert_not_called()
    conn.fetch.assert_not_called()
    # Even a refusal-shaped request reveals nothing while the flag is off.
    bad = await get(f"{BASE}?region=Wales&kind=nope", factory, enabled=False)
    assert bad.status_code == 404 and bad.json() == {"detail": "Not Found"}


async def test_preview_for_built_months():
    conn, factory = conn_factory()
    resp = await get(f"{BASE}?region=London&service=home-care&kind=six&first_month=2026-05", factory)
    assert resp.status_code == 200
    body = resp.json()
    assert body["price_pence"] == 24500 and body["future_months"] == []
    assert [m["month"] for m in body["months"]] == ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    conn.fetch.assert_awaited_once()
    assert conn.fetch.await_args.args[1:] == ("London", "home-care")


async def test_preview_with_future_months_needs_acceptance_and_lists_them():
    _, factory = conn_factory()
    refused = await get(f"{BASE}?region=London&kind=six&first_month=2026-08", factory)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "future_months_not_accepted"
    ok = await get(f"{BASE}?region=London&kind=six&first_month=2026-08&accept_future_months=true", factory)
    assert ok.status_code == 200
    assert ok.json()["future_months"] == ["2026-11", "2026-12", "2027-01"]
    assert ok.json()["months"][-1]["available_from"] == "2027-02-07"


async def test_a_list_of_months_is_not_accepted_only_one_first_month_is():
    _, factory = conn_factory()
    resp = await get(f"{BASE}?region=London&kind=six&first_month=2026-05,2026-06", factory)
    assert (resp.status_code, resp.json()["detail"]["code"]) == (422, "months_malformed")


@pytest.mark.parametrize(
    ("query", "status", "code"),
    [
        ("region=Wales&kind=single&first_month=2026-10", 422, "region_unsupported"),
        ("region=&kind=single&first_month=2026-10", 422, "region_unsupported"),
        ("kind=single&first_month=2026-10", 422, "region_unsupported"),
        ("region=London&service=spa&kind=single&first_month=2026-10", 422, "service_unsupported"),
        ("region=London&kind=yearly&first_month=2026-10", 422, "kind_unsupported"),
        ("region=London&kind=single", 422, "months_malformed"),
        ("region=London&kind=single&first_month=October", 422, "months_malformed"),
        ("region=London&kind=single&first_month=2026-03", 422, "month_before_earliest"),
        ("region=London&kind=twelve&first_month=2026-12&accept_future_months=true", 422, "future_months_too_far"),
    ],
)
async def test_refusals_carry_a_stable_code_and_a_plain_message(query, status, code):
    _, factory = conn_factory()
    resp = await get(f"{BASE}?{query}", factory)
    assert resp.status_code == status
    detail = resp.json()["detail"]
    assert detail["code"] == code
    assert detail["message"] and "{" not in detail["message"]


async def test_an_unbuilt_past_month_is_refused_with_409():
    _, factory = conn_factory(built=[d(2026, 4)])
    resp = await get(f"{BASE}?region=London&kind=single&first_month=2026-10", factory)
    assert (resp.status_code, resp.json()["detail"]["code"]) == (409, "month_not_built")


async def test_a_missing_builds_table_fails_closed():
    _, factory = conn_factory(table_present=False)
    resp = await get(f"{BASE}?region=London&kind=single&first_month=2026-10", factory)
    assert (resp.status_code, resp.json()["detail"]["code"]) == (503, "source_unavailable")


async def test_the_public_rate_limit_applies():
    statuses = []
    for _ in range(ip_rate_limit._MAX_PUBLIC_PER_MINUTE + 1):
        _, factory = conn_factory()
        statuses.append((await get(f"{BASE}?region=London&kind=single&first_month=2026-10", factory)).status_code)
    assert statuses[-1] == 429 and set(statuses[:-1]) == {200}


# --- the build command ------------------------------------------------------


def test_the_command_needs_exactly_one_of_dry_run_and_write():
    with pytest.raises(SystemExit):
        cli.parse_args([])
    with pytest.raises(SystemExit):
        cli.parse_args(["--dry-run", "--write"])
    assert cli.parse_args(["--dry-run"]).write is False
    assert cli.parse_args(["--write"]).write is True


def test_the_command_plans_the_latest_buildable_month_by_default():
    args = cli.parse_args(["--dry-run", "--regions", "London", "--services", "all-services,home-care"])
    plan = cli.plan_from_args(args, NOW)
    assert [(t.period_month, t.region, t.service_slug) for t in plan] == [(d(2026, 10), "London", None), (d(2026, 10), "London", "home-care")]
    ranged = cli.plan_from_args(cli.parse_args(["--dry-run", "--from-month", "2026-08", "--period-month", "2026-09", "--regions", "East"]), NOW)
    assert {t.period_month for t in ranged} == {d(2026, 8), d(2026, 9)}


def test_the_command_refuses_unsupported_input():
    for argv in (["--regions", "Wales"], ["--services", "nope"], ["--period-month", "2026-11"], ["--period-month", "2026-03"],
                 ["--period-month", "soon"], ["--from-month", "2026-10", "--period-month", "2026-09"]):
        with pytest.raises(RegionMonthlyError):
            cli.plan_from_args(cli.parse_args(["--dry-run", *argv]), NOW)


def test_the_command_needs_a_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert cli.main(["--dry-run"]) == cli.EXIT_REFUSED
    assert "database URL" in capsys.readouterr().err


# --- the workflow -----------------------------------------------------------

WORKFLOW = ROOT / ".github/workflows/region-monthly-build.yml"


def workflow():
    source = WORKFLOW.read_text(encoding="utf-8")
    return yaml.load(source, Loader=yaml.BaseLoader), source


def test_workflow_is_dispatch_only_with_the_schedule_commented_out():
    loaded, source = workflow()
    assert list(loaded["on"]) == ["workflow_dispatch"]
    assert "schedule" not in loaded["on"]
    assert '#   - cron: "30 6 7 * *"' in source
    assert not re.search(r"^\s*schedule:", source, re.MULTILINE)
    assert not re.search(r"^\s*-\s*cron:", source, re.MULTILINE)
    header = source.split("\non:")[0]
    assert "NOT ENABLED FOR SCHEDULING" in header and "Do not enable it until the owner has approved" in header
    assert loaded["on"]["workflow_dispatch"]["inputs"]["dry_run"]["default"] == "true"
    assert "period_month" in loaded["on"]["workflow_dispatch"]["inputs"]
    assert loaded["permissions"] == {"contents": "read"}


def test_workflow_writes_only_with_dry_run_false_from_main_and_approval():
    loaded, source = workflow()
    guard = "\n".join(s["run"] for s in loaded["jobs"]["validate-inputs"]["steps"])
    assert 'EXECUTING_REF"] != "refs/heads/main"' in guard
    assert "WRITES_APPROVED" in guard and "REGION_MONTHLY_BUILD_APPROVED" in source
    assert loaded["jobs"]["build"]["needs"] == "validate-inputs" == loaded["jobs"]["dry-run"]["needs"]
    assert "inputs.dry_run == false" in loaded["jobs"]["build"]["if"]
    assert loaded["jobs"]["dry-run"]["if"].endswith("inputs.dry_run")
    build_run = "\n".join(s.get("run", "") for s in loaded["jobs"]["build"]["steps"])
    dry_run = "\n".join(s.get("run", "") for s in loaded["jobs"]["dry-run"]["steps"])
    assert "--write" in build_run and "--dry-run" not in build_run
    assert "--dry-run" in dry_run and "--write" not in dry_run
    assert "${{" not in build_run + dry_run  # inputs reach the shell only through env


def test_workflow_actions_are_pinned_to_full_commit_shas():
    loaded, source = workflow()
    uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)", source, re.MULTILINE)
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", ref), ref
    # The same pins the other workflows already use.
    known = set(re.findall(r"uses:\s*(\S+@[0-9a-f]{40})", (ROOT / ".github/workflows/cqc-reconciliation.yml").read_text()))
    assert set(uses) <= known


def test_every_workflow_in_the_repo_pins_action_shas():
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for ref in re.findall(r"^\s*-?\s*uses:\s*(\S+)", path.read_text(encoding="utf-8"), re.MULTILINE):
            if ref.startswith("./"):
                continue
            assert re.fullmatch(r"[\w./-]+@[0-9a-f]{40}", ref), f"{path.name}: {ref}"
