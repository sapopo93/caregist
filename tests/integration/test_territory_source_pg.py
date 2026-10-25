"""Original CQC evidence survives import, file loss and paid-order retries."""
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import asyncpg
import psycopg2
import pytest

from api.services import territory_brief_source as source
from api.services.territory_brief_delivery import generate_pack
from tests.integration.conftest import apply_full_schema
from tools.import_territory_brief_source import import_edition


@pytest.fixture
async def source_db(fresh_db, monkeypatch):
    conn = await asyncpg.connect(fresh_db)
    await apply_full_schema(conn)
    @asynccontextmanager
    async def connection():
        yield conn
    monkeypatch.setattr(source, 'get_connection', connection)
    yield conn, fresh_db
    await conn.close()


def snapshot(tmp_path, label='Provider', count=12):
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=1)).date().isoformat()
    old = (now - timedelta(days=40)).date().isoformat()
    locations = [{
        'locationId': f'L{i}', 'providerId': f'P{i}', 'name': f'Location {i}',
        'localAuthority': 'Testshire', 'region': 'Test Region',
        'registrationDate': old, 'registrationStatus': 'Registered',
        'currentRatings': {'overall': {'rating': 'Good', 'reportDate': recent}},
        'historicRatings': [{'overall': {'rating': 'Requires improvement'}, 'reportDate': old}],
        'gacServiceTypes': [{'description': 'Care home service without nursing'}],
    } for i in range(count)]
    loc = tmp_path / 'locations.jsonl'
    prov = tmp_path / 'providers.jsonl'
    loc.write_text('\n'.join(json.dumps(r) for r in locations))
    prov.write_text('\n'.join(json.dumps({'providerId': f'P{i}', 'name': f'{label} {i}'}) for i in range(count)))
    return loc, prov, now


def load(url, files, age_days=0):
    conn = psycopg2.connect(url)
    try:
        return import_edition(conn, files[0], files[1], files[2] - timedelta(days=age_days))
    finally:
        conn.close()


SCOPE = {'kind': 'local_authority', 'name': 'Testshire', 'window_days': 90, 'shortlist_target': 10}


async def test_import_file_loss_and_pinned_retry(source_db, tmp_path):
    conn, url = source_db
    files = snapshot(tmp_path)
    edition = load(url, files)
    scope, selected = await source.prepare_checkout(SCOPE)
    assert selected == edition
    files[0].unlink()
    files[1].unlink()
    order = dict(id='test-order', scope_kind=scope.kind, scope_name=scope.name,
                 scope_window_days=90, scope_shortlist_target=10, source_edition_id=edition)
    first = await generate_pack(order, conn)
    assert first.pdf_bytes.startswith(b'%PDF')
    assert first.shortlisted == 10
    assert 'rating_changed' in first.csv_text
    assert 'Requires improvement' in first.csv_text
    second_edition = load(url, snapshot(tmp_path, label='New organisation'))
    assert second_edition != edition
    retry = await generate_pack(order, conn)
    assert retry.csv_text == first.csv_text
    assert 'New organisation' not in retry.csv_text
    assert (await source.load_source(SCOPE, edition_id=edition))[1]['id'] == edition
    with pytest.raises(asyncpg.RaiseError, match='immutable'):
        await conn.execute('DELETE FROM territory_brief_source_locations WHERE edition_id=$1', edition)
    with pytest.raises(asyncpg.RaiseError, match='immutable'):
        await conn.execute('TRUNCATE territory_brief_source_locations')
    with pytest.raises(asyncpg.RaiseError, match='sealed'):
        await conn.execute("""INSERT INTO territory_brief_source_locations
            (edition_id,location_id,local_authority,region,provider_name,payload)
            VALUES ($1,'extra','Testshire','Test Region','Wrong','{}')""", edition)
    # Actual rendered bytes retained for the quality review in a temporary test path.
    (tmp_path / 'brief.pdf').write_bytes(retry.pdf_bytes)
    (tmp_path / 'brief.csv').write_text(retry.csv_text)


async def test_empty_stale_and_incomplete_sources_fail_closed(source_db, tmp_path):
    conn, url = source_db
    with pytest.raises(source.SourceUnavailable, match='No CQC'):
        await source.prepare_checkout(SCOPE)
    files = snapshot(tmp_path)
    # Import an honestly old edition, with correspondingly old event dates.
    for path in files[:2]:
        text = path.read_text()
        text = text.replace((files[2] - timedelta(days=1)).date().isoformat(),
                            (files[2] - timedelta(days=20)).date().isoformat())
        path.write_text(text)
    edition = load(url, files, age_days=10)
    with pytest.raises(source.SourceUnavailable, match='stale'):
        await source.prepare_checkout(SCOPE)
    # A paid retry may still use its old, complete edition.
    assert (await source.load_source(SCOPE, edition_id=edition))[1]['id'] == edition
    await conn.execute('''INSERT INTO territory_brief_source_editions
        (source_retrieved_at,source_as_of,locations_sha256,providers_sha256,location_count)
        VALUES (NOW(),CURRENT_DATE,$1,$2,99)''', 'c'*64, 'd'*64)
    with pytest.raises(source.SourceUnavailable, match='incomplete'):
        await source.prepare_checkout(SCOPE)


