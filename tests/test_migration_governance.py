from api.services.rating_states import (
    PUBLISHED_RATING_VALUES,
    RATING_STATES,
    SENTINEL_STATE_BY_TEXT,
    assess_location_rating,
    classify_stored_rating,
    is_published_value,
    normalize_rating_text,
)
from tests.rating_corpus import CORPUS, NON_EMPTY_CORPUS
from tools.check_migration_governance import check_governance


def test_the_rating_classification_authority_is_behavioural_over_the_shared_corpus():
    """One authority, checked by behaviour rather than by parsing source text.

    The reviewed revision asserted on the *text* of migration 061 (parsing its
    ``WHEN src.normalized IN (...) THEN '<state>'`` branches) and on the text of
    ``incremental_update.py``. Source text is not behaviour: it does not prove
    what any value classifies as, and it moves when a file is reformatted.

    The SQL half of the authority is checked where the SQL actually runs --
    ``tests/integration/test_migration_061_rating_state.py`` executes migration
    061 against real PostgreSQL and drives both Python classifiers over this same
    corpus, failing on any value-for-value disagreement. What remains here is the
    database-free half: the corpus itself, classified through production code.
    """

    assert CORPUS, "the shared corpus must not be empty"
    assert PUBLISHED_RATING_VALUES, "no published rating values to compare against"

    disagreements: list[tuple[str | None, str, str]] = []
    for value in NON_EMPTY_CORPUS:
        payload_state = assess_location_rating(
            {"currentRatings": {"overall": {"rating": value}}}
        ).state
        stored_state = classify_stored_rating(value)[0]
        if payload_state != stored_state:
            disagreements.append((value, payload_state, stored_state))

    assert disagreements == [], (
        "payload classifier and stored classifier disagree (value, payload, stored): "
        f"{disagreements}"
    )


def test_only_published_ratings_are_ever_classified_as_rated():
    """'rated' is the published allow-list, and nothing else (FIX 4).

    Every sentinel must map to its sentinel state, and any other unrecognised
    text must come back ``'unknown'`` -- never ``'rated'``, which would assert a
    rating CQC never published.
    """

    for value in CORPUS:
        state, _ = classify_stored_rating(value)
        assert state in RATING_STATES, value

        if state == "rated":
            assert normalize_rating_text(value) in PUBLISHED_RATING_VALUES, value

    for text, expected_state in SENTINEL_STATE_BY_TEXT.items():
        assert expected_state != "rated"
        assert text not in PUBLISHED_RATING_VALUES
        assert classify_stored_rating(text) == (expected_state, None)


def test_the_sentinel_vocabulary_is_shared_by_the_migration_and_python():
    """Every sentinel is classified by behaviour, and none is a rating.

    ``test_backfill_is_a_no_op_on_the_second_run`` and
    ``test_payload_classifier_and_the_executed_migration_agree_value_for_value``
    (both in ``tests/integration/test_migration_061_rating_state.py``) prove the
    same property against the executed SQL; this is the database-free guard that
    the vocabulary the two sides share has not grown a rating.
    """

    assert set(SENTINEL_STATE_BY_TEXT.values()) <= RATING_STATES
    assert not (set(SENTINEL_STATE_BY_TEXT) & set(PUBLISHED_RATING_VALUES))
    assert all(not is_published_value(state) for state in SENTINEL_STATE_BY_TEXT.values())


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
