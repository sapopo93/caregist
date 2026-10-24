"""Resolved-current-rating contract against the frozen 22 Oct 2026 audit sample.

Fixtures: tests/fixtures/rating_audit_2026_10_22.json, frozen from
artifacts/rating-audit/2026-10-22 by
artifacts/report-readiness/2026-10-24/build_rating_fixtures.py.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from api.services.rating_resolver import (
    CURRENT,
    INHERITED,
    NONE,
    SOURCE_API,
    SOURCE_FILE,
    SOURCE_WEBSITE,
    UNRESOLVED,
    RatingEvidence,
    canonical_rating,
    evidence_from_provider_row,
    resolve_rating,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "rating_audit_2026_10_22.json").read_text()
)
FILE_EDITION = date.fromisoformat(FIXTURE["file_edition_date"])
BY_ID = {f["id"]: f for f in FIXTURE["fixtures"]}


def _d(text):
    return date.fromisoformat(text) if text else None


def _evidence(f, *, with_website=False):
    out = [
        RatingEvidence(
            source=SOURCE_API,
            value=canonical_rating(f["api_value"]),
            publication_date=_d(f["api_publication_date"]),
            raw_value=f["api_value"],
        )
    ]
    if f["file_value"]:
        out.append(
            RatingEvidence(
                source=SOURCE_FILE,
                value=canonical_rating(f["file_value"]),
                publication_date=_d(f["file_publication_date"]),
                inherited_flag=f["file_inherited_flag"],
                source_sha256=f["file_sha256"],
                edition_date=FILE_EDITION,
                raw_value=f["file_value"],
            )
        )
    if with_website and f["website_value"]:
        out.append(
            RatingEvidence(
                source=SOURCE_WEBSITE,
                value=canonical_rating(f["website_value"]),
                publication_date=_d(f["website_publication_date"]),
                inherited_flag=f["website_inherited"],
                observed_on=_d(f["website_observed_on"]),
            )
        )
    return out


def _resolve(f, **kw):
    return resolve_rating(_evidence(f, **kw), registration_date=_d(f["registration_date"]))


FILE_BACKED = [f for f in FIXTURE["fixtures"] if f["stratum"].startswith("file-backed")]
CONFLICTS = [f for f in FIXTURE["fixtures"] if f["stratum"] == "conflict"]
UNRATED = [f for f in FIXTURE["fixtures"] if f["stratum"] == "unrated"]


def test_frozen_sample_shape():
    assert (len(FILE_BACKED), len(CONFLICTS), len(UNRATED)) == (20, 5, 5)
    assert len(BY_ID) == 30


@pytest.mark.parametrize("f", FILE_BACKED, ids=lambda f: f["id"])
def test_file_backed_fixtures_keep_file_value_date_and_provenance(f):
    r = _resolve(f)
    assert r.value == f["file_value"]
    assert r.source == SOURCE_FILE
    assert r.publication_date == _d(f["file_publication_date"])
    out = r.to_dict()
    assert out["file_sha256"] == f["file_sha256"]
    assert out["file_edition_date"] == FIXTURE["file_edition_date"]
    assert out["api_value"] is None
    expected = INHERITED if f["id"] == "1-16491295796" else CURRENT
    assert r.status == expected


def test_tillingham_inherited_is_qualified_not_a_current_inspection():
    r = _resolve(BY_ID["1-16491295796"])
    assert r.status == INHERITED
    assert r.displayable and not r.is_current


@pytest.mark.parametrize(
    "location_id,expected",
    [
        ("1-152721284", "Requires improvement"),  # St Stephens: API Good 2019 vs file RI 2026
        ("1-390976877", "Requires improvement"),  # Althorp Grange: API Inadequate 2024 vs RI 2025
        ("1-552527797", "Requires improvement"),  # Chesser: API Good 2016 vs RI 2025
    ],
)
def test_older_api_value_cannot_override_newer_file_rating(location_id, expected):
    f = BY_ID[location_id]
    r = _resolve(f)
    assert (r.status, r.value, r.source) == (CURRENT, expected, SOURCE_FILE)
    assert r.value == f["website_value"]
    assert r.to_dict()["api_value"] == f["api_value"]  # both values kept


def test_irchester_inherited_api_value_does_not_silently_win():
    r = _resolve(BY_ID["1-22160036426"])
    assert r.status == UNRESOLVED
    assert r.value is None or not r.displayable
    assert r.to_dict()["value"] is None


def test_check_house_conflict_is_unresolved_and_omitted():
    r = _resolve(BY_ID["1-19886383752"])
    assert r.status == UNRESOLVED
    out = r.to_dict()
    assert out["value"] is None and out["source"] is None
    assert out["api_value"] == "Outstanding" and out["file_value"] == "Good"


@pytest.mark.parametrize("f", UNRATED, ids=lambda f: f["id"])
def test_unrated_fixtures_resolve_to_none(f):
    r = _resolve(f)
    assert r.status == NONE and r.value is None and not r.displayable


def test_inspected_but_not_rated_sentinel_is_kept_but_never_chosen():
    f = BY_ID["1-5588555895"]
    ev = [RatingEvidence(source=SOURCE_API, value=canonical_rating("Inspected but not rated"),
                         raw_value="Inspected but not rated")]
    r = resolve_rating(ev, registration_date=_d(f["registration_date"]))
    assert r.status == NONE
    assert r.to_dict()["api_raw_value"] == "Inspected but not rated"


def test_post_snapshot_website_rating_is_visibly_newer_than_file_edition():
    """Chestnuts: file Inadequate 25 Sep 2025; CQC page RI 13 Oct 2026."""
    f = BY_ID["1-125730630"]
    without = _resolve(f)
    assert (without.status, without.value, without.newer_than_file_edition) == (
        CURRENT, "Inadequate", False,
    )
    with_obs = _resolve(f, with_website=True)
    assert (with_obs.status, with_obs.value, with_obs.source) == (
        CURRENT, "Requires improvement", SOURCE_WEBSITE,
    )
    assert with_obs.newer_than_file_edition is True
    assert with_obs.publication_date == date(2026, 10, 13)


def test_check_house_website_observation_resolves_as_inherited_not_current():
    """The page shows only the inherited 8 Jun 2018 Outstanding (REPORT.md exceptions)."""
    f = BY_ID["1-19886383752"]
    ev = _evidence(f) + [
        RatingEvidence(
            source=SOURCE_WEBSITE, value="Outstanding", publication_date=date(2018, 6, 8),
            inherited_flag=True, observed_on=_d(f["website_observed_on"]),
        )
    ]
    r = resolve_rating(ev, registration_date=_d(f["registration_date"]))
    assert (r.status, r.value) == (INHERITED, "Outstanding")
    assert not r.is_current


def test_website_observations_agree_with_resolution_where_the_page_shows_a_current_rating():
    """Where the page shows a current numerical rating, resolution must not contradict it."""
    contradictions = []
    for f in FIXTURE["fixtures"]:
        if not f["website_value"] or f["website_inherited"]:
            continue
        r = _resolve(f)
        if r.displayable and r.value != f["website_value"]:
            contradictions.append(f["id"])
    # Only the post-snapshot Chestnuts update remains, and it is a freshness gap.
    assert contradictions == ["1-125730630"]


def test_undated_conflict_is_unresolved():
    ev = [
        RatingEvidence(source=SOURCE_API, value="Good", publication_date=None),
        RatingEvidence(source=SOURCE_FILE, value="Inadequate", publication_date=date(2026, 1, 1)),
    ]
    assert resolve_rating(ev, registration_date=None).status == UNRESOLVED


def test_same_date_conflict_is_unresolved():
    ev = [
        RatingEvidence(source=SOURCE_API, value="Good", publication_date=date(2026, 1, 1)),
        RatingEvidence(source=SOURCE_FILE, value="Inadequate", publication_date=date(2026, 1, 1)),
    ]
    assert resolve_rating(ev, registration_date=None).status == UNRESOLVED


def test_agreeing_channels_choose_the_newest_date():
    ev = [
        RatingEvidence(source=SOURCE_API, value="Good", publication_date=date(2025, 1, 1)),
        RatingEvidence(source=SOURCE_FILE, value="Good", publication_date=date(2025, 3, 1)),
    ]
    r = resolve_rating(ev, registration_date=date(2020, 1, 1))
    assert (r.status, r.source, r.publication_date) == (CURRENT, SOURCE_FILE, date(2025, 3, 1))


def test_unfamiliar_text_is_not_a_rating():
    assert canonical_rating("Suspended") is None
    assert canonical_rating("  requires   IMPROVEMENT ") == "Requires improvement"


def test_evidence_from_provider_row_reads_migration_068_columns():
    row = {
        "overall_rating": "Good", "last_published_rating_date": date(2019, 7, 16),
        "file_overall_rating": "Requires improvement", "file_overall_rating_date": date(2026, 5, 20),
        "file_rating_source_sha256": "abc", "registration_date": date(2011, 1, 26),
    }
    r = resolve_rating(evidence_from_provider_row(row, file_edition_date=FILE_EDITION),
                       registration_date=row["registration_date"])
    assert (r.value, r.source, r.to_dict()["file_sha256"]) == ("Requires improvement", SOURCE_FILE, "abc")
