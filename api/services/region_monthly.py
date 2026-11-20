"""Region Monthly: a monthly, versioned set of counts for one England region and
one service type (stage 1: build, store and preview; no payment, no download).

A month means a UK calendar month (Europe/London). It is built on the 7th day of
the FOLLOWING month, so every month's record has a seven-day lag. Customers will
buy access to specific months; a future month can be bought only when the
purchase says so explicitly, and it can be downloaded only after it is built.

Everything here is a count, a date or a quoted source value. There are no
scores, rankings, forecasts or trend claims, and the archive is never described
as complete. The data holds less than a naive reading suggests, and each gap is
stated as a fixed template (``LIMITS``) and per metric (``metric_coverage``):

* new registrations come from ``care_providers.registration_date`` and can be
  stated for any month, for the locations CareGist holds;
* ratings come from ``provider_rating_history``, which CareGist began to fill on
  31 March 2026 and whose inspection dates end on 11 August 2026; later months
  are "not available after" that date. Ledger ``rating_status_changed`` events
  have different meaning and are never mixed in;
* closures and reinstatements come from ledger ``status_changed`` events that
  CareGist observed from 10 August 2026. Earlier months are "not captured";
* ``ownership_changed`` ledger rows are a seeding artefact and are never used.

The pure functions (month maths, coverage, backfill planning, purchase
resolution, hashing) do no I/O; ``build_month`` and ``store_build`` take an
asyncpg connection.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

from api.queries import region_monthly as q
from api.service_taxonomy import resolve_service_filter, taxonomy

UK = ZoneInfo("Europe/London")
UTC = timezone.utc

SCHEMA_VERSION = 1

# The nine regions of England, spelled exactly as ``care_providers.region`` holds
# them. The empty region and "Wales" also exist in that column and are refused.
REGIONS: tuple[str, ...] = (
    "East",
    "East Midlands",
    "London",
    "North East",
    "North West",
    "South East",
    "South West",
    "West Midlands",
    "Yorkshire & Humberside",
)

# The first month the product covers. CareGist began recording ratings on
# 31 March 2026, so April 2026 is the first month wholly after capture began:
# its ratings were recorded as they appeared, not read back from ratings that
# were still current on the day recording began. Registrations alone could go
# back to April 2010, but a product that quietly changes meaning month to month
# would be worse than a shorter one. This is an owner decision to confirm.
EARLIEST_SUPPORTED_MONTH = date(2026, 4, 1)

# provider_rating_history was first filled on this date.
RATING_HISTORY_CAPTURE_FROM = date(2026, 3, 31)
# The last inspection date in provider_rating_history. Rating records after it
# are not read (see module docstring). Move it only with a reviewed change that
# defines a clean rule for later months.
RATING_HISTORY_AVAILABLE_THROUGH = date(2026, 8, 11)
# The first day CareGist observed ledger status changes.
STATUS_EVENTS_OBSERVED_FROM = date(2026, 8, 10)

BUILD_DAY = 7
# A purchase may not reach further than this many months beyond the latest month
# that can already be built.
MAX_MONTHS_AHEAD = 12

CURRENCY = "gbp"


@dataclass(frozen=True)
class PurchaseKind:
    months: int
    price_pence: int


# The one place the prices and bundle lengths live. Stage 2 (checkout) must read
# them from here and from nowhere else.
PURCHASE_KINDS: dict[str, PurchaseKind] = {
    "single": PurchaseKind(months=1, price_pence=4900),
    "six": PurchaseKind(months=6, price_pence=24500),
    "twelve": PurchaseKind(months=12, price_pence=44500),
}

METRICS = ("new_registrations", "ratings_published", "closures_observed", "reinstatements_observed")

METRIC_LABELS = {
    "new_registrations": "New registrations",
    "ratings_published": "Ratings published",
    "closures_observed": "Closures observed",
    "reinstatements_observed": "Reinstatements observed",
}

METRIC_DEFINITIONS = {
    "new_registrations": (
        "Locations whose CQC registration date falls in the month. The date is the registration date "
        "CQC publishes."
    ),
    "ratings_published": (
        "Overall rating records CareGist holds with an inspection date in the month, counted by rating value. "
        "A record with no published rating value is counted separately."
    ),
    "closures_observed": (
        "Changes from active to inactive that CareGist saw in CQC data during the month. "
        "The date is when CareGist saw the change."
    ),
    "reinstatements_observed": (
        "Changes from inactive back to active that CareGist saw in CQC data during the month. "
        "The date is when CareGist saw the change."
    ),
}

# Fixed limits, stored with every build and shown in the preview. Verbatim; a
# change to this text is a new schema_version, because the text is hashed.
LIMITS: tuple[str, ...] = (
    "These figures are counts and dates only. They are not scores, rankings or predictions.",
    "They cover only the locations CareGist holds. CareGist holds locations that are on the CQC register and "
    "locations recorded as no longer active. It does not hold other locations CQC registered in the past.",
    "Region and service type are the values CareGist holds on the build date. They are not the values on the "
    "date of the event.",
    "A location with more than one service type is counted once under each of its service types. Do not add "
    "the service figures together to get a regional figure. The regional figure for all services counts each "
    "location once.",
    "Ratings published counts the rating records CareGist holds. CareGist began recording ratings on "
    "31 March 2026. After that date a rating is recorded when the published rating differs from the previous "
    "one, so an inspection that confirmed the same rating may not be counted. Rating records with an "
    "inspection date after 11 August 2026 are not available.",
    "Closures observed and reinstatements observed begin on 10 August 2026. The date is the date CareGist "
    "saw the change. It is not the date CQC removed or restored the registration.",
    "Locations that CareGist could not confirm against CQC data are left out.",
    "A month is built on the 7th day of the following month. If a month is corrected, the correction is a "
    "new numbered version and the earlier version is kept.",
)

FUTURE_MONTH_NOTICE = (
    "A future month can be downloaded only after it has been built, on the 7th day of the following month."
)


# --- refusals ---------------------------------------------------------------

REFUSAL_MESSAGES: dict[str, str] = {
    "region_unsupported": "That region is not available. Region Monthly covers these regions of England: {regions}.",
    "service_unsupported": "That service type is not available. Use one of the service names listed by CareGist.",
    "kind_unsupported": "That purchase length is not available. Choose one month, six months or twelve months.",
    "months_malformed": "The months could not be read. Give months as YYYY-MM, for example 2026-10.",
    "months_not_consecutive": "The months must follow each other with no gaps, in date order.",
    "months_count_mismatch": "The number of months does not match the purchase length: {expected} expected.",
    "month_before_earliest": "{month} is before the first month available, {earliest}.",
    "month_not_built": "{month} has not been built yet, so it cannot be sold. Please try again later.",
    "future_months_not_accepted": (
        "This purchase includes months that are not built yet: {months}. "
        "Confirm that you accept them to continue."
    ),
    "future_months_too_far": (
        "A purchase cannot include months after {latest}. That is {limit} months beyond the latest month "
        "that can be built."
    ),
    "month_not_yet_buildable": "{month} can be built from {available}.",
    "range_invalid": "The first month must not be after the last month.",
    "source_unavailable": "Region Monthly is unavailable because a required data source is missing.",
}

# HTTP status used by the API for each refusal code.
REFUSAL_STATUS: dict[str, int] = {
    "region_unsupported": 422,
    "service_unsupported": 422,
    "kind_unsupported": 422,
    "months_malformed": 422,
    "months_not_consecutive": 422,
    "months_count_mismatch": 422,
    "month_before_earliest": 422,
    "month_not_built": 409,
    "future_months_not_accepted": 409,
    "future_months_too_far": 422,
    "month_not_yet_buildable": 409,
    "range_invalid": 422,
    "source_unavailable": 503,
}


class RegionMonthlyError(Exception):
    """A refusal with a stable machine code and a plain-English message."""

    def __init__(self, code: str, **fields: Any) -> None:
        template = REFUSAL_MESSAGES[code]
        self.code = code
        self.fields = fields
        self.message = template.format(**fields)
        super().__init__(self.message)

    @property
    def status_code(self) -> int:
        return REFUSAL_STATUS[self.code]


# --- months and UK time -----------------------------------------------------


def format_month(period_month: date) -> str:
    return f"{period_month.strftime('%B')} {period_month.year}"


def format_day(day: date) -> str:
    return f"{day.day} {day.strftime('%B')} {day.year}"


def month_key(period_month: date) -> str:
    return f"{period_month.year:04d}-{period_month.month:02d}"


def first_of_month(day: date) -> date:
    return date(day.year, day.month, 1)


def add_months(period_month: date, count: int) -> date:
    index = period_month.year * 12 + (period_month.month - 1) + count
    return date(index // 12, index % 12 + 1, 1)


def month_range(first_month: date, count: int) -> list[date]:
    return [add_months(first_month, i) for i in range(count)]


def _require_month(value: Any) -> date:
    """A first-of-month date, or a ``months_malformed`` refusal."""
    if isinstance(value, datetime) or not isinstance(value, date) or value.day != 1:
        raise RegionMonthlyError("months_malformed")
    return value


def parse_month(text: str) -> date:
    match = re.fullmatch(r"(\d{4})-(\d{2})", (text or "").strip())
    if not match:
        raise RegionMonthlyError("months_malformed")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12 or year < 2000:
        raise RegionMonthlyError("months_malformed")
    return date(year, month, 1)


def uk_month_bounds(period_month: date) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of a month as UK-time instants.

    Months start at 00:00 Europe/London, so a month's length in hours changes
    with the clock: October 2026 is 745 hours, March 2026 is 743.
    """
    first = _require_month(period_month)
    return (
        datetime(first.year, first.month, 1, tzinfo=UK),
        datetime.combine(add_months(first, 1), datetime.min.time(), tzinfo=UK),
    )


