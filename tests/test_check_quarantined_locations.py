"""Tests for tools/check_quarantined_locations.py: what counts as found, absent or unknown."""

from __future__ import annotations

from tools import check_quarantined_locations as tool


def test_http_classification_never_treats_an_error_as_absence():
    assert tool.classify_http(200) == tool.FOUND
    assert tool.classify_http(404) == tool.ABSENT
    assert tool.classify_http(403) == tool.UNKNOWN
    assert tool.classify_http(500) == tool.UNKNOWN
    assert tool.classify_http(None) == tool.UNKNOWN


def test_any_source_holding_the_id_makes_it_a_resolve_candidate():
    assert tool.verdict(tool.FOUND, tool.ABSENT, {}) == "resolve_candidate"
    assert tool.verdict(tool.ABSENT, tool.FOUND, {}) == "resolve_candidate"
    assert tool.verdict(tool.ABSENT, tool.ABSENT, {"directory_csv": tool.FOUND}) == "resolve_candidate"


def test_keep_quarantined_needs_both_live_sources_to_say_absent():
    assert tool.verdict(tool.ABSENT, tool.ABSENT, {}) == "keep_quarantined"
    # A ratings file lists rated locations only; its absence changes nothing.
    assert tool.verdict(tool.ABSENT, tool.ABSENT, {"ratings_file": tool.ABSENT}) == "keep_quarantined"


def test_an_unreadable_source_is_inconclusive_not_absent():
    assert tool.verdict(tool.ABSENT, tool.UNKNOWN, {}) == "inconclusive"
    assert tool.verdict(tool.UNKNOWN, tool.UNKNOWN, {}) == "inconclusive"


def test_directory_csv_is_read_past_its_preamble(tmp_path):
    f = tmp_path / "dir.csv"
    f.write_text(
        "CQC directory produced on 22 October 2026\n\n"
        "Name,CQC Location ID (for office use only),Town\n"
        "A,1-111,X\nB,1-222,Y\n"
    )
    assert tool.directory_ids(str(f)) == {"1-111", "1-222"}
