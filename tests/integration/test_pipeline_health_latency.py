"""Disposable-PostgreSQL adversarial proof for the operational-latency gate.

The approved_source_to_ledger_latency gate measures CareGist's own ingestion
latency (observed_at - source_checked_at), never CQC's historical publication
date. These tests insert synthetic ledger rows and execute the exact production
query constant (api.services.pipeline_health._LEDGER_LATENCY_SQL), covering:
historical publication dates, prompt ingestion, genuine delay, missing/invalid
timestamps, the seven-day window, and the 45-minute p95 boundary.

These are database-level synthetic fixtures only; they make no claim about
production CQC freshness or latency.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from api.services.pipeline_health import LEDGER_LATENCY_SLA_SECONDS, _LEDGER_LATENCY_SQL
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")

pytestmark = pytest.mark.asyncio


async def _insert_event(
    conn,
    *,
    row_index: int,
    delta_minutes: int,
    event_type: str = "new_registration",
    location_id: str | None = None,
    source_published_at: datetime | None = None,
    source_checked_at: datetime | None = None,
    observed_at: datetime | None = None,
    missing_checked_at: bool = False,
) -> None:
    """Insert one synthetic trusted_event_ledger row.

    delta_minutes is the intended observed_at - source_checked_at gap; pass
    explicit timestamps instead for the negative/future and stale-window cases.
    missing_checked_at inserts a legacy row with a NULL retrieval timestamp.
    """
    if missing_checked_at:
        checked = None
    elif source_checked_at is not None:
        checked = source_checked_at
    else:
        checked = datetime.now(UTC) - timedelta(minutes=delta_minutes)
    observed = observed_at if observed_at is not None else datetime.now(UTC)
    loc = location_id or f"LOC-{row_index}"
    await conn.execute(
        """
        INSERT INTO care_providers (id, name, slug, status)
        VALUES ($1::text, $2::text, $2::text, 'ACTIVE')
        ON CONFLICT (id) DO NOTHING
        """,
        loc,
        f"Synthetic Care {row_index}",
    )
    await conn.execute(
        """
        INSERT INTO trusted_event_ledger (
          entity_type, entity_id, location_id, event_type,
          effective_date, effective_date_source, old_value, new_value,
          source, dedupe_key, source_published_at, source_checked_at, observed_at
        ) VALUES (
          'care_provider', $1::text, $1::text, $2::text,
          CURRENT_DATE, 'cqc_api', '{}'::jsonb, '{}'::jsonb,
          'cqc_api', $3::text, $4, $5, $6
        )
        """,
        loc,
        event_type,
        f"{event_type}:{loc}:latency-synthetic-{row_index}",
        source_published_at,
        checked,
        observed,
    )


async def _measured_latency(conn) -> dict:
    return await conn.fetchrow(_LEDGER_LATENCY_SQL)


async def test_latency_measures_ingestion_not_historical_publication(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        now = datetime.now(UTC)

        # Historical CQC publication date (2012): under the old semantics this
        # single row would show ~7.4 million minutes of "latency". CareGist
        # checked the source recently and ingested promptly.
        await _insert_event(
            conn,
            row_index=1,
            delta_minutes=1,
            source_published_at=datetime(2012, 6, 1, tzinfo=UTC),
        )
        # Prompt ingestion: checked 5 minutes ago, observed 4 minutes ago.
        await _insert_event(
            conn,
            row_index=2,
            delta_minutes=1,
            event_type="rating_changed",
        )
        # Genuine delay: checked 35 minutes ago, observed now.
        await _insert_event(
            conn,
            row_index=3,
            delta_minutes=35,
        )
        # At the 45-minute boundary.
        await _insert_event(
            conn,
            row_index=4,
            delta_minutes=45,
        )
        # Missing retrieval timestamp (legacy row): excluded, not measured.
        await _insert_event(
            conn,
            row_index=5,
            delta_minutes=1,
            missing_checked_at=True,
        )
        # Invalid timestamps: observed before checked -> excluded.
        await _insert_event(
            conn,
            row_index=6,
            delta_minutes=-10,
            source_checked_at=now + timedelta(minutes=10),
            observed_at=now,
        )
        # Outside the seven-day observed window -> excluded.
        await _insert_event(
            conn,
            row_index=7,
            delta_minutes=2,
            source_checked_at=now - timedelta(days=9),
            observed_at=now - timedelta(days=9) + timedelta(minutes=2),
        )

        measured = await _measured_latency(conn)

        # Only rows 1-4 are measured; their deltas in seconds are
        # [60, 60, 2100, 2700]. percentile_cont(0.95) interpolates at
        # position 1 + 0.95 * 3 = 3.85 -> 2100 + 0.85 * 600 = 2610 seconds.
        assert measured["measured_events"] == 4
        assert float(measured["p95_seconds"]) == pytest.approx(2610.0)
        assert float(measured["p95_seconds"]) <= LEDGER_LATENCY_SLA_SECONDS

        # Historical publication dates are preserved in the ledger untouched.
        preserved = await conn.fetchval(
            "SELECT source_published_at FROM trusted_event_ledger WHERE location_id = $1",
            "LOC-1",
        )
        assert preserved == datetime(2012, 6, 1, tzinfo=UTC)
    finally:
        await conn.close()


async def test_latency_p95_crosses_45_minute_boundary_when_genuinely_delayed(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)

        for row_index, delta_minutes in enumerate((1, 35, 45, 50), start=1):
            await _insert_event(
                conn,
                row_index=row_index,
                delta_minutes=delta_minutes,
                source_published_at=datetime(2015, 1, 15, tzinfo=UTC),
            )

        measured = await _measured_latency(conn)

        # Deltas [60, 2100, 2700, 3000]; percentile_cont(0.95) interpolates at
        # position 1 + 0.95 * 3 = 3.85 -> 2700 + 0.85 * 300 = 2955 seconds.
        assert measured["measured_events"] == 4
        assert float(measured["p95_seconds"]) == pytest.approx(2955.0)
        assert float(measured["p95_seconds"]) > LEDGER_LATENCY_SLA_SECONDS
    finally:
        await conn.close()
