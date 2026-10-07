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
