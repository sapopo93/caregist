"""Territory Opportunity Brief generator.

This is the production generation service behind the £795 one-off product. It
extends the deterministic scaffolding in
``tools/generate_radar_territory_sample.py`` (window derivation, supported-event
rules, provenance) with the parts a paying buyer needs and a raw CSV does not:

* a validated buyer-chosen scope (one England local authority or region),
* a deterministic ranked shortlist of organisations,
* a plain-English, evidence-bound reason for every shortlisted organisation,
* territory-level aggregate insight,
* evidence-bounded recommended next actions,
* structured output that renders to both a professional brief and a CSV.

Design rules
------------
* Deterministic: identical source files + scope + ``generated_at`` produce a
  byte-identical brief. No wall-clock, no RNG, stable tie-breaks everywhere.
* Evidence only: every reason and insight is built from fields that exist in
  the mirrored public CQC snapshot. Nothing is inferred or invented.
* Stripe-independent: ``generate_territory_opportunity_brief`` takes a plain
  ``TerritoryScope`` and ``PurchaseContext`` and never imports billing.
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from tools.generate_radar_territory_sample import (
    _load_ndjson,
    _parse_date,
    _rating_sequence,
    load_provider_names,
)

OGL_ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0"
)
CQC_PROFILE_URL = "https://api.service.cqc.org.uk/public/v1/locations/{location_id}"
CQC_DATA_PAGE = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"

_RATING_RANK = {
    "outstanding": 4,
    "good": 3,
    "requires improvement": 2,
    "inadequate": 1,
}

MIN_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 365
MIN_SHORTLIST = 10
MAX_SHORTLIST = 50
DEFAULT_SHORTLIST = 30
DEFAULT_WINDOW_DAYS = 90


class ScopeError(ValueError):
    """Raised when a buyer-supplied scope is missing, malformed, or unknown."""


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TerritoryScope:
    """A validated buyer-chosen territory.

    ``kind`` is 'local_authority' or 'region'. ``name`` is matched
    case-insensitively against the values actually present in the snapshot;
    the canonical spelling from the data is stored back here by
    :func:`validate_scope`.
    """

    kind: Literal["local_authority", "region"]
    name: str
    window_days: int = DEFAULT_WINDOW_DAYS
    shortlist_target: int = DEFAULT_SHORTLIST

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PurchaseContext:
    """Non-PII provenance for the generated artefact.

    Deliberately excludes buyer email / name: the brief is stored in Blob and
    delivered by token, so it must not embed personal data. ``order_reference``
    is the opaque local order id used for audit correlation only.
    """

    order_reference: str
    generated_at: datetime
    product: str = "territory-opportunity-brief"
    price_gbp: int = 795
    terms_version: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "order_reference": self.order_reference,
            "generated_at": self.generated_at.astimezone(timezone.utc).isoformat(),
            "product": self.product,
            "price_gbp": self.price_gbp,
            "terms_version": self.terms_version,
        }


# --------------------------------------------------------------------------- #
# Intermediate + output types
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class OrgEvent:
    event_type: str  # new_registration | rating_changed | rating_published | reactivated
    effective_date: date
    old_value: Any
    new_value: Any
    detail: str
    source_url: str
    source_field: str


@dataclass(frozen=True)
class RankedOrganisation:
    rank: int
    organisation_name: str
    location_name: str
    location_id: str
    provider_id: str
    local_authority: str
    region: str
    postcode: str
    service_types: tuple[str, ...]
    number_of_beds: int | None
    current_rating: str | None
    primary_signal: str
    most_recent_event_date: date | None
    score: float
    score_breakdown: dict[str, float]
    reason: str
    evidence: tuple[dict[str, Any], ...]

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["service_types"] = list(self.service_types)
        data["most_recent_event_date"] = (
            self.most_recent_event_date.isoformat() if self.most_recent_event_date else None
        )
        data["evidence"] = [dict(item) for item in self.evidence]
        return data


@dataclass(frozen=True)
class TerritoryBrief:
    scope: TerritoryScope
    purchase_context: PurchaseContext
    as_of_date: date
    window_start: date
    window_end: date
    considered_locations: int
    territory_locations: int
    shortlist: tuple[RankedOrganisation, ...]
    executive_summary: dict[str, Any]
    territory_insights: dict[str, Any]
    next_actions: tuple[str, ...]
    methodology_notes: tuple[str, ...]
    data_caveats: tuple[str, ...]
    source_provenance: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "scope": self.scope.to_json(),
            "purchase_context": self.purchase_context.to_json(),
            "as_of_date": self.as_of_date.isoformat(),
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "considered_locations": self.considered_locations,
            "territory_locations": self.territory_locations,
            "shortlist": [org.to_json() for org in self.shortlist],
            "executive_summary": self.executive_summary,
            "territory_insights": self.territory_insights,
            "next_actions": list(self.next_actions),
            "methodology_notes": list(self.methodology_notes),
            "data_caveats": list(self.data_caveats),
            "source_provenance": self.source_provenance,
        }


# --------------------------------------------------------------------------- #
# Scope validation
# --------------------------------------------------------------------------- #

_NAME_OK = re.compile(r"^[A-Za-z0-9 .,'()&/-]{2,80}$")


def known_territories(locations: Iterable[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Map normalised -> canonical name for every LA and region in the snapshot."""
    las: dict[str, str] = {}
    regions: dict[str, str] = {}
    for row in locations:
        la = str(row.get("localAuthority") or "").strip()
        region = str(row.get("region") or "").strip()
        if la:
            las.setdefault(la.casefold(), la)
        if region:
            regions.setdefault(region.casefold(), region)
    return {"local_authority": las, "region": regions}


