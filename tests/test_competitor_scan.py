import csv
import io
import re
import zlib
from datetime import date
from unittest.mock import patch

import pytest

from api.services.competitor_scan import (
    INDEPENDENCE_STATEMENT,
    ScanDisabled,
    ScanInputError,
    build_competitor_scan,
    export_row_matches,
    haversine_km,
    render_scan_pdf,
    scan_to_csv,
    validate_inputs,
)

ORIGIN = (51.4666, -2.5992)


def _dir_row(lid, distance, **kw):
    row = {"id": lid, "name": f"Home {lid}", "postcode": "BS6 6BH", "distance_km": distance,
           "number_of_beds": 30, "registration_date": date(2015, 1, 1), "overall_rating": None,
           "last_published_rating_date": None, "file_overall_rating": None, "file_overall_rating_date": None,
           "file_rating_source": None, "file_rating_source_sha256": None}
    row.update(kw)
    return row


def _exp(lid, lat=51.4670, lon=-2.5990, **kw):
    row = {"locationId": lid, "name": f"Home {lid}", "postalCode": f"BS{lid}", "careHome": "Y",
           "onspdLatitude": lat, "onspdLongitude": lon, "registrationStatus": "Registered",
           "registrationDate": "2010-01-01", "dormancy": "N", "relationships": [],
           "gacServiceTypes": [{"description": "Care home service without nursing"}]}
    row.update(kw)
    return row


def _scan(directory_rows, export_rows, **kw):
    args = dict(
        postcode="bs6 6bh", radius_km=5, service_type="care_home", origin=ORIGIN, origin_method="test",
        directory_rows=directory_rows, export_rows=export_rows, export_window_end=date(2026, 10, 16),
        file_edition_date=date(2026, 10, 2),
        data_as_at={"CQC API location export retrieved": "2026-10-20", "CQC ratings file edition": "2026-10-02"},
    )
    args.update(kw)
    with patch("api.config.settings.competitor_scan_enabled", True):
        return build_competitor_scan(**args)


def test_flag_defaults_off_and_refuses():
    from api.config import Settings

    assert Settings.model_fields["competitor_scan_enabled"].default is False
    with pytest.raises(ScanDisabled):
        build_competitor_scan(
            postcode="BS6 6BH", radius_km=5, service_type="care_home", origin=ORIGIN, origin_method="t",
            directory_rows=[], export_rows=[], export_window_end=date(2026, 10, 16),
            file_edition_date=None, data_as_at={},
        )


@pytest.mark.parametrize("args", [("", 5, "care_home"), ("BS6 6BH", 0.1, "care_home"),
                                  ("BS6 6BH", 80, "care_home"), ("BS6 6BH", 5, "hospital"),
                                  ("BS6 6BH", "x", "care_home")])
def test_input_validation(args):
    with pytest.raises(ScanInputError):
        validate_inputs(*args)


def test_haversine_and_service_matching():
    assert haversine_km(51.0, 0.0, 51.0, 0.0) == 0
    assert 110 < haversine_km(51.0, 0.0, 52.0, 0.0) < 112
    home = _exp("1", gacServiceTypes=[{"description": "Care home service with nursing"}])
    assert export_row_matches(home, "care_home") and export_row_matches(home, "care_home_nursing")
    assert not export_row_matches(home, "care_home_residential") and not export_row_matches(home, "homecare")


def test_ratings_are_resolved_not_api_first():
    scan = _scan([
        _dir_row("a", 0.4, overall_rating="Good", last_published_rating_date=date(2019, 7, 16),
                 file_overall_rating="Requires improvement", file_overall_rating_date=date(2026, 5, 20)),
        _dir_row("b", 0.2, registration_date=date(2024, 10, 21), overall_rating="Outstanding",
                 last_published_rating_date=date(2018, 6, 8), file_overall_rating="Good",
                 file_overall_rating_date=date(2026, 5, 7)),
        _dir_row("c", 1.0, registration_date=date(2023, 7, 26), file_overall_rating="Outstanding",
                 file_overall_rating_date=date(2018, 8, 24)),
    ], [])
    assert [c.location_id for c in scan.competitors] == ["b", "a", "c"]  # by distance
    by_id = {c.location_id: c.rating for c in scan.competitors}
    assert (by_id["a"].status, by_id["a"].value) == ("current", "Requires improvement")
    assert by_id["b"].status == "unresolved"
    assert by_id["c"].status == "inherited"
    assert scan.rating_counts == {
        "Requires improvement": 1, "inherited from a predecessor registration": 1,
        "not shown: CQC sources conflict": 1,
    }
    rows = {r["cqc_location_id"]: r for r in csv.DictReader(io.StringIO(scan_to_csv(scan)))}
    assert rows["b"]["rating"] == "" and rows["b"]["api_rating"] == "Outstanding" and rows["b"]["file_rating"] == "Good"
    assert rows["a"]["rating_publication_date"] == "2026-05-20"


