"""Territory Opportunity Brief fulfilment against a real, freshly migrated Postgres.

tests/test_territory_brief_pg_integration.py only runs when TB_PG_URL is set,
and no workflow sets it, so the paid path was never exercised in CI. This runs
the same scenario against the throwaway database the integration fixtures
build from init.sql and every numbered migration (060 included).
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import apply_full_schema, asyncpg
from tests.test_territory_brief_pg_integration import FIXTURE, run_fulfilment_scenario

pytestmark = pytest.mark.skipif(
    not (FIXTURE / "locations_detail.jsonl").exists(),
    reason="Territory Brief fixture is missing",
)


@pytest.mark.asyncio
async def test_territory_brief_fulfilment_on_migrated_schema(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        applied = await apply_full_schema(conn)
    finally:
        await conn.close()
    assert "060_territory_brief_fulfilment.sql" in applied

    await run_fulfilment_scenario(fresh_db)
