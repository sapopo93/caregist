import re
from pathlib import Path

from api.services.rating_states import (
    NOT_APPLICABLE,
    NOT_PUBLISHED,
    NOT_YET_INSPECTED,
    PUBLISHED_RATING_VALUES,
    SENTINEL_STATE_BY_TEXT,
    UNRATED,
)
from tools.check_migration_governance import check_governance

MIGRATION_061 = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "061_provider_rating_state.sql"
)

# WHEN src.normalized IN (<values>) THEN '<state>'
_BRANCH = re.compile(
    r"WHEN\s+src\.normalized\s+IN\s*\(([^)]*)\)\s*THEN\s+'([a-z_]+)'", re.IGNORECASE
)


def _sql_without_comments() -> str:
    """Migration 061 with its ``--`` commentary stripped.

    The prose deliberately *quotes* the removed ``ELSE 'rated'`` catch-all, so
    assertions about the executable classification must ignore comments.
    """

    return "\n".join(
        line.split("--", 1)[0] for line in MIGRATION_061.read_text(encoding="utf-8").splitlines()
    )


def _sql_vocabulary() -> dict[str, set[str]]:
    """Parse the per-state IN-lists out of migration 061.

    This is the SQL half of the rating-classification authority.  The Python
    half is ``api/services/rating_states.py``; the two must classify every
    stored value identically or a value can be ``rated`` in one and not the
    other (the FIX 4 finding).
    """
    sql = _sql_without_comments()
    groups: dict[str, set[str]] = {}
    for raw_values, state in _BRANCH.findall(sql):
        groups[state] = {
            value.strip().strip("'") for value in raw_values.split(",") if value.strip()
        }
    return groups


def _python_vocabulary() -> dict[str, set[str]]:
    """The Python half of the same authority, grouped the way SQL groups it."""

    groups: dict[str, set[str]] = {"rated": set(PUBLISHED_RATING_VALUES)}
    for text, state in SENTINEL_STATE_BY_TEXT.items():
        groups.setdefault(state, set()).add(text)
    return groups


def test_migration_061_rating_vocabulary_is_the_python_authority():
    """The SQL branches must equal the Python vocabulary, state by state."""

    sql_groups = _sql_vocabulary()

    assert sql_groups, "migration 061 no longer classifies with IN-lists"
    assert set(sql_groups) == {
        "rated",
        NOT_YET_INSPECTED,
        NOT_PUBLISHED,
        UNRATED,
        NOT_APPLICABLE,
    }
    assert sql_groups["rated"] == set(PUBLISHED_RATING_VALUES)
    for state in (NOT_YET_INSPECTED, NOT_PUBLISHED, UNRATED, NOT_APPLICABLE):
        assert sql_groups[state] == {
            text for text, mapped in SENTINEL_STATE_BY_TEXT.items() if mapped == state
        }, state
    assert _python_vocabulary() == sql_groups


def test_migration_061_never_classifies_a_sentinel_as_rated():
    """No sentinel text may appear in the 'rated' branch."""

    published = _sql_vocabulary()["rated"]

    assert published == set(PUBLISHED_RATING_VALUES)
    for sentinel_text in SENTINEL_STATE_BY_TEXT:
        assert sentinel_text not in published


def test_migration_061_unrecognised_values_fall_back_to_unknown_not_rated():
    """There must be no `ELSE 'rated'` catch-all asserting an unobserved rating."""

    sql = _sql_without_comments()

    assert re.search(r"ELSE\s+'unknown'", sql, re.IGNORECASE)
    assert not re.search(r"ELSE\s+'rated'", sql, re.IGNORECASE)


def test_governance_rejects_prisma_db_push(tmp_path):
    (tmp_path / "script.sh").write_text("prisma db push\n", encoding="utf-8")

    findings = check_governance(tmp_path)

    assert any(f.rule == "no_prisma_db_push" for f in findings)


def test_governance_rejects_destructive_migration_without_approval(tmp_path, monkeypatch):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_bad.sql").write_text("ALTER TABLE users DROP COLUMN name;\n", encoding="utf-8")
    down = migrations / "down"
    down.mkdir()
    (down / "036_bad.down.sql").write_text("ALTER TABLE users ADD COLUMN name text;\n", encoding="utf-8")
    monkeypatch.delenv("APPROVED_DESTRUCTIVE", raising=False)

    findings = check_governance(tmp_path)

    assert any(f.rule == "destructive_sql_requires_approval" for f in findings)


def test_governance_accepts_only_the_frozen_047_destructive_migration(tmp_path, monkeypatch):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "047_expand_analytics_provider_reference.sql").write_text(
        "ALTER TABLE analytics_events ALTER COLUMN provider_id TYPE TEXT;\n",
        encoding="utf-8",
    )
    down = migrations / "down"
    down.mkdir()
    (down / "047_expand_analytics_provider_reference.down.sql").write_text(
        "ALTER TABLE analytics_events ALTER COLUMN provider_id TYPE VARCHAR(20);\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APPROVED_DESTRUCTIVE", raising=False)

    assert check_governance(tmp_path) == []


def test_governance_requires_down_migration_for_numbered_sql(tmp_path):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_additive.sql").write_text("CREATE TABLE demo (id bigint);\n", encoding="utf-8")

    findings = check_governance(tmp_path)

    assert any(f.rule == "missing_down_migration" for f in findings)


def test_governance_accepts_additive_reversible_migration(tmp_path):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_additive.sql").write_text("CREATE TABLE demo (id bigint);\n", encoding="utf-8")
    down = migrations / "down"
    down.mkdir()
    (down / "036_additive.down.sql").write_text("DROP TABLE IF EXISTS demo;\n", encoding="utf-8")

    assert check_governance(tmp_path) == []


def test_governance_rejects_duplicate_migration_numbers(tmp_path):
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "036_first.sql").write_text("CREATE TABLE first_demo (id bigint);\n", encoding="utf-8")
    (migrations / "036_second.sql").write_text("CREATE TABLE second_demo (id bigint);\n", encoding="utf-8")
    down = migrations / "down"
    down.mkdir()
    (down / "036_first.down.sql").write_text("DROP TABLE IF EXISTS first_demo;\n", encoding="utf-8")
    (down / "036_second.down.sql").write_text("DROP TABLE IF EXISTS second_demo;\n", encoding="utf-8")

    findings = check_governance(tmp_path)

    assert any(f.rule == "duplicate_migration_number" for f in findings)