def validate_scope(
    raw: dict[str, Any] | TerritoryScope,
    catalogue: dict[str, dict[str, str]],
) -> TerritoryScope:
    """Validate and canonicalise a buyer-supplied scope.

    ``catalogue`` comes from :func:`known_territories`. Raises :class:`ScopeError`
    on anything missing, malformed, or not present in the source data - never
    falls back to a default territory.
    """
    if isinstance(raw, TerritoryScope):
        kind, name, window_days, shortlist_target = (
            raw.kind, raw.name, raw.window_days, raw.shortlist_target,
        )
    else:
        if not isinstance(raw, dict):
            raise ScopeError("scope must be an object")
        kind = str(raw.get("kind") or "").strip()
        name = str(raw.get("name") or "").strip()
        window_days = raw.get("window_days", DEFAULT_WINDOW_DAYS)
        shortlist_target = raw.get("shortlist_target", DEFAULT_SHORTLIST)

    if kind not in ("local_authority", "region"):
        raise ScopeError("scope.kind must be 'local_authority' or 'region'")
    if not name:
        raise ScopeError("scope.name is required")
    if not _NAME_OK.match(name):
        raise ScopeError("scope.name contains unsupported characters")

    try:
        window_days = int(window_days)
    except (TypeError, ValueError):
        raise ScopeError("scope.window_days must be an integer")
    if not (MIN_WINDOW_DAYS <= window_days <= MAX_WINDOW_DAYS):
        raise ScopeError(
            f"scope.window_days must be between {MIN_WINDOW_DAYS} and {MAX_WINDOW_DAYS}"
        )

    try:
        shortlist_target = int(shortlist_target)
    except (TypeError, ValueError):
        raise ScopeError("scope.shortlist_target must be an integer")
    if not (MIN_SHORTLIST <= shortlist_target <= MAX_SHORTLIST):
        raise ScopeError(
            f"scope.shortlist_target must be between {MIN_SHORTLIST} and {MAX_SHORTLIST}"
        )

    canonical = catalogue.get(kind, {}).get(name.casefold())
    if not canonical:
        raise ScopeError(
            f"{name!r} is not a recognised England {kind.replace('_', ' ')} in the current source data"
        )

    return TerritoryScope(
        kind=kind,  # type: ignore[arg-type]
        name=canonical,
        window_days=window_days,
        shortlist_target=shortlist_target,
    )


# --------------------------------------------------------------------------- #
# Event collection
# --------------------------------------------------------------------------- #


def _service_types(row: dict[str, Any]) -> tuple[str, ...]:
    out: list[str] = []
    for item in row.get("gacServiceTypes") or []:
        if isinstance(item, dict):
            name = str(item.get("description") or item.get("name") or "").strip()
            if name and name not in out:
                out.append(name)
    return tuple(out)


