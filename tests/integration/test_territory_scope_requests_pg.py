from __future__ import annotations

import pytest

from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio


async def test_scope_request_lifecycle_is_durable_and_fail_closed(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_full_schema(conn)
        assert "064_territory_scope_requests.sql" in applied

        request_id = await conn.fetchval(
            """
            INSERT INTO territory_scope_requests (
              public_reference, submission_key, requester_fingerprint,
              contact_email, region, buyer_type,
              location_count, provider_organisation_count,
              coverage_verdict, coverage_sufficient
            ) VALUES ('TSR-PGTEST000001', repeat('a', 64), repeat('b', 64),
                      'buyer@example.com', 'London',
                      'requires_improvement', 40, 30, 'ready', TRUE)
            RETURNING id
            """
        )
        row = await conn.fetchrow(
            "SELECT status, checkout_eligible FROM territory_scope_requests WHERE id = $1",
            request_id,
        )
        assert row["status"] == "requested"
        assert row["checkout_eligible"] is False
        assert await conn.fetchval(
            "SELECT event_type FROM territory_scope_request_events WHERE request_id = $1",
            request_id,
        ) == "requested"

        with pytest.raises(asyncpg.RaiseError, match="must begin in requested"):
            await conn.execute(
                """
                INSERT INTO territory_scope_requests (
                  public_reference, submission_key, requester_fingerprint,
                  contact_email, region, buyer_type, location_count,
                  provider_organisation_count, coverage_verdict,
                  coverage_sufficient, status, reviewed_at
                ) VALUES ('TSR-PGTESTTERMINAL', repeat('c', 64), repeat('d', 64),
                          'other@example.com', 'London', 'requires_improvement', 1,
                          1, 'insufficient', FALSE, 'accepted', NOW())
                """
            )

        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                "UPDATE territory_scope_requests SET checkout_eligible = TRUE WHERE id = $1",
                request_id,
            )
        with pytest.raises(asyncpg.RaiseError, match="append-only"):
            await conn.execute(
                "UPDATE territory_scope_request_events SET note = 'changed' WHERE request_id = $1",
                request_id,
            )
        with pytest.raises(asyncpg.RaiseError, match="does not match current status"):
            await conn.execute(
                """
                INSERT INTO territory_scope_request_events (request_id, event_type, actor_type)
                VALUES ($1, 'accepted', 'operator')
                """,
                request_id,
            )
        with pytest.raises(asyncpg.RaiseError, match="invalid territory scope request transition"):
            await conn.execute(
                "UPDATE territory_scope_requests SET status = 'fulfilled' WHERE id = $1",
                request_id,
            )

        await conn.execute(
            """
            UPDATE territory_scope_requests
            SET status = 'reviewing'
            WHERE id = $1
            """,
            request_id,
        )
        await conn.execute(
            "UPDATE territory_scope_requests SET status = 'accepted', reviewed_at = NOW() WHERE id = $1",
            request_id,
        )
        with pytest.raises(asyncpg.RaiseError, match="immutable once set"):
            await conn.execute(
                "UPDATE territory_scope_requests SET reviewed_at = NULL WHERE id = $1",
                request_id,
            )
        await conn.execute(
            "UPDATE territory_scope_requests SET status = 'fulfilled', fulfilled_at = NOW() WHERE id = $1",
            request_id,
        )
        assert await conn.fetchval(
            "SELECT status FROM territory_scope_requests WHERE id = $1", request_id
        ) == "fulfilled"
        assert await conn.fetchval(
            "SELECT array_agg(event_type ORDER BY id) FROM territory_scope_request_events WHERE request_id = $1",
            request_id,
        ) == [
            "requested",
            "reviewing",
            "accepted",
            "fulfilled",
        ]

        with pytest.raises(asyncpg.RaiseError, match="append-only"):
            await conn.execute(
                "DELETE FROM territory_scope_request_events WHERE request_id = $1",
                request_id,
            )

        with pytest.raises(asyncpg.RaiseError, match="invalid territory scope request transition"):
            await conn.execute(
                "UPDATE territory_scope_requests SET status = 'reviewing' WHERE id = $1",
                request_id,
            )
    finally:
        await conn.close()
