#!/usr/bin/env python3
"""Write every registration ending in a window with its class (read-only).

    python3 -m tools.classify_registration_endings \\
        --export .tmp/cqc-export-20261020-final/_locations_detail.ndjson \\
        --start 2025-10-17 --end 2026-10-16 --out artifacts/.../endings.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from api.services.registration_endings import EndingIndex, classify_ending
from tools.report_sources import iter_export, parse_day


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", type=Path, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    start, end = parse_day(args.start), parse_day(args.end)

    rows = list(iter_export(args.export))
    index = EndingIndex.build(rows)
    counts: Counter[tuple[str, str]] = Counter()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["location_id", "name", "postcode", "care_home", "service_types", "deregistration_date",
                    "ending_class", "kind", "successor_ids", "successors_in_export", "reason", "cqc_url"])
        for row in rows:
            ending = classify_ending(row, index)
            if ending is None:
                continue
            if ending.end_date and not (start <= ending.end_date <= end):
                continue
            if ending.end_date is None and ending.ending_class != "unresolved":
                continue
            services = "|".join(sorted(str(g.get("description") or "") for g in row.get("gacServiceTypes") or []))
            counts[(row.get("careHome") or "", ending.ending_class)] += 1
            w.writerow([ending.location_id, row.get("name"), row.get("postalCode"), row.get("careHome"), services,
                        ending.end_date.isoformat() if ending.end_date else "", ending.ending_class,
                        ending.kind or "", " ".join(ending.successor_ids), " ".join(ending.successors_in_data),
                        ending.reason, f"https://www.cqc.org.uk/location/{ending.location_id}"])
    for (care_home, cls), n in sorted(counts.items()):
        print(f"careHome={care_home or '-'} {cls}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