def _in_scope(row: dict[str, Any], scope: TerritoryScope) -> bool:
    if scope.kind == "local_authority":
        return str(row.get("localAuthority") or "").strip().casefold() == scope.name.casefold()
    return str(row.get("region") or "").strip().casefold() == scope.name.casefold()


def _location_events(
    row: dict[str, Any],
    *,
    window_start: date,
    window_end: date,
    as_of: date,
) -> list[OrgEvent]:
    events: list[OrgEvent] = []
    location_id = str(row.get("locationId") or "").strip()
    url = CQC_PROFILE_URL.format(location_id=location_id) if location_id else CQC_DATA_PAGE

    reg_date = _parse_date(row.get("registrationDate"))
    dormant = str(row.get("dormancy") or "").strip().upper().startswith("Y")
    if reg_date is not None and window_start <= reg_date <= window_end and not dormant:
        events.append(
            OrgEvent(
                event_type="new_registration",
                effective_date=reg_date,
                old_value=None,
                new_value=str(row.get("registrationStatus") or "Registered").strip(),
                detail=f"CQC registration recorded {reg_date.isoformat()}",
                source_url=url,
                source_field="location.registrationDate",
            )
        )

    ratings = _rating_sequence(row)
    previous: str | None = None
    for report_date, rating in ratings:
        if previous is not None and previous != rating and window_start <= report_date <= window_end:
            events.append(
                OrgEvent(
                    event_type="rating_changed",
                    effective_date=report_date,
                    old_value=previous,
                    new_value=rating,
                    detail=f"Overall rating {previous} -> {rating} on {report_date.isoformat()}",
                    source_url=url,
                    source_field="location.historicRatings/currentRatings.overall",
                )
            )
        previous = rating

    # Rating published inside the window with no detected transition (single
    # report or first rating): a weaker but genuine "fresh inspection" signal.
    if ratings:
        last_date, last_rating = ratings[-1]
        has_change = any(e.event_type == "rating_changed" for e in events)
        if not has_change and window_start <= last_date <= window_end:
            events.append(
                OrgEvent(
                    event_type="rating_published",
                    effective_date=last_date,
                    old_value=None,
                    new_value=last_rating,
                    detail=f"Inspection report published {last_date.isoformat()} (rating {last_rating})",
                    source_url=url,
                    source_field="location.currentRatings.overall.reportDate",
                )
            )

    return events


# --------------------------------------------------------------------------- #
# Scoring + reasons
# --------------------------------------------------------------------------- #

_BASE_WEIGHT = {
    "new_registration": 42.0,
    "rating_changed": 34.0,
    "rating_published": 14.0,
    "reactivated": 20.0,
}


def _recency_multiplier(event_date: date, as_of: date) -> float:
    age = (as_of - event_date).days
    if age <= 30:
        return 1.5
    if age <= 90:
        return 1.2
    if age <= 180:
        return 1.05
    return 1.0


def _rating_direction(old: Any, new: Any) -> str:
    o = _RATING_RANK.get(str(old or "").strip().casefold())
    n = _RATING_RANK.get(str(new or "").strip().casefold())
    if o is None or n is None:
        return "changed"
    if n < o:
        return "decline"
    if n > o:
        return "improvement"
    return "changed"


def _score(
    events: list[OrgEvent],
    *,
    beds: int | None,
    provider_cluster: int,
    as_of: date,
    re_registration: bool = False,
) -> tuple[float, dict[str, float]]:
    breakdown: dict[str, float] = {}
    total = 0.0
    for ev in events:
        base = _BASE_WEIGHT.get(ev.event_type, 10.0)
        mult = _recency_multiplier(ev.effective_date, as_of)
        contribution = base * mult
        if ev.event_type == "rating_changed":
            direction = _rating_direction(ev.old_value, ev.new_value)
            if direction == "decline":
                contribution += 16.0
            elif direction == "improvement":
                contribution += 9.0
        breakdown[f"{ev.event_type}@{ev.effective_date.isoformat()}"] = round(contribution, 2)
        total += contribution

    size_factor = 0.0
    if beds:
        size_factor = min(beds, 60) / 6.0
        breakdown["size_factor"] = round(size_factor, 2)
        total += size_factor

    if provider_cluster >= 2:
        cluster_bonus = min(provider_cluster, 5) * 3.0
        breakdown["provider_cluster"] = round(cluster_bonus, 2)
        total += cluster_bonus

    if re_registration:
        # A re-registration (ownership / entity change) on an existing service is
        # a slightly stronger commercial trigger than a greenfield opening.
        breakdown["re_registration"] = 6.0
        total += 6.0

    return round(min(total, 100.0), 2), breakdown


