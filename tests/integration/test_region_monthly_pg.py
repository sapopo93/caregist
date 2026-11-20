"""Region Monthly against a real Postgres: counts reconcile to seeded rows, UK
month edges, service mapping, exclusions, immutability and the build command.

Seeded world (all dates 2026). Locations are in London unless stated.

  RM-1   ACTIVE    Domiciliary care service | Supported living service   registered 3 Sep
  RM-2   ACTIVE    Domiciliary care service                              registered 30 Sep
  RM-3   INACTIVE  Care home service with nursing                        registered 15 Sep
  RM-4   ACTIVE    Dental service                                        registered 1 Oct
  RM-5   ACTIVE    Domiciliary care service                              registered 31 Aug
  RM-6   ACTIVE    Domiciliary care service, quarantined                 registered 10 Sep
  RM-7   ACTIVE    Domiciliary care service, South East                  registered 10 Sep
  RM-8   ACTIVE    region ''                                             registered 10 Sep
  RM-9   ACTIVE    region 'Wales'                                        registered 10 Sep
  RM-10  ACTIVE    no service types                                      registered 20 Sep
  RM-11  ACTIVE    Supported Living | Supported living service (aliases)  registered 25 Sep
  RM-12  ACTIVE    a service type outside the taxonomy                    registered 12 Sep
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.middleware import ip_rate_limit
from api.queries import region_monthly as q
from api.services import region_monthly as svc
from api.services.region_monthly import BuildTarget, RegionMonthlyError
from tests.integration.conftest import MIGRATIONS_DIR, apply_full_schema
from tools import build_region_monthly as cli

asyncpg = pytest.importorskip("asyncpg")
pytestmark = pytest.mark.asyncio

UTC = timezone.utc
AS_OF = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
SEPT, OCT, JULY, AUG = date(2026, 9, 1), date(2026, 10, 1), date(2026, 7, 1), date(2026, 8, 1)

HOME = "Domiciliary care service"
SUPPORTED = "Supported living service"
NURSING = "Care home service with nursing"

# id, status, region, service_types, registered
LOCATIONS = [
    ("RM-1", "ACTIVE", "London", f"{HOME}|{SUPPORTED}", date(2026, 9, 3)),
    ("RM-2", "ACTIVE", "London", HOME, date(2026, 9, 30)),
    ("RM-3", "INACTIVE", "London", NURSING, date(2026, 9, 15)),
    ("RM-4", "ACTIVE", "London", "Dental service", date(2026, 10, 1)),
    ("RM-5", "ACTIVE", "London", HOME, date(2026, 8, 31)),
    ("RM-6", "ACTIVE", "London", HOME, date(2026, 9, 10)),
    ("RM-7", "ACTIVE", "South East", HOME, date(2026, 9, 10)),
    ("RM-8", "ACTIVE", "", HOME, date(2026, 9, 10)),
    ("RM-9", "ACTIVE", "Wales", HOME, date(2026, 9, 10)),
    ("RM-10", "ACTIVE", "London", None, date(2026, 9, 20)),
    ("RM-11", "ACTIVE", "London", f"Supported Living|{SUPPORTED}", date(2026, 9, 25)),
    ("RM-12", "ACTIVE", "London", "Some other service", date(2026, 9, 12)),
]

# provider_id, rating, inspection_date
RATINGS = [
    ("RM-1", "Outstanding", date(2026, 6, 30)),  # June
    ("RM-1", "Good", date(2026, 7, 1)),
    ("RM-2", "Requires improvement", date(2026, 7, 31)),
    ("RM-3", "Inadequate", date(2026, 7, 15)),
    ("RM-10", "Outstanding", date(2026, 7, 10)),
    ("RM-11", "  good ", date(2026, 7, 20)),  # case and spaces are normalised
    ("RM-12", None, date(2026, 7, 12)),
    ("RM-12", "Not Yet Inspected", date(2026, 7, 13)),
    ("RM-6", "Good", date(2026, 7, 5)),  # quarantined
    ("RM-7", "Good", date(2026, 7, 5)),  # another region
    ("RM-9", "Good", date(2026, 7, 5)),  # Wales
    ("RM-3", "Good", date(2026, 8, 1)),
    ("RM-2", "Good", date(2026, 8, 11)),  # the last day the rating history speaks for
    ("RM-1", "Good", date(2026, 8, 12)),  # after it: not read
    ("RM-1", "Good", date(2026, 9, 2)),  # September: not available
]

# location, old, new, observed_at (UTC), event_type
LEDGER = [
    ("RM-1", "ACTIVE", "INACTIVE", datetime(2026, 9, 15, 10, 0, tzinfo=UTC), "status_changed"),
    ("RM-2", "ACTIVE", "INACTIVE", datetime(2026, 9, 30, 22, 59, 59, tzinfo=UTC), "status_changed"),  # 23:59:59 BST, September
    ("RM-3", "ACTIVE", "INACTIVE", datetime(2026, 9, 30, 23, 0, 0, tzinfo=UTC), "status_changed"),  # 00:00 BST, October
    ("RM-10", "INACTIVE", "ACTIVE", datetime(2026, 9, 5, 9, 0, tzinfo=UTC), "status_changed"),
    ("RM-11", "ACTIVE", "INACTIVE", datetime(2026, 10, 31, 23, 30, tzinfo=UTC), "status_changed"),  # 23:30 GMT, October
    ("RM-11", "INACTIVE", "ACTIVE", datetime(2026, 11, 1, 0, 0, tzinfo=UTC), "status_changed"),  # November
    ("RM-1", "Alpha Ltd", "Beta Ltd", datetime(2026, 9, 16, 9, 0, tzinfo=UTC), "ownership_changed"),  # never used
    ("RM-1", "Good", "Not yet inspected", datetime(2026, 9, 17, 9, 0, tzinfo=UTC), "rating_status_changed"),  # never used
    ("RM-6", "ACTIVE", "INACTIVE", datetime(2026, 9, 18, 9, 0, tzinfo=UTC), "status_changed"),  # quarantined
    ("RM-7", "ACTIVE", "INACTIVE", datetime(2026, 9, 18, 9, 0, tzinfo=UTC), "status_changed"),  # another region
    ("RM-1", "ACTIVE", "INACTIVE", datetime(2026, 8, 5, 9, 0, tzinfo=UTC), "status_changed"),  # before capture began
    ("RM-4", "ACTIVE", "INACTIVE", datetime(2026, 8, 9, 22, 59, 59, tzinfo=UTC), "status_changed"),  # 23:59:59 BST on 9 Aug
    ("RM-2", "ACTIVE", "INACTIVE", datetime(2026, 8, 9, 23, 0, 0, tzinfo=UTC), "status_changed"),  # 00:00 BST on 10 Aug
]


async def seed(conn, *, reverse: bool = False) -> None:
    def ordered(rows):
        return list(reversed(rows)) if reverse else list(rows)

    for loc, status, region, services, registered in ordered(LOCATIONS):
        await conn.execute(
            """INSERT INTO care_providers (id, provider_id, name, slug, status, region, service_types, registration_date)
               VALUES ($1, $2, $1, $7, $3, $4, $5, $6)""",
            loc, "P-" + loc, status, region, services, registered, loc.lower(),
        )
    await conn.execute(
        "INSERT INTO reconciliation_quarantined_locations (location_id, reason, last_error) VALUES ('RM-6', 'test', 'test')"
    )
    for provider, rating, inspected in ordered(RATINGS):
        await conn.execute(
            "INSERT INTO provider_rating_history (provider_id, overall_rating, inspection_date) VALUES ($1, $2, $3)",
            provider, rating, inspected,
        )
    for index, (loc, old, new, observed, kind) in enumerate(ordered(LEDGER)):
        await conn.execute(
            """INSERT INTO trusted_event_ledger
               (entity_type, entity_id, location_id, event_type, effective_date, observed_at,
                old_value, new_value, source, dedupe_key)
               VALUES ('care_provider', $1::text, $1::varchar, $2, NULL, $3, to_jsonb($4::text), to_jsonb($5::text), 'integration-test', $6)""",
            loc, kind, observed, old, new, f"rm-{kind}-{loc}-{observed.isoformat()}-{index}",
        )


@pytest.fixture
async def conn(fresh_db):
    connection = await asyncpg.connect(fresh_db)
    await apply_full_schema(connection)
    await seed(connection)
    yield connection
    await connection.close()


async def build(conn, month, region="London", service=None, as_of=AS_OF):
    return await svc.build_month(conn, month, region, service, as_of)


# --- counts reconcile to the seeded rows ------------------------------------


async def test_september_counts_reconcile_to_the_seeded_rows(conn):
    built = await build(conn, SEPT)
    # RM-1, 2, 3, 10, 11, 12 registered in September in London. RM-6 is quarantined; RM-7, 8, 9 are
    # elsewhere or have no England region.
    assert built.metrics["new_registrations"] == 6
    assert built.metrics["ratings_published"] is None  # not available after 11 August 2026
    assert built.metrics["closures_observed"] == 2  # RM-1 and RM-2 (RM-3 is 00:00 BST on 1 October)
    assert built.metrics["reinstatements_observed"] == 1  # RM-10
    assert built.coverage["ratings_published"]["status"] == "not_available_after"
    assert built.coverage["closures_observed"]["status"] == "available"
    assert built.limits == svc.LIMITS


async def test_october_counts_use_london_time_across_the_end_of_bst(conn):
    built = await build(conn, OCT)
    assert built.metrics["new_registrations"] == 1  # RM-4 on 1 October
    # RM-3 at 2026-09-30T23:00Z (00:00 BST on 1 Oct) and RM-11 at 2026-10-31T23:30Z (23:30 GMT) are October;
    # RM-11's reinstatement at 2026-11-01T00:00Z is November.
    assert built.metrics["closures_observed"] == 2
    assert built.metrics["reinstatements_observed"] == 0


async def test_july_ratings_are_counted_by_value_and_closures_are_not_captured(conn):
    built = await build(conn, JULY)
    assert built.metrics["ratings_published"] == {
        "outstanding": 1,  # RM-10 (RM-1's Outstanding is June)
        "good": 2,  # RM-1 and RM-11 ("  good ")
        "requires_improvement": 1,
        "inadequate": 1,
        "no_published_rating_value": 2,  # RM-12: NULL and "Not Yet Inspected"
        "total": 7,
    }
    assert built.metrics["closures_observed"] is None and built.metrics["reinstatements_observed"] is None
    assert built.coverage["closures_observed"]["text"] == "not captured before 10 August 2026"
    assert built.metrics["new_registrations"] == 0
    june = await build(conn, date(2026, 6, 1))
    assert june.metrics["ratings_published"]["outstanding"] == 1 and june.metrics["ratings_published"]["total"] == 1


async def test_august_is_partial_for_ratings_and_status_changes(conn):
    built = await build(conn, AUG)
    assert built.metrics["new_registrations"] == 1  # RM-5 on 31 August
    assert built.metrics["ratings_published"]["good"] == 2  # RM-3 on 1 Aug, RM-2 on 11 Aug; RM-1 on 12 Aug is not read
    assert built.metrics["ratings_published"]["total"] == 2
    # RM-2 at 00:00 BST on 10 August counts; RM-4 at 23:59:59 BST on 9 August and RM-1 on 5 August do not.
    assert built.metrics["closures_observed"] == 1
    assert built.coverage["ratings_published"]["status"] == "partial"
    assert built.coverage["closures_observed"]["status"] == "partial"


async def test_a_location_with_two_service_types_counts_once_under_each_and_once_in_the_region(conn):
    total = (await build(conn, SEPT)).metrics["new_registrations"]
    by_service = {slug: (await build(conn, SEPT, service=slug)).metrics["new_registrations"] for slug in svc.supported_services()}
    assert by_service["home-care"] == 2  # RM-1, RM-2 (RM-6 quarantined, RM-7/8/9 elsewhere)
    assert by_service["supported-living"] == 2  # RM-1 and RM-11 (RM-11 holds two aliases of one slug: once)
    assert by_service["nursing-care-homes"] == 1  # RM-3
    assert by_service["dental-services"] == 0
    assert {k: v for k, v in by_service.items() if v} == {"home-care": 2, "supported-living": 2, "nursing-care-homes": 1}
    # RM-1 is in two slugs; RM-10 (no service) and RM-12 (outside the taxonomy) are in none.
    assert total == 6 and sum(by_service.values()) == 5 and total != sum(by_service.values())
    # The same rules hold for the other metrics.
    assert (await build(conn, SEPT, service="home-care")).metrics["closures_observed"] == 2
    assert (await build(conn, SEPT, service="supported-living")).metrics["closures_observed"] == 1
    assert (await build(conn, SEPT, service="supported-living")).metrics["reinstatements_observed"] == 0
    july_sl = (await build(conn, JULY, service="supported-living")).metrics["ratings_published"]
    assert (july_sl["good"], july_sl["total"]) == (2, 2)


async def test_empty_region_and_wales_are_never_counted_or_buildable(conn):
    for region in ("Wales", "", "wales"):
        with pytest.raises(RegionMonthlyError) as raised:
            await build(conn, SEPT, region=region)
        assert raised.value.code == "region_unsupported"
    totals = 0
    for region in svc.REGIONS:
        totals += (await build(conn, SEPT, region=region)).metrics["new_registrations"]
    assert totals == 6 + 1  # London's six plus RM-7 in the South East; RM-8 (empty) and RM-9 (Wales) in none


async def test_quarantined_locations_are_left_out_until_resolved(conn):
    assert (await build(conn, SEPT)).metrics["new_registrations"] == 6
    await conn.execute("UPDATE reconciliation_quarantined_locations SET resolved_at = NOW(), updated_at = NOW()")
    resolved = await build(conn, SEPT)
    assert resolved.metrics["new_registrations"] == 7
    assert resolved.metrics["closures_observed"] == 3  # RM-6's closure now counts


async def test_seventh_day_rule_applies_to_building_across_bst(conn):
    # September: 7 October 00:00 BST is 2026-10-06T23:00Z.
    with pytest.raises(RegionMonthlyError) as raised:
        await build(conn, SEPT, as_of=datetime(2026, 10, 6, 22, 59, 59, tzinfo=UTC))
    assert raised.value.code == "month_not_yet_buildable"
    assert (await build(conn, SEPT, as_of=datetime(2026, 10, 6, 23, 0, tzinfo=UTC))).metrics["new_registrations"] == 6
    # October: 7 November 00:00 GMT is 2026-11-07T00:00Z.
    with pytest.raises(RegionMonthlyError):
        await build(conn, OCT, as_of=datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC))
    assert await build(conn, OCT, as_of=datetime(2026, 11, 7, 0, 0, tzinfo=UTC))


async def test_the_hash_is_independent_of_insert_order_and_build_time(fresh_db):
    connection = await asyncpg.connect(fresh_db)
    hashes = []
    try:
        await apply_full_schema(connection)
        for reverse, as_of in ((False, AS_OF), (True, datetime(2027, 3, 1, 9, 0, tzinfo=UTC))):
            await seed(connection, reverse=reverse)
            hashes.append(
                [
                    (await build(connection, m, service=s, as_of=as_of)).content_sha256
                    for m in (JULY, AUG, SEPT, OCT)
                    for s in (None, "home-care", "supported-living")
                ]
            )
            for table in ("trusted_event_ledger", "provider_rating_history", "reconciliation_quarantined_locations", "care_providers"):
                await connection.execute(f"DELETE FROM {table}")
    finally:
        await connection.close()
    assert hashes[0] == hashes[1]
    assert len(set(hashes[0])) == len(hashes[0])  # twelve different records, twelve different hashes


# --- the immutable store ----------------------------------------------------


async def test_a_stored_build_round_trips_and_its_hash_can_be_recomputed(conn):
    built = await build(conn, SEPT, service="home-care")
    stored = await svc.store_build(conn, built)
    assert (stored.action, stored.build_version) == ("inserted", 1)
    row = await conn.fetchrow("SELECT * FROM region_monthly_builds")
    assert (row["period_month"], row["region"], row["service_slug"], row["build_version"]) == (SEPT, "London", "home-care", 1)
    assert row["supersedes_build_version"] is None and row["correction_reason"] is None
    assert row["built_from_data_cutoff"] == AS_OF and row["built_at"] is not None
    content = svc.canonical_content(
        row["period_month"], row["region"], row["service_slug"],
        json.loads(row["metrics"]), json.loads(row["coverage"]), json.loads(row["limits"]), row["schema_version"],
    )
    assert svc.content_sha256(content) == row["content_sha256"] == built.content_sha256


async def test_unchanged_months_are_not_rewritten_and_changes_need_a_reason(conn):
    built = await build(conn, SEPT)
    assert (await svc.store_build(conn, built)).action == "inserted"
    assert (await svc.store_build(conn, await build(conn, SEPT, as_of=datetime(2026, 12, 7, tzinfo=UTC)))).action == "unchanged"
    await conn.execute(
        "INSERT INTO care_providers (id, provider_id, name, slug, status, region, registration_date) "
        "VALUES ('RM-LATE', 'P-RM-LATE', 'late', 'rm-late', 'ACTIVE', 'London', '2026-09-28')"
    )
    changed = await build(conn, SEPT)
    assert changed.metrics["new_registrations"] == 7
    refused = await svc.store_build(conn, changed)
    assert (refused.action, refused.build_version) == ("changed_not_stored", 1)
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 1
    corrected = await svc.store_build(conn, changed, correction_reason="Location RM-LATE was registered late.")
    assert (corrected.action, corrected.build_version) == ("inserted", 2)
    rows = await conn.fetch("SELECT build_version, supersedes_build_version, correction_reason, metrics FROM region_monthly_builds ORDER BY build_version")
    assert [(r["build_version"], r["supersedes_build_version"]) for r in rows] == [(1, None), (2, 1)]
    assert json.loads(rows[0]["metrics"])["new_registrations"] == 6  # the older version is kept as it was
    assert json.loads(rows[1]["metrics"])["new_registrations"] == 7
    assert rows[1]["correction_reason"] == "Location RM-LATE was registered late."


async def test_built_rows_cannot_be_updated_deleted_or_truncated(conn):
    await svc.store_build(conn, await build(conn, SEPT))
    for statement in (
        "UPDATE region_monthly_builds SET metrics = '{}'::jsonb",
        "UPDATE region_monthly_builds SET region = 'East'",
        "UPDATE region_monthly_builds SET built_at = NOW()",
        "DELETE FROM region_monthly_builds",
        "TRUNCATE region_monthly_builds",
    ):
        with pytest.raises(asyncpg.RaiseError, match="immutable"):
            await conn.execute(statement)
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 1
    # The same holds inside a transaction that tries to be clever.
    with pytest.raises(asyncpg.RaiseError):
        async with conn.transaction():
            await conn.execute("DELETE FROM region_monthly_builds WHERE true")


INSERT = """
INSERT INTO region_monthly_builds
  (period_month, region, service_slug, build_version, supersedes_build_version, correction_reason,
   built_from_data_cutoff, metrics, coverage, limits, content_sha256)
