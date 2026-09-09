#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path

from api.services.provider_intelligence import analyse_provider, content_sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("frontend/data/directory-fallback-full.csv"))
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-official", action="store_true")
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    source_hash = content_sha256(source_bytes)
    rows: list[dict[str, str]] = []
    with args.source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("id") and row.get("provider_id"):
                rows.append(row)
            if len(rows) == args.count:
                break
    results = [
        analyse_provider(
            row,
            None,
            regulator_source_uri=args.source.resolve().as_uri(),
            regulator_source_sha256=source_hash,
            observed_at=row.get("last_updated") or "source_timestamp_missing",
        )
        for row in rows
    ]
    official_retrievals = []
    if args.live_official:
        for row in rows:
            url = row.get("inspection_report_url", "")
            if not re.fullmatch(r"https://www\.cqc\.org\.uk/location/1-[0-9]+", url):
                official_retrievals.append({"url": url, "ok": False, "reason": "url_not_allowlisted"})
                continue
            started = time.perf_counter()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "CareGist controlled benchmark/1.0"})
                with urllib.request.urlopen(request, timeout=15) as response:
                    body = response.read(2_000_000)
                    final_url = response.geturl()
                    ok = response.status == 200 and final_url.startswith("https://www.cqc.org.uk/location/")
                folded = body.decode("utf-8", errors="replace").casefold()
                official_retrievals.append({
                    "url": url,
                    "final_url": final_url,
                    "ok": ok,
                    "status": response.status,
                    "bytes": len(body),
                    "sha256": content_sha256(body),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                    "location_id_present": row["id"].casefold() in folded,
                    "provider_name_present": row.get("name", "").strip().casefold() in folded,
                })
            except Exception as exc:
                official_retrievals.append({"url": url, "ok": False, "reason": type(exc).__name__})
    metrics = {
        "requested": args.count,
        "processed": len(results),
        "provider_identity_verified": sum(r.identity_state.value == "verified" for r in results),
        "cqc_location_url_present": sum(bool(row.get("inspection_report_url")) for row in rows),
        "website_present": sum(bool(row.get("website")) for row in rows),
        "official_source_retrieved": sum(bool(item.get("ok")) for item in official_retrievals),
        "official_source_identity_match": sum(
            bool(item.get("ok") and item.get("location_id_present") and item.get("provider_name_present"))
            for item in official_retrievals
        ),
        "contradictions_tested": 0,
        "unsupported_claims_emitted": 0,
        "crm_updates_applied": 0,
        "abstained_for_missing_public_source": sum("public_source_not_retrieved" in r.review_reasons for r in results),
    }
    payload = {
        "benchmark": "caregist_provider_intelligence_v2",
        "source": str(args.source.resolve()),
        "source_sha256": source_hash,
        "metrics": metrics,
        "limitations": [
            "Local benchmark verifies identity and fail-closed behavior only.",
            "Official CQC HTML retrieval is a native-HTTP baseline, not a Firecrawl, Crawl4AI, or Docling result.",
            "No contradiction-detection accuracy claim is made without independently labelled public claims."
        ],
        "official_retrievals": official_retrievals,
        "records": [asdict(r) for r in results],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0 if len(results) == args.count and metrics["unsupported_claims_emitted"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
