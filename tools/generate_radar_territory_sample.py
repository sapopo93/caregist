#!/usr/bin/env python3
"""Generate an internal CareGist Radar weekly territory sample from local CQC data.

The generator is deterministic:
1. Find the newest source date present in the mirrored CQC snapshot.
2. Define the latest inclusive seven-day window ending on that date.
3. Build supported new-registration and rating-change events in that window.
4. Select the local authority with the highest supported event count;
   break ties alphabetically by territory name.
5. Emit one Markdown sample alert plus machine-readable JSON evidence.

No live API calls are made. All provenance points back to the local snapshot files
that hold the public CQC data.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUTPUT_DIR = Path("artifacts/radar-sample")
DEFAULT_LOCATIONS_SOURCE = Path("_locations_detail.ndjson")
DEFAULT_PROVIDERS_SOURCE = Path("_providers_detail.ndjson")
CQC_PROFILE_URL = "https://api.service.cqc.org.uk/public/v1/locations/{location_id}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TerritoryEvent:
    event_type: str
    territory: str
    provider_id: str
    provider_name: str
    location_id: str
    location_name: str
    local_authority: str
    region: str
    effective_date: date
    old_value: Any
    new_value: Any
    source_path: str
    source_url: str
    source_note: str


@dataclass(frozen=True)
class SampleBundle:
    generated_at: datetime
    as_of_date: date | None
    window_start: date | None
    window_end: date | None
    selection_rule: str
    selected_territory: str | None
    territory_counts: list[dict[str, Any]]
    events: list[TerritoryEvent]
    source_paths: dict[str, str]
    rating_change_reason: str
    skipped_locations: int
    zero_event_reason: str | None = None



def _load_ndjson(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            yield json.loads(line)



def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None



def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None



def _uk_date(value: date | None) -> str:
    if value is None:
        return "n/a"
    return value.strftime("%d/%m/%Y")



def load_provider_names(path: Path) -> dict[str, str]:
    names: dict[str, str] = {}
    for row in _load_ndjson(path):
        provider_id = str(row.get("providerId") or "").strip()
        provider_name = str(row.get("name") or "").strip()
        if provider_id and provider_name and provider_id not in names:
            names[provider_id] = provider_name
    return names



def _source_path_text(path: Path) -> str:
    # Persist paths relative to the repository so generated evidence is portable
    # across developer machines and CI workspaces.
    return Path(os.path.relpath(path.resolve(), REPOSITORY_ROOT)).as_posix()



def _source_url(location_id: str) -> str:
    return CQC_PROFILE_URL.format(location_id=location_id)



def _territory_name(row: dict[str, Any]) -> str | None:
    territory = str(row.get("localAuthority") or "").strip()
    if territory:
        return territory
    fallback = str(row.get("region") or "").strip()
    return fallback or None



def _rating_sequence(row: dict[str, Any]) -> list[tuple[date, str]]:
    """Return one valid overall rating per report date in chronological order.

    Later historic entries replace earlier entries for a duplicate date. The
    current rating is authoritative for its report date and therefore replaces
    any historic value recorded for that same date.
    """

    by_report_date: dict[date, str] = {}
    historic = row.get("historicRatings")
    if isinstance(historic, list):
        for item in historic:
            if not isinstance(item, dict):
                continue
            report_date = _parse_date(item.get("reportDate"))
            overall = item.get("overall")
            rating = str(overall.get("rating") or "").strip() if isinstance(overall, dict) else ""
            if report_date is not None and rating:
                by_report_date[report_date] = rating

    current = row.get("currentRatings")
    current_overall = current.get("overall") if isinstance(current, dict) else None
    if isinstance(current_overall, dict):
        report_date = _parse_date(current_overall.get("reportDate"))
        rating = str(current_overall.get("rating") or "").strip()
        if report_date is not None and rating:
            by_report_date[report_date] = rating

    return sorted(by_report_date.items())



def latest_source_date(locations: Iterable[dict[str, Any]]) -> date | None:
    latest: date | None = None
    for row in locations:
        for candidate in (_parse_date(row.get("registrationDate")),):
            if candidate is not None and (latest is None or candidate > latest):
                latest = candidate
        for report_date, _rating in _rating_sequence(row):
            if latest is None or report_date > latest:
                latest = report_date
    return latest



def _new_registration_event(
    row: dict[str, Any],
    *,
    provider_names: dict[str, str],
    source_path: Path,
    window_start: date,
    window_end: date,
) -> TerritoryEvent | None:
    registration_date = _parse_date(row.get("registrationDate"))
    if registration_date is None or not (window_start <= registration_date <= window_end):
        return None

    provider_id = str(row.get("providerId") or "").strip()
    location_id = str(row.get("locationId") or "").strip()
    provider_name = provider_names.get(provider_id, "").strip()
    territory = _territory_name(row)
    location_name = str(row.get("name") or "").strip()
    if not provider_id or not location_id or not provider_name or not territory or not location_name:
        return None

    return TerritoryEvent(
        event_type="new_registration",
        territory=territory,
        provider_id=provider_id,
        provider_name=provider_name,
        location_id=location_id,
        location_name=location_name,
        local_authority=str(row.get("localAuthority") or "").strip(),
        region=str(row.get("region") or "").strip(),
        effective_date=registration_date,
        old_value=None,
        new_value={
            "registrationStatus": str(row.get("registrationStatus") or "").strip() or None,
            "registrationDate": _iso(registration_date),
        },
        source_path=_source_path_text(source_path),
        source_url=_source_url(location_id),
        source_note="Derived from location.registrationDate in the mirrored public CQC snapshot; no live API call was made.",
    )



def _rating_change_events(
    row: dict[str, Any],
    *,
    provider_names: dict[str, str],
    source_path: Path,
    window_start: date,
    window_end: date,
) -> list[TerritoryEvent]:
    provider_id = str(row.get("providerId") or "").strip()
    location_id = str(row.get("locationId") or "").strip()
    provider_name = provider_names.get(provider_id, "").strip()
    territory = _territory_name(row)
    location_name = str(row.get("name") or "").strip()
    if not provider_id or not location_id or not provider_name or not territory or not location_name:
        return []

    entries = _rating_sequence(row)
    if len(entries) < 2:
        return []

    events: list[TerritoryEvent] = []
    previous_rating: str | None = None
    for report_date, rating in entries:
        if previous_rating is not None and previous_rating != rating and window_start <= report_date <= window_end:
            events.append(
                TerritoryEvent(
                    event_type="rating_changed",
                    territory=territory,
                    provider_id=provider_id,
                    provider_name=provider_name,
                    location_id=location_id,
                    location_name=location_name,
                    local_authority=str(row.get("localAuthority") or "").strip(),
                    region=str(row.get("region") or "").strip(),
                    effective_date=report_date,
                    old_value=previous_rating,
                    new_value=rating,
                    source_path=_source_path_text(source_path),
                    source_url=_source_url(location_id),
                    source_note=(
                        "Derived from normalized historicRatings[].overall and currentRatings.overall values ordered by "
                        "reportDate; currentRatings.overall is authoritative for duplicate dates; no live API call was made."
                    ),
                )
            )
        previous_rating = rating
    return events



def collect_events(
    locations: Iterable[dict[str, Any]],
    *,
    provider_names: dict[str, str],
    source_path: Path,
    window_start: date,
    window_end: date,
) -> tuple[list[TerritoryEvent], int]:
    events: list[TerritoryEvent] = []
    skipped_locations = 0
    for row in locations:
        before = len(events)
        reg_event = _new_registration_event(
            row,
            provider_names=provider_names,
            source_path=source_path,
            window_start=window_start,
            window_end=window_end,
        )
        if reg_event is not None:
            events.append(reg_event)
        events.extend(
            _rating_change_events(
                row,
                provider_names=provider_names,
                source_path=source_path,
                window_start=window_start,
                window_end=window_end,
            )
        )
        if len(events) == before:
            skipped_locations += 1
    events.sort(key=lambda event: (event.effective_date, event.provider_name, event.location_id, event.event_type, event.location_name))
    return events, skipped_locations



def _event_counts(events: Iterable[TerritoryEvent]) -> tuple[Counter[str], Counter[str]]:
    territory_counts: Counter[str] = Counter()
    event_type_counts: Counter[str] = Counter()
    for event in events:
        territory_counts[event.territory] += 1
        event_type_counts[event.event_type] += 1
    return territory_counts, event_type_counts



def select_territory(territory_counts: Counter[str]) -> str | None:
    if not territory_counts:
        return None
    max_count = max(territory_counts.values())
    return sorted([territory for territory, count in territory_counts.items() if count == max_count])[0]



def _territory_counts_list(territory_counts: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"territory": territory, "count": count}
        for territory, count in sorted(territory_counts.items(), key=lambda item: (-item[1], item[0]))
    ]



def _format_new_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item is None or item == "":
                continue
            parts.append(f"{key}={item}")
        return "; ".join(parts) if parts else "n/a"
    return str(value)



def render_markdown(bundle: SampleBundle) -> str:
    lines: list[str] = [
        "# DRAFT — not approved",
        "# INTERNAL SAMPLE — not for sending or publication",
        "",
        "## CareGist Radar weekly territory sample",
        "",
        f"**As of:** {_uk_date(bundle.as_of_date)}",
        f"**Window:** {_uk_date(bundle.window_start)} to {_uk_date(bundle.window_end)}",
        f"**Deterministic rule:** {bundle.selection_rule}",
    ]

    if bundle.selected_territory is None:
        lines.extend(
            [
                "",
                "### No supported events found",
                bundle.zero_event_reason or "The latest seven-day window contains no supported new-registration or rating-change events in the local CQC snapshot.",
                "",
                "### CTA placeholder",
                "[CTA PLACEHOLDER: Review this empty-window sample internally before any external action.]",
                "",
                "*Historical source dates only. This internal sample is based on a mirrored public CQC snapshot and must not be treated as live data, publication-ready copy, or an endorsement by CQC.*",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    registration_events = [event for event in bundle.events if event.event_type == "new_registration"]
    rating_events = [event for event in bundle.events if event.event_type == "rating_changed"]
    lines.extend(
        [
            "",
            f"**Selected territory:** {bundle.selected_territory}",
            f"**Supported new registrations:** {len(registration_events)}",
            f"**Supported rating changes:** {len(rating_events)}",
            "",
            "### Why this territory",
            "It has the highest supported event count in the latest seven-day window. Ties are broken alphabetically, and the window is anchored to the newest source date found in the mirrored snapshot.",
        ]
    )

    if registration_events:
        lines.extend([
            "",
            "### New registrations",
        ])
        for event in registration_events:
            lines.extend(
                [
                    "",
                    f"- **{event.location_name}** ({event.location_id})",
                    f"  - Provider: {event.provider_name} ({event.provider_id})",
                    f"  - Event: {event.event_type.replace('_', ' ')}",
                    f"  - Effective date: {_uk_date(event.effective_date)}",
                    f"  - Old value: {_format_new_value(event.old_value)}",
                    f"  - New value: {_format_new_value(event.new_value)}",
                    f"  - Provenance: {event.source_path}",
                    f"  - URL / method note: {event.source_url} — {event.source_note}",
                ]
            )
    if rating_events:
        lines.extend([
            "",
            "### Rating changes",
        ])
        for event in rating_events:
            lines.extend(
                [
                    "",
                    f"- **{event.location_name}** ({event.location_id})",
                    f"  - Provider: {event.provider_name} ({event.provider_id})",
                    f"  - Event: {event.event_type.replace('_', ' ')}",
                    f"  - Effective date: {_uk_date(event.effective_date)}",
                    f"  - Old value: {_format_new_value(event.old_value)}",
                    f"  - New value: {_format_new_value(event.new_value)}",
                    f"  - Provenance: {event.source_path}",
                    f"  - URL / method note: {event.source_url} — {event.source_note}",
                ]
            )
    else:
        lines.extend(
            [
                "",
                "### Rating changes",
                "0 supported rating-change events in this seven-day window.",
                "Reason: no normalized historic/current rating sequence produced a changed rating dated inside the selected window.",
            ]
        )

    lines.extend(
        [
            "",
            "### CTA placeholder",
            f"[CTA PLACEHOLDER: Review the {bundle.selected_territory} sample internally before any external action.]",
            "",
            "*Historical source dates only. This internal sample is based on a mirrored public CQC snapshot and must not be treated as live data, publication-ready copy, or an endorsement by CQC.*",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"



def build_sample(
    *,
    locations_source: Path,
    providers_source: Path,
) -> SampleBundle:
    provider_names = load_provider_names(providers_source)
    location_rows = list(_load_ndjson(locations_source))
    latest_date = latest_source_date(location_rows)
    selection_rule = (
        "Choose the local authority with the highest count of supported events in the latest seven-day window ending on "
        f"the newest source date in the snapshot ({_uk_date(latest_date)}); break ties alphabetically by territory name."
    )

    if latest_date is None:
        return SampleBundle(
            generated_at=datetime(1970, 1, 1, tzinfo=timezone.utc),
            as_of_date=None,
            window_start=None,
            window_end=None,
            selection_rule=selection_rule,
            selected_territory=None,
            territory_counts=[],
            events=[],
            source_paths={
                "locations_detail": _source_path_text(locations_source),
                "providers_detail": _source_path_text(providers_source),
            },
            rating_change_reason="No source dates were available in the mirrored snapshot.",
            skipped_locations=0,
            zero_event_reason="No source dates were available to define a seven-day window.",
        )

    window_end = latest_date
    window_start = latest_date - timedelta(days=6)
    events, skipped_locations = collect_events(
        location_rows,
        provider_names=provider_names,
        source_path=locations_source,
        window_start=window_start,
        window_end=window_end,
    )
    territory_counts, event_type_counts = _event_counts(events)
    selected_territory = select_territory(territory_counts)
    selected_events = [event for event in events if event.territory == selected_territory] if selected_territory else []
    rating_reason = (
        "No supported rating-change events fell inside the selected window. "
        f"Supported event types in the window: {dict(event_type_counts)}."
        if event_type_counts.get("rating_changed", 0) == 0
        else "Supported rating-change events were found and included in the selected territory sample."
    )

    zero_event_reason = None
    if not events:
        zero_event_reason = (
            "The latest seven-day window contains no supported new-registration or rating-change events in the local CQC snapshot."
        )

    return SampleBundle(
        # Anchor metadata to the snapshot rather than wall-clock time so
        # byte-for-byte output is reproducible for identical inputs.
        generated_at=datetime.combine(latest_date, datetime.min.time(), tzinfo=timezone.utc),
        as_of_date=latest_date,
        window_start=window_start,
        window_end=window_end,
        selection_rule=selection_rule,
        selected_territory=selected_territory,
        territory_counts=_territory_counts_list(territory_counts),
        events=selected_events,
        source_paths={
            "locations_detail": _source_path_text(locations_source),
            "providers_detail": _source_path_text(providers_source),
        },
        rating_change_reason=rating_reason,
        skipped_locations=skipped_locations,
        zero_event_reason=zero_event_reason,
    )



def render_json(bundle: SampleBundle) -> dict[str, Any]:
    registration_events = [event for event in bundle.events if event.event_type == "new_registration"]
    rating_events = [event for event in bundle.events if event.event_type == "rating_changed"]
    return {
        "generated_at": bundle.generated_at.isoformat(),
        "as_of_date": _iso(bundle.as_of_date),
        "window_start": _iso(bundle.window_start),
        "window_end": _iso(bundle.window_end),
        "selection_rule": bundle.selection_rule,
        "selected_territory": bundle.selected_territory,
        "territory_counts": bundle.territory_counts,
        "summary": {
            "new_registration_events": len(registration_events),
            "rating_change_events": len(rating_events),
            "skipped_locations_without_supported_events": bundle.skipped_locations,
            "rating_change_reason": bundle.rating_change_reason,
        },
        "source_paths": bundle.source_paths,
        "events": [
            {
                "event_type": event.event_type,
                "territory": event.territory,
                "provider_id": event.provider_id,
                "provider_name": event.provider_name,
                "location_id": event.location_id,
                "location_name": event.location_name,
                "local_authority": event.local_authority,
                "region": event.region,
                "effective_date": _iso(event.effective_date),
                "source_date": _iso(event.effective_date),
                "old_value": event.old_value,
                "new_value": event.new_value,
                "source_path": event.source_path,
                "source_url": event.source_url,
                "source_note": event.source_note,
            }
            for event in bundle.events
        ],
        "zero_event_reason": bundle.zero_event_reason,
    }



def write_outputs(bundle: SampleBundle, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "weekly-territory-sample.md"
    json_path = output_dir / "weekly-territory-sample.json"
    markdown_path.write_text(render_markdown(bundle), encoding="utf-8")
    json_path.write_text(json.dumps(render_json(bundle), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return markdown_path, json_path



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the CareGist Radar weekly territory sample.")
    parser.add_argument("--locations-source", type=Path, default=DEFAULT_LOCATIONS_SOURCE)
    parser.add_argument("--providers-source", type=Path, default=DEFAULT_PROVIDERS_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    bundle = build_sample(locations_source=args.locations_source, providers_source=args.providers_source)
    markdown_path, json_path = write_outputs(bundle, args.output_dir)
    print(f"Wrote {markdown_path}")
    print(f"Wrote {json_path}")
    print(f"Selected territory: {bundle.selected_territory or 'none'}")
    print(f"Window: {_uk_date(bundle.window_start)} to {_uk_date(bundle.window_end)}")
    print(f"Supported events: {len(bundle.events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
