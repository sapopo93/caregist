"""Contract tests for the dated Radar sample builder (artifacts/product-polish).

The builder runs at module level and writes relative to its own directory, so the
tests drive it as a subprocess with explicit output paths. That keeps the real
sample directory (artifacts/product-polish/radar-pilot-sample) untouched and
exercises the CLI shape callers actually use.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
BUILDER = REPO / "artifacts/product-polish/build_radar_pilot_sample.py"

PROVENANCE = {
    "territory": "Kent",
    "edition_date": "2026-08-04",
    "window_start": "2026-07-29",
    "window_end": "2026-08-04",
    "source_file": "2026-08-04_HSCA_Active_Locations.ods",
    "parsed_rows": 57009,
    "territory_rows": 1675,
    "source_page": "https://www.cqc.org.uk/about-us/transparency/using-cqc-data",
}


def digest(tmp_path: Path, events, territory="Kent") -> Path:
    payload = {"provenance": {**PROVENANCE, "territory": territory}, "events": events}
    path = tmp_path / "digest.json"
    path.write_text(json.dumps(payload))
    return path


def run(tmp_path: Path, src: Path):
    return subprocess.run(
        [sys.executable, str(BUILDER), str(src), str(tmp_path / "out.pdf"), str(tmp_path / "out.html")],
        capture_output=True,
        text=True,
        cwd=REPO,
    )


NEW_REG = {
    "event_type": "new_registration",
    "provider_name": "Melvyn & Jan John",
    "location_name": "Melvyn & Jan John",
    "postcode": "CT14 8JL",
    "effective_date": "2026-07-30",
}
RATING = {
    "event_type": "rating_published",
    "provider_name": "Purelake (Chase) Limited",
    "location_name": "The Chase",
    "effective_date": "2026-07-30",
    "new_value": {"rating": "Inadequate"},
}


def test_territory_is_data_driven_not_hardcoded(tmp_path):
    """A territory must never be printed from a constant."""
    result = run(tmp_path, digest(tmp_path, [NEW_REG, RATING], territory="West Sussex"))
    assert "West Sussex" in result.stdout
    html = (tmp_path / "out.html").read_text()
    assert "West Sussex weekly digest" in html
    assert "Gloucestershire" not in html


def test_every_event_is_rendered_with_its_real_count(tmp_path):
    events = [NEW_REG, RATING, {**RATING, "provider_name": "Dover House (GC) Limited", "new_value": {"rating": "Requires improvement"}}]
    run(tmp_path, digest(tmp_path, events))
    html = (tmp_path / "out.html").read_text()

    # counts, not prose: 1 new registration + 2 ratings
    assert '<div class="number">1</div>' in html
    assert '<div class="number">2</div>' in html
    for event in events:
        assert event["provider_name"] in html
    assert "Inadequate" in html and "Requires improvement" in html
    assert "2026-07-30" in html


def test_unsupported_event_type_fails_loudly(tmp_path):
    """Silently dropping an event type would under-report the register."""
    result = run(tmp_path, digest(tmp_path, [{**RATING, "event_type": "location_closed"}]))
    assert result.returncode != 0
    assert "location_closed" in (result.stdout + result.stderr)
    assert not (tmp_path / "out.html").exists()


def test_html_is_always_written_even_without_reportlab(tmp_path):
    """HTML is the always-available output; the PDF path is optional."""
    result = run(tmp_path, digest(tmp_path, [NEW_REG]))
    assert (tmp_path / "out.html").exists(), "HTML must be written regardless of reportlab"
    try:
        import reportlab  # noqa: F401
    except ImportError:
        # Honest degraded path: say the PDF was not produced rather than imply it was.
        assert result.returncode != 0
        assert "PDF not produced" in (result.stdout + result.stderr)
        assert not (tmp_path / "out.pdf").exists()
    else:
        assert result.returncode == 0
        assert (tmp_path / "out.pdf").exists()


def test_defaults_still_point_at_the_gloucestershire_sample():
    """Parametrising the builder must not silently move the existing default."""
    source = BUILDER.read_text()
    assert "2026-08-04-fresh-weekly-digest-gloucestershire.json" in source
    assert "caregist-radar-gloucestershire-dated-format-sample.pdf" in source


@pytest.mark.parametrize("field", ["provider_name", "effective_date"])
def test_missing_event_field_is_not_silently_blanked(tmp_path, field):
    """A malformed event must error, not render an empty cell."""
    broken = {k: v for k, v in RATING.items() if k != field}
    result = run(tmp_path, digest(tmp_path, [broken]))
    assert result.returncode != 0
    assert field in (result.stdout + result.stderr)