_SIGNAL_LABEL = {
    "new_registration": "New CQC registration",
    "rating_changed": "Rating change",
    "rating_published": "New inspection report",
    "reactivated": "Returned from dormancy",
}


def _primary_signal(events: list[OrgEvent]) -> str:
    order = ["rating_changed", "new_registration", "rating_published", "reactivated"]
    for kind in order:
        if any(e.event_type == kind for e in events):
            return _SIGNAL_LABEL[kind]
    return "Territory activity"


def _service_and_size(svc: str, beds: int | None) -> str:
    if not beds:
        return f"{svc}, non-bed-based"
    return f"{svc}, {beds} beds"


def _size_emphasis(beds: int | None) -> str:
    if not beds:
        return ""
    if beds >= 60:
        return f" At {beds} beds it is one of the larger entrants in this window."
    if beds >= 40:
        return f" A {beds}-bed location is a material single account."
    return ""


def _recency_phrase(event_date: date, as_of: date) -> str:
    age = (as_of - event_date).days
    if age <= 21:
        return "in the last three weeks, so it is still standing up policies, training and systems"
    if age <= 60:
        return "in the last two months, so onboarding decisions are still open"
    if age <= 120:
        return "within the last four months"
    return f"about {age // 30} months ago"


def _reason(
    *,
    org_name: str,
    events: list[OrgEvent],
    beds: int | None,
    service_types: tuple[str, ...],
    territory: str,
    provider_cluster: int,
    current_rating: str | None,
    has_rating_history: bool,
    as_of: date,
) -> str:
    """Compose a non-empty, evidence-bound explanation. Never returns ''."""
    parts: list[str] = []
    svc = service_types[0].lower() if service_types else "care service"

    regs = [e for e in events if e.event_type == "new_registration"]
    changes = [e for e in events if e.event_type == "rating_changed"]
    published = [e for e in events if e.event_type == "rating_published"]

    if regs:
        ev = regs[0]
        when = _recency_phrase(ev.effective_date, as_of)
        descriptor = _service_and_size(svc, beds)
        emphasis = _size_emphasis(beds)
        if has_rating_history or current_rating:
            # A "new registration" that already carries a rating/history is a
            # re-registration - an ownership, legal-entity or management change.
            rating_note = (
                f" It carries an inherited overall rating of {current_rating}."
                if current_rating
                else ""
            )
            parts.append(
                f"Re-registered with CQC on {ev.effective_date.strftime('%d %b %Y')} "
                f"({descriptor}) {when}. A new legal entity or owner has taken on an existing "
                f"service in {territory} - a natural point to review incumbent suppliers.{rating_note}{emphasis}"
            )
        else:
            parts.append(
                f"Newly registered with CQC on {ev.effective_date.strftime('%d %b %Y')} "
                f"({descriptor}) {when}. A first-time operator in {territory} with no incumbent "
                f"supplier relationships and no inspection history yet.{emphasis}"
            )
    for ev in changes:
        direction = _rating_direction(ev.old_value, ev.new_value)
        if direction == "decline":
            parts.append(
                f"Overall CQC rating moved down from {ev.old_value} to {ev.new_value} on "
                f"{ev.effective_date.strftime('%d %b %Y')} - a downgrade that typically "
                f"triggers commissioner scrutiny, an improvement plan and remedial spend."
            )
        elif direction == "improvement":
            parts.append(
                f"Overall CQC rating improved from {ev.old_value} to {ev.new_value} on "
                f"{ev.effective_date.strftime('%d %b %Y')} - usually evidence of a "
                f"management or ownership change worth timing outreach around."
            )
        else:
            parts.append(
                f"Overall CQC rating was re-published as {ev.new_value} on "
                f"{ev.effective_date.strftime('%d %b %Y')} (previously {ev.old_value})."
            )
    if published and not changes:
        ev = published[0]
        parts.append(
            f"CQC published a new inspection report on {ev.effective_date.strftime('%d %b %Y')} "
            f"(current rating {ev.new_value}) - a fresh regulatory touchpoint and a natural "
            f"reason to make contact."
        )

    if provider_cluster >= 2:
        parts.append(
            f"The provider behind this location has {provider_cluster} locations moving in "
            f"{territory} in this window, so it is an account-level opportunity, not a one-off."
        )

    if not parts:
        # Defensive: an organisation only reaches the shortlist via >=1 event,
        # so this path is unreachable in normal operation. Keep it truthful.
        latest = max(events, key=lambda e: e.effective_date) if events else None
        if latest:
            parts.append(
                f"{_SIGNAL_LABEL.get(latest.event_type, 'Territory activity')} recorded on "
                f"{latest.effective_date.strftime('%d %b %Y')}: {latest.detail}."
            )
        else:
            parts.append(
                f"Included on territory relevance to {territory}; see the evidence links for the "
                f"underlying CQC record."
            )

    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Territory insights + next actions
