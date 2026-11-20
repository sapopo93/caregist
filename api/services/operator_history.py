"""Operator History (stage 1): CQC's published record of one care operator.

One operator is one CQC Provider ID (``care_providers.provider_id``). A name
alone never identifies an operator: a name search either resolves to exactly one
Provider ID or is refused, and the caller chooses by ID.

Every sentence the customer can read is a fixed template over counts, dates and
values quoted from CQC or from CareGist's own observation records. Nothing here
scores, ranks, predicts or calls an operator risky, and no model writes any
field. The record's ``content_sha256`` covers the whole record, with no
generation timestamp and no database serial number, so the same data always
gives the same hash.

What the data holds, and does not hold (measured 20 Nov 2026):

* ``care_providers`` has the location name, registration date, current status
  and service types. It has no deregistration date and no legal provider name.
* ``provider_rating_history`` has inspection dates and ratings. CareGist only
  began recording it on 31 Mar 2026; earlier dates are CQC dates captured later.
* ``trusted_event_ledger`` ``status_changed`` rows give only the date CareGist
  observed a location's status change. ``ownership_changed`` rows are a seeding
  artefact (old value is a category, new value is empty) and are never read.
* The legal provider name comes from the stored CQC editions
  (``territory_brief_source_editions``). Each edition location's ``payload``
  carries the CQC ``providerId`` and the row carries the provider name from the
  same file, so the pair (edition, Provider ID) binds a name to an operator.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from api.services.rating_states import RATED, classify_stored_rating

RECORD_SCHEMA_VERSION = 1
PROVIDER_ID_RE = re.compile(r"^1-[0-9]{3,15}$")
NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 120
MAX_CANDIDATES = 10
CQC_LOCATION_URL = "https://www.cqc.org.uk/location/{location_id}"

# Refusal codes. They are part of the API contract and do not change.
NOT_FOUND = "not_found"
AMBIGUOUS = "ambiguous"
IDENTITY_DISPUTED = "identity_disputed"
NO_LEGAL_NAME_HELD = "no_legal_name_held"
NOT_ENOUGH_HISTORY = "not_enough_history"
INVALID_INPUT = "invalid_input"

REFUSAL_STATUS = {
    NOT_FOUND: 404,
    AMBIGUOUS: 409,
    IDENTITY_DISPUTED: 409,
    NO_LEGAL_NAME_HELD: 409,
    NOT_ENOUGH_HISTORY: 409,
    INVALID_INPUT: 422,
}

REFUSAL_MESSAGES = {
    NOT_FOUND: "CareGist holds no record of an operator that matches this search.",
    AMBIGUOUS: (
        "More than one operator matches this name. Choose one by its CQC Provider ID."
    ),
    IDENTITY_DISPUTED: (
        "CareGist's records do not agree on which locations belong to this operator, "
        "so no history can be produced for it."
    ),
    NO_LEGAL_NAME_HELD: (
        "CareGist does not hold a CQC provider name for this operator, "
        "so no history can be produced for it."
    ),
    NOT_ENOUGH_HISTORY: "CareGist holds no locations for this operator.",
    INVALID_INPUT: (
        "Give either a CQC Provider ID such as 1-101234567, or an operator name of "
        f"{NAME_MIN_LENGTH} to {NAME_MAX_LENGTH} characters, but not both."
    ),
}

# Fixed limit templates. Dates are filled from the data; no other text is built.
LIMIT_CLOSURE = (
    "Closure dates are the date CareGist first observed a location absent from CQC's "
    "active directory, not CQC's deregistration date. The record does not say why a "
    "location left the directory."
)
LIMIT_STATUS_START = (
    "CareGist began recording changes to a location's status on {date}. A location "
    "that is not on the active directory and shows no observation date has no status "
    "change recorded by CareGist."
)
LIMIT_STATUS_START_NONE = "CareGist has recorded no changes to any location's status."
LIMIT_RATING = (
    "CareGist recorded rating history from {date}; earlier rating dates are CQC "
    "inspection dates captured later."
)
LIMIT_RATING_NONE = "CareGist holds no rating records for this operator's locations."
LIMIT_NAMES = (
    "Provider names are held only from the CQC editions CareGist has stored; renames "
    "before {date} are not shown."
)
LIMIT_LOCATIONS = (
    "This record covers only the locations CareGist holds. This operator may have had "
    "other locations that CareGist does not hold."
)
LIMIT_CUTOFF = (
    "This record includes CareGist's observations up to {date}. Later observations "
    "are not shown."
)
LIMIT_CUTOFF_NONE = "CareGist holds no observation dates for this operator's locations."

# Fixed event wording. {rating} is CQC's own value, quoted.
EVENT_TEXT = {
    "registration": "Registered with CQC.",
    "closure_observed": (
        "First observed no longer on CQC's active directory. This is the date CareGist "
        "observed it, not CQC's deregistration date."
    ),
    "reinstatement_observed": (
        "First observed back on CQC's active directory. This is the date CareGist "
        "observed it."
    ),
    "rating_published": (
        "CQC overall rating published: {rating}. The date is the inspection date CQC gives."
    ),
}
EVENT_ORDER = {"registration": 0, "rating_published": 1, "closure_observed": 2, "reinstatement_observed": 3}

STATUS_LABELS = {
    "on_active_directory": "On CQC's active directory",
    "no_longer_on_active_directory": "No longer on CQC's active directory",
    "status_not_held": "Status not held",
}

REGISTRATION_SOURCE_LABEL = "CQC registration date"
RATING_SOURCE_LABEL = "CQC inspection report"
OBSERVATION_SOURCE_LABEL = "CareGist observation of CQC's active directory"


class OperatorRefusal(Exception):
    """A typed refusal: stable machine ``code``, plain-English ``message``."""

    def __init__(self, code: str, *, candidates: list[dict[str, Any]] | None = None,
                 total_matches: int | None = None, reasons: list[str] | None = None) -> None:
        self.code = code
        self.message = REFUSAL_MESSAGES[code]
        self.http_status = REFUSAL_STATUS[code]
        self.candidates = candidates
        self.total_matches = total_matches
        self.reasons = reasons
        super().__init__(f"{code}: {self.message}")

    def as_detail(self) -> dict[str, Any]:
        detail: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.candidates is not None:
            detail["candidates"] = self.candidates
            detail["total_matches"] = self.total_matches
        if self.reasons:
            detail["reasons"] = self.reasons
        return detail


@dataclass(frozen=True)
class HeldName:
    """The provider name one stored CQC edition holds for a Provider ID."""

    name: str
    retrieved_on: date
    source_as_of: date
    providers_sha256: str
    locations_sha256: str


@dataclass(frozen=True)
class ResolvedOperator:
    provider_id: str
    legal_name: str
    held_names: tuple[HeldName, ...]  # oldest edition first
    location_count: int


# --------------------------------------------------------------------------
# SQL. Every value is a bound parameter; nothing is interpolated.
# --------------------------------------------------------------------------

SQL_HELD_NAMES = """
SELECT e.id AS edition_id, e.source_retrieved_at, e.source_as_of,
       e.providers_sha256, e.locations_sha256, l.provider_name
