"""Bounded 072/073 production runner; dry-run unless --apply is explicit.

Uses the reviewed worktree SQL, target-specific credentials in memory, per-file
transactions and timeouts. Never runs the old run_072.py script.
"""
import argparse
import asyncio
import hashlib
import json
import pathlib
import subprocess
import urllib.parse

import asyncpg
from dotenv import dotenv_values
from inspect_databases import BRIEF, OUT, ROOT, snapshot

WORK = pathlib.Path('/tmp/caregist-migrations-072-073')
CANDIDATE = '73613c03a8fa9bb1eb6691fb17d16094ee211138'
FILES = {
    '072_shared_customer_package.sql': 'e7307bcff25f47c6492f84b16ea9a86f8876022e8237bce5a6a496d01e53f177',
    '073_rebuild_territory_brief_tables.sql': '7e7b3821c0547a9abd5ca9760bbfdde71ba04d8520d91741c165acf6091c77c3',
}

def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, default=str))

async def read_snapshot(c):
    async with c.transaction(readonly=True, isolation='repeatable_read'):
        await c.execute("SET LOCAL statement_timeout='30s'")
        return await snapshot(c)

async def main(apply):
    if not __debug__:
        raise RuntimeError('Optimized Python disables guards; refuse execution')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORK, text=True).strip()
    assert head == CANDIDATE, 'Worktree is not the frozen reviewed candidate'
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=WORK, text=True).strip()
    for name, expected in FILES.items():
        assert hashlib.sha256((WORK / 'db/migrations' / name).read_bytes()).hexdigest() == expected

    prod = dotenv_values(ROOT / '.env')['DATABASE_URL']
    stage = dotenv_values(ROOT / '.env.local')['STAGING_DATABASE_URL']
    assert prod != stage, 'Staging and production credentials must differ'
    assert urllib.parse.urlsplit(prod).hostname == 'ep-wandering-grass-abgnc3qe-pooler.eu-west-2.aws.neon.tech', 'Production endpoint differs from the established production binding'
    s = await asyncpg.connect(stage, timeout=20)
    try:
        staged = await read_snapshot(s)
        assert set(FILES) <= {r['filename'] for r in staged['migrations']}
        assert any(r['table_name'] == 'territory_brief_orders' and r['column_name'] == 'source_edition_id'
                   for r in staged['columns'])
    finally:
        await s.close()

    p = await asyncpg.connect(prod, timeout=20)
    try:
        assert await p.fetchval('SELECT current_user') == 'neondb_owner'
        pre = await read_snapshot(p)
        all_names = {f.name for f in (WORK / 'db/migrations').glob('[0-9][0-9][0-9]_*.sql')}
        missing = all_names - {r['filename'] for r in pre['migrations']}
        assert missing == set(FILES), f'Unexpected pending migration set: {sorted(missing)}'
        assert all(pre['counts'][t] == 0 for t in BRIEF), 'A Brief table is populated; stop'
        assert all(r['owner'] == 'neondb_owner' and r['relacl'] is None
                   and not r['relrowsecurity'] and not r['relforcerowsecurity'] for r in pre['table_access'])
        save('production-immediate-preflight.json', pre)
        print('Production preflight passed: exactly072/073 pending, five Brief tables empty, ownership/ACL/RLS match review.', flush=True)
        if not apply:
            return

        journal = {'candidate': CANDIDATE, 'recovery_branch': 'br-floral-paper-abjaq0oa', 'applied': []}
        save('application-journal.json', journal)
        for name, sha in FILES.items():
            async with p.transaction(isolation='read_committed'):
                await p.execute("SET LOCAL lock_timeout='10s'")
                await p.execute("SET LOCAL statement_timeout='120s'")
                await p.execute((WORK / 'db/migrations' / name).read_text())
                await p.execute('INSERT INTO schema_migrations(filename) VALUES($1)', name)
            journal['applied'].append({'filename': name, 'sha256': sha})
            save('application-journal.json', journal)
            print('Applied', name, flush=True)

        post = await read_snapshot(p)
        save('production-after.json', post)
        assert set(FILES) <= {r['filename'] for r in post['migrations']}
        assert post['counts'] == pre['counts'], 'Counts changed; investigate before declaring completion'
        assert post['provider_status_counts'] == pre['provider_status_counts']
        assert post['table_access'] == pre['table_access']
        def signature(data):
            return sorted((r['table_name'], r['column_name'], r['data_type'], r['is_nullable'], r['column_default'])
                          for r in data['columns'])
        assert signature(post) == signature(staged), 'Production columns differ from accepted staging schema'
        assert any(r['table_name'] == 'territory_brief_orders' and 'source_edition_id' in r['definition']
                   and 'FOREIGN KEY' in r['definition'] and 'ON DELETE RESTRICT' in r['definition']
                   for r in post['constraints'])
        assert any(r['table_name'] == 'territory_brief_download_tokens'
                   and 'artifact_kind' in r['definition'] and "'zip'" in r['definition']
                   for r in post['constraints'])
        print('Verified migration ledger, schema parity with staging, source FK, zip check, unchanged counts and access.', flush=True)
    finally:
        await p.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    asyncio.run(main(args.apply))