# --------------------------------------------------------------------------- #


def _territory_insights(
    ranked: list[RankedOrganisation],
    *,
    all_event_rows: list[tuple[dict[str, Any], list[OrgEvent]]],
    scope: TerritoryScope,
) -> dict[str, Any]:
    event_type_counts: Counter[str] = Counter()
    subarea_counts: Counter[str] = Counter()
    service_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    decline = improvement = 0
    beds_entering = 0

    for row, events in all_event_rows:
        subarea = (
            str(row.get("localAuthority") or "").strip()
            if scope.kind == "region"
            else str(row.get("region") or "").strip()
        )
        for ev in events:
            event_type_counts[ev.event_type] += 1
            if subarea:
                subarea_counts[subarea] += 1
            if ev.event_type == "rating_changed":
                d = _rating_direction(ev.old_value, ev.new_value)
                if d == "decline":
                    decline += 1
                elif d == "improvement":
                    improvement += 1
            if ev.event_type == "new_registration":
                try:
                    beds_entering += int(row.get("numberOfBeds") or 0)
                except (TypeError, ValueError):
                    pass
        for svc in _service_types(row):
            service_counts[svc] += 1
        pname = str(row.get("providerName") or row.get("_provider_name") or "").strip()
        if pname:
            provider_counts[pname] += 1

    most_active_providers = [
        {"provider": name, "locations_moving": count}
        for name, count in provider_counts.most_common(5)
        if count >= 2
    ]

    return {
        "events_by_type": dict(sorted(event_type_counts.items())),
        "rating_moves": {"declines": decline, "improvements": improvement},
        "new_beds_entering_market": beds_entering,
        "activity_by_sub_area": [
            {"area": area, "events": count}
            for area, count in subarea_counts.most_common(8)
        ],
        "service_type_mix": [
            {"service_type": svc, "organisations": count}
            for svc, count in service_counts.most_common(6)
        ],
        "most_active_providers": most_active_providers,
        "shortlist_size": len(ranked),
    }


