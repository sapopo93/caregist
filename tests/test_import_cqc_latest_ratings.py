import pytest
import zipfile

from tools.import_cqc_latest_ratings import overall_ratings

HEADER = ["Location ID", "Service / Population Group", "Domain", "Latest Rating", "Publication Date"]


def _ods(path, rows):
    def cell(v):
        return f'<table:table-cell><text:p>{v}</text:p></table:table-cell>'
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


def test_only_published_overall_rows_and_ambiguity_skipped(tmp_path):
    p = tmp_path / "r.ods"
    _ods(p, [
        ["1-A", "Overall", "Overall", "Inadequate", "01/09/2026"],
        ["1-A", "Residential", "Safe", "Good", "01/09/2026"],
        ["1-B", "Overall", "Overall", "Not Rated", "01/09/2026"],
        ["1-C", "Overall", "Overall", "Good", "01/09/2026"],
        ["1-C", "Overall", "Overall", "Inadequate", "01/09/2026"],
    ])
    ratings, ambiguous = overall_ratings(p)
    assert ratings == {"1-A": ("Inadequate", "01/09/2026")}
    assert ambiguous == {"1-C"}


class _Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.statements.append(sql)
        self.conn.on_execute(sql)
        self.rowcount = 3


class _DeadlockOnce:
    """A connection whose first transaction is aborted as a deadlock."""

    def __init__(self):
        self.attempts = 0
        self.statements = []

    def __enter__(self):
        self.attempts += 1
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return _Cursor(self)

    def on_execute(self, sql):
        import psycopg2

        if self.attempts == 1 and sql.startswith("SELECT 1 FROM care_providers"):
            raise psycopg2.errors.DeadlockDetected("deadlock detected")


def test_apply_retries_a_deadlocked_transaction_and_locks_rows_in_id_order(monkeypatch):
    from tools import import_cqc_latest_ratings as importer

    monkeypatch.setattr("psycopg2.extras.execute_values", lambda cur, sql, rows, page_size: None)
    conn, waits = _DeadlockOnce(), []
    n, cleared = importer.apply_with_retry(conn, [("1-A", "Good", None)], None, "sha", "f.ods", sleep=waits.append)
    assert conn.attempts == 2 and waits == [15]
    assert (n, cleared) == (3, 3)
    assert any("ORDER BY id FOR UPDATE" in s for s in conn.statements)


def test_apply_gives_up_after_the_last_attempt(monkeypatch):
    import psycopg2

    from tools import import_cqc_latest_ratings as importer

    class AlwaysDeadlock(_DeadlockOnce):
        def on_execute(self, sql):
            if sql.startswith("SELECT 1 FROM care_providers"):
                raise psycopg2.errors.DeadlockDetected("deadlock detected")

    monkeypatch.setattr("psycopg2.extras.execute_values", lambda cur, sql, rows, page_size: None)
    with pytest.raises(psycopg2.errors.DeadlockDetected):
        importer.apply_with_retry(AlwaysDeadlock(), [], None, "sha", "f.ods", attempts=3, sleep=lambda s: None)
