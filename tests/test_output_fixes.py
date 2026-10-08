"""Wave 3 output fixes for the Territory Brief, outbound emails and price copy.

Each test pins one gap from the quality review and failed on
``claude/acceptance-caregist`` before the fix.
"""

from __future__ import annotations

import csv
import io
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from api.services.territory_brief import (
    MIN_SHORTLIST,
    OGL_ATTRIBUTION,
    PurchaseContext,
    brief_to_csv,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_render import render_brief_pdf

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "territory_brief"
GENERATED = datetime(2026, 10, 8, tzinfo=timezone.utc)


def _brief(name: str, target: int = 30):
    return generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": name, "window_days": 365, "shortlist_target": target},
        PurchaseContext(order_reference="wave3", generated_at=GENERATED, terms_version="wave3"),
        locations_source=FIX / "locations_detail.jsonl",
        providers_source=FIX / "providers_detail.jsonl",
    )


def _pdf_text(brief, tmp_path: Path) -> str:
    path = tmp_path / "brief.pdf"
    path.write_bytes(render_brief_pdf(brief))
    return subprocess.run(
        ["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True
    ).stdout


def _csv_rows(brief) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(brief_to_csv(brief))))


@pytest.fixture(scope="module")
def southampton():
    return _brief("Southampton")


@pytest.fixture(scope="module")
def isle_of_wight():
    # The fixture yields 8 organisations here, below the code floor of 10.
    return _brief("Isle of Wight", target=50)


# H1 -------------------------------------------------------------------------


def test_pdf_states_the_real_generation_date_and_the_source_edition(southampton, tmp_path):
    front = _pdf_text(southampton, tmp_path).split("2. Ranked opportunity shortlist")[0]
    assert "generated 08 October 2026" in front
    assert "generated 18 February 2026" not in front
    assert southampton.executive_summary["date_generated"] == "2026-10-08"
    assert southampton.executive_summary["source_edition"] == southampton.as_of_date.isoformat()
    assert f"Source edition {southampton.as_of_date.isoformat()}" in re.sub(r"\s+", " ", front)


# H2 -------------------------------------------------------------------------


def test_cqc_record_links_use_the_public_cqc_location_page(southampton, tmp_path):
    rows = _csv_rows(southampton)
    for row in rows:
        assert row["cqc_record_url"] == f"https://www.cqc.org.uk/location/{row['cqc_location_id']}"
    text = _pdf_text(southampton, tmp_path)
    assert "api.service.cqc.org.uk" not in text
    assert "https://www.cqc.org.uk/location/" in text


# H8 -------------------------------------------------------------------------


def test_csv_carries_open_government_licence_on_every_row(southampton):
    rows = _csv_rows(southampton)
    assert rows
    assert all(row["licence"] == OGL_ATTRIBUTION for row in rows)


# C2 -------------------------------------------------------------------------


def test_short_brief_carries_a_plain_shortfall_notice_in_pdf_and_csv(isle_of_wight, tmp_path):
    shortlisted = len(isle_of_wight.shortlist)
    assert shortlisted < MIN_SHORTLIST  # floor unchanged; the brief is not padded
    notice = isle_of_wight.executive_summary["shortfall_notice"]
    assert notice and f"{shortlisted} organisation(s)" in notice and str(MIN_SHORTLIST) in notice

    pdf = re.sub(r"\s+", " ", _pdf_text(isle_of_wight, tmp_path))
    assert re.sub(r"\s+", " ", notice) in pdf

    rows = _csv_rows(isle_of_wight)
    assert len(rows) == shortlisted
    assert all(row["shortlist_notice"] == notice for row in rows)


def test_full_brief_has_no_shortfall_notice(southampton, tmp_path):
    assert len(southampton.shortlist) >= MIN_SHORTLIST
    assert southampton.executive_summary["shortfall_notice"] is None
    assert "Shortfall" not in _pdf_text(southampton, tmp_path)
    assert all(row["shortlist_notice"] == "" for row in _csv_rows(southampton))


# M3 -------------------------------------------------------------------------


def test_executive_text_points_at_the_right_sections(southampton, tmp_path):
    text = re.sub(r"\s+", " ", _pdf_text(southampton, tmp_path))
    assert "(see section 6)" in text and "(see section 5)" not in text
    assert "sections 1-7 are the executive brief" in text
    assert "Strongest areas of movement" not in text
    assert "Highest-ranked organisations:" in text
    # A local-authority brief has one parent region, so the table would only
    # repeat the territory.
    assert len(southampton.territory_insights["activity_by_sub_area"]) == 1
    assert "Activity by sub-area" not in text