def _next_actions(insights: dict[str, Any], ranked: list[RankedOrganisation], scope: TerritoryScope) -> tuple[str, ...]:
    actions: list[str] = []
    by_type = insights["events_by_type"]
    new_regs = by_type.get("new_registration", 0)
    declines = insights["rating_moves"]["declines"]
    improvements = insights["rating_moves"]["improvements"]

    if new_regs:
        actions.append(
            f"Contact the {new_regs} newly registered location(s) first: they have no incumbent "
            f"supplier and are setting up policies, training and systems now. The shortlist marks "
            f"each one and links its CQC record."
        )
    if declines:
        actions.append(
            f"Approach the {declines} location(s) with a rating downgrade with a specific "
            f"improvement-support offer; a downgrade is a budget-releasing event and the provider "
            f"is on a clock with the regulator."
        )
    if improvements:
        actions.append(
            f"Note the {improvements} location(s) that improved their rating - these are proof "
            f"points and possible reference customers rather than immediate remedial sales."
        )
    if insights["most_active_providers"]:
        top = insights["most_active_providers"][0]["provider"]
        actions.append(
            f"Treat {top} as an account, not a lead: multiple of their locations are moving in "
            f"this window, so target the provider's central quality lead."
        )
    top_area = insights["activity_by_sub_area"][0]["area"] if insights["activity_by_sub_area"] else None
    if top_area and scope.kind == "region":
        actions.append(
            f"Concentrate field time on {top_area}: it has the highest count of qualifying "
            f"events in {scope.name} this window."
        )
    actions.append(
        "Verify each organisation's current status on the linked CQC page before outreach - this "
        "brief reflects the published register edition, not a live lookup."
    )
    return tuple(actions)


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #


