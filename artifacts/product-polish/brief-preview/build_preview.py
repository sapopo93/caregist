#!/usr/bin/env python3
"""Build the £795 Territory Opportunity Brief client delivery preview.

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
    pal = {"Good": ("#ECFDF5", "#065F46", "#A7F3D0", "●"),
           "Outstanding": ("#ECFDF5", "#065F46", "#A7F3D0", "★"),
           "Requires improvement": ("#FFFBEB", "#92400E", "#FDE68A", "▲"),
           "Inadequate": ("#FEF2F2", "#991B1B", "#FECACA", "■")}.get(r, ("#F3EFEA", "#4B5161", "#E2DDD5", "·"))
    tag = ' <span class="q">inherited</span>' if inh == "Y" else ""
    return (f'<span class="chip" style="background:{pal[0]};color:{pal[1]};border-color:{pal[2]}">'
            f'<span class="g">{pal[3]}</span>{e(r)}</span>{tag}')

def val(v, absent="Not stated in reviewed source"):
    s = ("" if v is None else str(v)).strip()
    return e(s) if s else f'<span class="absent">{absent}</span>'

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
    f'<div class="tile"><div class="tnum">{v}</div><div class="tlab">{e(l)}</div><div class="tsub">{e(s)}</div></div>'
    for v, l, s in tiles)

authhtml = " · ".join(f'{e(k)} <strong>{v}</strong>' for k, v in auth.items())
routehtml = "".join(f'<tr><td>{e(k)}</td><td class="num">{v}</td></tr>' for k, v in m["routes"].items())
rathtml = "".join(
    f'<tr><td>{"<span class=\'absent\'>Not stated in reviewed source</span>" if k=="Not supplied" else e(k)}</td>'
    f'<td class="num">{v}</td></tr>'
    for k, v in sorted(ratings.items(), key=lambda x: -x[1]))

# --- 25 account cards ---------------------------------------------------------
cards = ""
for r in sl:
    cards += f'''<article class="acct">
<header><span class="ord">{r['review_order']:02d}</span>
<div class="ahead"><h3>{e(r['provider_name'])}</h3>
<div class="meta"><code>{e(r['provider_id'])}</code> · {val(r.get('authorities'))} · {val(r.get('service_mix'))}</div></div>
<span class="route">{e(r['review_route'])}</span></header>
<div class="abody">
<div class="fact"><span class="lab">Published fact</span><p>{val(r.get('published_fact'))}</p></div>
<div class="why"><span class="lab">Why included</span><p>{val(r.get('reason_for_review'))}</p></div>
<div class="ask"><span class="lab">What to check next</span><p>{val(r.get('qualification_question'))}</p></div>
<div class="unc"><span class="lab">Uncertainty</span><p>{val(r.get('uncertainty'))}</p></div>
</div>
<footer><div><span class="lab">Representative location</span> {val(r.get('representative_location'))} <code>{e(r.get('location_id',''))}</code></div>
<div><span class="lab">Local / England locations</span> <span class="num">{r.get('local_locations','')}</span> / <span class="num">{r.get('england_domiciliary_locations','')}</span></div>
<div><span class="lab">Source</span> <a href="{e(r.get('cqc_url',''))}" rel="noopener">CQC location page</a> · checked {val(r.get('web_check_date'))} · {val(r.get('web_check_result'))}</div>
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
    f'<tr><td>{e(s["file"])}</td><td class="num">{s["http_status"]}</td>'
    f'<td class="mono">{e(s["retrieved_at"])}</td><td class="num">{s["bytes"]:,}</td>'
    f'<td><code class="hash">{e(s["sha256"])}</code></td></tr>' for s in m["source_manifest"])
wcpass = sum(1 for w in wc if w.get("result") == "MATCH")
wcrows = "".join(
    f'<tr><td><code>{e(w["location_id"])}</code></td><td class="num">{w["http_status"]}</td>'
    f'<td class="mono">{e(w["checked_at"])}</td>'
    f'<td>{"yes" if w.get("location_name_found") else "no"}</td>'
    f'<td>{"yes" if w.get("archived_notice_found") else "no"}</td>'
    f'<td><code class="hash">{e(w["sha256"])}</code></td><td>{e(w["result"])}</td></tr>' for w in wc)

CSS = """
:root{--canvas:#FAF8F5;--l1:#FFF;--l2:#F3EFEA;--hover:#F8F6F1;--bsub:#E2DDD5;--bstr:#1A1C22;
--ink:#1A1C22;--meta:#4B5161;--accent:#C27838;--pos:#059669;--crit:#C02633;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--canvas);color:var(--ink);font:400 15px/22px Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-variant-numeric:tabular-nums lining-nums;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:32px}
h1,h2,h3{font-family:"Source Serif 4",Georgia,serif;font-weight:600;margin:0}
h1{font-size:36px;line-height:44px;letter-spacing:-.02em}
h2{font-size:26px;line-height:34px;letter-spacing:-.01em}
h3{font-size:17px;line-height:24px}
code{font:500 11.5px/16px var(--mono);color:var(--meta);word-break:break-all}
.hash{font-size:10.5px;letter-spacing:-.01em}
.lab,.tlab{font:600 11px/14px Inter,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--meta)}
.mono{font:500 11.5px/16px var(--mono);color:var(--meta);white-space:nowrap}
.num{font-variant-numeric:tabular-nums;font-weight:600}
a{color:var(--ink);text-decoration:underline;text-underline-offset:2px;text-decoration-color:var(--accent)}
header.top{border-bottom:2px solid var(--bstr);padding-bottom:20px;margin-bottom:8px}
.status{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:12px}
.chip{display:inline-flex;align-items:center;gap:5px;border:1px solid;border-radius:2px;padding:2px 7px;font:600 11px/14px Inter,sans-serif;letter-spacing:.02em;white-space:nowrap}
.chip .g{font-size:9px}
.q{color:var(--meta);font-size:11px;font-weight:500}
.absent{color:var(--meta);font-style:normal;font-size:12.5px;border-bottom:1px dotted var(--bsub)}
section{margin:36px 0}
.sublab{font:600 11px/14px Inter,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--meta);margin-bottom:8px}
.sub{color:var(--meta);font-size:13px;line-height:19px;margin:8px 0 16px;max-width:80ch}
.note{background:var(--l2);border:1px solid var(--bsub);border-left:3px solid var(--accent);border-radius:2px;padding:13px 15px;font-size:13px;line-height:19px}
.note.warn{background:#FFFBEB;border-color:#FDE68A;border-left-color:#D97706;color:#92400E}
.note .nh{margin:0 0 6px;font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:15px;line-height:21px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.tile{background:var(--l1);border:1px solid var(--bsub);border-radius:4px;padding:14px 16px}
.tnum{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:32px;line-height:38px}
.tsub{color:var(--meta);font-size:12px;line-height:16px;margin-top:4px}
table{width:100%;border-collapse:collapse;background:var(--l1);border:1px solid var(--bsub);border-radius:4px}
thead th{background:var(--l2);border-bottom:2px solid var(--bstr);text-align:left;padding:9px 12px;font:600 11px/14px Inter,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--meta);white-space:nowrap;position:sticky;top:0}
td{border-bottom:1px solid var(--bsub);padding:9px 12px;vertical-align:top;font-size:13px;line-height:18px}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--hover)}
.scroll{overflow-x:auto}
.tall{max-height:560px;overflow:auto;border:1px solid var(--bsub);border-radius:4px}
.tall table{border:0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.acct{background:var(--l1);border:1px solid var(--bsub);border-radius:8px;padding:0;margin-bottom:12px}
.acct header{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-bottom:1px solid var(--l2)}
.ord{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:20px;color:var(--meta);min-width:26px}
.ahead{flex:1}
.acct .meta{color:var(--meta);font-size:12px;line-height:17px;margin-top:3px}
.route{border:1px solid var(--bsub);background:var(--l2);border-radius:2px;padding:3px 8px;font:600 11px/14px Inter,sans-serif;letter-spacing:.02em;color:var(--meta);white-space:nowrap}
.abody{display:grid;grid-template-columns:1fr 1fr;gap:0}
.abody>div{padding:12px 16px;border-bottom:1px solid var(--l2)}
.abody>div:nth-child(odd){border-right:1px solid var(--l2)}
.abody p{margin:4px 0 0;font-size:13px;line-height:19px}
.why{background:#FDFCFA}
.unc p{color:var(--meta)}
.acct footer{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;padding:12px 16px;font-size:12.5px;line-height:17px}
.acct footer .lab{display:block;margin-bottom:2px}
.files{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.file{background:var(--l1);border:1px solid var(--bsub);border-radius:4px;padding:14px 16px}
.file .n{font-weight:600;font-size:13px}
.file .d{color:var(--meta);font-size:12px;line-height:17px;margin:4px 0 8px}
footer.doc{margin-top:44px;border-top:1px solid var(--bsub);padding-top:16px;color:var(--meta);font-size:12px;line-height:18px}
@media(max-width:768px){.wrap{padding:24px 16px}h1{font-size:28px;line-height:36px}
.two,.abody{grid-template-columns:1fr}.abody>div:nth-child(odd){border-right:0}
.acct header{flex-wrap:wrap}}
"""

doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Territory Opportunity Brief — preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><div class="wrap">

<header class="top">
<div class="sublab">Territory Opportunity Brief · £795 one-off · client delivery preview</div>
<h1 style="margin-top:8px">Birmingham and Solihull</h1>
<p class="sub">Domiciliary care territory, source edition {e(m["source_edition"])}, retrieved {e(m["retrieved_date"])}. This page previews the retained client delivery files and shows the data, evidence and limits behind them.</p>
<div class="status">
<span class="chip" style="background:#FFFBEB;color:#92400E;border-color:#FDE68A"><span class="g">▲</span>Launch preparation — not purchasable</span>
<span class="chip" style="background:#F3EFEA;color:#4B5161;border-color:#E2DDD5"><span class="g">·</span>Sample — no buyer engaged</span>
<span class="chip" style="background:#F3EFEA;color:#4B5161;border-color:#E2DDD5"><span class="g">·</span>State: Draft, evidence checked</span>
</div>
</header>

<section>
<div class="note warn"><p class="nh">Buyer fit is the open limitation</p>
<p style="margin:0">The pack records its own limits: <em>{e(m["limits"])}</em></p>
<p style="margin:8px 0 0">In practice: the reason on every account below is specific to that provider and derived from a published fact, but the <strong>criteria that selected them</strong> were set for an illustrative homecare staffing buyer. A real engagement begins with a 15-minute scoping call to agree criteria, after which the selection is re-run. Nothing here should be sent to a buyer as though their criteria produced it.</p></div>
</section>

<section>
<div class="sublab">Executive findings</div>
<h2>What the territory contains</h2>
<p class="sub">Local authorities: {authhtml}. All counts reproduce from the {len(ds)} rows in the territory dataset below.</p>
<div class="tiles">{tilehtml}</div>
<div class="two" style="margin-top:16px">
<div><div class="sublab">Published rating distribution</div><table><thead><tr><th>Rating as published</th><th>Locations</th></tr></thead><tbody>{rathtml}</tbody></table>
<p class="sub" style="margin-top:10px">A published rating is inspection history, not a statement of current compliance. The source's two absence states are kept distinct: no rating supplied and <em>Not Rated</em>. An inherited-rating flag is shown separately where supplied.</p></div>
<div><div class="sublab">Review routes</div><table><thead><tr><th>Route</th><th>Providers</th></tr></thead><tbody>{routehtml}</tbody></table>
<p class="sub" style="margin-top:10px">Supported living among qualifying locations: <strong>{m["supported_living_locations"]}</strong>. Providers holding more than one local location: <strong>{m["multi_location_providers"]}</strong>. No vacancy, staffing, budget or purchasing-intent figure is derived anywhere in this deliverable.</p></div>
</div>
</section>

<section>
<div class="sublab">Selected organisations · {len(sl)} of {m["distinct_providers"]} providers</div>
<h2>Accounts put forward, and why</h2>
<p class="sub">Each card carries a published fact, the reason it was selected, the question to ask when qualifying it, and what remains unknown. Identifiers are shown in full so they can be copied into a CRM.</p>
{cards}
</section>

<section>
<div class="sublab">Territory dataset · {len(ds)} qualifying locations</div>
<h2>The full export, not a sample</h2>
<p class="sub">Every qualifying location in scope, the same rows that produce the counts above. Scroll within the table; the complete file is available below.</p>
<div class="tall"><table><thead><tr><th>Location ID</th><th>Location</th><th>Provider</th><th>Authority</th><th>Postcode</th><th>Rating as published</th><th>Rating published</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>

<section>
<div class="sublab">Files</div>
<h2>What the buyer receives</h2>
<div class="files">
<div class="file"><div class="n">territory-dataset.csv</div><div class="d">{len(ds)} qualifying locations, 21 columns, ready for import after the buyer maps fields to their CRM.</div><a href="territory-dataset.csv" download>Download CSV</a></div>
<div class="file"><div class="n">shortlist-25.csv</div><div class="d">The {len(sl)} selected organisations with fact, reason, question and uncertainty.</div><a href="shortlist-25.csv" download>Download CSV</a></div>
<div class="file"><div class="n">caregist-birmingham-solihull-territory-brief.xlsx</div><div class="d">Workbook built from the same frozen edition.</div><a href="caregist-birmingham-solihull-territory-brief.xlsx" download>Download workbook</a></div>
<div class="file"><div class="n">caregist-birmingham-solihull-executive-brief.pdf</div><div class="d">Four-page executive brief, built from the same frozen source edition and checked for four readable pages.</div><a href="caregist-birmingham-solihull-executive-brief.pdf" download>Download executive brief</a></div>
</div>
</section>

<section>
<div class="sublab">Sources and checks</div>
<h2>Evidence behind every figure</h2>
<p class="sub">Source editions were downloaded, hashed and retained. Hashes identify file integrity; they are not proof of factual accuracy, authorship or regulatory compliance.</p>
<div class="scroll"><table><thead><tr><th>Source file</th><th>HTTP</th><th>Retrieved at</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{srcrows}</tbody></table></div>
<p class="sub" style="margin-top:18px">For each selected organisation, its representative CQC location page was fetched. <strong>{wcpass} of {len(wc)}</strong> captures returned MATCH, meaning the saved check recorded the expected location name and no archived notice. This is a limited page-name check, not a fresh audit of every source field or a statement about the provider.</p>
<div class="tall" style="margin-top:8px"><table><thead><tr><th>Location ID</th><th>HTTP</th><th>Checked at</th><th>Name found</th><th>Archived notice</th><th>SHA-256</th><th>Result</th></tr></thead><tbody>{wcrows}</tbody></table></div>
</section>

<section>
<div class="note"><p class="nh">Limitations carried with this deliverable</p>
<p style="margin:0">Current published CQC editions, not real-time state. Source updates may lag. Monthly source: {m["source_rows"]:,} rows. Weekly cross-check edition: {m["weekly_source_rows"]:,} rows. No full inspection history. No vacancy, staffing shortage, purchasing budget or buying-intent inference. Selection criteria are illustrative and not yet buyer-agreed. Rating comparisons are not made across incompatible service or rating levels. No breach matrix, director-link or named-manager research is included.</p></div>
</section>

<footer class="doc">
CareGist is an independent intelligence provider and does not represent the Care Quality Commission (CQC). Contains public sector information licensed under the Open Government Licence v3.0.<br><br>
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
