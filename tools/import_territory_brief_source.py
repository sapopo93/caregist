#!/usr/bin/env python3
"""Import a reconciled CQC edition into Postgres, atomically and without truncation.

Run with `python -m tools.import_territory_brief_source --help`. The retrieval
stamp must come from the collection receipt, not file mtime or import time.
This command does not enable checkout or approve source reconciliation.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

from api.services.territory_brief import _latest_source_date
from tools.generate_radar_territory_sample import _load_ndjson, load_provider_names


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def import_edition(conn, locations_path: Path, providers_path: Path, retrieved_at: datetime):
    if retrieved_at.tzinfo is None or retrieved_at > datetime.now(timezone.utc):
        raise ValueError('A timezone-aware, non-future collection retrieval time is required')
    names = load_provider_names(providers_path)
    if not names:
        raise ValueError('Provider source is empty')
    hashes = file_hash(locations_path), file_hash(providers_path)
    # Two streaming passes avoid loading the national register into memory.
    count, as_of = 0, None
    for row in _load_ndjson(locations_path):
        count += 1
        latest = _latest_source_date([row])
        if latest is not None:
            as_of = max(as_of, latest) if as_of else latest
    if not count or as_of is None or as_of > retrieved_at.date():
        raise ValueError('Source is empty, undated, or contains dates after retrieval')
    with conn:
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO territory_brief_source_editions
                (source_retrieved_at, source_as_of, locations_sha256, providers_sha256, location_count)
                VALUES (%s,%s,%s,%s,%s) RETURNING id''', (retrieved_at, as_of, *hashes, count))
            edition_id = cur.fetchone()[0]
            batch = []
            for row in _load_ndjson(locations_path):
                location_id = str(row.get('locationId') or '').strip()
                provider_id = str(row.get('providerId') or '').strip()
                if not location_id or not provider_id or provider_id not in names:
                    raise ValueError('Location lacks a verified provider identity/name')
                batch.append((edition_id, location_id, str(row.get('localAuthority') or '').strip(),
                              str(row.get('region') or '').strip(), names[provider_id], Json(row)))
                if len(batch) >= 500:
                    _insert(cur, batch)
                    batch.clear()
            if batch:
                _insert(cur, batch)
            if hashes != (file_hash(locations_path), file_hash(providers_path)):
                raise ValueError('Source files changed during import')
    return edition_id


def _insert(cur, rows):
    execute_values(cur, '''INSERT INTO territory_brief_source_locations
        (edition_id, location_id, local_authority, region, provider_name, payload) VALUES %s''', rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--locations-source', type=Path, required=True)
    parser.add_argument('--providers-source', type=Path, required=True)
    parser.add_argument('--source-retrieved-at', type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    try:
        edition_id = import_edition(conn, args.locations_source, args.providers_source, args.source_retrieved_at)
        print(f'Imported immutable CQC evidence edition {edition_id}; checkout flags unchanged')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
