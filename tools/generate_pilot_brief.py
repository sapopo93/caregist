#!/usr/bin/env python3
"""Operator CLI for a buyer-specific pilot Territory Opportunity Brief.

Generates the base brief at the maximum shortlist, then applies a care software
vendor's profile and CRM suppression via
:func:`api.services.territory_brief_pilot.build_pilot_brief`. For manually
delivered pilots only; the paid self-serve path does not use it. No network
calls.

Example
-------
    python3 -m tools.generate_pilot_brief \\
        --kind region --name "West Midlands" \\
        --group-size-min 5 --group-size-max 30 \\
        --crm-suppression .tmp/buyer-crm.csv \\
        --locations-source _locations_detail.ndjson \\
        --providers-source _providers_detail.ndjson
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from api.services.territory_brief import (
    MAX_SHORTLIST,
    PurchaseContext,
    ScopeError,
    brief_to_csv,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_pilot import (
    DEFAULT_PILOT_TARGET,
    BuyerProfile,
    build_pilot_brief,
    load_crm_suppression,
    pilot_to_crm_csv,
    pilot_to_csv,
    pilot_to_review_markdown,
)
from api.services.territory_brief_render import render_brief_pdf


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kind", choices=["local_authority", "region"], default="local_authority")
    p.add_argument("--name", required=True, help="territory name (case-insensitive)")
    p.add_argument("--window-days", type=int, default=90)
    p.add_argument("--pilot-target", type=int, default=DEFAULT_PILOT_TARGET)
    p.add_argument("--group-size-min", type=int)
    p.add_argument("--group-size-max", type=int)
    p.add_argument("--beds-min", type=int)
    p.add_argument("--beds-max", type=int)
    p.add_argument("--include-service-type", action="append", default=[])
    p.add_argument("--exclude-service-type", action="append", default=[])
    p.add_argument("--exclude-provider-id", action="append", default=[])
    p.add_argument("--crm-suppression", type=Path, help="buyer CRM CSV; only ID/name columns are read")
    p.add_argument("--locations-source", type=Path, default=Path("_locations_detail.ndjson"))
    p.add_argument("--providers-source", type=Path, default=Path("_providers_detail.ndjson"))
    p.add_argument("--order-reference", default="pilot")
    p.add_argument("--generated-at", default=None, help="ISO timestamp; default fixed epoch for reproducibility")
    p.add_argument("--out-dir", type=Path, default=Path(".tmp/pilot-brief"))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = (
        datetime.fromisoformat(args.generated_at)
        if args.generated_at
        else datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    context = PurchaseContext(
        order_reference=args.order_reference,
        generated_at=generated_at,
        terms_version="pilot",
    )
    profile = BuyerProfile(
        group_size_min=args.group_size_min,
        group_size_max=args.group_size_max,
        beds_min=args.beds_min,
        beds_max=args.beds_max,
        include_service_types=tuple(args.include_service_type),
        exclude_service_types=tuple(args.exclude_service_type),
        exclude_provider_ids=tuple(args.exclude_provider_id),
        pilot_target=args.pilot_target,
    )
    try:
        suppression = load_crm_suppression(args.crm_suppression) if args.crm_suppression else None
        brief = generate_territory_opportunity_brief(
            {
                "kind": args.kind,
                "name": args.name,
                "window_days": args.window_days,
                "shortlist_target": MAX_SHORTLIST,
            },
            context,
            locations_source=args.locations_source,
            providers_source=args.providers_source,
        )
        pilot = build_pilot_brief(
            brief, profile, locations_source=args.locations_source, suppression=suppression
        )
    except ScopeError as exc:
        print(f"scope error: {exc}")
        return 2

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = brief.scope.name.lower().replace(" ", "-").replace("/", "-")
    outputs = {
        "base pdf": (out_dir / f"base-brief-{slug}.pdf", render_brief_pdf(brief)),
        "base csv": (out_dir / f"base-brief-{slug}.csv", brief_to_csv(brief)),
        "pilot json": (
            out_dir / f"pilot-brief-{slug}.json",
            json.dumps(pilot.to_json(), indent=2, sort_keys=True) + "\n",
        ),
        "qualification": (out_dir / f"pilot-qualification-{slug}.csv", pilot_to_csv(pilot)),
        "crm import": (out_dir / f"pilot-crm-import-{slug}.csv", pilot_to_crm_csv(pilot)),
        "review": (out_dir / f"pilot-review-{slug}.md", pilot_to_review_markdown(pilot)),
    }
    for path, content in outputs.values():
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")

    print(f"territory:   {brief.scope.name} ({brief.scope.kind})")
    print(f"window:      {brief.window_start} to {brief.window_end}")
    print(f"pool:        {pilot.pool_size}")
    print(f"accounts:    {len(pilot.accounts)} of target {profile.pilot_target}")
    print("exclusions:  " + ", ".join(f"{k} {v}" for k, v in pilot.exclusions.items()))
    if pilot.shortfall_notice:
        print(f"notice:      {pilot.shortfall_notice}")
    for label, (path, _) in outputs.items():
        print(f"{label + ':':<13}{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
