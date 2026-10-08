"""Acceptance test (CG-AT-001): every price a buyer can read matches the one that is charged.

tests/test_price_single_source.py only hunts for the retired GBP 795. Three buyer
pages still hard-code the current price instead of reading TERRITORY_BRIEF_PRICE_GBP,
so a future change to the constant would leave them stale without failing anything.
This guard fails when any hard-coded pound amount on a public page, other than the
two sold products and the free tier, is not the checkout amount.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
AMOUNT = re.compile(r"(?:£|&pound;)\s?(\d[\d,]*)")
ALLOWED = {0, 150, 745}  # free tier, Weekly Digest pilot, Territory Opportunity Brief
PLACEHOLDER_FILES = {"app/provider-dashboard/[slug]/page.tsx"}  # form placeholder text, not a price


def _public_files():
    for sub in ("app", "components", "lib", "public"):
        for path in sorted((FRONTEND / sub).rglob("*")):
            if path.suffix in {".tsx", ".ts", ".html"} and not path.name.endswith(".test.ts"):
                if "node_modules" not in path.parts:
                    yield path


def test_only_the_sold_prices_are_hard_coded_on_public_pages():
    stray = {}
    for path in _public_files():
        rel = path.relative_to(FRONTEND).as_posix()
        if rel in PLACEHOLDER_FILES:
            continue
        amounts = {int(m.replace(",", "")) for m in AMOUNT.findall(path.read_text(encoding="utf-8", errors="ignore"))}
        if amounts - ALLOWED:
            stray[rel] = sorted(amounts - ALLOWED)
    assert not stray, f"unexpected pound amounts on public pages: {stray}"


def test_brief_price_on_buyer_pages_equals_the_checkout_amount_in_the_manifest():
    # The three buyer pages now render TERRITORY_BRIEF_PRICE_GBP (M1, wave 3), so the
    # check moves to the constant they read; any literal left behind must still match.
    manifest = json.loads((REPO_ROOT / "deploy" / "stripe-price-manifest.json").read_text(encoding="utf-8"))
    pence = manifest["products"]["territory-opportunity-brief"]["unit_amount"]
    constant = (FRONTEND / "lib" / "territory-scope.ts").read_text(encoding="utf-8")
    match = re.search(r"export const TERRITORY_BRIEF_PRICE_GBP\s*=\s*(\d+)\s*;", constant)
    assert match and int(match.group(1)) == pence // 100, "TERRITORY_BRIEF_PRICE_GBP differs from the checkout price"
    for rel in ("app/page.tsx", "app/pricing/page.tsx", "app/pricing/territory/page.tsx"):
        text = (FRONTEND / rel).read_text(encoding="utf-8")
        assert re.search(r"(?:£|&pound;)\{TERRITORY_BRIEF_PRICE_GBP\}", text), f"{rel} does not render the Brief price"
        shown = {int(m.replace(",", "")) for m in AMOUNT.findall(text)} & {745}
        assert shown <= {pence // 100}, f"{rel} does not show the checkout price {pence // 100}"
