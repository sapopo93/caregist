#!/usr/bin/env python3
"""Run a safe local buyer-journey simulation for the £795 Brief.

It accepts only a scope that the retained evidence pack can support. An
incompatible request is a successful guardrail test, never a customer result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
PACK = ROOT.parent / "launch-samples/bsol-domiciliary-fresh-2026-09-08"
PREVIEW = ROOT / "brief-preview"

SUPPORTED = {
    "buyer_type": "homecare_staffing_supplier",
    "authorities": ["Birmingham", "Solihull"],
    "service": "Domiciliary care",
    "selection_routes": ["multi_location_provider", "recent_registration"],
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_scope(scope: dict) -> list[str]:
    errors = []
    for key in ("buyer_type", "authorities", "service", "selection_routes"):
        if scope.get(key) != SUPPORTED[key]:
            errors.append(f"{key} is outside the retained pack's supported scope")
    forbidden = {"vacancy", "buying_intent", "budget", "breach_history", "director_links", "ownership", "financial_valuation", "live_monitoring"}
    requested = set(scope.get("requested_enrichment", []))
    if requested & forbidden:
        errors.append("requested enrichment is not in the £795 Brief evidence pack: " + ", ".join(sorted(requested & forbidden)))
    return errors

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    buyer = json.loads(args.input.read_text())
    scope = buyer["scope"]
    scope_errors = check_scope(scope)
    data = json.loads((PACK / "pack-data.json").read_text())
    manifest = json.loads((PREVIEW / "delivery-manifest.json").read_text())
    assets = []
    for item in manifest["assets"]:
        path = PREVIEW / item["file"]
        assets.append({"file": item["file"], "present": path.exists(), "hash_matches": path.exists() and sha256(path) == item["sha256"]})
    usable_rows = [r for r in data["shortlist"] if r["published_fact"] and r["reason_for_review"] and r["qualification_question"] and r["uncertainty"]]
    checks = {
        "buyer_intake": {"result": "PASS" if buyer.get("simulation") else "FAIL", "detail": "Synthetic buyer fixture is labelled simulation."},
        "scope_gate": {"result": "PASS" if not scope_errors else "REJECTED", "detail": scope_errors or "Scope matches the retained Birmingham/Solihull homecare staffing pack."},
        "shortlist": {"result": "PASS" if len(usable_rows) == 25 else "FAIL", "detail": f"{len(usable_rows)} of 25 records contain the four required fields."},
        "delivery_assets": {"result": "PASS" if all(a["present"] and a["hash_matches"] for a in assets) else "FAIL", "detail": assets},
        "executive_pdf": {"result": "PASS" if len(PdfReader(PREVIEW / "caregist-birmingham-solihull-executive-brief.pdf").pages) == 4 else "FAIL", "detail": "Four-page retained executive brief."},
        "payment_acceptance": {"result": "BLOCKED", "detail": "No live £795 product, price or Payment Link exists in the local Stripe manifest. This simulation never creates a charge."},
        "terms": {"result": "BLOCKED", "detail": "Current Terms do not state the Territory Opportunity Brief scope or one-off cancellation/refund terms."},
    }
    fulfilment_ready = all(checks[name]["result"] == "PASS" for name in ("buyer_intake", "scope_gate", "shortlist", "delivery_assets", "executive_pdf"))
    order_ready = fulfilment_ready and checks["payment_acceptance"]["result"] == "PASS" and checks["terms"]["result"] == "PASS"
    report = {
        "simulation": True,
        "buyer_label": buyer.get("buyer_label"),
        "source_pack": str(PACK),
        "fulfilled_locally": fulfilment_ready,
        "order_ready": order_ready,
        "checks": checks,
        "rule": "A compatible scope may proceed to a human delivery-date confirmation. It must not become an accepted paid order until payment and Terms pass.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