def month_for_timestamp(ts: datetime) -> date:
    """The UK calendar month (first day) an instant falls in."""
    if not isinstance(ts, datetime) or ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError("month_for_timestamp needs a timezone-aware datetime")
    local = ts.astimezone(UK)
    return date(local.year, local.month, 1)


def available_on(period_month: date) -> date:
    """The day a month is built: the 7th of the following month."""
    following = add_months(_require_month(period_month), 1)
    return date(following.year, following.month, BUILD_DAY)


def buildable_from(period_month: date) -> datetime:
    """The first instant a month may be built: 00:00 UK time on the 7th."""
    day = available_on(period_month)
    return datetime(day.year, day.month, day.day, tzinfo=UK)


def is_buildable(period_month: date, now: datetime) -> bool:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("is_buildable needs a timezone-aware 'now'")
    return now >= buildable_from(period_month)


def latest_buildable_month(now: datetime) -> date:
    """The newest month that may be built at ``now``."""
    month = month_for_timestamp(now)
    while not is_buildable(month, now):
        month = add_months(month, -1)
    return month


# --- regions, services ------------------------------------------------------


def normalise_region(value: str | None) -> str:
    key = " ".join((value or "").replace("&", " & ").split()).casefold().replace(" and ", " & ")
    for region in REGIONS:
        if region.casefold() == key:
            return region
    raise RegionMonthlyError("region_unsupported", regions=", ".join(REGIONS))


