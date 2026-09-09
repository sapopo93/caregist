"""Pack-generation integration test against a real CQC register subset.

The fixture (``tests/fixtures/territory_brief/``) is a field-trimmed extract of
the public CQC register for three South-coast local authorities (Isle of Wight,
Portsmouth, Southampton). It is real public data under the Open Government
Licence, reduced to the fields the generator reads so it can live in the repo.

This test generates the complete artefact and inspects the ranking, reasons,
CSV, JSON and the rendered PDF (page count, structure, encoding), not just that
files were produced.
"""

from __future__ import annotations

import csv
import io
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from api.services.territory_brief import (
    PurchaseContext,
    brief_to_csv,
    generate_territory_opportunity_brief,
)
from api.services.territory_brief_render import render_brief_pdf

FIXTURE = Path(__file__).parent / "fixtures" / "territory_brief"
LOCATIONS = FIXTURE / "locations_detail.jsonl"
PROVIDERS = FIXTURE / "providers_detail.jsonl"

pytestmark = pytest.mark.skipif(
    not LOCATIONS.exists(), reason="territory_brief fixture not present"
)

CONTEXT = PurchaseContext(
    order_reference="itest-0001",
    generated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    terms_version="itest",
)


@pytest.fixture(scope="module")
def brief():
    return generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "Southampton", "window_days": 365, "shortlist_target": 30},
        CONTEXT,
        locations_source=LOCATIONS,
        providers_source=PROVIDERS,
    )


def test_shortlist_is_populated_and_in_promised_band(brief):
    assert 10 <= len(brief.shortlist) <= 50
    assert brief.considered_locations >= len(brief.shortlist)
    assert brief.territory_locations > len(brief.shortlist)


def test_ranks_are_dense_and_ordered(brief):
    ranks = [o.rank for o in brief.shortlist]
    assert ranks == list(range(1, len(ranks) + 1))
    scores = [o.score for o in brief.shortlist]
    assert scores == sorted(scores, reverse=True)


def test_every_org_has_reason_evidence_and_identifiers(brief):
    for o in brief.shortlist:
        assert o.reason.strip() and len(o.reason) > 40
        assert o.evidence, f"{o.organisation_name} has no evidence"
        assert o.location_id.startswith("1-")
        assert o.provider_id
        assert o.organisation_name and o.location_name
        for e in o.evidence:
            assert e["effective_date"]
            assert brief.window_start.isoformat() <= e["effective_date"] <= brief.window_end.isoformat()


def test_territory_data_is_populated(brief):
    ins = brief.territory_insights
    assert sum(ins["events_by_type"].values()) >= len(brief.shortlist)
    assert ins["service_type_mix"]
    assert brief.executive_summary["opportunity_set_size"] == brief.considered_locations
    # window is anchored to the newest date in this fixture subset
    assert brief.as_of_date.isoformat().startswith("2026-02")
    assert brief.window_end == brief.as_of_date


def test_csv_round_trips_and_matches_shortlist(brief):
    rows = list(csv.DictReader(io.StringIO(brief_to_csv(brief))))
    assert len(rows) == len(brief.shortlist)
    assert rows[0]["organisation"] == brief.shortlist[0].organisation_name
    for row in rows:
        assert row["reason"].strip()
        assert row["cqc_record_url"].startswith("https://api.service.cqc.org.uk/")


def test_determinism_on_real_data():
    a = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "Isle of Wight", "window_days": 180},
        CONTEXT, locations_source=LOCATIONS, providers_source=PROVIDERS,
    )
    b = generate_territory_opportunity_brief(
        {"kind": "local_authority", "name": "isle of wight", "window_days": 180},
        CONTEXT, locations_source=LOCATIONS, providers_source=PROVIDERS,
    )
    assert [o.to_json() for o in a.shortlist] == [o.to_json() for o in b.shortlist]
    assert render_brief_pdf(a) == render_brief_pdf(b)


def test_rendered_pdf_is_valid_and_well_formed(brief, tmp_path):
    pdf_bytes = render_brief_pdf(brief)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    out = tmp_path / "brief.pdf"
    out.write_bytes(pdf_bytes)

    pdftotext = _which("pdftotext")
    if pdftotext:
        text = subprocess.run(
            [pdftotext, "-layout", str(out), "-"], capture_output=True, text=True, check=True
        ).stdout
        # executive brief structure
        for marker in [
            "Territory Opportunity Brief",
            "1. Executive summary",
            "2. Ranked opportunity shortlist",
            "4. Territory insights",
            "5. Recommended next actions",
            "6. Methodology and data notes",
            "7. Limitations and disclaimer",
            "Appendix A. Reason and evidence",
            "Open Government Licence",
        ]:
            assert marker in text, f"missing section: {marker!r}"
        # every shortlisted organisation appears in the appendix
        for o in brief.shortlist:
            assert o.organisation_name in text
        # no obvious encoding corruption / raw json / debug
        assert "�" not in text
        assert "{'" not in text and '{"' not in text
        assert "Traceback" not in text
        pages = text.count("\f") + 1
        assert pages >= 5, f"expected a multi-page brief, got {pages}"

    pdfinfo = _which("pdfinfo")
    if pdfinfo:
        info = subprocess.run([pdfinfo, str(out)], capture_output=True, text=True, check=True).stdout
        assert "Territory Opportunity Brief" in info


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)
