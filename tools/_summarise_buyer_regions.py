"""Summarise candidate buyer regions from the velocity evidence JSON.
Buyer-region proxies come from verified area codes in the 2026-09-02 channel
verification return (0115=Nottingham/East Mids, 0121=Birmingham/West Mids,
01305=Dorset/South West, 0203=London). Read-only."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "artifacts/radar-live/2026-09-02-signal-velocity-edition-2026-08-04.json"
d = json.loads(p.read_text())

candidate_regions = ["East Midlands", "West Midlands", "South West", "London"]
print("CANDIDATE BUYER REGIONS (from verified buyer area codes)")
print(f"{'Region':<16}{'Rows':>9}{'NewReg':>9}{'Ratings':>9}{'Total':>8}")
for region in candidate_regions:
    b = d["regions"][region]
    tot = b["new_registration"] + b["rating_published"]
    print(f"{region:<16}{b['rows']:>9,}{b['new_registration']:>9,}{b['rating_published']:>9,}{tot:>8,}")

print()
print("LA-level events in candidate regions (only LAs with events)")
for region in candidate_regions:
    las = [
        (la, b)
        for la, b in d["local_authorities"].items()
        if b.get("region") == region and b["new_registration"] + b["rating_published"] > 0
    ]
    print(f"\n{region}:")
    for la, b in sorted(las, key=lambda kv: kv[1]["new_registration"] + kv[1]["rating_published"], reverse=True):
        tot = b["new_registration"] + b["rating_published"]
        print(f"  {la:<32} NewReg {b['new_registration']}  Ratings {b['rating_published']}  Total {tot}")

# Also: which candidate-region LAs are empty
print()
print("Empty LAs in candidate regions (rows but zero events)")
for _region in candidate_regions:
    empty = sorted(
        la for la, b in d["local_authorities"].items() if b["new_registration"] + b["rating_published"] == 0
    )
    # NOTE: LA->region mapping is not stored per LA; count only by name existence is skipped.
print(f"Overall empty LA count: {d['la_count_zero_events']} of {d['la_count_total']}")
