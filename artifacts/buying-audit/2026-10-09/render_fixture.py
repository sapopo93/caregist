"""Reproduce an illustrative pack; these fixtures are not a customer's order."""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from api.services.territory_brief import PurchaseContext, brief_to_csv, generate_territory_opportunity_brief
from api.services.territory_brief_render import render_brief_pdf

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FIX = ROOT / "tests/fixtures/territory_brief"
manifest = {"synthetic": True, "notice": "Historical test fixtures, not a sale or current source assurance", "packs": []}
for territory, target in [("Southampton", 30), ("Isle of Wight", 50)]:
    brief = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": territory, "window_days": 365, "shortlist_target": target},
        PurchaseContext(order_reference="SYNTHETIC-BUYING-AUDIT", generated_at=datetime(2026, 10, 9, tzinfo=timezone.utc), terms_version="synthetic-audit"),
        locations_source=FIX / "locations_detail.jsonl", providers_source=FIX / "providers_detail.jsonl",
    )
    files = []
    for kind, data in [("pdf", render_brief_pdf(brief)), ("csv", brief_to_csv(brief).encode("utf-8"))]:
        path = OUT / (territory.lower().replace(" ", "-") + "." + kind)
        path.write_bytes(data)
        files.append({"file": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    rows = list(csv.DictReader(io.StringIO(brief_to_csv(brief))))
    manifest["packs"].append({"territory": territory, "target": target, "shortlisted": len(brief.shortlist), "csvRows": len(rows), "columns": list(rows[0]) if rows else next(csv.reader(io.StringIO(brief_to_csv(brief)))), "shortfall": brief.executive_summary.get("shortfall_notice"), "files": files})
(OUT / "pack-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
