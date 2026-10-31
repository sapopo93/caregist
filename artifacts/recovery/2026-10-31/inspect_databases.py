"""Read-only migration and schema evidence; prints no database credentials."""
import asyncio
import datetime
import json
import pathlib

import asyncpg
from dotenv import dotenv_values

ROOT = pathlib.Path('/Users/user/CareGist')
OUT = pathlib.Path(__file__).parent
BRIEF = ['territory_brief_orders', 'territory_brief_consents',
         'territory_brief_download_tokens', 'territory_brief_scope_versions',
         'territory_brief_scope_exclusions']

async def snapshot(conn):
    result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    result['database'] = await conn.fetchval('SELECT current_database()')
    result['migrations'] = [dict(r) for r in await conn.fetch(
        'SELECT filename, applied_at::text FROM schema_migrations ORDER BY filename')]
    result['counts'] = {}
    for table in BRIEF + ['care_providers', 'users', 'subscriptions', 'api_keys',
                          'territory_brief_source_editions', 'territory_brief_source_locations']:
        result['counts'][table] = await conn.fetchval(f'SELECT count(*) FROM {table}')
    result['provider_status_counts'] = [dict(r) for r in await conn.fetch(
        'SELECT status,count(*) FROM care_providers GROUP BY status ORDER BY status')]
    result['columns'] = [dict(r) for r in await conn.fetch(
        "SELECT table_name,column_name,data_type,is_nullable,column_default "
        "FROM information_schema.columns WHERE table_schema=current_schema() "
        "AND table_name=ANY($1::text[]) ORDER BY table_name,column_name", BRIEF)]
    result['constraints'] = [dict(r) for r in await conn.fetch(
        "SELECT conrelid::regclass::text AS table_name,conname,pg_get_constraintdef(oid) AS definition "
        "FROM pg_constraint WHERE conrelid=ANY(SELECT to_regclass(t) FROM unnest($1::text[]) t) "
        "ORDER BY 1,2", BRIEF)]
    result['triggers'] = [dict(r) for r in await conn.fetch(
        "SELECT tgrelid::regclass::text AS table_name,tgname,pg_get_triggerdef(oid) AS definition "
        "FROM pg_trigger WHERE NOT tgisinternal "
        "AND tgrelid=ANY(SELECT to_regclass(t) FROM unnest($1::text[]) t) ORDER BY 1,2", BRIEF)]
    result['table_access'] = [dict(r) for r in await conn.fetch(
        "SELECT relname,pg_get_userbyid(relowner) AS owner,relacl::text,relrowsecurity,relforcerowsecurity "
        "FROM pg_class WHERE oid=ANY(SELECT to_regclass(t) FROM unnest($1::text[]) t) ORDER BY 1", BRIEF)]
    return result

async def main():
    urls = {'production': dotenv_values(ROOT / '.env')['DATABASE_URL'],
            'staging': dotenv_values(ROOT / '.env.local')['STAGING_DATABASE_URL']}
    for label, url in urls.items():
        conn = await asyncpg.connect(url, timeout=20)
        try:
            async with conn.transaction(readonly=True, isolation='repeatable_read'):
                await conn.execute("SET LOCAL statement_timeout='30s'")
                data = await snapshot(conn)
            (OUT / f'{label}-before.json').write_text(json.dumps(data, indent=2, default=str))
            print(label, json.dumps({'last_migrations': data['migrations'][-3:], 'counts': data['counts'],
                  'table_access': data['table_access']}), flush=True)
        finally:
            await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
