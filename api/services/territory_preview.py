"""Free Territory Brief preview: factual counts and up to three dated new registrations.

This is deliberately not the Brief's ranking engine (``territory_brief.py``),
which reads a full source edition and is far too heavy for a public request.
The preview only reports what the live directory and event ledger record, and
says so. Three rules keep it from overclaiming:

* a count it cannot measure is reported as unavailable, never as zero
  (production ``rating_changed`` events can lack a source date);
* the window end is event recency, and CQC source freshness is reported
  separately, qualifying every claim when it is not ``fresh``;
* quarantined locations are excluded upstream by the queries.

Wording follows docs/manuals/SALES_GTM_MANUAL.md: providers to focus on,
never leads, need or intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from api.service_taxonomy import taxonomy

WINDOW_DAYS = 90
EXAMPLE_COUNT = 3
BRIEF_MAX_ORGANISATIONS = 50
CQC_LOCATION_URL = "https://www.cqc.org.uk/location/{location_id}"


@dataclass(frozen=True)
class PreviewScope:
    kind: str
    name: str
    service_key: str | None
    service_slug: str | None


def window_for(window_end: date) -> tuple[date, date]:
    return window_end - timedelta(days=WINDOW_DAYS - 1), window_end


def _fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def _service_names() -> tuple[dict[str, str], dict[str, str]]:
    by_slug = {e["slug"]: e["name"] for e in taxonomy()}
    by_alias = {a.casefold().strip(): e["name"] for e in taxonomy() for a in e["aliases"]}
    return by_slug, by_alias


# CQC's own service-type wording for the four services the preview filters on.
CQC_SERVICE_LABELS = {
    "home-care": "Domiciliary care service",
    "residential-care-homes": "Care home service without nursing",
    "nursing-care-homes": "Care home service with nursing",
    "supported-living": "Supported living service",
}


def service_display_name(slug: str | None) -> str | None:
    """CQC's wording where we have it, else the taxonomy's canonical name."""
    if not slug:
        return None
    return CQC_SERVICE_LABELS.get(slug) or _service_names()[0].get(slug)


def _location_service(service_types: str | None, preferred_slug: str | None) -> str | None:
    """Canonical service name for the row: the filtered service, else its first known one."""
    preferred = service_display_name(preferred_slug)
    if preferred:
        return preferred
    by_alias = _service_names()[1]
    slug_by_alias = {a.casefold().strip(): e["slug"] for e in taxonomy() for a in e["aliases"]}
    for raw in (service_types or "").split("|"):
        key = raw.casefold().strip()
        slug = slug_by_alias.get(key)
        if slug in CQC_SERVICE_LABELS:
            return CQC_SERVICE_LABELS[slug]
        if key in by_alias:
            return by_alias[key]
    return None


def reason_for(event: dict[str, Any], preferred_slug: str | None) -> str:
    """One factual, dated sentence; it never claims need, budget or intent to buy."""
    when = event["event_date"]
    service = _location_service(event.get("service_types"), preferred_slug)
    suffix = f" · {service}" if service else ""
    if event["event_type"] == "new_registration":
        return f"Registered with CQC on {_fmt(when)}{suffix}"
    old, new = event.get("old_value") or "a previous rating", event.get("new_value") or "a new rating"
    return f"CQC rating moved from {old} to {new}, report dated {_fmt(when)}{suffix}"


def pick_examples(events: Iterable[dict[str, Any]], limit: int = EXAMPLE_COUNT) -> list[dict[str, Any]]:
    """Newest first, one per provider, alternating signal types when both exist."""
    ordered = sorted(events, key=lambda e: (e["event_date"], str(e["location_id"])), reverse=True)
    by_type: dict[str, list[dict[str, Any]]] = {}
    for event in ordered:
        by_type.setdefault(event["event_type"], []).append(event)
    queues = [by_type[t] for t in ("rating_changed", "new_registration") if t in by_type]
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    while queues and len(chosen) < limit:
        for queue in list(queues):
            while queue:
                event = queue.pop(0)
                org = str(event.get("provider_id") or event["location_id"])
                if org not in seen:
                    seen.add(org)
                    chosen.append(event)
                    break
            if not queue:
                queues.remove(queue)
            if len(chosen) >= limit:
                break
    return chosen


def rating_availability(dated: int, undated: int) -> dict[str, Any]:
    """Distinguish 'none recorded' from 'cannot be measured'."""
    if undated == 0:
        return {"status": "available", "count": dated, "undated": 0}
    if dated == 0:
        return {
            "status": "unavailable",
            "count": None,
            "undated": undated,
            "note": "We can't yet date rating changes here, so they aren't counted.",
        }
    return {
        "status": "partial",
        "count": dated,
        "undated": undated,
        "note": f"We can't yet date {undated:,} rating changes here, so they aren't counted.",
    }


_FRESHNESS_NOTICES = {
    "partial": "Our copy of the CQC register still has incomplete or unconfirmed source evidence",
    "stale": "Our latest full check of the CQC register is out of date",
}


def freshness_notice(status: str) -> str | None:
    """Plain-English qualification shown whenever source coverage is not confirmed."""
    if status == "fresh":
        return None
    lead = _FRESHNESS_NOTICES.get(status, "We can't currently confirm how up to date our copy of the CQC register is")
    return f"{lead}, so these figures are provisional and may be incomplete."


def _source(freshness: dict[str, Any], window_end: date) -> dict[str, Any]:
    status = freshness.get("status") or "unknown"
    return {
        "notice": freshness_notice(status),
        "window_anchor": window_end.isoformat(),
        "window_anchor_basis": "Newest CQC registration date recorded by CareGist. This is not a freshness guarantee.",
        "freshness_status": status,
        "coverage_confirmed": status == "fresh",
        "source_published_at": freshness.get("sourcePublishedAt"),
        "reconciled_at": freshness.get("reconciledAt"),
        "freshness_message": freshness.get("message"),
        "basis": "Public CQC register records held by CareGist. CareGist is independent of CQC.",
        "licence": "Contains public sector information licensed under the Open Government Licence v3.0.",
        "licence_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
    }


def build_preview(
    scope: PreviewScope,
    *,
    organisations: int,
    locations: int,
    window_end: date,
    counts: dict[str, int],
    events: list[dict[str, Any]],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    window_start, _ = window_for(window_end)
    source = _source(freshness, window_end)
    confirmed = source["coverage_confirmed"]
    ratings = rating_availability(counts["rating_changes_dated"], counts["rating_changes_undated"])
    examples = [
        {
            "location_name": e["name"],
            "location_id": e["location_id"],
            "provider_id": e.get("provider_id"),
            "town": e.get("town"),
            "signal": e["event_type"],
            "event_date": e["event_date"].isoformat(),
            "reason": reason_for(e, scope.service_slug),
            "source_url": CQC_LOCATION_URL.format(location_id=e["location_id"]),
        }
        for e in pick_examples(events)
    ]
    if organisations:
        note = "A Brief can include up to 50 providers. We confirm suitability and the exact shortlist size before any payment."
    else:
        note = "No distinct providers match. We need to review or widen the scope before any payment."
    if not confirmed:
        note += " These figures are provisional."

    caveats = [
        "Examples are the most recent new registrations by organisation providers, not the Brief's ranked shortlist. "
        "Rating changes are counted but not named, and providers registered as individuals or partnerships are not named.",
        "Providers to focus on, not leads ready to buy. Public records do not show need, budget or intent.",
    ]
    if not confirmed:
        caveats.insert(0, source["notice"])
    if ratings["status"] != "available":
        caveats.insert(0, ratings["note"])

    return {
        "scope": {
            "kind": scope.kind,
            "name": scope.name,
            "service": scope.service_key,
            "service_label": service_display_name(scope.service_slug),
        },
        "organisations": organisations,
        "locations": locations,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat(), "days": WINDOW_DAYS},
        "signals": {
            "new_registrations": counts["new_registrations"],
            "rating_changes": ratings,
            "organisations_with_signals": counts["organisations_with_signals"],
        },
        "examples": examples,
        "brief": {
            "fits": None if organisations else False,
            "provisional": not confirmed,
            "min_organisations": None,
            "max_organisations": BRIEF_MAX_ORGANISATIONS,
            "note": note,
        },
        "source": source,
        "caveats": caveats,
    }
