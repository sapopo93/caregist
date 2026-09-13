#!/usr/bin/env python3
"""Build a draft manual-service pack from a read-only canonical database snapshot.

Requires DATABASE_URL and CQC_API_KEY in the process environment. Does not send
email, create orders, take payment, or change production data.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import httpx

from api.services.territory_manual_pack import BUYERS, build_pack, write_pack


async def capture(region):
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    try:
        async with conn.transaction(isolation='repeatable_read', readonly=True):
            rows = [dict(r) for r in await conn.fetch('''
                SELECT id,name,provider_id,region,local_authority,postcode,service_types,
                       overall_rating,registration_date,last_inspection_date,status,
                       signal_checked_at,last_updated
                FROM care_providers WHERE region=$1 AND upper(status)='ACTIVE'
                ORDER BY id
            ''', region)]
            source = await conn.fetchrow('''
                SELECT id,status,source_uri,source_retrieved_at,completed_at,
                       source_checksum_sha256,manifest_checksum_sha256
                FROM reconciliation_batches ORDER BY created_at DESC LIMIT 1
            ''')
            return rows, {k: str(v) if v is not None else None for k, v in dict(source or {}).items()}
    finally:
        await conn.close()


async def run(args):
    observed = datetime.now(timezone.utc)
    rows, source = await capture(args.region)
    kwargs = dict(region=args.region, buyer=args.buyer_type, service_type=args.service_type,
                  observed_at=observed, source_evidence=source, order_reference=args.order_reference)
    preliminary = build_pack(rows, provider_names={}, **kwargs)
    names = {}
    name_sources = []
    # Resolve official provider names for the ranked accounts. Do not substitute
    # site names or infer legal ownership from group labels.
    headers = {'Ocp-Apim-Subscription-Key': os.environ['CQC_API_KEY']}
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        for row in preliminary['shortlist']:
            pid = row['provider_id']
            response = await client.get(f'https://api.service.cqc.org.uk/public/v1/providers/{pid}')
            response.raise_for_status()
            payload = response.json()
            if payload.get('providerId') != pid or not str(payload.get('name') or '').strip():
                raise ValueError('CQC provider identity or name missing')
            names[pid] = payload['name'].strip()
            name_sources.append({'provider_id': pid, 'url': str(response.url),
                                 'checked_at': datetime.now(timezone.utc).isoformat(),
                                 'response_sha256': hashlib.sha256(response.content).hexdigest()})
            await asyncio.sleep(0.1)
    pack = build_pack(rows, provider_names=names, **kwargs)
    pack['provider_name_sources'] = name_sources
    evidence = write_pack(pack, args.out_dir)
    print(f"Draft: {len(pack['locations'])} locations; {pack['provider_count']} providers; {len(pack['shortlist'])} shortlisted")
    print('Source blockers: ' + '; '.join(evidence['blockers']))
    print(f'Output: {args.out_dir}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--region', required=True)
    p.add_argument('--buyer-type', choices=sorted(BUYERS), required=True)
    p.add_argument('--service-type', default='')
    p.add_argument('--order-reference', required=True)
    p.add_argument('--out-dir', type=Path, required=True)
    args = p.parse_args()
    asyncio.run(run(args))


if __name__ == '__main__':
    main()
