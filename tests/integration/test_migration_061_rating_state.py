"""Real-Postgres proof for the provider rating-state migrations (FIX 4).

The reviewed revision's 061 classified every unrecognised non-empty value as
``'rated'`` (``ELSE 'rated'``). That asserted a rating CQC never published, it
disagreed with the application's own classifier, and re-running it rewrote rows
that ingestion had correctly left ``'unknown'``.

These tests execute the migration SQL as-is (twice where it matters) against a
real Postgres and compare the stored states with
:func:`api.services.rating_states.classify_stored_rating` *and* with the payload
classifier :func:`api.services.rating_states.assess_location_rating`, over the
same corpus (``tests/rating_corpus.py``), so the SQL and both Python entry points
cannot disagree. Skipped unless CAREGIST_TEST_DATABASE_URL is set; see
tests/integration/conftest.py.
"""

from __future__ import annotations

import pytest

from api.services.rating_states import (
    assess_location_rating,
    classify_stored_rating,
    is_published_value,
)
from tests.integration.conftest import MIGRATIONS_DIR, apply_full_schema
from tests.rating_corpus import CORPUS, NON_EMPTY_CORPUS

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio

RATING_STATE_SQL = MIGRATIONS_DIR / "061_provider_rating_state.sql"
LAST_PUBLISHED_SQL = MIGRATIONS_DIR / "062_provider_last_published_rating.sql"

# ``CORPUS`` / ``NON_EMPTY_CORPUS`` come from tests.rating_corpus: one corpus,
# shared with the Python-side corpus test, so the SQL classification and the
# payload classification cannot be checked against different value sets.


async def _seed(conn, values: tuple[str | None, ...], *, prefix: str = "MIG") -> list[str]:
    ids: list[str] = []
    for index, value in enumerate(values):
        location_id = f"{prefix}{index:05d}"
        await conn.execute(
            "INSERT INTO care_providers (id, name, slug, overall_rating) "
            "VALUES ($1, $2, $3, $4)",
            location_id,
            f"Migration probe {index}",
            f"migration-probe-{prefix.lower()}-{index}",
            value,
        )
        ids.append(location_id)
    return ids


async def _run_sql(conn, path) -> None:
    body = path.read_text(encoding="utf-8").strip()
    async with conn.transaction():
        await conn.execute(body)


async def _snapshot(conn) -> dict[str, tuple]:
    rows = await conn.fetch(
        "SELECT id, overall_rating, rating_state, rating_state_source, "
        "last_published_rating, last_published_rating_date "
        "FROM care_providers ORDER BY id"
    )
    return {row["id"]: tuple(row[1:]) for row in rows}


