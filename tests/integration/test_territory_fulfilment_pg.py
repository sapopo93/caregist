"""Run the paid Brief persistence journey in the mandatory isolated DB job.

Stripe, storage and outbound sending stay synthetic. SQL, the PDF/CSV render,
consent ledger, delivery outbox, hashes and replay behavior run for real.
"""
import asyncpg

from tests.integration.conftest import apply_full_schema
from tests import test_territory_brief_pg_integration as journey


async def test_territory_payment_to_delivery_persistence(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
    finally:
        await conn.close()
    monkeypatch.setattr(journey, "TB_PG_URL", fresh_db)
    await journey.test_full_fulfilment_against_real_postgres()


async def test_small_provider_caps_and_overflow_on_real_schema(fresh_db):
    import pytest
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        for cap in (1, 8, 24, 50):
            row = await conn.fetchrow("""
                INSERT INTO territory_brief_orders
                    (customer_email, stripe_price_id, scope_kind, scope_name, scope_window_days, scope_shortlist_target)
                VALUES ('synthetic@example.test', 'price_test', 'region', 'North West', 90, $1)
                RETURNING scope_shortlist_target
            """, cap)
            assert row['scope_shortlist_target'] == cap
        for cap in (0, 51):
            with pytest.raises(asyncpg.CheckViolationError):
                await conn.execute("""
                    INSERT INTO territory_brief_orders
                        (customer_email, stripe_price_id, scope_kind, scope_name, scope_window_days, scope_shortlist_target)
                    VALUES ('synthetic@example.test', 'price_test', 'region', 'North West', 90, $1)
                """, cap)
    finally:
        await conn.close()