def supported_services() -> tuple[str, ...]:
    """Canonical service slugs from the site taxonomy; nothing is added here."""
    return tuple(entry["slug"] for entry in taxonomy())


def normalise_service(value: str | None) -> str | None:
    """A canonical slug, or None for all services."""
    if value is None or not value.strip():
        return None
    slug = value.strip()
    if slug not in supported_services():
        raise RegionMonthlyError("service_unsupported")
    return slug


def require_kind(kind: str) -> PurchaseKind:
    spec = PURCHASE_KINDS.get(kind) if isinstance(kind, str) else None
    if spec is None:
        raise RegionMonthlyError("kind_unsupported")
    return spec


# --- coverage ---------------------------------------------------------------

AVAILABLE = "available"
PARTIAL = "partial"
NOT_CAPTURED_BEFORE = "not_captured_before"
NOT_AVAILABLE_AFTER = "not_available_after"


def _coverage_entry(status: str, boundary: date | None = None) -> dict[str, Any]:
    if status == AVAILABLE:
        text = "available"
    elif status == NOT_CAPTURED_BEFORE:
        text = f"not captured before {format_day(boundary)}"  # type: ignore[arg-type]
    elif status == NOT_AVAILABLE_AFTER:
        text = f"not available from the rating history table after {format_day(boundary)}"  # type: ignore[arg-type]
    else:
        text = "partial"
    return {"status": status, "boundary": boundary.isoformat() if boundary else None, "text": text}


