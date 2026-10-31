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


async def test_digest_real_ledger_to_rendered_bound_zip(fresh_db, tmp_path):
    import asyncio
    import io
    import json
    import zipfile
    from datetime import datetime, timezone
    import pytest
    from api.services import customer_package as packages
    from tools import build_weekly_digest_pilot as digest

    conn = await asyncpg.connect(fresh_db)
    try:
        await apply_full_schema(conn)
        await conn.execute("""
            INSERT INTO care_providers (id, name, slug, region, local_authority, status)
            VALUES ('1-NEW', 'Synthetic New Home', 'synthetic-new', 'North West', 'Manchester', 'ACTIVE'),
                   ('1-OTHER', 'Other Region', 'other-region', 'London', 'Westminster', 'ACTIVE')
        """)
        await conn.execute("""
            INSERT INTO trusted_event_ledger
                (entity_type, entity_id, location_id, event_type, effective_date, source, dedupe_key)
            VALUES ('location', '1-NEW', '1-NEW', 'new_registration', '2026-10-14', 'integration-test', 'digest-new'),
                   ('location', '1-OTHER', '1-OTHER', 'new_registration', '2026-10-14', 'integration-test', 'digest-other')
        """)
    finally:
        await conn.close()
    source = tmp_path / 'public-synthetic.ndjson'
    source.write_text(json.dumps({'locationId': '1-RATING', 'providerId': '1-P', 'region': 'North West',
        'name': 'Synthetic Rated Home', 'localAuthority': 'Manchester', 'registrationStatus': 'Registered',
        'currentRatings': {'reportDate': '2026-10-15', 'overall': {'rating': 'Good'}}}) + '\n')
    out = tmp_path / 'generated'
    binding_customer = packages.customer_email_reference('synthetic@example.test')
    result = await asyncio.to_thread(digest.main, ['--region', 'North West', '--week-ending', '2026-10-19',
        '--issue', '1', '--customer', 'Synthetic test', '--order-ref', 'DIGEST-DB-TEST',
        '--customer-reference', binding_customer, '--locations-source', str(source),
        '--source-retrieved-at', '2026-10-20T12:00:00+00:00', '--out-dir', str(out)], database_url=fresh_db)
    assert result == 0
    manifest = json.loads(next(out.glob('*.manifest.json')).read_text())
    assert manifest['counts'] == {'new_registrations': 1, 'ratings_published': 1, 'registration_endings': 0}
    snapshot = packages.verified_snapshot(order_reference='DIGEST-DB-TEST', customer_reference=binding_customer,
        product_id='weekly-digest', payment_reference='cs_synthetic_verified',
        template_version=packages.WEEKLY_DIGEST_TEMPLATE_VERSION, source_version=manifest['sources']['ratings']['sha256'],
        geography='North West', rating_context_criteria=('issue 1 of 4', 'week ending 2026-10-19'),
        confirmed_at=datetime(2026, 10, 20, tzinfo=timezone.utc))
    built = packages.build_package_bytes(snapshot, {
        'digest.pdf': packages.PackageArtifact('digest.pdf', next(out.glob('*.pdf')).read_bytes(), 'application/pdf'),
        'digest.csv': packages.PackageArtifact('digest.csv', next(out.glob('*.csv')).read_bytes(), 'text/csv')},
        evidence={'generator_manifest': manifest})
    with pytest.raises(packages.PackageBindingError):
        packages.publish_package_atomically(built, root=tmp_path / 'packages',
            order_reference='DIGEST-DB-TEST', customer_reference='another-customer')
    published = packages.publish_package_atomically(built, root=tmp_path / 'packages',
        order_reference='DIGEST-DB-TEST', customer_reference=binding_customer)
    with zipfile.ZipFile(io.BytesIO(published.read_bytes())) as archive:
        csv_bytes = archive.read('digest.csv')
        assert b'Synthetic New Home' in csv_bytes and b'Synthetic Rated Home' in csv_bytes
        assert b'Other Region' not in csv_bytes