VALUES ($1, $2, $3, $4, $5, $6, NOW(), '{}', '{}', '[]', $7)
"""
SHA = "a" * 64
CHAIN_ERRORS = (asyncpg.CheckViolationError, asyncpg.RaiseError)


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ((date(2026, 9, 2), "London", None, 1, None, None, SHA), asyncpg.CheckViolationError),  # not first of month
        ((SEPT, "Wales", None, 1, None, None, SHA), asyncpg.CheckViolationError),
        ((SEPT, "", None, 1, None, None, SHA), asyncpg.CheckViolationError),
        ((SEPT, "Scotland", None, 1, None, None, SHA), asyncpg.CheckViolationError),
        ((SEPT, "London", "Home Care", 1, None, None, SHA), asyncpg.CheckViolationError),
        ((SEPT, "London", None, 1, None, None, "xyz"), asyncpg.CheckViolationError),
        ((SEPT, "London", None, 0, None, None, SHA), asyncpg.CheckViolationError),
        ((SEPT, "London", None, 1, 0, "why", SHA), asyncpg.CheckViolationError),  # v1 supersedes nothing
        # A correction needs a reason and must supersede the previous version. The insert trigger may
        # refuse these first (there is no earlier version in an empty table); either refusal is correct.
        ((SEPT, "London", None, 2, 1, None, SHA), CHAIN_ERRORS),
        ((SEPT, "London", None, 2, 1, "  ", SHA), CHAIN_ERRORS),
        ((SEPT, "London", None, 3, 1, "why", SHA), CHAIN_ERRORS),
    ],
)
async def test_the_table_refuses_malformed_builds(conn, args, error):
    with pytest.raises(error):
        await conn.execute(INSERT, *args)


async def test_versions_form_an_unbroken_chain_and_the_key_covers_all_services(conn):
    # NULL service (all services) must be unique per version, which a plain UNIQUE would miss.
    await conn.execute(INSERT, SEPT, "London", None, 1, None, None, SHA)
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(INSERT, SEPT, "London", None, 1, None, None, "b" * 64)
    # Version 2 needs version 1 in the same (month, region, service) key.
    with pytest.raises(asyncpg.RaiseError, match="no version 1 to supersede"):
        await conn.execute(INSERT, SEPT, "London", "home-care", 2, 1, "why", SHA)
    with pytest.raises(asyncpg.RaiseError):
        await conn.execute(INSERT, OCT, "London", None, 2, 1, "why", SHA)
    await conn.execute(INSERT, SEPT, "London", "home-care", 1, None, None, SHA)
    await conn.execute(INSERT, SEPT, "London", "home-care", 2, 1, "why", "c" * 64)
    # A different month, region or service has its own chain.
    await conn.execute(INSERT, OCT, "London", None, 1, None, None, SHA)
    await conn.execute(INSERT, SEPT, "East", None, 1, None, None, SHA)
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 5


async def test_migration_074_has_a_working_down_script_and_can_be_reapplied(conn):
    up = (MIGRATIONS_DIR / "074_region_monthly_builds.sql").read_text(encoding="utf-8")
    down = (MIGRATIONS_DIR / "down" / "074_region_monthly_builds.down.sql").read_text(encoding="utf-8")
    await svc.store_build(conn, await build(conn, SEPT))
    await conn.execute(down)
    assert not await conn.fetchval(q.BUILDS_TABLE_PRESENT)
    assert not await conn.fetchval("SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'region_monthly_builds%'")
    await conn.execute(up)
    await conn.execute(up)  # the up script can be run again without error
    assert await conn.fetchval(q.BUILDS_TABLE_PRESENT)
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 0


# --- the build command ------------------------------------------------------


async def test_dry_run_writes_nothing_and_write_stores_then_reports_unchanged(conn):
    plan = svc.plan_backfill(JULY, SEPT, AS_OF, regions=["London"], services=[None, "home-care"])
    assert len(plan) == 6
    async with conn.transaction(readonly=True):
        dry = await cli.run_builds(conn, plan, write=False, now=AS_OF)
    assert {o.action for o in dry} == {"would_insert"}
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 0

    written = await cli.run_builds(conn, plan, write=True, now=AS_OF)
    assert {o.action for o in written} == {"inserted"}
    assert [o.content_sha256 for o in written] == [o.content_sha256 for o in dry]
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 6

    async with conn.transaction(readonly=True):
        again = await cli.run_builds(conn, plan, write=False, now=AS_OF)
    assert {o.action for o in again} == {"unchanged"}
    rewrite = await cli.run_builds(conn, plan, write=True, now=AS_OF)
    assert {o.action for o in rewrite} == {"unchanged"}
    assert cli.summarise(rewrite) == {"unchanged": 6}
    assert await conn.fetchval("SELECT COUNT(*) FROM region_monthly_builds") == 6


async def test_dry_run_before_the_migration_reports_what_it_would_insert(fresh_db):
    connection = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(connection, through="073_rebuild_territory_brief_tables.sql")
        await seed(connection)
        plan = [BuildTarget(SEPT, "London", None)]
        async with connection.transaction(readonly=True):
            outcomes = await cli.run_builds(connection, plan, write=False, now=AS_OF)
        assert [o.action for o in outcomes] == ["would_insert"]
        with pytest.raises(RegionMonthlyError) as raised:
            await cli.run_builds(connection, plan, write=True, now=AS_OF)
        assert raised.value.code == "source_unavailable"
    finally:
        await connection.close()


async def test_a_dry_run_in_a_read_only_transaction_cannot_write_even_by_mistake(conn):
    built = await build(conn, SEPT)
    with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
        async with conn.transaction(readonly=True):
            await svc.store_build(conn, built)


# --- the route against built rows -------------------------------------------


async def test_the_preview_route_reads_real_builds(conn):
    plan = svc.plan_backfill(date(2026, 4, 1), OCT, AS_OF, regions=["London"], services=["home-care"])
    await cli.run_builds(conn, plan, write=True, now=AS_OF)

    @asynccontextmanager
    async def get_connection():
        yield conn

    async def fetch(path):
        ip_rate_limit._public_ip_requests.clear()
        with patch("api.routers.region_monthly.get_connection", get_connection), patch(
            "api.routers.region_monthly.settings.region_monthly_enabled", True
        ), patch("api.routers.region_monthly._now", return_value=AS_OF):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
                return await client.get(path)

    base = "/api/v1/region-monthly/coverage?region=London&service=home-care"
    ok = await fetch(f"{base}&kind=six&first_month=2026-05")
    assert ok.status_code == 200 and [m["status"] for m in ok.json()["months"]] == ["built"] * 6
    # London has no all-services builds, so the same request without a service is refused.
    none = await fetch("/api/v1/region-monthly/coverage?region=London&kind=single&first_month=2026-10")
    assert (none.status_code, none.json()["detail"]["code"]) == (409, "month_not_built")
    future = await fetch(f"{base}&kind=six&first_month=2026-08&accept_future_months=true")
    assert future.status_code == 200 and future.json()["future_months"] == ["2026-11", "2026-12", "2027-01"]
    assert (await fetch(f"{base}&kind=single&first_month=2026-03")).json()["detail"]["code"] == "month_before_earliest"
