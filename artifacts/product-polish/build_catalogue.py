#!/usr/bin/env python3
"""Render the internal, evidence-led CareGist product catalogue.

This is a local decision and delivery view. It does not create checkout,
publish an offer, or represent readiness that the evidence does not support.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "catalogue"
products = json.loads((ROOT / "catalogue-evidence.json").read_text())["products"]
e = html.escape

EXTRA = {
    "territory-opportunity-brief": "The retained Birmingham and Solihull prototype includes a 353-location CSV, a 25-organisation shortlist, a three-sheet workbook and a four-page executive brief. Its shortlist criteria are illustrative, so it is a delivery prototype, not a buyer-ready order.",
    "market-movement-report": "No completed edition or compatible event ledger is retained. A buyer must not be charged today because there is no checked report to give them. The proposed 20–35 page scope is a specification, not a present deliverable.",
    "radar-founding-buyer-pilot": "The recorded pilot promise is four weekly email/PDF digests for an agreed region, with no software. A dated Gloucestershire format sample exists. A fresh weekly source path and four-week delivery are not verified, so no new payment should be taken.",
    "free-directory": "A free directory is not a paid intelligence product. Its quality requirement is accurate search and distinct status rendering.",
}

def delivery_now(p):
    slug = p["slug"]
    if slug == "territory-opportunity-brief":
        return '<a class="button" href="../brief-preview/index.html">Open retained £795 delivery preview</a>'
    if slug == "market-movement-report":
        return '<span class="blocked">No report exists to deliver today</span>'
    if slug == "radar-founding-buyer-pilot":
        return '<a class="button secondary" href="../radar-pilot-sample/index.html">Open dated format sample</a>'
    return '<span class="blocked">No current buyer delivery</span>'

cards = "".join(f'''<article class="card" id="{e(p['slug'])}">
  <div class="eyebrow">{e(p['status'].replace('-', ' '))}</div>
  <h2>{e(p['name'])}</h2>
  <p class="price">{e(p['documented_price'])}</p>
  <p>{e(EXTRA.get(p['slug'], p['notes']))}</p>
  <dl><dt>Current route</dt><dd>{e(p['sale_channel'])}</dd>
      <dt>Delivery gate</dt><dd>{e(p['capability_gate'])}</dd></dl>
  <div class="delivery">{delivery_now(p)}</div>
</article>''' for p in products)

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CareGist product catalogue, evidence view</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#faf8f5;--paper:#fff;--soft:#f3efea;--ink:#1a1c22;--muted:#4b5161;--line:#e2ddd5;--accent:#c27838;--warning:#92400e;}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Inter,Arial,sans-serif}} .wrap{{max-width:1180px;margin:auto;padding:40px 28px}}
h1,h2{{font-family:"Source Serif 4",Georgia,serif;font-weight:600;margin:0}} h1{{font-size:42px;line-height:1.1;letter-spacing:-.02em;max-width:19ch}} h2{{font-size:24px;line-height:1.15}}
.eyebrow{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}} .intro{{max-width:70ch;color:var(--muted);margin:14px 0 28px}}
.notice{{border-left:3px solid var(--accent);background:#fffbeb;border:1px solid #fde68a;border-left:3px solid var(--accent);padding:14px 16px;margin:20px 0 36px;color:var(--warning);max-width:900px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}} .card{{background:var(--paper);border:1px solid var(--line);border-radius:7px;padding:20px;display:flex;flex-direction:column;min-height:325px}} .price{{font:600 18px/1.2 Inter,sans-serif;margin:10px 0;color:var(--ink)}} .card>p:not(.price){{color:var(--muted);font-size:13px;margin:4px 0 16px}}
dl{{border-top:1px solid var(--line);padding-top:12px;margin:0}} dt{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;color:var(--muted);margin-top:10px}} dd{{font-size:12px;line-height:1.45;margin:2px 0;color:var(--ink)}} .delivery{{margin-top:auto;padding-top:16px}} .button,.blocked{{display:inline-block;border-radius:3px;padding:8px 11px;font-size:12px;font-weight:600}} .button{{background:var(--ink);color:white;text-decoration:none}} .button.secondary{{background:var(--soft);color:var(--ink)}} .blocked{{background:var(--soft);color:var(--muted)}} footer{{border-top:1px solid var(--line);color:var(--muted);font-size:12px;margin-top:40px;padding-top:16px;max-width:80ch}} @media(max-width:600px){{.wrap{{padding:28px 16px}}h1{{font-size:34px}}.grid{{grid-template-columns:1fr}}}}
</style></head><body><main class="wrap">
<div class="eyebrow">CareGist · internal product and delivery view · {len(products)} entries</div>
<h1>What exists, what a buyer receives, and what remains closed</h1>
<p class="intro">This catalogue uses the current decision record and local evidence. A documented price is not a live price, and a product with no buyer delivery stays closed even when its card looks finished.</p>
<div class="notice"><strong>Today’s buying position.</strong> CareGist is not currently VAT-registered. The £795 prototype is the only complete local delivery bundle. The £495 report has no completed edition. The £150 pilot has a recorded four-week scope and one dated format sample, but its fresh weekly path and delivery cadence are not verified. Terms and checkout remain unresolved. Review all paid-product wording before VAT registration takes effect.</div>
<section class="grid">{cards}</section>
<footer>Sources: <code>artifacts/product-polish/catalogue-evidence.json</code>; the 7 September 2026 founder decision; retained launch and Radar artefacts. Generated locally for review. It makes no checkout, delivery or release change.</footer>
</main></body></html>'''

OUT.mkdir(exist_ok=True)
(OUT / "index.html").write_text(doc)
print(f"wrote {OUT / 'index.html'} with {len(products)} products")
