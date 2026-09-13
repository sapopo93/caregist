#!/usr/bin/env python3
"""CLI wrapper around :func:`api.services.territory_brief.generate_territory_opportunity_brief`.

For operator dry-runs and the pack-generation integration test. The paid
delivery path calls the service function directly, not this script.

Example
-------
    python3 tools/generate_territory_opportunity_brief.py \\
        --kind local_authority --name "Isle of Wight" \\
        --locations-source _locations_detail.ndjson \\
        --providers-source _providers_detail.ndjson \\
        --out-dir artifacts/territory-brief-sample
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from api.services.territory_brief import (
    PurchaseContext,
    ScopeError,
    brief_to_csv,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_render import render_brief_pdf


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kind", choices=["local_authority", "region"], default="local_authority")
    p.add_argument("--name", required=True, help="territory name (case-insensitive)")
    p.add_argument("--window-days", type=int, default=90)
    p.add_argument("--shortlist", type=int, default=30)
    p.add_argument("--locations-source", type=Path, default=Path("_locations_detail.ndjson"))
    p.add_argument("--providers-source", type=Path, default=Path("_providers_detail.ndjson"))
    p.add_argument("--order-reference", default="dry-run")
    p.add_argument("--generated-at", default=None, help="ISO timestamp; default fixed epoch for reproducibility")
    p.add_argument("--out-dir", type=Path, default=Path("artifacts/territory-brief-sample"))
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
        terms_version="dry-run",
    )
    try:
        brief = generate_territory_opportunity_brief(
            {
                "kind": args.kind,
                "name": args.name,
                "window_days": args.window_days,
                "shortlist_target": args.shortlist,
            },
            context,
            locations_source=args.locations_source,
            providers_source=args.providers_source,
        )
    except ScopeError as exc:
        print(f"scope error: {exc}")
        return 2

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = brief.scope.name.lower().replace(" ", "-").replace("/", "-")
    pdf_path = out_dir / f"territory-opportunity-brief-{slug}.pdf"
    csv_path = out_dir / f"territory-opportunity-brief-{slug}.csv"
    json_path = out_dir / f"territory-opportunity-brief-{slug}.json"

    pdf_path.write_bytes(render_brief_pdf(brief))
    csv_path.write_text(brief_to_csv(brief), encoding="utf-8")
    json_path.write_text(json.dumps(brief.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"territory:   {brief.scope.name} ({brief.scope.kind})")
    print(f"window:      {brief.window_start} to {brief.window_end}")
    print(f"considered:  {brief.considered_locations}")
    print(f"shortlist:   {len(brief.shortlist)}")
    print(f"pdf:         {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
    print(f"csv:         {csv_path}")
    print(f"json:        {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