FROM territory_brief_source_locations l
JOIN territory_brief_source_editions e ON e.id = l.edition_id
WHERE l.payload->>'providerId' = $1
GROUP BY e.id, e.source_retrieved_at, e.source_as_of, e.providers_sha256,
         e.locations_sha256, l.provider_name
ORDER BY e.source_retrieved_at, e.id, l.provider_name
"""

SQL_ANY_EDITION = "SELECT EXISTS (SELECT 1 FROM territory_brief_source_editions)"

SQL_LOCATION_COUNT = "SELECT count(*)::int FROM care_providers WHERE provider_id = $1"

SQL_OPEN_DISPUTE = (
    "SELECT EXISTS (SELECT 1 FROM operator_identity_disputes "
    "WHERE provider_id = $1 AND resolved_at IS NULL)"
)

# A location CareGist holds under this Provider ID, listed in a stored edition
# under a different one.
SQL_CONFLICT_EDITION_OTHER_ID = """
SELECT EXISTS (
  SELECT 1
  FROM care_providers cp
  JOIN territory_brief_source_locations l ON l.location_id = cp.id
  WHERE cp.provider_id = $1
    AND NULLIF(BTRIM(l.payload->>'providerId'), '') IS NOT NULL
    AND BTRIM(l.payload->>'providerId') <> $1
)
"""

# A location a stored edition lists under this Provider ID, held by CareGist
# under a different one.
SQL_CONFLICT_HELD_OTHER_ID = """
SELECT EXISTS (
  SELECT 1
  FROM territory_brief_source_locations l
  JOIN care_providers cp ON cp.id = l.location_id
  WHERE l.payload->>'providerId' = $1
    AND cp.provider_id IS NOT NULL
    AND cp.provider_id <> $1
)
"""

# A status observation CareGist recorded for one of this operator's locations
# under a different Provider ID.
SQL_CONFLICT_LEDGER = """
SELECT EXISTS (
  SELECT 1
  FROM trusted_event_ledger t
  JOIN care_providers cp ON cp.id = t.location_id
  WHERE cp.provider_id = $1
    AND t.event_type = 'status_changed'
    AND NULLIF(BTRIM(t.provider_id), '') IS NOT NULL
    AND BTRIM(t.provider_id) <> $1
)
"""

SQL_NAME_MATCHES_EXACT = """
WITH matched AS (
  SELECT DISTINCT l.payload->>'providerId' AS provider_id
  FROM territory_brief_source_locations l
  WHERE lower(BTRIM(l.provider_name)) = lower($1)
    AND NULLIF(BTRIM(l.payload->>'providerId'), '') IS NOT NULL
)
SELECT m.provider_id, count(cp.id)::int AS location_count, count(*) OVER ()::int AS total
FROM matched m LEFT JOIN care_providers cp ON cp.provider_id = m.provider_id
GROUP BY m.provider_id
ORDER BY location_count DESC, m.provider_id
LIMIT $2
"""

SQL_NAME_MATCHES_CONTAINS = """
WITH matched AS (
  SELECT DISTINCT l.payload->>'providerId' AS provider_id
  FROM territory_brief_source_locations l
  WHERE l.provider_name ILIKE '%' || $1 || '%' ESCAPE '\\'
    AND NULLIF(BTRIM(l.payload->>'providerId'), '') IS NOT NULL
)
SELECT m.provider_id, count(cp.id)::int AS location_count, count(*) OVER ()::int AS total
FROM matched m LEFT JOIN care_providers cp ON cp.provider_id = m.provider_id
GROUP BY m.provider_id
ORDER BY location_count DESC, m.provider_id
LIMIT $2
"""

SQL_LATEST_NAMES = """
SELECT DISTINCT ON (l.payload->>'providerId')
       l.payload->>'providerId' AS provider_id, l.provider_name
