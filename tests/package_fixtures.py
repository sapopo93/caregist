"""Real, openable PDFs for tests that pass through the shared customer package.

The package builder opens every PDF and, for a Brief, requires the order
reference and the validated provider roster hash in the text, so byte stubs
such as b"%PDF-1.4 test" no longer stand in for a brief.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Any

from api.services.customer_package import provider_roster_sha256
from api.services.pdf_writer import PdfBuilder


def brief_pdf(order_reference: str, providers: Iterable[Mapping[str, Any]], *, note: str = "test brief", geography="Southampton") -> bytes:
    roster = provider_roster_sha256(providers)
    pdf = PdfBuilder(title="Territory Opportunity Brief", footer=f"Confidential to order {order_reference}")
    pdf.title_block(
        subtitle=note,
        meta_lines=[f"Prepared for order {order_reference}", f"Scope geography: {geography}", f"Provider roster SHA-256: {roster}"],
    )
    return pdf.build()


def roster(count: int, *, width: int = 0) -> list[dict[str, Any]]:
    return [
        {
            "provider_id": f"P{index:0{width}d}",
            "provider_name": f"Provider {index}",
            "location_ids": [f"L{index:0{width}d}"],
        }
        for index in range(count)
    ]


def plain_pdf(text: str = "test") -> bytes:
    pdf = PdfBuilder(title="Test")
    pdf.paragraph(text)
    return pdf.build()


def digest_pdf(binding, csv_bytes=b"section,date,location_id,name,local_authority,detail,cqc_url\n") -> bytes:
    import csv
    import io
    from datetime import date
    pdf = PdfBuilder(title="Weekly Digest")
    start, end = date.fromisoformat(binding["window_start"]), date.fromisoformat(binding["window_end"])
    pdf.title_block(f"{binding['region']} - issue {binding['issue']} of 4", [f"Order: {binding['order_reference']}",
                                  f"Observation window: {start:%d %B %Y} to {end:%d %B %Y}",
                                  f"Digest content SHA-256: {binding['sha256']}"])
    for row in csv.DictReader(io.StringIO(csv_bytes.decode())):
        pdf.heading(f"Event ID: {row['section']}|{row['location_id']}|{row['date']}", level=2)
        for label, key in (("Name", "name"), ("Local authority", "local_authority"), ("Date", "date"),
                           ("Detail", "detail"), ("CQC source", "cqc_url")):
            pdf.paragraph(f"{label}: {row[key]}")
    return pdf.build()
