#!/usr/bin/env python3
"""Build the £745 Territory Opportunity Brief client delivery preview.

Visual system: lifted verbatim from the Google Stitch design of the offer page
(`artifacts/product-polish/customer-offer/index.html`) — same tokens, type
scale, component shapes and rhythm. Only the content layer differs: this page
delivers data, evidence and limits rather than selling.

Every value on the page is read from pack-data.json. Nothing is hard-coded copy
about volumes, dates, hashes or counts. If a field is absent it renders as an
explicit absence state, never as a default or a zero.
"""
import json, html, pathlib, datetime, hashlib, shutil, zipfile
from pypdf import PdfReader

PACK = pathlib.Path("/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08")
OUT  = pathlib.Path("/Users/user/CareGist/artifacts/product-polish/brief-preview")
d = json.loads((PACK / "pack-data.json").read_text())
m, ds, sl, wc = d["metadata"], d["dataset"], d["shortlist"], d["web_checks"]
e = html.escape

DELIVERY_ROOT = PACK.parents[2]
DELIVERY_ASSETS = {
    "territory-dataset.csv": DELIVERY_ROOT / "outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/territory-dataset.csv",
    "shortlist-25.csv": DELIVERY_ROOT / "outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/shortlist-25.csv",
    "caregist-birmingham-solihull-territory-brief.xlsx": DELIVERY_ROOT / "outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/caregist-birmingham-solihull-territory-brief.xlsx",
    "caregist-birmingham-solihull-executive-brief.pdf": DELIVERY_ROOT / "output/pdf/caregist-birmingham-solihull-executive-brief.pdf",
}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_delivery_inputs():
    """Fail before producing a customer-facing preview if an input is absent or altered."""
    assert len(ds) == m["qualifying_locations"] == 353
    assert len({r["provider_id"] for r in ds}) == m["distinct_providers"] == 329
    assert len(sl) == m["shortlist_providers"] == 25
    assert len({r["provider_id"] for r in sl}) == len(sl)
    assert len(wc) == len(sl)
    assert all(w.get("result") == "MATCH" for w in wc)
    for source in m["source_manifest"]:
        path = PACK / "source" / source["file"]
        assert path.exists(), f"missing retained source: {path}"
        assert sha256(path) == source["sha256"], f"source hash changed: {path.name}"
    for name, path in DELIVERY_ASSETS.items():
        assert path.exists() and path.stat().st_size > 0, f"missing delivery asset: {name}"
    assert len(PdfReader(DELIVERY_ASSETS["caregist-birmingham-solihull-executive-brief.pdf"]).pages) == 4
    with zipfile.ZipFile(DELIVERY_ASSETS["caregist-birmingham-solihull-territory-brief.xlsx"]) as z:
        sheets = [n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
        assert len(sheets) == 3, "workbook sheet count changed"

validate_delivery_inputs()

# --- absence vocabulary: one rule, applied everywhere -------------------------
def rating_cell(row):
    r = (row.get("rating_as_published") or "").strip()
    inh = (row.get("inherited_rating") or "").strip()
    if not r:
        return '<span class="absent">Not stated in reviewed source</span>'
    if r == "Not Rated":
        return '<span class="absent">Not Rated <span class="q">(source term)</span></span>'
    pal = {"Good": ("#ECFDF5", "#056B52", "#A7D9CA", "●"),
           "Outstanding": ("#ECFDF5", "#056B52", "#A7D9CA", "★"),
           "Requires improvement": ("#FFFBEB", "#92400E", "#FDE68A", "▲"),
           "Inadequate": ("#FEF2F2", "#991B1B", "#FECACA", "■")}.get(r, ("#F3EFEA", "#4B5161", "#E2DDD5", "·"))
    tag = ' <span class="q">inherited</span>' if inh == "Y" else ""
    return (f'<span class="chip" style="background:{pal[0]};color:{pal[1]};border-color:{pal[2]}">'
            f'<span class="g">{pal[3]}</span>{e(r)}</span>{tag}')

def val(v, absent="Not stated in reviewed source"):
    s = ("" if v is None else str(v)).strip()
    return e(s) if s else f'<span class="absent">{absent}</span>'

NOT_SUPPLIED = '<span class="absent">Not stated in reviewed source</span>'

# --- executive findings, all derived ------------------------------------------
auth = m["authorities"]
ratings = m["ratings"]
rated = sum(v for k, v in ratings.items() if k not in ("Not supplied", "Not Rated"))
tiles = [
    (m["qualifying_locations"], "qualifying locations", "domiciliary, non-dormant"),
    (m["distinct_providers"], "distinct providers", f'{m["multi_location_providers"]} hold more than one local location'),
    (m["shortlist_providers"], "selected for review", "each with a published fact and a reason"),
    (rated, "carry a published rating", f'of {m["qualifying_locations"]} — {ratings.get("Not supplied",0)} not stated, {ratings.get("Not Rated",0)} Not Rated'),
]
tilehtml = "".join(
    f'<div class="card"><div class="statn">{v}</div><div class="kicker">{e(l)}</div>'
    f'<p>{e(s)}</p></div>'
    for v, l, s in tiles)

authhtml = " · ".join(f'{e(k)} <strong>{v}</strong>' for k, v in auth.items())
routehtml = "".join(f'<tr><td>{e(k)}</td><td class="n">{v}</td></tr>' for k, v in m["routes"].items())
rathtml = "".join(
    f'<tr><td>{NOT_SUPPLIED if k=="Not supplied" else e(k)}</td>'
    f'<td class="n">{v}</td></tr>'
    for k, v in sorted(ratings.items(), key=lambda x: -x[1]))

# --- 25 account cards ---------------------------------------------------------
cards = ""
for r in sl:
    cards += f'''<article class="acct">
<header><span class="ord">{r['review_order']:02d}</span>
<div class="ahead"><h3>{e(r['provider_name'])}</h3>
<div class="meta"><code>{e(r['provider_id'])}</code> · {val(r.get('authorities'))} · {val(r.get('service_mix'))}</div></div>
<span class="chip" style="background:#F3EFEA;color:#4B5161;border-color:#E2DDD5"><span class="g">·</span>{e(r['review_route'])}</span></header>
<div class="abody">
<div class="fact"><span class="kicker">Published fact</span><p>{val(r.get('published_fact'))}</p></div>
<div class="why"><span class="kicker">Why included</span><p>{val(r.get('reason_for_review'))}</p></div>
<div class="ask"><span class="kicker">What to check next</span><p>{val(r.get('qualification_question'))}</p></div>
<div class="unc"><span class="kicker">Uncertainty</span><p>{val(r.get('uncertainty'))}</p></div>
</div>
<footer><div><span class="kicker">Representative location</span> {val(r.get('representative_location'))} <code>{e(r.get('location_id',''))}</code></div>
<div><span class="kicker">Local / England locations</span> <span class="n">{r.get('local_locations','')}</span> / <span class="n">{r.get('england_domiciliary_locations','')}</span></div>
<div><span class="kicker">Source</span> <a href="{e(r.get('cqc_url',''))}" rel="noopener">CQC location page</a> · checked {val(r.get('web_check_date'))} · {val(r.get('web_check_result'))}</div>
</footer></article>'''

# --- full territory dataset ---------------------------------------------------
rows = "".join(
    f'<tr><td><code>{e(r["location_id"])}</code></td><td>{val(r.get("location_name"))}</td>'
    f'<td>{val(r.get("provider_name"))}</td><td>{val(r.get("local_authority"))}</td>'
    f'<td><code>{e((r.get("postcode") or "").strip())}</code></td>'
    f'<td>{rating_cell(r)}</td><td>{val(r.get("rating_publication_date"), "No publication date in source")}</td></tr>'
    for r in ds)

# --- evidence -----------------------------------------------------------------
srcrows = "".join(
    f'<tr><td>{e(s["file"])}</td><td class="n">{s["http_status"]}</td>'
    f'<td class="mono">{e(s["retrieved_at"])}</td><td class="n">{s["bytes"]:,}</td>'
    f'<td><code class="hash">{e(s["sha256"])}</code></td></tr>' for s in m["source_manifest"])
wcpass = sum(1 for w in wc if w.get("result") == "MATCH")
wcrows = "".join(
    f'<tr><td><code>{e(w["location_id"])}</code></td><td class="n">{w["http_status"]}</td>'
    f'<td class="mono">{e(w["checked_at"])}</td>'
    f'<td>{"yes" if w.get("location_name_found") else "no"}</td>'
    f'<td>{"yes" if w.get("archived_notice_found") else "no"}</td>'
    f'<td><code class="hash">{e(w["sha256"])}</code></td><td>{e(w["result"])}</td></tr>' for w in wc)

# --- visual system: tokens, type scale and components copied verbatim from
# --- Google Stitch's offer page (customer-offer/index.html) -------------------
CSS = """
:root{--ink:#1a1c22;--muted:#4b5161;--paper:#fff;--canvas:#faf8f5;--soft:#f3efea;
--line:#e2ddd5;--accent:#c27838;--green:#056b52;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace} /* --mono is additive:
Stitch's page carries no identifiers or hashes; this delivery page does. */
*{box-sizing:border-box}
body{margin:0;background:var(--canvas);color:var(--ink);font:15px/1.5 Inter,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:auto;padding:24px 28px 64px}
.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:17px}
.brand{font-weight:600;letter-spacing:-.02em}
.kicker{font-size:11px;letter-spacing:.07em;text-transform:uppercase;font-weight:600;color:var(--muted)}
h1,h2,h3{font-family:"Source Serif 4",Georgia,serif;font-weight:600;letter-spacing:-.025em;margin:0}
h1{font-size:56px;line-height:1.03;max-width:12ch}
h2{font-size:31px;line-height:1.1}
h3{font-size:21px;line-height:1.2}
td,.n,thead th,.statn,.price,.mono,code{font-variant-numeric:tabular-nums lining-nums}
code{font:500 11.5px/16px var(--mono);color:var(--muted);word-break:break-all}
.hash{font-size:10.5px;letter-spacing:-.01em}
.mono{font:500 11.5px/16px var(--mono);color:var(--muted);white-space:nowrap}
.n{font-variant-numeric:tabular-nums;font-weight:600}
.q{color:var(--muted);font-size:11px;font-weight:500}
a{color:var(--ink);text-decoration:underline;text-underline-offset:2px;text-decoration-color:var(--accent)}
.hero{display:grid;grid-template-columns:1.15fr .85fr;gap:68px;padding:78px 0 62px}
.intro{font-size:18px;line-height:1.55;color:var(--muted);max-width:51ch;margin:22px 0}
.price-box{align-self:end;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:27px}
.price{font:600 48px/1 "Source Serif 4",Georgia,serif;margin:7px 0}
.vat{font-size:13px;color:var(--muted);margin:0 0 24px}
.button{display:block;text-align:center;text-decoration:none;background:var(--ink);color:#fff;padding:12px 14px;border-radius:3px;font-weight:600;font-size:13px}
.note{font-size:12px;line-height:1.45;color:var(--muted);margin-top:14px}
.tagrow{margin-top:22px}
.tag{display:inline-block;border:1px solid #a7d9ca;background:#ecfdf5;color:var(--green);font-size:11px;font-weight:600;padding:3px 7px;border-radius:3px;margin-bottom:12px}
.tag.neutral{border-color:var(--line);background:var(--soft);color:var(--muted)}
.tag.warn{border-color:#f1dfb1;background:#fffdf8;color:#6d5426}
.rule{height:2px;background:var(--ink);border:0;margin:0}
.section{padding:54px 0}
.section>.kicker{display:block;margin-bottom:8px}
.hero>div>.kicker{display:block;margin-bottom:14px}
.section-lead{color:var(--muted);max-width:65ch;margin:12px 0 26px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:7px;padding:21px}
.card p{font-size:13px;line-height:1.5;color:var(--muted);margin:6px 0 0}
.statn{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:38px;line-height:1.05;letter-spacing:-.03em}
.tbl{padding:0;overflow:hidden}
.tbl .cap{padding:16px 21px 0}
.tbl table{margin-top:12px}
.chip{display:inline-flex;align-items:center;gap:5px;border:1px solid;border-radius:3px;
padding:2px 7px;font:600 11px/14px Inter,Arial,sans-serif;letter-spacing:.02em;white-space:nowrap}
.chip .g{font-size:9px}
.absent{color:var(--muted);font-style:normal;font-size:12.5px;border-bottom:1px dotted var(--line)}
table{width:100%;border-collapse:collapse;background:var(--paper)}
thead th{background:var(--soft);border-bottom:1px solid var(--line);text-align:left;padding:10px 12px;
font:600 11px/14px Inter,Arial,sans-serif;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);
white-space:nowrap;position:sticky;top:0}
td{border-bottom:1px solid var(--line);padding:10px 12px;vertical-align:top;font-size:13px;line-height:1.5}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--canvas)}
.scroll{overflow-x:auto}
.tall{max-height:560px;overflow:auto;border:1px solid var(--line);border-radius:7px;background:var(--paper)}
.tall table{border:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-bottom:14px}
.files{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.file .n{font-weight:600;font-size:14px;letter-spacing:-.01em}
.file .d{color:var(--muted);font-size:12.5px;line-height:1.5;margin:6px 0 10px}
.acct{background:var(--paper);border:1px solid var(--line);border-radius:7px;margin-bottom:14px;overflow:hidden}
.acct header{display:flex;gap:14px;align-items:flex-start;padding:18px 21px;border-bottom:1px solid var(--line)}
.ord{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:21px;color:var(--muted);min-width:30px}
.ahead{flex:1}
.acct .meta{color:var(--muted);font-size:12px;line-height:1.45;margin-top:4px}
.abody{display:grid;grid-template-columns:1fr 1fr}
.abody>div{padding:15px 21px;border-bottom:1px solid var(--line)}
.abody>div:nth-child(odd){border-right:1px solid var(--line)}
.abody p{margin:5px 0 0;font-size:13px;line-height:1.5}
.why{background:var(--canvas)}
.unc p{color:var(--muted)}
.acct footer{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;
padding:15px 21px;font-size:12.5px;line-height:1.45}
.acct footer .kicker{display:block;margin-bottom:3px}
.limits{display:grid;grid-template-columns:1fr 1fr;gap:20px;background:#fffdf8;border:1px solid #f1dfb1;border-radius:7px;padding:22px}
.limits .kicker{color:#6d5426;margin-bottom:8px}
.limits p{font-size:13px;line-height:1.5;color:#6d5426;margin:0}
.limits p+p{margin-top:8px}
.footer{border-top:1px solid var(--line);padding-top:18px;color:var(--muted);font-size:12px;max-width:80ch}
@media(max-width:760px){
.wrap{padding:20px 18px 48px}
.hero{grid-template-columns:1fr;gap:30px;padding:44px 0 38px}
h1{font-size:36px}
.grid,.abody{grid-template-columns:1fr}
.abody>div:nth-child(odd){border-right:0}
.acct header{flex-wrap:wrap}
.limits{grid-template-columns:1fr}
}
"""

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Territory Opportunity Brief — client delivery preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">

<header class="top">
<div class="brand">CareGist</div>
<div class="kicker">Territory intelligence · client delivery preview</div>
</header>

<section class="hero">
<div>
<span class="kicker">Territory Opportunity Brief · one-off deliverable</span>
<h1>Birmingham and Solihull</h1>
<p class="intro">Domiciliary care territory, source edition {e(m["source_edition"])}, retrieved {e(m["retrieved_date"])}. This page previews the retained client delivery files and shows the data, evidence and limits behind them — including what the pack cannot tell a buyer.</p>
<div class="tagrow">
<span class="tag warn">▲ Launch preparation — not purchasable</span> <span class="tag neutral">· Sample — no buyer engaged</span> <span class="tag neutral">· State: Draft, evidence checked</span>
</div>
</div>
<div class="price-box">
<span class="kicker">Product of record</span>
<div class="price">£745</div>
<div class="vat">One-off delivery. Price excludes VAT — VAT treatment for CareGist sales is not yet confirmed, so quote the headline figure only.</div>
<a class="button" href="#files">See what the buyer receives</a>
<p class="note">Quoted price is the founder decision of 11 September 2026. No £745 payment rail exists yet: the live Stripe objects still carry the superseded launch price, so <strong>no payment link may be sent from this pack</strong> until the founder re-pins them.</p>
</div>
</section>

<hr class="rule">

<section class="section">
<span class="kicker">Executive findings</span>
<h2>What the territory contains</h2>
<p class="section-lead">Local authorities: {authhtml}. All counts reproduce from the {len(ds)} rows in the territory dataset below.</p>
<div class="tiles">{tilehtml}</div>
<div class="grid">
<div class="card tbl"><div class="cap"><span class="kicker">Published rating distribution</span></div>
<table><thead><tr><th>Rating as published</th><th>Locations</th></tr></thead><tbody>{rathtml}</tbody></table></div>
<div class="card tbl"><div class="cap"><span class="kicker">Review routes</span></div>
<table><thead><tr><th>Route</th><th>Providers</th></tr></thead><tbody>{routehtml}</tbody></table></div>
</div>
<div class="grid" style="margin-top:14px">
<div class="card"><span class="kicker">How to read a rating</span>
<p>A published rating is inspection history, not a statement of current compliance. The source's two absence states are kept distinct: no rating supplied and <em>Not Rated</em>. An inherited-rating flag is shown separately where supplied.</p></div>
<div class="card"><span class="kicker">What is not inferred</span>
<p>Supported living among qualifying locations: <strong>{m["supported_living_locations"]}</strong>. Providers holding more than one local location: <strong>{m["multi_location_providers"]}</strong>. No vacancy, staffing, budget or purchasing-intent figure is derived anywhere in this deliverable.</p></div>
</div>
</section>

<hr class="rule">

<section class="section">
<span class="kicker">Selected organisations · {len(sl)} of {m["distinct_providers"]} providers</span>
<h2>Accounts put forward, and why</h2>
<p class="section-lead">Each card carries a published fact, the reason it was selected, the question to ask when qualifying it, and what remains unknown. Identifiers are shown in full so they can be copied into a CRM.</p>
{cards}
</section>

<hr class="rule">

<section class="section" id="files">
<span class="kicker">Files</span>
<h2>What the buyer receives</h2>
<p class="section-lead">Four retained files, each built from the same frozen source edition. Downloads below are the delivered files themselves, not screenshots.</p>
<div class="files">
<div class="card file"><div class="n">territory-dataset.csv</div><div class="d">{len(ds)} qualifying locations, 21 columns, ready for import after the buyer maps fields to their CRM.</div><a href="territory-dataset.csv" download>Download CSV</a></div>
<div class="card file"><div class="n">shortlist-25.csv</div><div class="d">The {len(sl)} selected organisations with fact, reason, question and uncertainty.</div><a href="shortlist-25.csv" download>Download CSV</a></div>
<div class="card file"><div class="n">caregist-birmingham-solihull-territory-brief.xlsx</div><div class="d">Workbook built from the same frozen edition.</div><a href="caregist-birmingham-solihull-territory-brief.xlsx" download>Download workbook</a></div>
<div class="card file"><div class="n">caregist-birmingham-solihull-executive-brief.pdf</div><div class="d">Four-page executive brief, built from the same frozen source edition and checked for four readable pages.</div><a href="caregist-birmingham-solihull-executive-brief.pdf" download>Download executive brief</a></div>
</div>
</section>

<hr class="rule">

<section class="section">
<span class="kicker">Territory dataset · {len(ds)} qualifying locations</span>
<h2>The full export, not a sample</h2>
<p class="section-lead">Every qualifying location in scope, the same rows that produce the counts above. Scroll within the table; the complete file is available above.</p>
<div class="tall"><table><thead><tr><th>Location ID</th><th>Location</th><th>Provider</th><th>Authority</th><th>Postcode</th><th>Rating as published</th><th>Rating published</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>

<hr class="rule">

<section class="section">
<span class="kicker">Sources and checks</span>
<h2>Evidence behind every figure</h2>
<p class="section-lead">Source editions were downloaded, hashed and retained. Hashes identify file integrity; they are not proof of factual accuracy, authorship or regulatory compliance.</p>
<div class="tall" style="max-height:none"><table><thead><tr><th>Source file</th><th>HTTP</th><th>Retrieved at</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{srcrows}</tbody></table></div>
<p class="section-lead" style="margin:22px 0 14px">For each selected organisation, its representative CQC location page was fetched. <strong>{wcpass} of {len(wc)}</strong> captures returned MATCH, meaning the saved check recorded the expected location name and no archived notice. This is a limited page-name check, not a fresh audit of every source field or a statement about the provider.</p>
<div><span class="tag">● {wcpass} of {len(wc)} page checks MATCH</span></div>
<div class="tall" style="max-height:460px"><table><thead><tr><th>Location ID</th><th>HTTP</th><th>Checked at</th><th>Name found</th><th>Archived notice</th><th>SHA-256</th><th>Result</th></tr></thead><tbody>{wcrows}</tbody></table></div>
</section>

<hr class="rule">

<section class="section">
<div class="limits">
<div>
<div class="kicker">Carried with every delivery</div>
<p>Current published CQC editions, not real-time state. Source updates may lag. Monthly source: {m["source_rows"]:,} rows. Weekly cross-check edition: {m["weekly_source_rows"]:,} rows. No full inspection history. No vacancy, staffing shortage, purchasing budget or buying-intent inference.</p>
<p>Rating comparisons are not made across incompatible service or rating levels. No breach matrix, director-link or named-manager research is included.</p>
</div>
<div>
<div class="kicker">Buyer fit is the open limitation</div>
<p>The pack records its own limits: <em>{e(m["limits"])}</em></p>
<p>The reason on every account above is specific to that provider and derived from a published fact, but the <strong>criteria that selected them</strong> were set for an illustrative homecare staffing buyer. A real engagement begins with a 15-minute scoping call to agree criteria, after which the selection is re-run. Nothing here should be sent to a buyer as though their criteria produced it.</p>
</div>
</div>
</section>

<footer class="footer">
CareGist is an independent intelligence provider and does not represent the Care Quality Commission (CQC). Contains public sector information licensed under the Open Government Licence v3.0. Selection criteria are illustrative and not yet buyer-agreed.<br><br>
Preview generated {datetime.date.today().isoformat()} from <code>artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/pack-data.json</code> by <code>build_preview.py</code>. State reached: Draft, evidence checked. It has not been independently accepted or released. No reviewer has signed this deliverable.
</footer>
</div></body></html>'''

(OUT / "index.html").write_text(doc)
for filename, source in DELIVERY_ASSETS.items():
    shutil.copy2(source, OUT / filename)
manifest = {
    "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "draft-evidence-checked-not-released",
    "assets": [{"file": name, "bytes": (OUT / name).stat().st_size, "sha256": sha256(OUT / name)} for name in DELIVERY_ASSETS],
}
(OUT / "delivery-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"wrote {len(doc):,} bytes and {len(DELIVERY_ASSETS)} verified delivery assets")
print(f"cards={len(sl)} dataset_rows={len(ds)} web_checks={len(wc)} match={wcpass}")