FROM territory_brief_source_locations l
JOIN territory_brief_source_editions e ON e.id = l.edition_id
WHERE l.payload->>'providerId' = ANY($1::text[])
ORDER BY l.payload->>'providerId', e.source_retrieved_at DESC, e.id DESC, l.provider_name
"""

SQL_LOCATIONS = """
SELECT id, name, registration_date, status, service_types
FROM care_providers
WHERE provider_id = $1
ORDER BY registration_date NULLS LAST, id
"""

SQL_STATUS_EVENTS = """
SELECT location_id, observed_at, old_value #>> '{}' AS old_status,
       new_value #>> '{}' AS new_status, source_url
FROM trusted_event_ledger
WHERE event_type = 'status_changed' AND location_id = ANY($1::text[])
ORDER BY observed_at, location_id, new_value #>> '{}', old_value #>> '{}'
"""

SQL_RATINGS = """
SELECT provider_id AS location_id, overall_rating, inspection_date, report_url, recorded_at
FROM provider_rating_history
WHERE provider_id = ANY($1::text[])
ORDER BY provider_id, inspection_date NULLS LAST, overall_rating, report_url, recorded_at
"""

SQL_FIRST_STATUS_OBSERVATION = (
    "SELECT min(observed_at) FROM trusted_event_ledger WHERE event_type = 'status_changed'"
)


# --------------------------------------------------------------------------
# Small pure helpers
# --------------------------------------------------------------------------


def _clean_name(raw: str) -> str:
    return " ".join(raw.split())


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so a name search is a literal substring search."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _utc_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date()


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def format_date(value: date) -> str:
    return f"{value.day} {value:%B %Y}"


def _status_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def _classify_status(raw: Any) -> str:
    text = _status_text(raw)
    if text == "ACTIVE":
        return "on_active_directory"
    if text == "INACTIVE":
        return "no_longer_on_active_directory"
    return "status_not_held"


def _split_services(raw: Any) -> list[str]:
    if not raw:
        return []
    seen: list[str] = []
    for part in str(raw).split("|"):
        label = part.strip()
        if label and label not in seen:
            seen.append(label)
    return sorted(seen)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(record: dict[str, Any]) -> str:
    body = {key: val for key, val in record.items() if key != "content_sha256"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def build_limits(
    *,
    first_rating_recorded_on: date | None,
    earliest_edition_on: date | None,
    first_status_observed_on: date | None,
    history_cutoff: date | None,
) -> list[str]:
    """The limits list, built only from the fixed templates above."""
    limits = [LIMIT_CLOSURE]
    limits.append(
        LIMIT_STATUS_START.format(date=format_date(first_status_observed_on))
        if first_status_observed_on else LIMIT_STATUS_START_NONE
    )
    limits.append(
        LIMIT_RATING.format(date=format_date(first_rating_recorded_on))
        if first_rating_recorded_on else LIMIT_RATING_NONE
    )
    if earliest_edition_on:
        limits.append(LIMIT_NAMES.format(date=format_date(earliest_edition_on)))
    limits.append(LIMIT_LOCATIONS)
    limits.append(
        LIMIT_CUTOFF.format(date=format_date(history_cutoff)) if history_cutoff else LIMIT_CUTOFF_NONE
    )
    return limits


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------


def normalise_inputs(provider_id: str | None, name: str | None) -> tuple[str | None, str | None]:
    """Exactly one of Provider ID or name, in a safe shape; otherwise invalid_input."""
    pid = provider_id.strip() if isinstance(provider_id, str) else None
    cleaned = _clean_name(name) if isinstance(name, str) else None
    if bool(pid) == bool(cleaned):
        raise OperatorRefusal(INVALID_INPUT)
    if pid:
        if not PROVIDER_ID_RE.fullmatch(pid):
            raise OperatorRefusal(INVALID_INPUT)
        return pid, None
    assert cleaned is not None
    if not NAME_MIN_LENGTH <= len(cleaned) <= NAME_MAX_LENGTH or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise OperatorRefusal(INVALID_INPUT)
    return None, cleaned


async def _held_names(conn, provider_id: str) -> list[Any]:
    return list(await conn.fetch(SQL_HELD_NAMES, provider_id))


async def _dispute_reasons(conn, provider_id: str, held_rows: list[Any]) -> list[str]:
    reasons: list[str] = []
    if await conn.fetchval(SQL_OPEN_DISPUTE, provider_id):
        reasons.append("recorded_dispute")
    names_by_edition: dict[int, set[str]] = {}
    for row in held_rows:
        names_by_edition.setdefault(row["edition_id"], set()).add(row["provider_name"].strip())
    if any(len(names) > 1 for names in names_by_edition.values()):
        reasons.append("edition_names_conflict")
    if await conn.fetchval(SQL_CONFLICT_EDITION_OTHER_ID, provider_id) or await conn.fetchval(
        SQL_CONFLICT_HELD_OTHER_ID, provider_id
    ):
        reasons.append("location_under_another_provider_id")
    if await conn.fetchval(SQL_CONFLICT_LEDGER, provider_id):
        reasons.append("observation_under_another_provider_id")
    return reasons


async def _resolve_by_provider_id(conn, provider_id: str) -> ResolvedOperator:
    held_rows = await _held_names(conn, provider_id)
    location_count = await conn.fetchval(SQL_LOCATION_COUNT, provider_id)
    disputed = await conn.fetchval(SQL_OPEN_DISPUTE, provider_id)
    if not held_rows and not location_count and not disputed:
        raise OperatorRefusal(NOT_FOUND)
    reasons = await _dispute_reasons(conn, provider_id, held_rows)
    if reasons:
        raise OperatorRefusal(IDENTITY_DISPUTED, reasons=reasons)
    if not held_rows:
        raise OperatorRefusal(NO_LEGAL_NAME_HELD)
    if not location_count:
        raise OperatorRefusal(NOT_ENOUGH_HISTORY)
    held = tuple(
        HeldName(
            name=row["provider_name"].strip(),
            retrieved_on=_utc_date(row["source_retrieved_at"]),  # type: ignore[arg-type]
            source_as_of=row["source_as_of"],
            providers_sha256=row["providers_sha256"],
            locations_sha256=row["locations_sha256"],
        )
        for row in held_rows
    )
    return ResolvedOperator(
        provider_id=provider_id, legal_name=held[-1].name, held_names=held, location_count=location_count,
    )


async def _resolve_by_name(conn, name: str) -> ResolvedOperator:
    if not await conn.fetchval(SQL_ANY_EDITION):
        raise OperatorRefusal(NO_LEGAL_NAME_HELD)
    matches = await conn.fetch(SQL_NAME_MATCHES_EXACT, name, MAX_CANDIDATES)
    if not matches:
        matches = await conn.fetch(SQL_NAME_MATCHES_CONTAINS, escape_like(name), MAX_CANDIDATES)
    if not matches:
        raise OperatorRefusal(NOT_FOUND)
    total = matches[0]["total"]
    if total == 1:
        return await _resolve_by_provider_id(conn, matches[0]["provider_id"])
    ids = [row["provider_id"] for row in matches]
    latest = {row["provider_id"]: row["provider_name"].strip() for row in await conn.fetch(SQL_LATEST_NAMES, ids)}
    # Identity, name and size only: nothing else about a candidate is disclosed.
    candidates = [
        {"provider_id": row["provider_id"], "name": latest.get(row["provider_id"], ""), "location_count": row["location_count"]}
        for row in matches
    ]
    raise OperatorRefusal(AMBIGUOUS, candidates=candidates, total_matches=total)


async def resolve_operator(conn, provider_id: str | None = None, name: str | None = None) -> ResolvedOperator:
    """Exactly one operator, or a typed :class:`OperatorRefusal`."""
    pid, cleaned = normalise_inputs(provider_id, name)
    if pid is not None:
        return await _resolve_by_provider_id(conn, pid)
    assert cleaned is not None
    return await _resolve_by_name(conn, cleaned)


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


def _edition_block(held: HeldName) -> dict[str, Any]:
    return {
        "retrieved_on": held.retrieved_on.isoformat(),
        "source_as_of": held.source_as_of.isoformat(),
        "providers_sha256": held.providers_sha256,
        "locations_sha256": held.locations_sha256,
    }


def _name_block(operator: ResolvedOperator) -> dict[str, Any]:
    latest = operator.held_names[-1]
    earlier: dict[str, list[date]] = {}
    for held in operator.held_names:
        if held.name != operator.legal_name:
            earlier.setdefault(held.name, []).append(held.retrieved_on)
    earlier_names = sorted(
        (
            {"name": name, "first_edition_retrieved_on": min(days).isoformat(),
             "last_edition_retrieved_on": max(days).isoformat()}
            for name, days in earlier.items()
        ),
        key=lambda item: (item["first_edition_retrieved_on"], item["name"]),
    )
    return {"legal_name": operator.legal_name, "edition": _edition_block(latest), "earlier_names": earlier_names}


def _fold_status(location_id: str, recorded_status: Any, observations: list[dict[str, Any]]) -> dict[str, Any]:
    state = _classify_status(recorded_status)
    closures = [o["observed_on"] for o in observations if o["kind"] == "closure_observed"]
    reinstated = [o["observed_on"] for o in observations if o["kind"] == "reinstatement_observed"]
    return {
        "state": state,
        "label": STATUS_LABELS[state],
        "recorded_status": _status_text(recorded_status),
        "first_observed_absent_on": min(closures) if closures else None,
        "latest_reinstatement_observed_on": max(reinstated) if reinstated else None,
        "observations": observations,
    }


async def build_operator_history(
    conn, operator: ResolvedOperator, *, observed_through: date | None = None
) -> dict[str, Any]:
    """The full, sourced record for a resolved operator.

    ``observed_through`` (optional) leaves out CareGist observations made after
    that date. It is a hook for a publication cutoff, which the repo does not
    define for history; see docs/operator-history-v1.md.
    """
    location_rows = list(await conn.fetch(SQL_LOCATIONS, operator.provider_id))
    if not location_rows:
        raise OperatorRefusal(NOT_ENOUGH_HISTORY)
    ids = [row["id"] for row in location_rows]
    status_rows = list(await conn.fetch(SQL_STATUS_EVENTS, ids))
    rating_rows = list(await conn.fetch(SQL_RATINGS, ids))
    first_status_seen = _utc_date(await conn.fetchval(SQL_FIRST_STATUS_OBSERVATION))

    def within(day: date | None) -> bool:
        return observed_through is None or day is None or day <= observed_through

    observations: dict[str, list[dict[str, Any]]] = {}
    for row in status_rows:
        old, new = _status_text(row["old_status"]), _status_text(row["new_status"])
        if new == "INACTIVE" and old != "INACTIVE":
            kind = "closure_observed"
        elif new == "ACTIVE" and old == "INACTIVE":
            kind = "reinstatement_observed"
        else:
            continue
        seen_on = _utc_date(row["observed_at"])
        if not within(seen_on):
            continue
        observations.setdefault(row["location_id"], []).append({
            "kind": kind,
            "observed_on": _iso(seen_on),
            "source": {"label": OBSERVATION_SOURCE_LABEL, "url": row["source_url"] or None},
        })

    ratings: dict[str, list[dict[str, Any]]] = {}
    first_rating_recorded: date | None = None
    last_rating_recorded: date | None = None
    for row in rating_rows:
        recorded_on = _utc_date(row["recorded_at"])
        if not within(recorded_on):
            continue
        state, _value = classify_stored_rating(row["overall_rating"])
        ratings.setdefault(row["location_id"], []).append({
            "inspection_date": _iso(row["inspection_date"]),
            "rating": row["overall_rating"],
            "is_published_rating": state == RATED,
            "recorded_on": _iso(recorded_on),
            "source": {"label": RATING_SOURCE_LABEL, "url": row["report_url"] or None},
        })
        if recorded_on:
            first_rating_recorded = recorded_on if first_rating_recorded is None else min(first_rating_recorded, recorded_on)
            last_rating_recorded = recorded_on if last_rating_recorded is None else max(last_rating_recorded, recorded_on)

    locations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for row in location_rows:
        location_id, location_name = row["id"], row["name"]
        profile = CQC_LOCATION_URL.format(location_id=location_id)
        seen = observations.get(location_id, [])
        history = sorted(
            ratings.get(location_id, []),
            key=lambda r: (r["inspection_date"] is None, r["inspection_date"] or "", r["rating"] or "",
                           r["source"]["url"] or "", r["recorded_on"] or ""),
        )
        locations.append({
            "location_id": location_id,
            "name": location_name,
            "registration_date": _iso(row["registration_date"]),
            "registration_source": {"label": REGISTRATION_SOURCE_LABEL, "url": profile},
            "service_types": _split_services(row["service_types"]),
            "status": _fold_status(location_id, row["status"], seen),
            "rating_history": history,
        })
        if row["registration_date"]:
            events.append({
                "date": row["registration_date"].isoformat(), "kind": "registration",
                "location_id": location_id, "location_name": location_name,
                "text": EVENT_TEXT["registration"],
                "source": {"label": REGISTRATION_SOURCE_LABEL, "url": profile},
            })
        for obs in seen:
            events.append({
                "date": obs["observed_on"], "kind": obs["kind"],
                "location_id": location_id, "location_name": location_name,
                "text": EVENT_TEXT[obs["kind"]], "source": obs["source"],
            })
        for rated in history:
            if rated["inspection_date"] and rated["is_published_rating"]:
                events.append({
                    "date": rated["inspection_date"], "kind": "rating_published",
                    "location_id": location_id, "location_name": location_name,
                    "rating": rated["rating"],
                    "text": EVENT_TEXT["rating_published"].format(rating=rated["rating"]),
                    "source": rated["source"],
                })
    events.sort(key=lambda e: (e["date"], EVENT_ORDER[e["kind"]], e["location_id"], e.get("rating") or "", e["source"]["url"] or ""))

    observed_days = [date.fromisoformat(o["observed_on"]) for obs in observations.values() for o in obs]
    if last_rating_recorded:
        observed_days.append(last_rating_recorded)
    latest_observation = max(observed_days) if observed_days else None
    history_cutoff = observed_through or latest_observation
    earliest_edition = operator.held_names[0].retrieved_on
    # The status-start date only qualifies closures, so it never moves with the cutoff.
    limits = build_limits(
        first_rating_recorded_on=first_rating_recorded,
        earliest_edition_on=earliest_edition,
        first_status_observed_on=first_status_seen,
        history_cutoff=history_cutoff,
    )

    state_counts = {"on_active_directory": 0, "no_longer_on_active_directory": 0, "status_not_held": 0}
    for loc in locations:
        state_counts[loc["status"]["state"]] += 1
    registered = [loc["registration_date"] for loc in locations if loc["registration_date"]]
    inspections = [r["inspection_date"] for loc in locations for r in loc["rating_history"] if r["inspection_date"]]
    closures = [e for e in events if e["kind"] == "closure_observed"]
    reinstatements = [e for e in events if e["kind"] == "reinstatement_observed"]
    summary = {
        "locations_total": len(locations),
        **state_counts,
        "earliest_registration_date": min(registered) if registered else None,
        "latest_registration_date": max(registered) if registered else None,
        "rating_records": sum(len(loc["rating_history"]) for loc in locations),
        "earliest_inspection_date": min(inspections) if inspections else None,
        "latest_inspection_date": max(inspections) if inspections else None,
        "closures_observed": len(closures),
        "reinstatements_observed": len(reinstatements),
        "first_closure_observed_on": min(e["date"] for e in closures) if closures else None,
    }
    record: dict[str, Any] = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "provider_id": operator.provider_id,
        "provider": _name_block(operator),
        "history_cutoff": _iso(history_cutoff),
        "summary": summary,
        "locations": locations,
        "events": events,
        "limits": limits,
    }
    record["content_sha256"] = content_sha256(record)
    return record


async def coverage_preview(
    conn, provider_id: str | None = None, name: str | None = None, *, observed_through: date | None = None
) -> dict[str, Any]:
    """The free, pre-checkout summary. No location list and no event list."""
    operator = await resolve_operator(conn, provider_id=provider_id, name=name)
    record = await build_operator_history(conn, operator, observed_through=observed_through)
    summary = record["summary"]
    return {
        "provider_id": record["provider_id"],
        "legal_name": record["provider"]["legal_name"],
        "edition": record["provider"]["edition"],
        "earlier_names": record["provider"]["earlier_names"],
        "locations": {
            "total": summary["locations_total"],
            "on_active_directory": summary["on_active_directory"],
            "no_longer_on_active_directory": summary["no_longer_on_active_directory"],
            "status_not_held": summary["status_not_held"],
        },
        "registrations": {
            "earliest": summary["earliest_registration_date"],
            "latest": summary["latest_registration_date"],
        },
        "ratings": {
            "records": summary["rating_records"],
            "earliest_inspection_date": summary["earliest_inspection_date"],
            "latest_inspection_date": summary["latest_inspection_date"],
        },
        "status_changes": {
            "closures_observed": summary["closures_observed"],
            "reinstatements_observed": summary["reinstatements_observed"],
            "first_closure_observed_on": summary["first_closure_observed_on"],
        },
        "history_cutoff": record["history_cutoff"],
        "limits": record["limits"],
    }