def metric_coverage(period_month: date) -> dict[str, dict[str, Any]]:
    """What the data can say about each metric for one month. Pure."""
    first = _require_month(period_month)
    if first < EARLIEST_SUPPORTED_MONTH:
        raise RegionMonthlyError("month_before_earliest", month=format_month(first), earliest=format_month(EARLIEST_SUPPORTED_MONTH))
    last = add_months(first, 1) - timedelta(days=1)

    ratings = _coverage_entry(AVAILABLE)
    if first > RATING_HISTORY_AVAILABLE_THROUGH:
        ratings = _coverage_entry(NOT_AVAILABLE_AFTER, RATING_HISTORY_AVAILABLE_THROUGH)
    elif last > RATING_HISTORY_AVAILABLE_THROUGH:
        ratings = _coverage_entry(PARTIAL, RATING_HISTORY_AVAILABLE_THROUGH)
        ratings["text"] = f"partial: rating records up to {format_day(RATING_HISTORY_AVAILABLE_THROUGH)} only"

    status_moves = _coverage_entry(AVAILABLE)
    if last < STATUS_EVENTS_OBSERVED_FROM:
        status_moves = _coverage_entry(NOT_CAPTURED_BEFORE, STATUS_EVENTS_OBSERVED_FROM)
    elif first < STATUS_EVENTS_OBSERVED_FROM:
        status_moves = _coverage_entry(PARTIAL, STATUS_EVENTS_OBSERVED_FROM)
        status_moves["text"] = f"partial: observed from {format_day(STATUS_EVENTS_OBSERVED_FROM)} only"

    return {
        "new_registrations": _coverage_entry(AVAILABLE),
        "ratings_published": ratings,
        "closures_observed": dict(status_moves),
        "reinstatements_observed": dict(status_moves),
    }


# --- hashing ----------------------------------------------------------------


def canonical_content(
    period_month: date,
    region: str,
    service_slug: str | None,
    metrics: dict[str, Any],
    coverage: dict[str, Any],
    limits: Sequence[str],
    schema_version: int = SCHEMA_VERSION,
) -> dict[str, Any]:
    """The hashed content. It holds no generation time, version or row id."""
    return {
        "schema_version": schema_version,
        "period_month": period_month.isoformat(),
        "region": region,
        "service_slug": service_slug,
        "metrics": metrics,
        "coverage": coverage,
        "limits": list(limits),
    }


