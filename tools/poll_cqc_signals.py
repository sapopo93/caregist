#!/usr/bin/env python3
"""Poll approved CQC sources for new locations and recently published reports.

The first location-index run is a bootstrap only: it records the full CQC ID
set without treating historical IDs as new. Subsequent runs fetch details only
for newly observed IDs, report candidates, and a bounded rolling sweep.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from urllib.parse import urljoin

import psycopg2
from psycopg2.extras import execute_values

from incremental_update import (
    DEFAULT_BASE_URL,
    ChangesFetchError,
    _fetch_all_cqc_location_stubs,
    _request_with_retries,
    clean_location,
    fetch_location_detail,
    get_api_key,
    get_database_url,
    normalize_database_url,
    upsert_provider,
)


REPORT_INDEX_URL = "https://www.cqc.org.uk/search/all"
REPORT_INDEX_PARAMS = {
    "display": "list",
    "filters[]": [
        "archived:active",
        "lastPublished:all",
        "more_services:all",
        "services:all",
        "specialisms:all",
    ],
    "last-published": "week",
    "location-query": "",
    "query": "",
    "radius": "",
    "sort": "date",
}
SIGNAL_POLL_LOCK_ID = 802451204
DEFAULT_SWEEP_SIZE = 1200
DEFAULT_CHECKPOINT_SIZE = 100
LOCATION_ID_PATTERN = re.compile(r"/location/(?P<location_id>1-\d{5,12})(?:[/?#\"'])")


def fetch_report_candidates() -> tuple[set[str], bytes, str]:
    response = _request_with_retries(
        REPORT_INDEX_URL,
        headers={"Accept": "text/html", "User-Agent": "CareGist-Signal-Poller/1.0"},
        params=REPORT_INDEX_PARAMS,
        timeout=60,
    )
    content = response.content
    location_ids = {match.group("location_id") for match in LOCATION_ID_PATTERN.finditer(response.text)}
    return location_ids, content, str(response.url or REPORT_INDEX_URL)


def _snapshot_hash(location_ids: set[str]) -> str:
    canonical = "\n".join(sorted(location_ids)).encode()
    return hashlib.sha256(canonical).hexdigest()


def _upsert_source_snapshot(
    cur,
    *,
    source_type: str,
    source_uri: str,
    checksum_sha256: str,
    record_count: int,
    checked_at: datetime,
) -> int:
    cur.execute(
        """
        INSERT INTO source_snapshots (
          source_type, source_uri, source_checked_at,
          checksum_sha256, record_count, status
        )
        VALUES (%s, %s, %s, %s, %s, 'verified')
        ON CONFLICT (source_type, checksum_sha256) DO NOTHING
        RETURNING id
        """,
        (source_type, source_uri, checked_at, checksum_sha256, record_count),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        "SELECT id FROM source_snapshots WHERE source_type = %s AND checksum_sha256 = %s",
        (source_type, checksum_sha256),
    )
    return int(cur.fetchone()[0])


def _update_run_evidence(
    cur,
    run_id: int,
    *,
    source_total: int,
    checked: int,
    successes: int,
    failures: int,
    checkpoint_state: dict,
) -> None:
    """Persist collection coverage alongside the provider checkpoint."""
    cur.execute(
        """
        UPDATE pipeline_runs
        SET source_total_count = %s, checked_count = %s,
            success_count = %s, failure_count = %s,
            checkpoint_state = %s::jsonb
        WHERE id = %s
        """,
        (
            source_total,
            checked,
            successes,
            failures,
            json.dumps(checkpoint_state, sort_keys=True),
            run_id,
        ),
    )


def _record_location_index(
    cur,
    location_ids: set[str],
    *,
    snapshot_id: int,
    checked_at: datetime,
) -> tuple[bool, list[str]]:
    cur.execute("SELECT COUNT(*) FROM cqc_location_index_entries")
    bootstrapping = int(cur.fetchone()[0] or 0) == 0
    new_ids: list[str] = []
    if not bootstrapping:
        cur.execute(
            "SELECT location_id FROM cqc_location_index_entries WHERE location_id = ANY(%s)",
            (sorted(location_ids),),
        )
        known = {str(row[0]) for row in cur.fetchall()}
        new_ids = sorted(location_ids - known)

    execute_values(
        cur,
        """
        INSERT INTO cqc_location_index_entries (
          location_id, first_seen_at, last_seen_at, last_snapshot_id, is_present
        ) VALUES %s
        ON CONFLICT (location_id) DO UPDATE
        SET last_seen_at = EXCLUDED.last_seen_at,
            last_snapshot_id = EXCLUDED.last_snapshot_id,
            is_present = TRUE
        """,
        [(location_id, checked_at, checked_at, snapshot_id, True) for location_id in sorted(location_ids)],
        page_size=5000,
    )
    cur.execute(
        """
        UPDATE cqc_location_index_entries
        SET is_present = FALSE
        WHERE is_present = TRUE AND last_seen_at < %s
        """,
        (checked_at,),
    )
    return bootstrapping, new_ids


def _rolling_sweep_ids(cur, limit: int) -> list[str]:
    cur.execute(
        """
        SELECT id
        FROM care_providers
        WHERE UPPER(status) = 'ACTIVE'
        ORDER BY signal_checked_at ASC NULLS FIRST, id ASC
        LIMIT %s
        """,
        (limit,),
    )
    return [str(row[0]) for row in cur.fetchall()]


def _report_source_date(detail: dict) -> object:
    candidates = [detail.get("lastReport")]
    reports = detail.get("reports")
    if isinstance(reports, list):
        candidates.extend(reports)
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key in ("publicationDate", "publishedDate", "reportDate", "date"):
            if candidate.get(key):
                return candidate[key]
    return detail.get("lastUpdated") or detail.get("lastUpdatedDate")


def _absolute_report_url(value: str | None) -> str | None:
    if not value:
        return None
    return urljoin("https://www.cqc.org.uk", value)


def run_signal_poll(
    database_url: str,
    api_key: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    sweep_size: int = DEFAULT_SWEEP_SIZE,
    checkpoint_size: int = DEFAULT_CHECKPOINT_SIZE,
    sleep: float = 0.05,
    index_enabled: bool = True,
    report_enabled: bool = True,
) -> dict[str, int | bool]:
    if not index_enabled and not report_enabled:
        return {"skipped": True, "new_ids": 0, "report_candidates": 0, "processed": 0, "events": 0}
    checked_at = datetime.now(UTC)
    conn = psycopg2.connect(normalize_database_url(database_url))
    conn.autocommit = False
    cur = conn.cursor()
    lock_acquired = False
    run_id = None
    try:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (SIGNAL_POLL_LOCK_ID,))
        lock_acquired = bool(cur.fetchone()[0])
        if not lock_acquired:
            return {"skipped": True, "new_ids": 0, "report_candidates": 0, "processed": 0, "events": 0}

        intended_provenance = {
            "locationIndex": {
                "enabled": index_enabled,
                "uri": f"{base_url}/locations" if index_enabled else None,
            },
            "reportIndex": {
                "enabled": report_enabled,
                "uri": REPORT_INDEX_URL if report_enabled else None,
            },
        }
        cur.execute(
            """
            INSERT INTO pipeline_runs (
              run_type, started_at, status, source_provenance,
              checkpoint_state, counts_reconciled, reconciled_at
            )
            VALUES ('signal_poll', %s, 'running', %s::jsonb, %s::jsonb, FALSE, NULL)
            RETURNING id
            """,
            (
                checked_at,
                json.dumps(intended_provenance, sort_keys=True),
                json.dumps({"nextOffset": 0, "restartable": False, "restartMode": "fresh_run"}),
            ),
        )
        run_id = int(cur.fetchone()[0])
        conn.commit()

        location_ids: set[str] = set()
        index_checksum: str | None = None
        index_snapshot_id: int | None = None
        new_ids: list[str] = []
        bootstrapped = False
        if index_enabled:
            stubs = _fetch_all_cqc_location_stubs(base_url, api_key, sleep)
            location_ids = {
                str(stub.get("locationId") or stub.get("id"))
                for stub in stubs
                if stub.get("locationId") or stub.get("id")
            }
            index_checksum = _snapshot_hash(location_ids)
            index_snapshot_id = _upsert_source_snapshot(
                cur,
                source_type="cqc_location_index",
                source_uri=f"{base_url}/locations",
                checksum_sha256=index_checksum,
                record_count=len(location_ids),
                checked_at=checked_at,
            )
            bootstrapped, new_ids = _record_location_index(
                cur,
                location_ids,
                snapshot_id=index_snapshot_id,
                checked_at=checked_at,
            )

        report_ids: set[str] = set()
        report_checksum: str | None = None
        report_snapshot_id: int | None = None
        report_uri = REPORT_INDEX_URL
        if report_enabled:
            report_ids, report_content, report_uri = fetch_report_candidates()
            report_checksum = hashlib.sha256(report_content).hexdigest()
            report_snapshot_id = _upsert_source_snapshot(
                cur,
                source_type="cqc_report_index",
                source_uri=report_uri,
                checksum_sha256=report_checksum,
                record_count=len(report_ids),
                checked_at=checked_at,
            )
        rolling_ids = _rolling_sweep_ids(cur, sweep_size)
        conn.commit()

        ordered_ids = list(dict.fromkeys([*new_ids, *sorted(report_ids), *rolling_ids]))
        source_provenance = {
            "locationIndex": {
                "enabled": index_enabled,
                "uri": f"{base_url}/locations" if index_enabled else None,
                "checksumSha256": index_checksum,
                "snapshotId": index_snapshot_id,
                "recordCount": len(location_ids),
            },
            "reportIndex": {
                "enabled": report_enabled,
                "uri": report_uri if report_enabled else None,
                "checksumSha256": report_checksum,
                "snapshotId": report_snapshot_id,
                "recordCount": len(report_ids),
            },
        }
        cur.execute(
            """
            UPDATE pipeline_runs
            SET source_total_count = %s, source_provenance = %s::jsonb,
                source_uri = %s, source_retrieved_at = %s,
                source_checksum_sha256 = %s, source_record_count = %s,
                checkpoint_state = %s::jsonb,
                counts_reconciled = FALSE, reconciled_at = NULL
            WHERE id = %s
            """,
            (
                len(ordered_ids), json.dumps(source_provenance, sort_keys=True),
                f"{base_url}/locations" if index_enabled else report_uri, checked_at,
                index_checksum if index_enabled else report_checksum,
                len(location_ids) if index_enabled else len(report_ids),
                json.dumps({"nextOffset": 0, "restartable": False, "restartMode": "fresh_run"}), run_id,
            ),
        )
        conn.commit()
        events_before = 0
        if ordered_ids:
            cur.execute("SELECT COUNT(*) FROM trusted_event_ledger")
            events_before = int(cur.fetchone()[0] or 0)

        processed = 0
        inserted = 0
        updated = 0
        failures = 0
        failure_details: list[dict[str, str]] = []
        for index, location_id in enumerate(ordered_ids, start=1):
            detail = fetch_location_detail(base_url, api_key, location_id)
            if detail is None:
                failures += 1
                failure_details.append(
                    {"locationId": location_id, "reason": "detail_fetch_failed"}
                )
                if index % checkpoint_size == 0:
                    _update_run_evidence(
                        cur, run_id, source_total=len(ordered_ids), checked=index,
                        successes=processed, failures=failures,
                        checkpoint_state={
                            "nextOffset": index, "lastLocationId": location_id,
                            "restartable": False, "restartMode": "fresh_run",
                            "failures": failure_details,
                        },
                    )
                    conn.commit()
                continue
            record = clean_location(detail)
            if record is None:
                failures += 1
                failure_details.append(
                    {"locationId": location_id, "reason": "detail_clean_failed"}
                )
                if index % checkpoint_size == 0:
                    _update_run_evidence(
                        cur, run_id, source_total=len(ordered_ids), checked=index,
                        successes=processed, failures=failures,
                        checkpoint_state={
                            "nextOffset": index, "lastLocationId": location_id,
                            "restartable": False, "restartMode": "fresh_run",
                            "failures": failure_details,
                        },
                    )
                    conn.commit()
                continue
            is_report_candidate = location_id in report_ids
            report_url = _absolute_report_url(record.get("inspection_report_url"))
            if report_url:
                record["inspection_report_url"] = report_url
            record.update(
                {
                    "source_snapshot_id": report_snapshot_id if is_report_candidate else index_snapshot_id,
                    "source_snapshot_sha256": report_checksum if is_report_candidate else index_checksum,
                    "source_url": report_url if is_report_candidate and report_url else f"{base_url}/locations/{location_id}",
                    "source_checked_at": checked_at,
                    "source_published_at": _report_source_date(detail),
                }
            )
            action = upsert_provider(cur, record)
            cur.execute("UPDATE care_providers SET signal_checked_at = %s WHERE id = %s", (checked_at, location_id))
            processed += 1
            inserted += int(action == "inserted")
            updated += int(action == "updated")
            if index % checkpoint_size == 0:
                _update_run_evidence(
                    cur, run_id, source_total=len(ordered_ids), checked=index,
                    successes=processed, failures=failures,
                    checkpoint_state={
                        "nextOffset": index, "lastLocationId": location_id,
                        "restartable": False, "restartMode": "fresh_run",
                        "failures": failure_details,
                    },
                )
                conn.commit()
            time.sleep(sleep)
        cur.execute("SELECT COUNT(*) FROM trusted_event_ledger")
        events_after = int(cur.fetchone()[0] or 0)
        event_count = max(0, events_after - events_before)
        _update_run_evidence(
            cur, run_id, source_total=len(ordered_ids), checked=len(ordered_ids),
            successes=processed, failures=failures,
            checkpoint_state={
                "nextOffset": len(ordered_ids), "restartable": False,
                "fullCoverage": failures == 0,
                "failures": failure_details,
            },
        )
        cur.execute(
            """
            UPDATE pipeline_runs
            SET completed_at = NOW(), status = %s,
                records_added = %s, records_updated = %s,
                source_uri = %s, source_retrieved_at = %s,
                source_checksum_sha256 = %s, source_record_count = %s,
                error_message = %s
            WHERE id = %s
            """,
            (
                "completed" if failures == 0 else "partial",
                inserted,
                updated,
                f"{base_url}/locations" if index_enabled else report_uri,
                checked_at,
                index_checksum if index_enabled else report_checksum,
                len(location_ids) if index_enabled else len(report_ids),
                None if failures == 0 else f"{failures} source records failed collection",
                run_id,
            ),
        )
        conn.commit()
        return {
            "skipped": False,
            "bootstrapped": bootstrapped,
            "new_ids": len(new_ids),
            "report_candidates": len(report_ids),
            "processed": processed,
            "events": event_count,
        }
    except Exception as exc:
        conn.rollback()
        if run_id is not None:
            cur.execute(
                """
                UPDATE pipeline_runs
                SET completed_at = NOW(), status = 'failed', error_message = %s,
                    counts_reconciled = FALSE, reconciled_at = NULL,
                    checkpoint_state = checkpoint_state || %s::jsonb
                WHERE id = %s
                """,
                (
                    str(exc)[:4000],
                    json.dumps({
                        "restartable": False,
                        "restartMode": "fresh_run",
                        "failure": str(exc)[:1000],
                    }),
                    run_id,
                ),
            )
            conn.commit()
        raise
    finally:
        if lock_acquired:
            try:
                cur.execute("SELECT pg_advisory_unlock(%s)", (SIGNAL_POLL_LOCK_ID,))
            except Exception:
                pass
        cur.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll approved CQC signal sources")
    parser.add_argument("--database-url")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--sweep-size", type=int, default=DEFAULT_SWEEP_SIZE)
    parser.add_argument("--checkpoint-size", type=int, default=DEFAULT_CHECKPOINT_SIZE)
    parser.add_argument("--sleep", type=float, default=0.05)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.sweep_size <= 5000 or not 1 <= args.checkpoint_size <= 1000:
        print("ERROR: sweep/checkpoint sizes are outside safe bounds.", file=sys.stderr)
        return 1
    index_enabled = os.getenv("CQC_LOCATION_INDEX_POLL_ENABLED", "false").strip().lower() == "true"
    report_enabled = os.getenv("CQC_REPORT_POLL_ENABLED", "false").strip().lower() == "true"
    if not index_enabled and not report_enabled:
        print("Signal poll skipped: both collector kill switches are disabled.")
        return 0
    database_url = normalize_database_url(args.database_url) if args.database_url else get_database_url()
    api_key = get_api_key()
    if not database_url or not api_key:
        print("ERROR: DATABASE_URL and CQC_API_KEY are required.", file=sys.stderr)
        return 1
    try:
        result = run_signal_poll(
            database_url,
            api_key,
            base_url=args.base_url,
            sweep_size=args.sweep_size,
            checkpoint_size=args.checkpoint_size,
            sleep=max(0.0, args.sleep),
            index_enabled=index_enabled,
            report_enabled=report_enabled,
        )
    except (ChangesFetchError, psycopg2.Error, ValueError) as exc:
        print(f"Signal poll failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
