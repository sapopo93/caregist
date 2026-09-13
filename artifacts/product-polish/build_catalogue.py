#!/usr/bin/env python3
"""Render the internal, evidence-led CareGist product catalogue.

This is a local decision and delivery view. It does not create checkout,
publish an offer, or represent readiness that the evidence does not support.

Visual system: lifted verbatim from the Google Stitch design of the offer page
(`artifacts/product-polish/customer-offer/index.html`). Tokens, type scale and
component rules are Stitch's; only the components a catalogue needs beyond that
page (card price line, definition list) are additions, built from Stitch's own
tokens and scale.
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
        return '<a class="button" href="../brief-preview/index.html">Open retained £745 delivery preview</a>'
    if slug == "market-movement-report":
        return '<span class="tag neutral">No report exists to deliver today</span>'
    if slug == "radar-founding-buyer-pilot":
        return '<a class="button secondary" href="../radar-pilot-sample/index.html">Open dated format sample</a>'
    return '<span class="tag neutral">No current buyer delivery</span>'

cards = "".join(f'''<article class="card" id="{e(p['slug'])}">
  <div class="num">{e(p['status'].replace('-', ' '))}</div>
  <h3>{e(p['name'])}</h3>
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
:root{{--ink:#1a1c22;--muted:#4b5161;--paper:#fff;--canvas:#faf8f5;--soft:#f3efea;--line:#e2ddd5;--accent:#c27838;--green:#056b52}}
    *{{box-sizing:border-box}} body{{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.5 Inter,Arial,sans-serif;-webkit-font-smoothing:antialiased}}
    .wrap{{max-width:1160px;margin:auto;padding:24px 28px 64px}}.top{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:17px}}.brand{{font-weight:600;letter-spacing:-.02em}}.kicker{{font-size:11px;letter-spacing:.07em;text-transform:uppercase;font-weight:600;color:var(--muted)}}
    h1,h2,h3{{font-family:"Source Serif 4",Georgia,serif;font-weight:600;margin:0;letter-spacing:-.025em}}h1{{font-size:56px;line-height:1.03;max-width:12ch}}h2{{font-size:31px;line-height:1.1}}h3{{font-size:21px;line-height:1.2}}.hero{{display:grid;grid-template-columns:1.15fr .85fr;gap:68px;padding:78px 0 62px}}.intro{{font-size:18px;line-height:1.55;color:var(--muted);max-width:51ch;margin:22px 0}}.price-box{{align-self:end;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:27px}}.price{{font:600 48px/1 "Source Serif 4",Georgia,serif;margin:7px 0}}.vat{{font-size:13px;color:var(--muted);margin:0 0 24px}}.button{{display:block;text-align:center;text-decoration:none;background:var(--ink);color:#fff;padding:12px 14px;border-radius:3px;font-weight:600;font-size:13px}}.button:hover{{background:#363944}}.note{{font-size:12px;line-height:1.45;color:var(--muted);margin:12px 0 0}}.rule{{height:2px;background:var(--ink);border:0;margin:0}}.section{{padding:54px 0}}.section-lead{{color:var(--muted);max-width:65ch;margin:12px 0 26px}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}.card{{background:var(--paper);border:1px solid var(--line);border-radius:7px;padding:21px}}.num{{font:600 12px/1 Inter,Arial,sans-serif;color:var(--accent);letter-spacing:.06em}}.card p{{color:var(--muted);font-size:13px;margin:8px 0 0}}.sample{{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:30px;display:grid;grid-template-columns:1fr auto;gap:30px;align-items:center}}.sample p{{color:var(--muted);max-width:60ch;margin:8px 0 0}}.sample a{{color:var(--ink);font-weight:600;font-size:13px;text-underline-offset:3px}}.limits{{display:grid;grid-template-columns:1fr 1fr;gap:20px;background:#fffdf8;border:1px solid #f1dfb1;border-radius:7px;padding:22px}}.limits p{{font-size:13px;line-height:1.5;margin:7px 0 0;color:#6d5426}}.footer{{border-top:1px solid var(--line);padding-top:18px;color:var(--muted);font-size:12px;max-width:80ch}}.tag{{display:inline-block;border:1px solid #a7d9ca;background:#ecfdf5;color:var(--green);font-size:11px;font-weight:600;padding:3px 7px;border-radius:3px;margin-bottom:12px}}
    .card .num{{display:block;margin-bottom:12px}}.card .price{{font:600 22px/1.2 "Source Serif 4",Georgia,serif;color:var(--ink);margin:9px 0 0}}
    dl{{border-top:1px solid var(--line);padding-top:12px;margin:20px 0 0}}dt{{font-size:11px;letter-spacing:.07em;text-transform:uppercase;font-weight:600;color:var(--muted);margin-top:12px}}dd{{font-size:12.5px;line-height:1.45;margin:3px 0 0}}
    .delivery{{margin-top:18px}}.button.secondary{{background:var(--soft);color:var(--ink)}}.tag.neutral{{border-color:var(--line);background:var(--soft);color:var(--muted)}}
    .limits .kicker{{display:block;color:#6d5426}}.limits strong{{display:block;color:#6d5426;font-size:14px}}
    @media(max-width:760px){{.wrap{{padding:18px 16px 44px}}.top{{font-size:13px}}.hero{{grid-template-columns:1fr;gap:28px;padding:50px 0}}.grid,.limits{{grid-template-columns:1fr}}h1{{font-size:42px}}.sample{{grid-template-columns:1fr;gap:15px}}.price-box{{align-self:auto}}}}
</style></head><body><main class="wrap">
<header class="top"><div class="brand">CareGist</div><div class="kicker">Product catalogue · internal delivery view</div></header>
<section class="hero">
  <div><span class="kicker">CareGist · {len(products)} entries · evidence view</span>
  <h1>What exists, what a buyer receives, and what remains closed</h1>
  <p class="intro">This catalogue uses the current decision record and local evidence. A documented price is not a live price, and a product with no buyer delivery stays closed even when its card looks finished.</p></div>
  <aside class="price-box"><span class="kicker">Only complete local bundle</span>
    <div class="price">£745</div>
    <p class="vat">Territory Opportunity Brief, one-off. £745 is the final price. H-Kay Limited is not VAT registered, so no VAT is added.</p>
    <a class="button" href="../brief-preview/index.html">Open retained delivery preview</a>
    <p class="note">No price here is a live price, and no checkout is wired to any entry.</p></aside>
</section>
<hr class="rule">
<section class="section"><span class="kicker">Today’s buying position</span>
  <h2>What is closed, and why</h2>
  <p class="section-lead">Purchasability is set by delivered evidence, not by a card’s finish. Two of four entries have no acceptable buyer delivery today.</p>
  <div class="limits">
    <div><strong>Not purchasable today</strong><p>The £495 Market Movement Report has no completed edition or compatible event ledger. The £150 Radar pilot has a recorded four-week scope and one dated format sample, but its fresh weekly path and delivery cadence are not verified, so no new payment should be taken.</p></div>
    <div><strong>Not yet cleared to sell</strong><p>VAT treatment is not yet confirmed, terms are unresolved, and no checkout is wired. The £745 prototype carries illustrative shortlist criteria, so it is a delivery prototype rather than a buyer-ready order. Review all paid-product wording before any live sale.</p></div>
  </div>
</section>
<hr class="rule">
<section class="section"><span class="kicker">The catalogue</span>
  <h2>Every entry, with its delivery gate</h2>
  <p class="section-lead">Each entry states its documented price, the route it would be sold through, and the gate that must clear before a buyer can be charged.</p>
  <div class="grid">{cards}</div>
</section>
<footer class="footer">Sources: <code>artifacts/product-polish/catalogue-evidence.json</code>; the 7 September 2026 founder decision; retained launch and Radar artefacts. Generated locally for review. It makes no checkout, delivery or release change.</footer>
</main></body></html>'''

OUT.mkdir(exist_ok=True)
(OUT / "index.html").write_text(doc)
print(f"wrote {OUT / 'index.html'} with {len(products)} products")