async def test_shortfall_and_unpinned_order_fail_closed(source_db, tmp_path):
    conn, url = source_db
    load(url, snapshot(tmp_path, count=2))
    with pytest.raises(source.SourceUnavailable, match='shortlist'):
        await source.prepare_checkout(SCOPE)
    with pytest.raises(source.SourceUnavailable, match='no pinned'):
        await generate_pack({'id': 'legacy-paid'}, conn)


async def test_bad_import_rolls_back_whole_edition(source_db, tmp_path):
    conn, url = source_db
    files = snapshot(tmp_path)
    # Duplicate locations may not silently inflate counts or change evidence.
    files[0].write_text(files[0].read_text() + '\n' + files[0].read_text().splitlines()[0])
    with pytest.raises(psycopg2.errors.UniqueViolation):
        load(url, files)
    assert await conn.fetchval('SELECT count(*) FROM territory_brief_source_editions') == 0


async def test_source_normalization_preserves_all_records(source_db, tmp_path):
    conn, url = source_db
    files = snapshot(tmp_path)
    rows = [json.loads(line) for line in files[0].read_text().splitlines()]
    rows[0]['localAuthority'] = 'TESTSHIRE'
    rows[0]['providerId'] = ' P0 '
    files[0].write_text('\n'.join(json.dumps(row) for row in rows))
    edition = load(url, files)
    scope, metadata, locations, names = await source.load_source(SCOPE, edition_id=edition)
    assert len(locations) == 12
    assert names['P0'] == 'Provider 0'
    assert scope.name.casefold() == 'testshire'


async def test_paid_fulfilment_uses_pinned_postgres_source(source_db, tmp_path, monkeypatch):
    import hashlib
    from api.services import territory_brief_fulfilment as fulfilment
    conn, url = source_db
    files = snapshot(tmp_path)
    edition = load(url, files)
    scope, selected = await source.prepare_checkout(SCOPE)
    order_id = await conn.fetchval('''INSERT INTO territory_brief_orders
        (customer_email,stripe_price_id,scope_kind,scope_name,scope_window_days,
         scope_shortlist_target,stripe_checkout_session_id,source_edition_id)
        VALUES ('buyer@example.com','price_test','local_authority','Testshire',90,10,'cs_test',$1)
        RETURNING id''', selected)
    files[0].unlink()
    files[1].unlink()
    cfg = fulfilment.FulfilmentSettings(
        stripe_price_territory_brief='price_test', terms_version='test', terms_sha256='a'*64,
        consent_sha256=hashlib.sha256(fulfilment.TERRITORY_BRIEF_CONSENT_TEXT.encode()).hexdigest(),
        app_url='https://example.com',
    )
    session = dict(id='cs_test', metadata=fulfilment.build_checkout_metadata(str(order_id), SCOPE, cfg),
                   payment_status='paid', consent={'terms_of_service': 'accepted'},
                   line_items={'data': [{'price': {'id': 'price_test'}, 'quantity': 1}]},
                   payment_intent='pi_test', amount_total=74500, currency='gbp')
    uploads = {}
    def upload(order_id, kind, data, content_type):
        uploads[kind] = data
        return fulfilment.BlobRef(pathname=f'territory-briefs/{order_id}/brief.{kind}')
    async def audit(**kwargs):
        pass
    async def failure(*args):
        raise AssertionError('Unexpected fulfilment failure')
    def no_extra_connection():
        raise AssertionError('Generation must reuse the webhook connection')
    monkeypatch.setattr(source, 'get_connection', no_extra_connection)
    deps = fulfilment.FulfilmentDeps(
        generate=generate_pack, generate_with_connection=generate_pack, upload=upload,
        retrieve_session=lambda _: session, record_failure=failure, write_audit_log=audit,
    )
    async with conn.transaction():
        await fulfilment.fulfil_territory_brief_order(conn, session, cfg=cfg, deps=deps)
    row = await conn.fetchrow('SELECT status,source_edition_id FROM territory_brief_orders WHERE id=$1', order_id)
    assert row['status'] == 'fulfilled'
    assert row['source_edition_id'] == edition
    assert uploads['pdf'].startswith(b'%PDF')
    assert b'rating_changed' in uploads['csv']
    assert await conn.fetchval('SELECT count(*) FROM territory_brief_download_tokens WHERE order_id=$1', order_id) == 2
