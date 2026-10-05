#!/usr/bin/env python3
"""Render a scoped manual pack locally; never charge, send or mark acceptance."""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

FIELDS = (
    "provider_id", "provider_name", "location_id", "location_name",
    "registration_status", "registration_start", "registration_end",
    "regulated_activities", "service_types", "published_rating",
    "source_urls", "retrieved_at", "reviewed_by", "limitations",
)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(data.get("synthetic"), bool):
        raise ValueError("Explicit synthetic true/false is required")
    for key in FIELDS:
        value = data.get(key)
        if not value or (key != "source_urls" and not isinstance(value, str)):
            raise ValueError(f"Missing or invalid {key}")
    if not isinstance(data["source_urls"], list) or not all(isinstance(u, str) and u for u in data["source_urls"]):
        raise ValueError("Source URLs must be a non-empty list")
    if not data["synthetic"]:
        for key in ("provider_id", "location_id"):
            if not re.fullmatch(r"1-[0-9]+", data[key]):
                raise ValueError("Real packs require exact CQC identifiers")
        retrieved = datetime.fromisoformat(data["retrieved_at"].replace("Z", "+00:00"))
        if retrieved.tzinfo is None or not 0 <= (datetime.now(timezone.utc) - retrieved).total_seconds() <= 86400:
            raise ValueError("Real packs need source retrieval within the previous 24 hours")
        if not all(u.startswith("https://") for u in data["source_urls"]):
            raise ValueError("Real packs need explicit HTTPS sources")
        evidence = data.get("source_evidence_sha256")
        if not isinstance(evidence, list) or len(evidence) != len(data["source_urls"]) or not all(re.fullmatch(r"[a-f0-9]{64}", h) for h in evidence):
            raise ValueError("A saved evidence hash is required for each source")
        if data.get("rights_confirmed") is not True or data.get("independent_check_approved") is not True:
            raise ValueError("Source rights and independent factual check must be confirmed")
    args.output.mkdir(parents=True, exist_ok=True)
    stem = "synthetic-registration-factsheet" if data["synthetic"] else "registration-factsheet"
    csv_path = args.output / f"{stem}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("field", "value"))
        writer.writerow(("synthetic", str(data["synthetic"]).lower()))
        for key in FIELDS:
            value = "; ".join(data[key]) if key == "source_urls" else data[key]
            # CSV opened in a spreadsheet must not execute supplied formulas.
            if value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            writer.writerow((key, value))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=9, leading=13, alignment=TA_LEFT))
    title = "SYNTHETIC SAMPLE - NOT A CUSTOMER DELIVERY" if data["synthetic"] else "CareGist registration factsheet"
    story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 14),
             Paragraph("One provider / one location / dated public facts", styles["Heading2"]), Spacer(1, 10)]
    rows = [[Paragraph("Field", styles["Cell"]), Paragraph("Value", styles["Cell"])]]
    for key in FIELDS:
        value = "; ".join(data[key]) if key == "source_urls" else data[key]
        rows.append([Paragraph(escape(key.replace("_", " ").capitalize()), styles["Cell"]), Paragraph(escape(value), styles["Cell"])])
    table = Table(rows, colWidths=[132, 359], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EDF2")),
                              ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#CDD4DC")),
                              ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 16)])
    attribution = ("Invented sample data. No official CQC record was retrieved or approved." if data["synthetic"] else
                   "Contains public sector information licensed under the Open Government Licence v3.0. Source: Care Quality Commission. CareGist is independent of CQC; no endorsement is implied.")
    story.append(Paragraph(escape(attribution), styles["BodyText"]))
    pdf_path = args.output / f"{stem}.pdf"
    SimpleDocTemplate(str(pdf_path), pagesize=(595.28, 841.89), rightMargin=52, leftMargin=52, topMargin=42, bottomMargin=42).build(story)
    manifest = {"synthetic": data["synthetic"], "delivery_status": "rendered_only",
                "customer_acceptance": "not_recorded", "payment": "not_recorded",
                "files": [{"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in (pdf_path, csv_path)]}
    (args.output / f"{stem}-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Pack rendered locally; no payment, delivery or customer acceptance recorded.")

if __name__ == "__main__":
    main()
