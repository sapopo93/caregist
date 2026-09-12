#!/usr/bin/env python3
"""Create a dated Radar format sample (HTML + PDF) from a generated digest JSON.

Usage:
    build_radar_pilot_sample.py [digest_json] [out_pdf] [out_html]

Defaults reproduce the Gloucestershire 2026-08-04 sample, so existing callers
that pass no arguments keep the previous behaviour.

The builder is data-driven: territory, counts, and every event row come from the
digest JSON. Nothing about the territory is hardcoded, so a wrong territory can
never be printed next to another territory's rows.
"""
import json
import sys
from pathlib import Path

try:  # reportlab is not installed on every machine; HTML is the always-available output
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    HAVE_REPORTLAB = True
except ImportError:
    HAVE_REPORTLAB = False

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "radar-pilot-sample"

DEFAULT_JSON = ROOT / "radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.json"
DEFAULT_PDF = OUT / "caregist-radar-gloucestershire-dated-format-sample.pdf"
DEFAULT_HTML = OUT / "index.html"

args = sys.argv[1:]
digest_json = Path(args[0]) if len(args) > 0 else DEFAULT_JSON
out_pdf = Path(args[1]) if len(args) > 1 else DEFAULT_PDF
out_html = Path(args[2]) if len(args) > 2 else DEFAULT_HTML

data = json.loads(digest_json.read_text())
p = data["provenance"]
events = data["events"]
territory = p["territory"]

new_regs = [e for e in events if e["event_type"] == "new_registration"]
ratings = [e for e in events if e["event_type"] == "rating_published"]
n_new, n_rate = len(new_regs), len(ratings)

# Only the two supported event types are rendered. Anything else would be
# silently dropped, so fail loudly rather than under-report the register.
unknown = {e["event_type"] for e in events} - {"new_registration", "rating_published"}
if unknown:
    raise SystemExit(f"unsupported event_type(s) in digest: {sorted(unknown)}")

out_pdf.parent.mkdir(parents=True, exist_ok=True)
out_html.parent.mkdir(parents=True, exist_ok=True)


def rating_rows() -> str:
    return "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            e["provider_name"], e["location_name"], e["new_value"]["rating"], e["effective_date"]
        )
        for e in ratings
    )


def new_reg_rows() -> str:
    return "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            e["provider_name"], e["location_name"], e.get("postcode", ""), e["effective_date"]
        )
        for e in new_regs
    )