def generate_territory_opportunity_brief(
    scope: dict[str, Any] | TerritoryScope,
    purchase_context: PurchaseContext,
    *,
    locations_source: str | Path,
    providers_source: str | Path,
) -> TerritoryBrief:
    """Generate a complete Territory Opportunity Brief.

    ``scope`` may be a raw dict (from checkout metadata) or a
    :class:`TerritoryScope`; it is always validated against the source data.
    Raises :class:`ScopeError` for an invalid/unknown scope and
    :class:`FileNotFoundError` for a missing snapshot.
    """
    locations_path = Path(locations_source)
    providers_path = Path(providers_source)
    if not locations_path.exists():
        raise FileNotFoundError(f"locations snapshot not found: {locations_path}")
    if not providers_path.exists():
        raise FileNotFoundError(f"providers snapshot not found: {providers_path}")

    provider_names = load_provider_names(providers_path)
    location_rows = list(_load_ndjson(locations_path))

    catalogue = known_territories(location_rows)
    validated = validate_scope(scope, catalogue)

    # Anchor the window to the newest source date in the snapshot so output is
    # reproducible and never claims to be more current than the data.
    as_of = _latest_source_date(location_rows)
    if as_of is None:
        raise ScopeError("source snapshot has no usable dates; cannot define a window")
    window_end = as_of
    window_start = as_of - timedelta(days=validated.window_days - 1)

    # First pass: provider cluster counts within scope.
    scoped_rows = [row for row in location_rows if _in_scope(row, validated)]
    territory_locations = len(scoped_rows)

    provider_event_locations: Counter[str] = Counter()
    per_row_events: list[tuple[dict[str, Any], list[OrgEvent]]] = []
    for row in scoped_rows:
        events = _location_events(
            row, window_start=window_start, window_end=window_end, as_of=as_of
        )
        if events:
            provider_id = str(row.get("providerId") or "").strip()
            provider_event_locations[provider_id] += 1
            row = {**row, "_provider_name": provider_names.get(provider_id, "")}
            per_row_events.append((row, events))

    # Build ranked organisations.
    candidates: list[RankedOrganisation] = []
    for row, events in per_row_events:
        provider_id = str(row.get("providerId") or "").strip()
        location_id = str(row.get("locationId") or "").strip()
        provider_name = provider_names.get(provider_id) or str(row.get("name") or "").strip()
        location_name = str(row.get("name") or "").strip()
        if not provider_name or not location_name or not location_id:
            continue
        cluster = provider_event_locations.get(provider_id, 0)
        try:
            beds: int | None = int(row.get("numberOfBeds")) if row.get("numberOfBeds") else None
        except (TypeError, ValueError):
            beds = None
        service_types = _service_types(row)
        current_ratings = row.get("currentRatings") or {}
        overall = current_ratings.get("overall") if isinstance(current_ratings, dict) else None
        current_rating = (
            str(overall.get("rating") or "").strip() or None if isinstance(overall, dict) else None
        )
        has_history = bool(_rating_sequence(row))
        score, breakdown = _score(
            events, beds=beds, provider_cluster=cluster, as_of=as_of,
            re_registration=bool(any(e.event_type == "new_registration" for e in events) and (has_history or current_rating)),
        )
        most_recent = max((e.effective_date for e in events), default=None)
        reason = _reason(
            org_name=provider_name,
            events=events,
            beds=beds,
            service_types=service_types,
            territory=validated.name,
            provider_cluster=cluster,
            current_rating=current_rating,
            has_rating_history=has_history,
            as_of=as_of,
        )
        evidence = tuple(
            {
                "event_type": e.event_type,
                "effective_date": e.effective_date.isoformat(),
                "old_value": e.old_value,
                "new_value": e.new_value,
                "detail": e.detail,
                "source_field": e.source_field,
                "source_url": e.source_url,
                "source_edition": CQC_DATA_PAGE,
            }
            for e in sorted(events, key=lambda e: e.effective_date)
        )
        candidates.append(
            RankedOrganisation(
                rank=0,
                organisation_name=provider_name,
                location_name=location_name,
                location_id=location_id,
                provider_id=provider_id,
                local_authority=str(row.get("localAuthority") or "").strip(),
                region=str(row.get("region") or "").strip(),
                postcode=str(row.get("postalCode") or row.get("postcode") or "").strip(),
                service_types=service_types,
                number_of_beds=beds,
                current_rating=current_rating,
                primary_signal=_primary_signal(events),
                most_recent_event_date=most_recent,
                score=score,
                score_breakdown=breakdown,
                reason=reason,
                evidence=evidence,
            )
        )

    # Deterministic ordering: score desc, then most-recent event desc, then
    # name, then location id. Every key is total and stable.
    candidates.sort(
        key=lambda o: (
            -o.score,
            -(o.most_recent_event_date.toordinal() if o.most_recent_event_date else 0),
            o.organisation_name.casefold(),
            o.location_id,
        )
    )
    shortlist_rows = candidates[: validated.shortlist_target]
    shortlist = tuple(
        RankedOrganisation(**{**org.__dict__, "rank": i})
        for i, org in enumerate(shortlist_rows, start=1)
    )

    insights = _territory_insights(list(shortlist), all_event_rows=per_row_events, scope=validated)
    actions = _next_actions(insights, list(shortlist), validated)

    exec_summary = _executive_summary(
        scope=validated,
        as_of=as_of,
        window_start=window_start,
        window_end=window_end,
        considered=len(per_row_events),
        territory_locations=territory_locations,
        shortlist=shortlist,
        insights=insights,
    )

    caveats = (
        f"This brief reflects the published CQC register edition dated {as_of.isoformat()} "
        f"(the newest date present in the source), not a live API lookup.",
        "The register carries the latest rating and its report date. Where no rating history is "
        "present a change cannot be derived, so a first/refreshed rating is reported as a new "
        "inspection report rather than a rating change.",
        "Organisations with incomplete provider identifiers or names in the source are excluded "
        "from the shortlist rather than shown with gaps.",
        "Opportunity signals indicate where to investigate first; they are not statements about a "
        "provider's quality, finances, or intent.",
        OGL_ATTRIBUTION + ".",
    )
    methodology = (
        f"Scope: {validated.kind.replace('_', ' ')} = {validated.name}. "
        f"Window: {window_start.isoformat()} to {window_end.isoformat()} inclusive "
        f"({validated.window_days} days), anchored to the newest source date.",
        "Supported events: new CQC registration in-window (excluding dormant locations); overall "
        "rating change in-window (derived from ordered historic/current ratings); new inspection "
        "report in-window where no change can be derived.",
        "Score = base weight per event x recency multiplier (1.5 within 30 days, 1.2 within 90, "
        "1.05 within 180) + rating-direction adjustment (downgrade +16, upgrade +9) + a bed-count "
        "size factor + a provider-cluster bonus where the same provider has multiple locations "
        "moving. Scores are capped at 100.",
        "Ties break by most recent event date, then organisation name, then CQC location id, so "
        "the same source data always yields the same ranking.",
    )

    provenance = {
        "source_page": CQC_DATA_PAGE,
        "locations_snapshot": locations_path.name,
        "providers_snapshot": providers_path.name,
        "snapshot_edition_date": as_of.isoformat(),
        "generator": "api.services.territory_brief.generate_territory_opportunity_brief",
        "generated_at": purchase_context.generated_at.astimezone(timezone.utc).isoformat(),
        "licence": OGL_ATTRIBUTION,
        "licence_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
    }

    return TerritoryBrief(
        scope=validated,
        purchase_context=purchase_context,
        as_of_date=as_of,
        window_start=window_start,
        window_end=window_end,
        considered_locations=len(per_row_events),
        territory_locations=territory_locations,
        shortlist=shortlist,
        executive_summary=exec_summary,
        territory_insights=insights,
        next_actions=actions,
        methodology_notes=methodology,
        data_caveats=caveats,
        source_provenance=provenance,
    )