async def test_sql_and_python_classify_every_value_the_same_way(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        if await apply_full_schema(conn) is None:  # pragma: no cover - defensive
            pytest.fail("schema did not apply")
        ids = await _seed(conn, CORPUS)
        await _run_sql(conn, RATING_STATE_SQL)

        stored = await conn.fetch(
            "SELECT id, overall_rating, rating_state FROM care_providers WHERE id = ANY($1)",
            ids,
        )
        assert len(stored) == len(CORPUS)
        for row in stored:
            expected_state, _ = classify_stored_rating(row["overall_rating"])
            assert row["rating_state"] == expected_state, (
                f"SQL and Python disagree for {row['overall_rating']!r}: "
                f"SQL={row['rating_state']!r} Python={expected_state!r}"
            )
    finally:
        await conn.close()


async def test_sentinel_values_are_never_classified_as_rated(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        sentinels = [value for value in CORPUS if not is_published_value(
            classify_stored_rating(value)[0]
        )]
        assert sentinels, "corpus must contain non-rating values"
        ids = await _seed(conn, tuple(sentinels), prefix="SEN")
        await _run_sql(conn, RATING_STATE_SQL)

        rated = await conn.fetch(
            "SELECT id, overall_rating FROM care_providers "
            "WHERE id = ANY($1) AND rating_state = 'rated'",
            ids,
        )
        assert rated == [], f"non-rating values were classified as rated: {rated}"

        # ...and the real ratings in the corpus ARE classified as rated, so the
        # assertion above is not passing because nothing was classified at all.
        published = [value for value in CORPUS if is_published_value(
            classify_stored_rating(value)[0]
        )]
        published_ids = await _seed(conn, tuple(published), prefix="PUB")
        await _run_sql(conn, RATING_STATE_SQL)
        not_rated = await conn.fetch(
            "SELECT id, overall_rating FROM care_providers "
            "WHERE id = ANY($1) AND rating_state <> 'rated'",
            published_ids,
        )
        assert not_rated == [], f"published ratings were not classified as rated: {not_rated}"
    finally:
        await conn.close()


async def test_unrecognised_value_is_unknown_never_rated(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        ids = await _seed(conn, ("Suspended", "Not registered", "Deregistered"), prefix="UNK")
        await _run_sql(conn, RATING_STATE_SQL)

        rows = await conn.fetch(
            "SELECT overall_rating, rating_state FROM care_providers WHERE id = ANY($1)",
            ids,
        )
        assert {row["rating_state"] for row in rows} == {"unknown"}, rows
    finally:
        await conn.close()


async def test_backfill_is_a_no_op_on_the_second_run(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        ids = await _seed(conn, CORPUS)
        await _run_sql(conn, RATING_STATE_SQL)
        after_first = await _snapshot(conn)

        # Run 1 must have done real work, otherwise "no change" proves nothing.
        classify_count = await conn.fetchval(
            "SELECT COUNT(*) FROM care_providers WHERE rating_state_source = 'migration_061'"
        )
        assert classify_count == len(CORPUS)

        await _run_sql(conn, RATING_STATE_SQL)
        after_second = await _snapshot(conn)

        assert after_second == after_first
        assert set(after_second) >= set(ids)
    finally:
        await conn.close()


async def test_rerun_never_rewrites_a_row_ingestion_classified(fresh_db):
    """The reviewer's exact scenario: a row ingestion left 'unknown' stays 'unknown'."""
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute(
            "INSERT INTO care_providers (id, name, slug, overall_rating, rating_state, "
            "rating_state_source) VALUES ($1, $2, $3, $4, 'unknown', 'pipeline')",
            "ING00001",
            "Ingested probe",
            "ingested-probe-1",
            "Good",
        )
        before = await _snapshot(conn)

        await _run_sql(conn, RATING_STATE_SQL)

        assert await _snapshot(conn) == before
        assert (
            await conn.fetchval(
                "SELECT rating_state FROM care_providers WHERE id = 'ING00001'"
            )
            == "unknown"
        )
    finally:
        await conn.close()


async def test_payload_classifier_and_the_executed_migration_agree_value_for_value(fresh_db):
    """MEDIUM (`api/services/rating_states.py:140`): one authority, one corpus.

    The reviewer's observation was that the payload classifier called
    ``'Excellent'``, ``'Suspended'`` and ``'Under review'`` ``'rated'`` while
    ``classify_stored_rating`` and migration 061 called the same stored values
    ``'unknown'`` -- SQL and Python as two authorities.

    Here the payload classifier is driven the way ingestion drives it
    (:func:`assess_location_rating` on a real ``currentRatings.overall.rating``
    shape) and the migration classification is driven by executing migration 061
    against real PostgreSQL, over the same corpus. Every value that disagrees,
    in either direction, fails and is named.
    """

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        ids = await _seed(conn, NON_EMPTY_CORPUS, prefix="AGR")
        await _run_sql(conn, RATING_STATE_SQL)

        stored = await conn.fetch(
            "SELECT id, overall_rating, rating_state FROM care_providers WHERE id = ANY($1)",
            ids,
        )
        assert len(stored) == len(NON_EMPTY_CORPUS)

        disagreements: list[tuple[str, str, str]] = []
        for row in stored:
            raw = row["overall_rating"]
            payload_state = assess_location_rating(
                {"currentRatings": {"overall": {"rating": raw}}}
            ).state
            if payload_state != row["rating_state"]:
                disagreements.append((raw, payload_state, row["rating_state"]))

        assert disagreements == [], (
            "payload classifier and the executed migration disagree "
            "(value, payload_state, sql_state): "
            f"{disagreements}"
        )
    finally:
        await conn.close()


async def test_last_published_rating_is_recorded_once_and_is_re_run_safe(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await _seed(conn, ("Good", "Not Yet Inspected", "", "Suspended"), prefix="LPR")
        await _run_sql(conn, RATING_STATE_SQL)
        await _run_sql(conn, LAST_PUBLISHED_SQL)
        first = await _snapshot(conn)

        # Only a value the classifier accepts as a real published rating may be
        # copied into the evidence column; a sentinel or an unrecognised value
        # never becomes evidence of a published rating.
        evidence = await conn.fetch(
            "SELECT id, last_published_rating, rating_state FROM care_providers "
            "WHERE id = ANY($1)",
            ["LPR00000", "LPR00001", "LPR00002", "LPR00003"],
        )
        by_id = {row["id"]: row for row in evidence}
        assert by_id["LPR00000"]["last_published_rating"] == "Good"
        assert by_id["LPR00000"]["rating_state"] == "rated"
        assert by_id["LPR00001"]["last_published_rating"] is None
        assert by_id["LPR00002"]["last_published_rating"] is None
        assert by_id["LPR00003"]["last_published_rating"] is None

        await _run_sql(conn, LAST_PUBLISHED_SQL)
        assert await _snapshot(conn) == first
    finally:
        await conn.close()
