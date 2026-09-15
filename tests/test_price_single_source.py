"""One price, one source: public price surfaces must not drift again.

Founder finding, 2026-09-15. The £795 correction was applied to Stripe, the
Stripe manifest, /pricing, the checkout gates, the tests and the docs — and
declared solved — while `app/territory-opportunity-brief/page.tsx`,
`app/terms/page.tsx` and a published sample page still hardcoded £795 in
tracked source. Production faithfully served the wrong price, because nothing
compared the live pages with the canonical constant.

These guards fail the build if a hardcoded brief price reappears anywhere a
buyer can read it, and keep the frontend constant, the Stripe manifest and the
published terms on the same number.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
CANONICAL_GBP = 745
STALE_PATTERNS = (re.compile(r"£\s?795\b"), re.compile(r"\b79500\b"))
PUBLIC_DIRS = ("app", "components", "lib", "public")
SKIP = {"node_modules", ".next", "out", "dist", "coverage", ".turbo"}
SUFFIXES = {".tsx", ".ts", ".jsx", ".js", ".mjs", ".html", ".json", ".css", ".md"}


def _public_sources():
    for sub in PUBLIC_DIRS:
        root = FRONTEND / sub
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            if any(part in SKIP for part in path.parts):
                continue
            yield path


def test_no_stale_brief_price_on_a_public_surface():
    offenders = []
    for path in _public_sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in STALE_PATTERNS):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"hardcoded £795 left on a public surface: {offenders}"


def test_canonical_constant_is_745_and_the_offer_pages_use_it():
    constant = (FRONTEND / "lib" / "territory-scope.ts").read_text(encoding="utf-8")
    assert re.search(rf"TERRITORY_BRIEF_PRICE_GBP\s*=\s*{CANONICAL_GBP}\b", constant), (
        f"lib/territory-scope.ts must define TERRITORY_BRIEF_PRICE_GBP = {CANONICAL_GBP}"
    )
    for rel in ("app/territory-opportunity-brief/page.tsx", "app/terms/page.tsx"):
        text = (FRONTEND / rel).read_text(encoding="utf-8")
        assert "TERRITORY_BRIEF_PRICE_GBP" in text, f"{rel}: must render the canonical constant"
        assert "£{TERRITORY_BRIEF_PRICE_GBP}" in text, f"{rel}: price must be interpolated, not literal"


def _price_records(node, path=""):
    """Yield (path, unit_amount, has_reason) for every record carrying a price."""
    if isinstance(node, dict):
        if "unit_amount" in node:
            yield path, node["unit_amount"], bool(node.get("reason"))
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from _price_records(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _price_records(item, f"{path}[{index}]")


def test_stripe_manifest_keeps_only_the_canonical_price_live():
    manifest = json.loads(
        (REPO_ROOT / "deploy" / "stripe-price-manifest.json").read_text(encoding="utf-8")
    )
    brief = manifest["products"]["territory-opportunity-brief"]
    assert brief["unit_amount"] == CANONICAL_GBP * 100
    assert "live" in brief["status"], f"the brief is not the live selling price: {brief['status']}"

    records = list(_price_records(manifest))
    unexplained = [path for path, amount, has_reason in records if amount == 79500 and not has_reason]
    assert not unexplained, f"£795 recorded with no retirement reason: {unexplained}"
    assert [p for p, amount, has_reason in records if amount == 79500 and has_reason], (
        "the erroneous £795 prices must stay recorded for audit"
    )