def _latest_source_date(rows: list[dict[str, Any]]) -> date | None:
    latest: date | None = None
    for row in rows:
        cand = _parse_date(row.get("registrationDate"))
        if cand and (latest is None or cand > latest):
            latest = cand
        for report_date, _rating in _rating_sequence(row):
            if latest is None or report_date > latest:
                latest = report_date
    return latest


def _executive_summary(
    *,
    scope: TerritoryScope,
    as_of: date,
    window_start: date,
    window_end: date,
    considered: int,
    territory_locations: int,
    shortlist: tuple[RankedOrganisation, ...],
    insights: dict[str, Any],
) -> dict[str, Any]:
    by_type = insights["events_by_type"]
    top3 = [
        f"{o.organisation_name} ({o.location_name}) - {o.primary_signal.lower()}"
        for o in shortlist[:3]
    ]
    headline = (
        f"{considered} organisation(s) in {scope.name} show a supported opportunity signal in the "
        f"{scope.window_days}-day window ending {window_end.strftime('%d %b %Y')}; "
        f"{len(shortlist)} are shortlisted and ranked."
    )
    movement = []
    if by_type.get("new_registration"):
        movement.append(f"{by_type['new_registration']} new registration(s)")
    if by_type.get("rating_changed"):
        movement.append(f"{by_type['rating_changed']} rating change(s)")
    if by_type.get("rating_published"):
        movement.append(f"{by_type['rating_published']} new inspection report(s)")
    return {
        "territory": scope.name,
        "territory_kind": scope.kind.replace("_", " "),
        "date_generated": as_of.isoformat(),
        "window": f"{window_start.isoformat()} to {window_end.isoformat()}",
        "territory_locations_in_source": territory_locations,
        "opportunity_set_size": considered,
        "shortlisted": len(shortlist),
        "headline": headline,
        "movement_summary": ", ".join(movement) if movement else "no supported movement in window",
        "strongest_opportunities": top3,
        "limitations": (
            "Reflects the published CQC register edition, not a live lookup; opportunity signals "
            "show where to look first, not provider quality or intent."
        ),
    }


# --------------------------------------------------------------------------- #
# Supporting exports
# --------------------------------------------------------------------------- #


def brief_to_csv(brief: TerritoryBrief) -> str:
    """CRM-ready shortlist CSV. Supporting evidence, not the whole product."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "rank",
            "organisation",
            "location",
            "cqc_location_id",
            "cqc_provider_id",
            "local_authority",
            "region",
            "postcode",
            "service_types",
            "number_of_beds",
            "current_rating",
            "primary_signal",
            "most_recent_event_date",
            "opportunity_score",
            "reason",
            "evidence_events",
            "cqc_record_url",
        ]
    )
    for org in brief.shortlist:
        evidence_events = " | ".join(
            f"{e['event_type']} {e['effective_date']}"
            + (f" ({e['old_value']}->{e['new_value']})" if e.get("old_value") else "")
            for e in org.evidence
        )
        writer.writerow(
            [
                org.rank,
                org.organisation_name,
                org.location_name,
                org.location_id,
                org.provider_id,
                org.local_authority,
                org.region,
                org.postcode,
                "; ".join(org.service_types),
                org.number_of_beds if org.number_of_beds is not None else "",
                org.current_rating or "",
                org.primary_signal,
                org.most_recent_event_date.isoformat() if org.most_recent_event_date else "",
                org.score,
                org.reason,
                evidence_events,
                CQC_PROFILE_URL.format(location_id=org.location_id),
            ]
        )
    return buf.getvalue()