def test_movement_counts_confirmed_closures_only_within_radius_and_window():
    rows = [
        _exp("10", registrationDate="2026-03-01"),  # registration in window
        _exp("11", registrationStatus="Deregistered", deregistrationDate="2026-05-01"),  # closure
        _exp("12", registrationStatus="Deregistered", deregistrationDate="2026-05-01",
             relationships=[{"type": "HSCA Successor", "reason": "New Provider", "relatedLocationId": "13"}]),
        _exp("13", registrationDate="2026-05-02", name="Other"),  # successor registration
        _exp("14", registrationStatus="Deregistered", deregistrationDate="2026-05-01", dormancy="Y"),
        _exp("15", lat=52.5, registrationStatus="Deregistered", deregistrationDate="2026-05-01"),  # far away
        _exp("16", registrationStatus="Deregistered", deregistrationDate="2024-05-01"),  # before window
        _exp("17", careHome="N", gacServiceTypes=[{"description": "Domiciliary care service"}],
             registrationStatus="Deregistered", deregistrationDate="2026-05-01"),  # other type
    ]
    mv = _scan([], rows).movement
    assert mv.registrations == ("10", "13")
    assert mv.confirmed_closures == ("11",)
    assert mv.other_endings == {"dormant": 1, "re_registration": 1}
    assert (mv.window_start, mv.window_end) == (date(2025, 10, 17), date(2026, 10, 16))


def test_pdf_carries_as_at_dates_licence_and_independence_statement():
    scan = _scan([_dir_row("a", 0.4, overall_rating="Good", last_published_rating_date=date(2024, 1, 1))], [])
    pdf = render_scan_pdf(scan)
    text = b"\n".join(zlib.decompress(s) for s in re.findall(rb"stream\n(.*?)\nendstream", pdf, re.S))
    assert b"CQC data as at: 2026-10-20" in text and b"CQC data as at: 2026-10-02" in text
    assert b"Open Government Licence v3.0" in text
    assert INDEPENDENCE_STATEMENT[:40].encode() in text
    assert render_scan_pdf(scan) == pdf  # deterministic


def test_directory_rows_cqc_has_deregistered_are_excluded_and_named():
    scan = _scan([_dir_row("a", 0.4), _dir_row("gone", 0.5)],
                 [_exp("gone", registrationStatus="Deregistered", deregistrationDate="2026-10-14")])
    assert [c.location_id for c in scan.competitors] == ["a"]
    assert scan.excluded_deregistered == ("gone",)


def test_review_finding_6_movement_cutoff_is_the_export_date(tmp_path):
    from tools.report_sources import export_cutoff

    export = tmp_path / "_locations_detail.ndjson"
    export.write_text("")
    rows = [_exp("old", registrationDate="2026-09-01"),
            _exp("late", registrationStatus="Deregistered", deregistrationDate="2026-10-19")]
    (tmp_path / "RECEIPT.json").write_text('{"source_retrieved_at": "2026-10-20T07:41:27+00:00"}')
    cutoff = export_cutoff(export, None, rows)
    assert cutoff == date(2026, 10, 20)  # not the newest registration (2026-09-01)
    mv = _scan([], rows, export_window_end=cutoff).movement
    assert mv.confirmed_closures == ("late",)
    with pytest.raises(SystemExit, match="after its stated cutoff"):
        export_cutoff(export, "2026-10-18", rows)
    (tmp_path / "RECEIPT.json").unlink()
    with pytest.raises(SystemExit, match="cutoff unknown"):
        export_cutoff(export, None, rows)
