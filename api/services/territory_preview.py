"""Free Territory Brief preview: factual counts and three dated example signals.

This is deliberately not the Brief's ranking engine (``territory_brief.py``),
which reads a full source edition and is far too heavy for a public request.
The preview only reports what the live directory and event ledger record, and
says so. Wording follows docs/manuals/SALES_GTM_MANUAL.md: organisations to
investigate, never leads, need or intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

WINDOW_DAYS = 90
EXAMPLE_COUNT = 3
BRIEF_MIN_ORGANISATIONS = 25
BRIEF_MAX_ORGANISATIONS = 50
CQC_LOCATION_URL = "https://www.cqc.org.uk/location/{location_id}"


@dataclass(frozen=True)
class PreviewScope:
    kind: str
    name: str
    service_key: str | None
    service_label: str | None


def window_for(as_of: date) -> tuple[date, date]:
    return as_of - timedelta(days=WINDOW_DAYS - 1), as_of


def _fmt(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def _weeks_before(event_date: date, as_of: date) -> str:
    days = (as_of - event_date).days
    if days < 7:
        return "in the final week of the window"
    weeks = days // 7
    return f"{weeks} week{'s' if weeks != 1 else ''} before the data date"


def _first_service(service_types: str | None, preferred: str | None) -> str | None:
    services = [s.strip() for s in (service_types or "").split("|") if s.strip()]
    if preferred and preferred in services:
        return preferred
    return services[0] if services else None


def reason_for(event: dict[str, Any], as_of: date, preferred_service: str | None) -> str:
    """One factual sentence; it never claims need, budget or intent to buy."""
    when = event["event_date"]
    service = _first_service(event.get("service_types"), preferred_service)
    suffix = f" · {service}" if service else ""
    if event["event_type"] == "new_registration":
        return f"Registered with CQC on {_fmt(when)}, {_weeks_before(when, as_of)}{suffix}"
    old, new = event.get("old_value") or "a previous rating", event.get("new_value") or "a new rating"
    return f"CQC rating moved from {old} to {new}, report dated {_fmt(when)}{suffix}"


def pick_examples(events: Iterable[dict[str, Any]], limit: int = EXAMPLE_COUNT) -> list[dict[str, Any]]:
    """Newest first, one per organisation, alternating signal types when both exist."""
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


def build_preview(
    scope: PreviewScope,
    *,
    organisations: int,
    locations: int,
    as_of: date,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    window_start, window_end = window_for(as_of)
    new_regs = [e for e in events if e["event_type"] == "new_registration"]
    ratings = [e for e in events if e["event_type"] == "rating_changed"]
    signal_orgs = {str(e.get("provider_id") or e["location_id"]) for e in events}
    examples = [
        {
            "location_name": e["name"],
            "location_id": e["location_id"],
            "provider_id": e.get("provider_id"),
            "town": e.get("town"),
            "signal": e["event_type"],
            "event_date": e["event_date"].isoformat(),
            "reason": reason_for(e, as_of, scope.service_label),
            "source_url": CQC_LOCATION_URL.format(location_id=e["location_id"]),
        }
        for e in pick_examples(events)
    ]
    fits = organisations >= BRIEF_MIN_ORGANISATIONS
    return {
        "scope": {
            "kind": scope.kind,
            "name": scope.name,
            "service": scope.service_key,
            "service_label": scope.service_label,
        },
        "organisations": organisations,
        "locations": locations,
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat(), "days": WINDOW_DAYS},
        "signals": {
            "new_registrations": len(new_regs),
            "rating_changes": len(ratings),
            "organisations_with_signals": len(signal_orgs),
        },
        "examples": examples,
        "brief": {
            "fits": fits,
            "min_organisations": BRIEF_MIN_ORGANISATIONS,
            "max_organisations": BRIEF_MAX_ORGANISATIONS,
            "note": (
                "Enough distinct organisations for a 25 to 50 organisation Brief, subject to the agreed scope."
                if fits
                else "Fewer than 25 distinct organisations match. A Brief would need a wider scope; "
                "we confirm this before any payment."
            ),
        },
        "source": {
            "as_of": as_of.isoformat(),
            "basis": "Public CQC register records held by CareGist. CareGist is independent of CQC.",
        },
        "caveats": [
            "Examples are the most recent recorded signals, not the Brief's ranked shortlist.",
            "Organisations to investigate, not leads ready to buy. Public records do not show need, budget or intent.",
        ],
    }
