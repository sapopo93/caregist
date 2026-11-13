#!/usr/bin/env python3
"""Turn the table printed by the "Supply snapshot (read-only)" workflow into a PDF.

    python3 make_snapshot_pdf.py rows.txt out.pdf --title "Supply around ..." \
        --site "Carleton Hill Road, Penrith (centre CA11 8TZ)" --postcode "CA11 8TZ" --radius 5 \
        --checked "13 November 2026" [--site-note "..."]

rows.txt holds the workflow's lines, unchanged:
    miles|name|town|beds|nursing|rating|last_inspection|registered_on|id
The workflow prints a sha256 of the lines; check it before use:
    python3 -c "import hashlib;print(hashlib.sha256(open('rows.txt').read().rstrip('\\n').encode()).hexdigest())"

Every figure in the text is computed from the table. A home whose current CQC page shows
only a previous provider's ratings ("No own rating (inherited)") is treated as a change of
provider, not new supply. Needs Playwright with Chromium (node) for the PDF step.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import subprocess
import sys
import tempfile
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September",
     "October", "November", "December"], 1)}


def parse_date(text: str) -> dt.date | None:
    try:
        d, m, y = text.split()
        return dt.date(int(y), MONTHS[m], int(d))
    except (ValueError, KeyError):
        return None


def read_rows(path: str) -> list[dict]:
    rows = []
    for ln in Path(path).read_text().splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        miles, name, town, beds, nursing, rating, last, reg, lid = ln.split("|")
        rows.append({"miles": float(miles), "name": name, "town": town, "beds": int(beds),
                     "nursing": nursing == "Yes", "rating": rating, "last": last,
                     "reg": parse_date(reg), "reg_text": reg, "id": lid})
    return rows


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def findings(rows: list[dict], checked: dt.date, postcode: str, radius: float) -> list[str]:
    total = len(rows)
    beds = sum(r["beds"] for r in rows)
    cutoff = dt.date(checked.year - 2, checked.month, checked.day)
    inherited = [r for r in rows if r["rating"].startswith("No own rating")]
    unrated = [r for r in rows if r["rating"] == "Not yet rated"]
    new = [r for r in unrated if r["reg"] and r["reg"] >= cutoff]
    rated = [r for r in rows if r["rating"] in ("Outstanding", "Good", "Requires improvement", "Inadequate")]
    nursing = [r for r in rows if r["nursing"]]
    out = [f"There {'is' if total == 1 else 'are'} {plural(total, 'older-people care home')}, with {beds} registered "
           f"beds, within {radius:g} miles of {postcode}."]
    if new:
        nb = sum(r["beds"] for r in new)
        names = "; ".join(f"{r['name']} ({r['beds']} beds, {r['reg_text']})" for r in sorted(new, key=lambda r: r["reg"]))
        out.append(f"<b>{nb} beds newly registered in the last two years</b> across {plural(len(new), 'home')}: {names}. "
                   "None has a CQC rating yet.")
    else:
        out.append("<b>No new supply in the last two years.</b> No home within the radius registered with CQC "
                   "since " + cutoff.strftime("%d %B %Y").lstrip("0") + " that CQC shows as a new service without a prior provider's ratings.")
    if inherited:
        names = "; ".join(f"{r['name']} ({r['beds']} beds, current registration from {r['reg_text']})" for r in inherited)
        out.append("<b>Changes of provider.</b> CQC's page for each of these shows only ratings inherited from a previous "
                   f"provider, so the current registration has no rating of its own: {names}. These are existing beds under "
                   "new registrations, not new supply, and are worth checking before quoting them as competitors.")
    nb = sum(r["beds"] for r in nursing)
    out.append(f"<b>Nursing supply:</b> {plural(len(nursing), 'of the ' + str(total) + ' homes provides', 'of the ' + str(total) + ' homes provide')} "
               f"nursing ({nb} beds).")
    if rated:
        counts = {}
        for r in rated:
            counts[r["rating"]] = counts.get(r["rating"], 0) + 1
        mix = ", ".join(f"{n} {k}" for k, n in counts.items())
        out.append(f"<b>Quality:</b> {plural(len(rated), 'home has', 'homes have')} their own current rating: {mix}.")
    return out


def build_html(rows, args, checked_text, findings_html) -> str:
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in
                         (r["name"], r["town"], f"{r['miles']:.1f}", r["beds"], "Yes" if r["nursing"] else "No",
                          r["rating"], r["last"], r["reg_text"] if r["reg_text"] != "?" else "")) + "</tr>"
        for r in rows)
    lis = "".join(f"<li>{f}</li>" for f in findings_html[1:])
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>{html.escape(args.title)}</title>
<style>
body {{ font: 10.5pt/1.45 Helvetica, Arial, sans-serif; color:#1f2a24; }}
h1 {{ font-size: 20pt; margin: 0 0 4pt; }} h2 {{ font-size: 13pt; margin: 18pt 0 6pt; border-bottom: 1px solid #c9c2b0; padding-bottom:3pt; }}
.meta {{ color:#5b6a62; margin-bottom: 10pt; }} .small {{ font-size: 9pt; color:#46544c; }}
table {{ border-collapse: collapse; width:100%; font-size: 8.6pt; margin: 6pt 0; }}
th,td {{ border: 1px solid #d8d2c2; padding: 3pt 5pt; text-align:left; vertical-align: top; }}
th {{ background:#efe9d8; }} tr {{ page-break-inside: avoid; }} li {{ margin-bottom: 5pt; }}
</style></head><body>
<h1>{html.escape(args.title)}</h1>
<div class="meta">CareGist (H-Kay Limited) · supply picture around {html.escape(args.site)} · ratings, bed counts and registration status read from CQC on {html.escape(checked_text)}</div>
<p>{args.site_note or ''} This is a desk snapshot of registered supply. It is not a planning need assessment.</p>
<h2>Findings</h2>
<p>{findings_html[0]}</p><ul>{lis}</ul>
<h2>Supply within {args.radius:g} miles</h2>
<p>Older-people care homes (registered for adults over 65), nearest first. Distances are straight-line miles from {html.escape(args.postcode)}.
"No own rating (inherited)" means the home's current registration has no rating yet and CQC shows only ratings from a previous provider.
"Not held" means CareGist holds no date for the inspection behind the rating.</p>
<table><tr><th>Home</th><th>Town</th><th>Miles</th><th>Beds</th><th>Nursing</th><th>CQC rating</th><th>Last inspection</th><th>Registered (CQC page)</th></tr>{tr}</table>
<h2>Limits of this snapshot</h2>
<ul><li>Ratings and registration dates were read from each location's CQC page, and bed counts and registered status from CQC's API (CQC's pages do not publish bed counts), on {html.escape(checked_text)}. Distances and inspection dates come from CareGist's data.</li>
<li>Homes that CQC no longer shows as registered are excluded. A home that CQC lists under two location records (dual registration, one per provider) is counted once.</li>
<li>Distances are straight-line from the postcode centre, not drive times. Care homes registered for adults over 65 only; other services are excluded.</li>
<li>Not included: population projections for the catchment and planned supply from the planning register. A full assessment adds both.</li></ul>
<p class="small"><b>Source:</b> CQC data via CareGist, under the Open Government Licence.</p>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rows"); ap.add_argument("out")
    ap.add_argument("--title", required=True); ap.add_argument("--site", required=True)
    ap.add_argument("--postcode", required=True); ap.add_argument("--radius", type=float, default=5.0)
    ap.add_argument("--checked", required=True, help="e.g. '13 November 2026'")
    ap.add_argument("--site-note", default="")
    args = ap.parse_args()
    rows = read_rows(args.rows)
    if not rows:
        print("no rows", file=sys.stderr); return 2
    checked = parse_date(args.checked)
    if not checked:
        print("--checked must look like '13 November 2026'", file=sys.stderr); return 2
    doc = build_html(rows, args, args.checked, findings(rows, checked, args.postcode, args.radius))
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "s.html"; h.write_text(doc)
        js = Path(td) / "r.js"
        js.write_text("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();"
                      "const p=await b.newPage();await p.goto('file://'+process.argv[2]);"
                      "await p.pdf({path:process.argv[3],format:'A4',margin:{top:'18mm',bottom:'18mm',left:'16mm',right:'16mm'}});"
                      "await b.close();})();")
        subprocess.run(["node", str(js), str(h), str(Path(args.out).resolve())], check=True)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
