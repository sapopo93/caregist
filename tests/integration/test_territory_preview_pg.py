"""Production-shaped SQL proof on a disposable local database."""
from datetime import date, timedelta

import pytest

from api.queries import territory_preview as q
from api.service_taxonomy import resolve_service_filter
from api.services.territory_preview import PreviewScope, build_preview
from tests.integration.conftest import apply_full_schema

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio


async def test_preview_distinguishes_locations_providers_and_public_examples(fresh_db):
    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        day = date.today() - timedelta(days=2)
        for location, provider, owner, status in [
            ("preview-org-1", "P1", "Organisation", "ACTIVE"),
            ("preview-org-2", "P1", "Organisation", "ACTIVE"),
            ("preview-person", "P2", "Individual", "ACTIVE"),
            ("preview-inactive", "P3", "Organisation", "INACTIVE"),
            ("preview-quarantined", "P4", "Organisation", "ACTIVE"),
        ]:
            await conn.execute(
                """INSERT INTO care_providers
                   (id,provider_id,name,slug,status,region,local_authority,service_types,ownership_type,registration_date)
                   VALUES ($1,$2,$1,$1,$3,'West Midlands','Coventry','Domiciliary care service',$4,$5)""",
                location, provider, status, owner, day,
            )
        await conn.execute(
            "INSERT INTO reconciliation_quarantined_locations (location_id,reason,last_error) VALUES ('preview-quarantined','synthetic','synthetic')"
        )
        aliases = list(resolve_service_filter("home-care"))
        scope = await conn.fetchrow(q.scope_counts("region"), "west midlands", aliases)
        assert (scope["organisations"], scope["locations"]) == (2, 3)
        counts = dict(await conn.fetchrow(q.signal_counts("region"), "West Midlands", aliases, day-timedelta(days=89), day))
        assert counts["new_registrations"] == 3
        examples = [dict(r) for r in await conn.fetch(q.new_registration_examples("region"), "West Midlands", aliases, day-timedelta(days=89), day)]
        assert {r["location_id"] for r in examples} == {"preview-org-1", "preview-org-2"}
        body = build_preview(PreviewScope("region", "West Midlands", "homecare", "home-care"), organisations=scope["organisations"], locations=scope["locations"], window_end=day, counts=counts, events=examples, freshness={"status":"partial"})
        assert len(body["examples"]) == 1
        assert body["brief"]["fits"] is None
        assert body["source"]["coverage_confirmed"] is False
        before = await conn.fetchval(q.QUARANTINE_REVISION)
        await conn.execute("UPDATE reconciliation_quarantined_locations SET resolved_at=NOW(),updated_at=NOW() WHERE location_id='preview-quarantined'")
        assert await conn.fetchval(q.QUARANTINE_REVISION) != before
        after = await conn.fetchrow(q.scope_counts("region"), "West Midlands", aliases)
        assert (after["organisations"], after["locations"]) == (3, 4)
    finally:
        await conn.close()