def canonical_json(content: dict[str, Any]) -> str:
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(content: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


# --- building ---------------------------------------------------------------


@dataclass(frozen=True)
class BuiltMonth:
    period_month: date
    region: str
    service_slug: str | None
    metrics: dict[str, Any]
    coverage: dict[str, Any]
    limits: tuple[str, ...]
    content_sha256: str
    built_from_data_cutoff: datetime
    schema_version: int = SCHEMA_VERSION


def _check_buildable_month(period_month: date, as_of: datetime) -> date:
    first = _require_month(period_month)
    if first < EARLIEST_SUPPORTED_MONTH:
        raise RegionMonthlyError("month_before_earliest", month=format_month(first), earliest=format_month(EARLIEST_SUPPORTED_MONTH))
    if not is_buildable(first, as_of):
        raise RegionMonthlyError("month_not_yet_buildable", month=format_month(first), available=format_day(available_on(first)))
    return first


def _assemble(
    period_month: date,
    region: str,
    service_slug: str | None,
    row: Any,
    as_of: datetime,
) -> BuiltMonth:
    coverage = metric_coverage(period_month)
    metrics: dict[str, Any] = {
        "new_registrations": int(row["new_registrations"]),
        "ratings_published": None,
        "closures_observed": None,
        "reinstatements_observed": None,
    }
    if coverage["ratings_published"]["status"] != NOT_AVAILABLE_AFTER:
        metrics["ratings_published"] = {
            "outstanding": int(row["outstanding"]),
            "good": int(row["good"]),
            "requires_improvement": int(row["requires_improvement"]),
            "inadequate": int(row["inadequate"]),
            "no_published_rating_value": int(row["no_published_rating_value"]),
            "total": int(row["ratings_total"]),
        }
    if coverage["closures_observed"]["status"] != NOT_CAPTURED_BEFORE:
        metrics["closures_observed"] = int(row["closures_observed"])
        metrics["reinstatements_observed"] = int(row["reinstatements_observed"])
    content = canonical_content(period_month, region, service_slug, metrics, coverage, LIMITS)
    return BuiltMonth(
        period_month=period_month,
        region=region,
        service_slug=service_slug,
        metrics=metrics,
        coverage=coverage,
        limits=LIMITS,
        content_sha256=content_sha256(content),
        built_from_data_cutoff=as_of,
    )


async def build_month(conn, period_month: date, region: str, service_slug: str | None, as_of: datetime) -> BuiltMonth:
    """Count one month for one region and service. Reads only; stores nothing.

    ``as_of`` is the time the build runs. It is recorded as the data cut-off and
    decides whether the month may be built yet (the seven-day rule). It is not
    part of the hashed content.
    """
    canonical_region = normalise_region(region)
    slug = normalise_service(service_slug)
    first = _check_buildable_month(period_month, as_of)
    if not await conn.fetchval(q.QUARANTINE_TABLE_PRESENT):
        raise RegionMonthlyError("source_unavailable")

    aliases = list(resolve_service_filter(slug)) if slug else None
    month_start, month_end = uk_month_bounds(first)
    row = await conn.fetchrow(
        q.MONTH_COUNTS,
        canonical_region,
        aliases,
        first,
        add_months(first, 1),
        RATING_HISTORY_AVAILABLE_THROUGH,
        month_start,
        month_end,
        datetime(
            STATUS_EVENTS_OBSERVED_FROM.year, STATUS_EVENTS_OBSERVED_FROM.month, STATUS_EVENTS_OBSERVED_FROM.day, tzinfo=UK
        ),
    )
    return _assemble(first, canonical_region, slug, row, as_of)


@dataclass(frozen=True)
class StoreResult:
    action: str  # "inserted", "unchanged" or "changed_not_stored"
    build_version: int | None
    content_sha256: str


async def store_build(conn, built: BuiltMonth, *, correction_reason: str | None = None) -> StoreResult:
    """Insert a build as the next version. Never updates or deletes a row.

    A month with no build gets version 1. A month whose latest build has the same
    content hash is left alone. A month whose content differs is stored as a new
    version only when a correction reason is given; otherwise nothing is written.
    """
    lock_key = f"region-monthly:{built.period_month.isoformat()}:{built.region}:{built.service_slug or ''}"
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", lock_key)
        latest = await conn.fetchrow(q.LATEST_BUILD, built.period_month, built.region, built.service_slug)
        if latest is None:
            version, supersedes, reason = 1, None, None
        elif latest["content_sha256"] == built.content_sha256:
            return StoreResult("unchanged", latest["build_version"], built.content_sha256)
        elif not (correction_reason or "").strip():
            return StoreResult("changed_not_stored", latest["build_version"], built.content_sha256)
        else:
            version, supersedes, reason = latest["build_version"] + 1, latest["build_version"], correction_reason.strip()
        await conn.execute(
            q.INSERT_BUILD,
            built.period_month,
            built.region,
            built.service_slug,
            version,
            supersedes,
            reason,
            built.schema_version,
            built.built_from_data_cutoff,
            json.dumps(built.metrics, sort_keys=True),
            json.dumps(built.coverage, sort_keys=True),
            json.dumps(list(built.limits)),
            built.content_sha256,
        )
    return StoreResult("inserted", version, built.content_sha256)


# --- backfill planning ------------------------------------------------------


@dataclass(frozen=True)
class BuildTarget:
    period_month: date
    region: str
    service_slug: str | None  # None means all services


def default_services() -> tuple[str | None, ...]:
    """All services (None) first, then every canonical slug."""
    return (None, *supported_services())


def plan_backfill(
    first_month: date,
    last_month: date,
    now: datetime,
    *,
    regions: Iterable[str] | None = None,
    services: Iterable[str | None] | None = None,
) -> list[BuildTarget]:
    """Every (month, region, service) combination to build for a backfill range.

    Refuses a range that starts before the first supported month, that reaches a
    month that cannot be built yet, or that names an unsupported region or
    service. The order is fixed: month, then region, then service.
    """
    first = _require_month(first_month)
    last = _require_month(last_month)
    if first > last:
        raise RegionMonthlyError("range_invalid")
    if first < EARLIEST_SUPPORTED_MONTH:
        raise RegionMonthlyError("month_before_earliest", month=format_month(first), earliest=format_month(EARLIEST_SUPPORTED_MONTH))
    if not is_buildable(last, now):
        raise RegionMonthlyError("month_not_yet_buildable", month=format_month(last), available=format_day(available_on(last)))
    region_list = [normalise_region(r) for r in (REGIONS if regions is None else regions)]
    service_list = [normalise_service(s) for s in (default_services() if services is None else services)]
    months = month_range(first, _months_between(first, last) + 1)
    targets = {BuildTarget(m, r, s) for m in months for r in region_list for s in service_list}
    return sorted(targets, key=lambda t: (t.period_month, t.region, t.service_slug or ""))


def _months_between(first: date, last: date) -> int:
    return (last.year - first.year) * 12 + (last.month - first.month)


# --- purchases (pure; no payment) -------------------------------------------


@dataclass(frozen=True)
class PurchaseMonth:
    period_month: date
    status: str  # "built" or "future"
    available_from: date | None  # for a future month: the 7th of the following month


@dataclass(frozen=True)
class Purchase:
    kind: str
    region: str
    service_slug: str | None
    price_pence: int
    months: tuple[PurchaseMonth, ...]

    @property
    def future_months(self) -> tuple[PurchaseMonth, ...]:
        return tuple(m for m in self.months if m.status == "future")

    @property
    def built_months(self) -> tuple[PurchaseMonth, ...]:
        return tuple(m for m in self.months if m.status == "built")


def parse_months_param(value: str) -> list[date]:
    """Read ``2026-04,2026-05`` into month dates; one malformed item refuses all."""
    parts = [p.strip() for p in (value or "").split(",")]
    if not parts or any(not p for p in parts) or len(parts) > 12:
        raise RegionMonthlyError("months_malformed")
    return [parse_month(p) for p in parts]


def resolve_purchase(
    kind: str,
    first_month: date,
    now: datetime,
    *,
    region: str,
    service_slug: str | None = None,
    built_months: Iterable[date] = (),
    accept_future_months: bool = False,
    months: Sequence[date] | None = None,
) -> Purchase:
    """The exact months, price and build state of a purchase, or a refusal.

    Everything that can fail fails here, before any charge. ``built_months`` is
    the set of months already built for this region and service. If ``months``
    is given it must be exactly the consecutive run the kind describes.
    """
    spec = require_kind(kind)
    canonical_region = normalise_region(region)
    slug = normalise_service(service_slug)
    first = _require_month(first_month)

    if months is not None:
        listed = [_require_month(m) for m in months]
        if len(listed) != spec.months:
            raise RegionMonthlyError("months_count_mismatch", expected=spec.months)
        if listed != month_range(listed[0], len(listed)):
            raise RegionMonthlyError("months_not_consecutive")
        if listed[0] != first:
            raise RegionMonthlyError("months_not_consecutive")

    run = month_range(first, spec.months)
    if run[0] < EARLIEST_SUPPORTED_MONTH:
        raise RegionMonthlyError("month_before_earliest", month=format_month(run[0]), earliest=format_month(EARLIEST_SUPPORTED_MONTH))

    built = set(built_months)
    horizon = add_months(latest_buildable_month(now), MAX_MONTHS_AHEAD)
    if run[-1] > horizon:
        raise RegionMonthlyError("future_months_too_far", latest=format_month(horizon), limit=MAX_MONTHS_AHEAD)

    resolved: list[PurchaseMonth] = []
    for month in run:
        if month in built:
            resolved.append(PurchaseMonth(month, "built", None))
        elif is_buildable(month, now):
            raise RegionMonthlyError("month_not_built", month=format_month(month))
        else:
            resolved.append(PurchaseMonth(month, "future", available_on(month)))

    future = [m for m in resolved if m.status == "future"]
    if future and not accept_future_months:
        raise RegionMonthlyError("future_months_not_accepted", months=", ".join(format_month(m.period_month) for m in future))
    return Purchase(kind, canonical_region, slug, spec.price_pence, tuple(resolved))


def coverage_preview(
    kind: str,
    first_month: date,
    now: datetime,
    *,
    region: str,
    service_slug: str | None = None,
    built_months: Iterable[date] = (),
    accept_future_months: bool = False,
    months: Sequence[date] | None = None,
) -> dict[str, Any]:
    """The free summary shown before checkout. Raises the same refusals."""
    purchase = resolve_purchase(
        kind,
        first_month,
        now,
        region=region,
        service_slug=service_slug,
        built_months=built_months,
        accept_future_months=accept_future_months,
        months=months,
    )
    rows = []
    for m in purchase.months:
        rows.append(
            {
                "month": month_key(m.period_month),
                "label": format_month(m.period_month),
                "status": m.status,
                "available_from": m.available_from.isoformat() if m.available_from else None,
                "coverage": metric_coverage(m.period_month),
            }
        )
    first_label = format_month(purchase.months[0].period_month)
    last_label = format_month(purchase.months[-1].period_month)
    span = first_label if len(purchase.months) == 1 else f"{first_label} to {last_label}"
    parts = [f"{len(purchase.built_months)} built"]
    if purchase.future_months:
        parts.append(
            f"{len(purchase.future_months)} to be built (first on {format_day(purchase.future_months[0].available_from)})"  # type: ignore[arg-type]
        )
    return {
        "region": purchase.region,
        "service": purchase.service_slug,
        "kind": purchase.kind,
        "price_pence": purchase.price_pence,
        "currency": CURRENCY,
        "month_count": len(purchase.months),
        "summary": f"{span}: " + ", ".join(parts) + ".",
        "months": rows,
        "future_months": [r["month"] for r in rows if r["status"] == "future"],
        "future_month_notice": FUTURE_MONTH_NOTICE if purchase.future_months else None,
        "metrics": [
            {"key": key, "label": METRIC_LABELS[key], "definition": METRIC_DEFINITIONS[key]} for key in METRICS
        ],
        "limits": list(LIMITS),
    }
