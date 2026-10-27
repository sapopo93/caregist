"""The ratings importer applies a whole file in one statement, on real Postgres.

Runs the real ``tools.import_cqc_latest_ratings.main`` against a care_providers
table in a throwaway schema (never the migrated one): file values and the
edition date land, a page check survives re-importing the same file but not a
new one, rows absent from a new file lose their file claim, and
``--only-if-newer`` skips an edition production already holds.
"""

from __future__ import annotations

import os
import zipfile
from datetime import date
from urllib.parse import quote

import pytest

psycopg2 = pytest.importorskip("psycopg2")

from tools import import_cqc_latest_ratings as importer  # noqa: E402

# The schema is created and owned by the admin role (CI's test role may not
# create schemas); the importer needs no row-level security, so it uses it too.
DATABASE_URL = os.getenv("CAREGIST_TEST_ADMIN_DATABASE_URL") or os.getenv("CAREGIST_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not os.getenv("CAREGIST_TEST_DATABASE_URL"), reason="CAREGIST_TEST_DATABASE_URL not set")
SCHEMA = "import_ratings_test"
HEADER = ["Location ID", "Service / Population Group", "Domain", "Latest Rating", "Publication Date"]


def _ods(path, rows):
    def cell(v):
        return f"<table:table-cell><text:p>{v}</text:p></table:table-cell>"
    body = "".join(f"<table:table-row>{''.join(cell(c) for c in r)}</table:table-row>" for r in [HEADER, *rows])
    xml = (
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:spreadsheet>'
        f'<table:table table:name="Locations">{body}</table:table></office:spreadsheet></office:body>'
        "</office:document-content>"
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("content.xml", xml)


@pytest.fixture
def db(monkeypatch):
    admin = psycopg2.connect(DATABASE_URL)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE; CREATE SCHEMA {SCHEMA}")
        cur.execute(f"""CREATE TABLE {SCHEMA}.care_providers (
            id text PRIMARY KEY, status text, overall_rating text,
            file_overall_rating text, file_overall_rating_date date, file_rating_edition_date date,
            file_rating_source text, file_rating_source_sha256 text,
            site_check_rating text, site_check_at timestamptz)""")
        cur.execute(f"INSERT INTO {SCHEMA}.care_providers (id, status) VALUES ('1-A','ACTIVE'), ('1-B','ACTIVE'), ('1-C','ACTIVE')")
    sep = "&" if "?" in DATABASE_URL else "?"
    monkeypatch.setenv("DATABASE_URL", f"{DATABASE_URL}{sep}options={quote(f'-csearch_path={SCHEMA}')}")
    yield admin
    with admin.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    admin.close()


def _rows(admin):
    with admin.cursor() as cur:
        cur.execute(f"""SELECT id, file_overall_rating, file_overall_rating_date, file_rating_edition_date,
                               site_check_rating FROM {SCHEMA}.care_providers ORDER BY id""")
        return {r[0]: r[1:] for r in cur.fetchall()}


def test_apply_is_set_based_and_keeps_the_rule_invariants(db, tmp_path):
    first = tmp_path / "first.ods"
    _ods(first, [["1-A", "Overall", "Overall", "Good", "01/09/2026"],
                 ["1-B", "Overall", "Overall", "Inadequate", "15/09/2026"]])
    assert importer.main([str(first), "--edition-date", "2026-10-01", "--apply"]) == 0
    rows = _rows(db)
    assert rows["1-A"] == ("Good", date(2026, 9, 1), date(2026, 10, 1), None)
    assert rows["1-B"][0] == "Inadequate" and rows["1-C"][0] is None

    # A page check survives re-importing the same file...
    with db.cursor() as cur:
        cur.execute(f"UPDATE {SCHEMA}.care_providers SET site_check_rating='Good', site_check_at=now() WHERE id='1-B'")
    assert importer.main([str(first), "--edition-date", "2026-10-01", "--apply"]) == 0
    assert _rows(db)["1-B"][3] == "Good"

    # ...the scheduled run skips an edition already held...
    assert importer.main([str(first), "--edition-date", "2026-10-01", "--apply", "--only-if-newer"]) == 0

    # ...and a new file supersedes the check and drops rows it no longer lists.
    second = tmp_path / "second.ods"
    _ods(second, [["1-B", "Overall", "Overall", "Requires improvement", "10/10/2026"]])
    assert importer.main([str(second), "--edition-date", "2026-10-20", "--apply", "--only-if-newer"]) == 0
    rows = _rows(db)
    assert rows["1-B"] == ("Requires improvement", date(2026, 10, 10), date(2026, 10, 20), None)
    assert rows["1-A"] == (None, None, None, None)