html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CareGist Radar, dated format sample</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>@page{{size:A4;margin:12mm}}html{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}:root{{--bg:#faf8f5;--paper:#fff;--soft:#f3efea;--ink:#1a1c22;--muted:#4b5161;--line:#e2ddd5;--accent:#c27838;--warn:#92400e}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Inter,Arial,sans-serif}}main{{max-width:920px;margin:auto;padding:40px 28px}}h1,h2{{font-family:"Source Serif 4",Georgia,serif;font-weight:600;margin:0}}h1{{font-size:42px;line-height:1.1}}h2{{font-size:25px;margin-top:32px}}.eyebrow{{font:600 11px Inter,Arial,sans-serif;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}}.sub{{max-width:68ch;color:var(--muted)}}.notice{{border:1px solid #fde68a;border-left:3px solid var(--accent);background:#fffbeb;color:var(--warn);padding:14px 16px;margin:24px 0}}.tiles{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:22px 0}}.tile,.event{{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:18px}}.number{{font:600 34px/1 "Source Serif 4",Georgia,serif}}.label{{font-size:12px;color:var(--muted);margin-top:5px}}.event p{{margin:7px 0}}table{{width:100%;border-collapse:collapse;background:var(--paper);border:1px solid var(--line)}}th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:13px}}th{{background:var(--soft);font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}}.meta{{font-size:12px;color:var(--muted);border-top:1px solid var(--line);margin-top:32px;padding-top:16px}}a{{color:var(--ink)}}@media(max-width:600px){{main{{padding:28px 16px}}h1{{font-size:34px}}.tiles{{grid-template-columns:1fr}}}}</style></head><body><main>
<div class="eyebrow">CareGist Radar · dated format sample</div><h1>{territory} weekly digest</h1><p class="sub">Published CQC register edition dated {p['edition_date']}. Event window {p['window_start']} to {p['window_end']}. This shows the format and evidence treatment of a digest. It is not a current week, a live feed, or a completed pilot delivery.</p>
<div class="notice"><strong>£150 pilot position.</strong> The recorded scope is four weekly email/PDF digests for an agreed region, with no software. The fresh weekly source route and four-week delivery are not yet verified. No new buyer should be charged on the strength of this sample.</div>
<div class="tiles"><div class="tile"><div class="number">{n_new}</div><div class="label">new registrations in this dated window</div></div><div class="tile"><div class="number">{n_rate}</div><div class="label">rating publications in this dated window</div></div></div>
<h2>New registrations</h2><table><thead><tr><th>Provider</th><th>Location</th><th>Postcode</th><th>Registered</th></tr></thead><tbody>{new_reg_rows()}</tbody></table>
<h2>Ratings published</h2><table><thead><tr><th>Provider</th><th>Location</th><th>Rating</th><th>Published</th></tr></thead><tbody>{rating_rows()}</tbody></table>
<h2>What this digest does and does not say</h2><div class="event"><p>The source has the latest rating and its publication date. It does not contain full rating history, so this says <strong>rating published</strong>, not rating changed.</p><p>It makes no claim about vacancies, staffing needs, budgets, purchasing intent or current compliance.</p></div><div class="meta">Source: CQC Care directory with filters, file <code>{p['source_file']}</code>; {p['parsed_rows']:,} parsed rows, {p['territory_rows']:,} {territory} rows. Original source page: <a href="{p['source_page']}">{p['source_page']}</a>. Generated from retained JSON, no live API call.</div>
</main></body></html>'''
out_html.write_text(html)

if not HAVE_REPORTLAB:
    print(f"wrote HTML {out_html}  territory={territory} new_registrations={n_new} rating_publications={n_rate}")
    raise SystemExit(
        "reportlab not installed on this machine: HTML written, PDF not produced. "
        "Render the HTML to PDF (headless Chrome --print-to-pdf) or install reportlab."
    )

styles = getSampleStyleSheet()
title = ParagraphStyle("title", parent=styles["Title"], fontName="Times-Bold", fontSize=25, leading=29, textColor=HexColor("#1a1c22"), spaceAfter=8)
body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=14, textColor=HexColor("#1a1c22"), spaceAfter=8)
small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11, textColor=HexColor("#4b5161"))
h2 = ParagraphStyle("sub", parent=title, fontSize=15, leading=19, spaceBefore=14, spaceAfter=6)

story = [
    Paragraph("CAREGIST RADAR · DATED FORMAT SAMPLE", small),
    Paragraph(f"{territory} weekly digest", title),
    Paragraph(
        f"Published CQC register edition dated {p['edition_date']}. Event window "
        f"{p['window_start']} to {p['window_end']}. This is not a current week, a live feed, "
        f"or a completed pilot delivery.",
        body,
    ),
    Spacer(1, 4),
]

summary = Table(
    [[str(n_new), str(n_rate)], ["New registrations", "Rating publications"]],
    colWidths=[87 * mm, 87 * mm],
)
summary.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f3efea")),
    ("BOX", (0, 0), (-1, -1), .5, HexColor("#e2ddd5")),
    ("INNERGRID", (0, 0), (-1, -1), .5, HexColor("#e2ddd5")),
    ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 24),
    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ("ALIGN", (0, 1), (-1, 1), "CENTER"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 10),
]))
story += [summary]

TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f3efea")),
    ("GRID", (0, 0), (-1, -1), .5, HexColor("#e2ddd5")),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("PADDING", (0, 0), (-1, -1), 6),
])

story += [Paragraph("New registrations", h2)]
if new_regs:
    reg_table = Table(
        [["Provider", "Location", "Postcode", "Registered"]]
        + [[e["provider_name"], e["location_name"], e.get("postcode", ""), e["effective_date"]] for e in new_regs],
        colWidths=[62 * mm, 62 * mm, 22 * mm, 28 * mm],
    )
    reg_table.setStyle(TABLE_STYLE)
    story += [reg_table]
else:
    story += [Paragraph("0 supported new-registration events in this window.", body)]

story += [Paragraph("Ratings published", h2)]
if ratings:
    rate_table = Table(
        [["Provider", "Location", "Rating", "Published"]]
        + [[e["provider_name"], e["location_name"], e["new_value"]["rating"], e["effective_date"]] for e in ratings],
        colWidths=[58 * mm, 58 * mm, 30 * mm, 28 * mm],
    )
    rate_table.setStyle(TABLE_STYLE)
    story += [rate_table]
else:
    story += [Paragraph("0 supported rating-publication events in this window.", body)]

story += [
    Spacer(1, 14),
    Paragraph(
        "The source carries the latest rating and publication date, not full history. The honest event "
        "is rating published, not rating changed. It makes no claim about vacancies, staffing needs, "
        "budgets, purchasing intent or current compliance.",
        body,
    ),
    Paragraph(
        f"£150 pilot scope recorded: four weekly email/PDF digests for an agreed region, with no software. "
        f"Fresh weekly source and four-week delivery are not verified. Source: {p['source_file']}; "
        f"{p['parsed_rows']:,} parsed rows; {p['territory_rows']:,} {territory} rows.",
        small,
    ),
]

SimpleDocTemplate(
    str(out_pdf), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm
).build(story)

print(f"wrote HTML {out_html}")
print(f"wrote PDF  {out_pdf}  territory={territory} new_registrations={n_new} rating_publications={n_rate}")
