#!/usr/bin/env python3
"""Import a reconciled CQC edition into Postgres, atomically and without truncation.

Run with `python -m tools.import_territory_brief_source --help`. The retrieval
stamp must come from the collection receipt, not file mtime or import time.
This command does not enable checkout or approve source reconciliation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values

from api.services.territory_brief import _latest_source_date
from api.services.territory_rating import resolve_rating
from tools.generate_radar_territory_sample import _load_ndjson, load_provider_names


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def import_edition(conn, locations_path: Path, providers_path: Path, retrieved_at: datetime,
                   rating_evidence_path: Path | None = None):
    if retrieved_at.tzinfo is None or retrieved_at > datetime.now(timezone.utc):
        raise ValueError('A timezone-aware, non-future collection retrieval time is required')
    names = load_provider_names(providers_path)
    if not names:
        raise ValueError('Provider source is empty')
    evidence_bytes = rating_evidence_path.read_bytes() if rating_evidence_path else b""
    supplemental = json.loads(evidence_bytes) if evidence_bytes else {}
    if not isinstance(supplemental, dict):
        raise ValueError('Rating evidence must be keyed by location ID')
    allowed = {'file_overall_rating', 'file_overall_rating_date', 'file_rating_source',
               'file_rating_source_sha256', 'file_rating_edition', 'file_rating_status',
               'rating_website_evidence', 'api_rating_status'}
    if any(not isinstance(v, dict) or set(v) - allowed for v in supplemental.values()):
        raise ValueError('Rating evidence contains unsupported fields')
    original_hashes = file_hash(locations_path), file_hash(providers_path)
    # The edition identity includes sidecar bytes; retries cannot silently reuse
    # an edition with different current-provider evidence.
    hashes = ((hashlib.sha256((original_hashes[0] + ':').encode() + evidence_bytes).hexdigest()
               if evidence_bytes else original_hashes[0]), original_hashes[1])
    # Two streaming passes avoid loading the national register into memory.
    count, as_of = 0, None
    seen_ids = set()
    for row in _load_ndjson(locations_path):
        count += 1
        location_id = str(row.get('locationId') or '').strip()
        seen_ids.add(location_id)
        enriched = {**row, **supplemental.get(location_id, {})}
        resolution = resolve_rating(enriched)
        if any(e.get('publication_date') and e['publication_date'] > retrieved_at.date().isoformat()
               for e in resolution['evidence']):
            raise ValueError('Rating evidence contains publication dates after retrieval')
        latest = _latest_source_date([enriched])
        if latest is not None:
            as_of = max(as_of, latest) if as_of else latest
    if set(supplemental) - seen_ids:
        raise ValueError('Rating evidence includes locations absent from source')
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
                row = {**row, **supplemental.get(location_id, {}),
                       'source_snapshot_sha256': original_hashes[0],
                       'source_edition': f'CQC API snapshot retrieved {retrieved_at.isoformat()}'}
                row['rating_resolution'] = resolve_rating(row)
                batch.append((edition_id, location_id, str(row.get('localAuthority') or '').strip(),
                              str(row.get('region') or '').strip(), names[provider_id], Json(row)))
                if len(batch) >= 500:
                    _insert(cur, batch)
                    batch.clear()
            if batch:
                _insert(cur, batch)
            if (original_hashes != (file_hash(locations_path), file_hash(providers_path))
                    or (rating_evidence_path and rating_evidence_path.read_bytes() != evidence_bytes)):
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
    parser.add_argument('--rating-evidence', type=Path, help='Pinned JSON evidence keyed by location ID')
    args = parser.parse_args()
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    try:
        edition_id = import_edition(conn, args.locations_source, args.providers_source, args.source_retrieved_at, args.rating_evidence)
        print(f'Imported immutable CQC evidence edition {edition_id}; checkout flags unchanged')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
