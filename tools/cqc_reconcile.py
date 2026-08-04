#!/usr/bin/env python3
"""Plan, stage, resume, and atomically publish an authoritative CQC snapshot.

The command is deliberately separate from ``incremental_update.py``. Shards
only write immutable staging records. Customer-visible ``care_providers`` rows,
the source watermark, and canonical feed events change together in finalize.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import uuid
import zlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import psycopg2
import psycopg2.extras
import requests

from incremental_update import (
    ALLOWED_COLUMNS,
    INCREMENTAL_UPDATE_LOCK_ID,
    _make_slug,
    _slugify,
    clean_location,
)


DEFAULT_DATA_PAGE_URL = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"
DEFAULT_API_BASE_URL = "https://api.service.cqc.org.uk/public/v1"
DEFAULT_CHECKPOINT_SIZE = 250
DEFAULT_MAX_RETRIES = 3
MIN_EXPECTED_LOCATIONS = 50_000
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
MANIFEST_SCHEMA_VERSION = 1
CONFIRM_PHRASE = "RECONCILE CQC PRODUCTION"
_CQC_ID_RE = re.compile(r"^(?:1-\d{5,12}|[A-Z][A-Z0-9-]{1,19})$")


class ReconciliationError(RuntimeError):
    """Raised when an invariant prevents reconciliation from continuing."""


class ShardBusy(ReconciliationError):
    """Raised when another worker owns the same shard."""


@dataclass(frozen=True)
class CqcSnapshot:
    source_uri: str
    source_published_at: date
    source_retrieved_at: datetime
    source_checksum_sha256: str
    location_ids: frozenset[str]


@dataclass(frozen=True)
class ReconciliationPlan:
    current_ids: frozenset[str]
    current_active_ids: frozenset[str]
    source_ids: frozenset[str]
    intersection_ids: frozenset[str]
    addition_ids: frozenset[str]
    reactivation_ids: frozenset[str]
    deactivation_ids: frozenset[str]

    def counts(self) -> dict[str, int]:
        return {
            "sourceCount": len(self.source_ids),
            "currentCount": len(self.current_active_ids),
            "intersectionCount": len(self.intersection_ids),
            "additionCount": len(self.addition_ids),
            "reactivationCount": len(self.reactivation_ids),
            "deactivationCount": len(self.deactivation_ids),
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def ids_sha256(values: Iterable[str]) -> str:
    return _sha256_json(sorted(values))


def _is_approved_cqc_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "cqc.org.uk" or host.endswith(".cqc.org.uk"))


def _is_approved_api_base(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() == "api.service.cqc.org.uk"


def normalize_database_url(value: str) -> str:
    """Use a direct Neon host because shard locks are session scoped."""
    parts = urlsplit(value)
    hostname = parts.hostname or ""
    if "-pooler." not in hostname or not parts.netloc:
        return value
    direct_host = hostname.replace("-pooler.", ".", 1)
    return urlunsplit(
        (parts.scheme, parts.netloc.replace(hostname, direct_host, 1), parts.path, parts.query, parts.fragment)
    )


def _request_with_retries(url: str, *, headers: dict[str, str], timeout: int = 90) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                final_url = str(getattr(response, "url", "") or url)
                if not _is_approved_cqc_url(final_url):
                    raise ReconciliationError("CQC source redirected outside the approved HTTPS host boundary")
                return response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise ReconciliationError(f"CQC source returned HTTP {response.status_code}")
            last_error = ReconciliationError(f"CQC source returned HTTP {response.status_code}")
        except requests.RequestException as exc:
            last_error = exc
        if attempt < DEFAULT_MAX_RETRIES:
            time.sleep(attempt)
    raise ReconciliationError(f"CQC source fetch failed after retries: {last_error}")


def fetch_snapshot(
    data_page_url: str = DEFAULT_DATA_PAGE_URL,
    *,
    min_expected: int = MIN_EXPECTED_LOCATIONS,
) -> CqcSnapshot:
    if not _is_approved_cqc_url(data_page_url):
        raise ReconciliationError("Refusing a non-CQC data page URL")
    headers = {"Accept": "text/html,text/csv", "User-Agent": "CareGist-Reconciler/2.0"}
    page = _request_with_retries(data_page_url, headers=headers)
    match = re.search(
        r'href=["\']([^"\']*CQC_directory\.csv(?:\?[^"\']*)?)["\']',
        page.text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ReconciliationError("Official CQC directory link was not found")
    source_uri = urljoin(data_page_url, match.group(1))
    if not _is_approved_cqc_url(source_uri):
        raise ReconciliationError("Refusing a directory outside the approved CQC HTTPS hosts")
    response = _request_with_retries(source_uri, headers=headers)
    content = response.content
    if not content:
        raise ReconciliationError("CQC directory was empty")

    lines = content.decode("utf-8-sig").splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if line.startswith("Name,Also known as,Address,")),
        None,
    )
    if header_index is None:
        raise ReconciliationError("CQC directory header was not recognised")
    preamble = "\n".join(lines[:header_index])
    published_match = re.search(r"produced on\s+([^,\r\n]+)", preamble, flags=re.IGNORECASE)
    if not published_match:
        raise ReconciliationError("CQC publication date was not found")
    try:
        published = datetime.strptime(published_match.group(1).strip(), "%d %B %Y").date()
    except ValueError as exc:
        raise ReconciliationError("CQC publication date was invalid") from exc
    if published > date.today():
        raise ReconciliationError("CQC publication date is in the future")

    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
    id_column = "CQC Location ID (for office use only)"
    if not reader.fieldnames or id_column not in reader.fieldnames:
        raise ReconciliationError("CQC location ID column was missing")
    ids: list[str] = []
    for row in reader:
        location_id = (row.get(id_column) or "").strip()
        if not location_id:
            continue
        if not _CQC_ID_RE.fullmatch(location_id):
            raise ReconciliationError(f"Invalid CQC location ID: {location_id[:40]}")
        ids.append(location_id)
    if len(ids) != len(set(ids)):
        raise ReconciliationError("CQC directory contains duplicate location IDs")
    if len(ids) < min_expected:
        raise ReconciliationError(f"CQC directory has {len(ids)} locations; expected at least {min_expected}")
    return CqcSnapshot(
        source_uri=source_uri,
        source_published_at=published,
        source_retrieved_at=datetime.now(timezone.utc),
        source_checksum_sha256=hashlib.sha256(content).hexdigest(),
        location_ids=frozenset(ids),
    )


def build_plan(snapshot: CqcSnapshot, rows: Iterable[tuple[Any, Any]]) -> ReconciliationPlan:
    current_ids: set[str] = set()
    active_ids: set[str] = set()
    for raw_id, raw_status in rows:
        if not raw_id:
            continue
        location_id = str(raw_id)
        current_ids.add(location_id)
        if str(raw_status or "").upper() == "ACTIVE":
            active_ids.add(location_id)
    inactive_ids = current_ids - active_ids
    source = snapshot.location_ids
    return ReconciliationPlan(
        current_ids=frozenset(current_ids),
        current_active_ids=frozenset(active_ids),
        source_ids=source,
        intersection_ids=frozenset(source & active_ids),
        addition_ids=frozenset(source - current_ids),
        reactivation_ids=frozenset(source & inactive_ids),
        deactivation_ids=frozenset(active_ids - source),
    )


def build_manifest(
    snapshot: CqcSnapshot,
    plan: ReconciliationPlan,
    *,
    batch_id: uuid.UUID,
    shard_count: int,
    max_deactivations: int,
) -> dict[str, Any]:
    validate_shard_coordinates(shard_count)
    if max_deactivations < 0:
        raise ValueError("max_deactivations must not be negative")
    if len(plan.deactivation_ids) > max_deactivations:
        raise ReconciliationError(
            f"Plan has {len(plan.deactivation_ids)} deactivations, above the approved ceiling {max_deactivations}"
        )
    payload: dict[str, Any] = {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "batchId": str(batch_id),
        "sourceUri": snapshot.source_uri,
        "sourcePublishedAt": snapshot.source_published_at.isoformat(),
        "sourceRetrievedAt": snapshot.source_retrieved_at.isoformat(),
        "sourceChecksumSha256": snapshot.source_checksum_sha256,
        "locationIds": sorted(snapshot.location_ids),
        **plan.counts(),
        "additionIdsSha256": ids_sha256(plan.addition_ids),
        "reactivationIdsSha256": ids_sha256(plan.reactivation_ids),
        "deactivationIdsSha256": ids_sha256(plan.deactivation_ids),
        "maxDeactivations": max_deactivations,
        "shardCount": shard_count,
    }
    return {**payload, "manifestChecksumSha256": _sha256_json(payload)}


def validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ReconciliationError("Manifest must be a JSON object")
    checksum = manifest.get("manifestChecksumSha256")
    payload = {key: value for key, value in manifest.items() if key != "manifestChecksumSha256"}
    if checksum != _sha256_json(payload):
        raise ReconciliationError("Manifest checksum does not match its contents")
    ids = manifest.get("locationIds")
    if not isinstance(ids, list) or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ReconciliationError("Manifest location IDs must be sorted and unique")
    if manifest.get("schemaVersion") != MANIFEST_SCHEMA_VERSION:
        raise ReconciliationError("Unsupported manifest schema version")
    if manifest.get("sourceCount") != len(ids):
        raise ReconciliationError("Manifest source count is inconsistent")
    validate_shard_coordinates(int(manifest.get("shardCount", 0)))
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"Unable to load manifest: {exc}") from exc
    return validate_manifest(manifest)


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_shard_coordinates(shard_count: int, shard_index: int | None = None) -> None:
    if shard_count < 1:
        raise ValueError("shard_count must be at least 1")
    if shard_index is not None and not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be between 0 and shard_count - 1")


def shard_for_location(location_id: str, shard_count: int) -> int:
    validate_shard_coordinates(shard_count)
    return zlib.crc32(location_id.encode("utf-8")) % shard_count


def partition_location_ids(location_ids: Iterable[str], shard_count: int) -> list[list[str]]:
    validate_shard_coordinates(shard_count)
    partitions: list[list[str]] = [[] for _ in range(shard_count)]
    for location_id in sorted(location_ids):
        partitions[shard_for_location(location_id, shard_count)].append(location_id)
    return partitions


def checkpoint_slices(location_ids: list[str], start: int, size: int):
    if size < 1:
        raise ValueError("checkpoint_size must be at least 1")
    if not 0 <= start <= len(location_ids):
        raise ValueError("checkpoint offset is outside the shard")
    offset = start
    while offset < len(location_ids):
        batch = location_ids[offset : offset + size]
        yield offset, batch
        offset += len(batch)


def _parse_batch_id(value: str | None) -> uuid.UUID:
    if not value:
        raise ValueError("--batch-id is required")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("--batch-id must be a UUID") from exc
    if str(parsed) != value.lower():
        raise ValueError("--batch-id must use canonical UUID form")
    return parsed


def _require_manifest_path(value: str | None) -> Path:
    if not value:
        raise ValueError("--manifest is required")
    return Path(value)


def _load_durable_manifest(
    args: argparse.Namespace,
    cur,
    batch_id: uuid.UUID,
) -> dict[str, Any]:
    cur.execute(
        "SELECT manifest FROM cqc_reconciliation_batches WHERE id = %s",
        (str(batch_id),),
    )
    row = cur.fetchone()
    if not row:
        raise ReconciliationError(f"Batch {batch_id} does not exist")
    durable = validate_manifest(row[0] if isinstance(row[0], dict) else json.loads(row[0]))
    if args.manifest:
        path = Path(args.manifest)
        if path.exists():
            artifact = load_manifest(path)
            if artifact != durable:
                raise ReconciliationError("Manifest artifact does not match the durable batch manifest")
        else:
            _write_manifest(path, durable)
    return durable


def _assert_write_confirmation(args: argparse.Namespace, manifest: dict[str, Any]) -> None:
    expected = {
        "confirm_phrase": CONFIRM_PHRASE,
        "confirm_source_sha256": manifest["sourceChecksumSha256"],
        "confirm_source_published_at": manifest["sourcePublishedAt"],
        "confirm_source_count": manifest["sourceCount"],
        "confirm_current_count": manifest["currentCount"],
        "confirm_intersection_count": manifest["intersectionCount"],
        "confirm_addition_count": manifest["additionCount"],
        "confirm_reactivation_count": manifest["reactivationCount"],
        "confirm_deactivation_count": manifest["deactivationCount"],
    }
    for attribute, value in expected.items():
        if getattr(args, attribute, None) != value:
            raise ReconciliationError(f"Write confirmation mismatch: --{attribute.replace('_', '-')}")


def _fetch_detail(base_url: str, api_key: str, location_id: str) -> dict[str, Any]:
    if not _is_approved_api_base(base_url):
        raise ReconciliationError("Refusing a non-CQC API base URL")
    headers = {
        "Accept": "application/json",
        "User-Agent": "CareGist-Reconciler/2.0",
        "Ocp-Apim-Subscription-Key": api_key,
        "Subscription-Key": api_key,
    }
    url = f"{base_url.rstrip('/')}/locations/{location_id}"
    last_status: int | None = None
    for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=False)
            last_status = response.status_code
            if response.status_code == 200:
                return response.json()
            if response.status_code not in RETRYABLE_STATUS_CODES:
                break
        except (requests.RequestException, ValueError):
            pass
        if attempt < DEFAULT_MAX_RETRIES:
            time.sleep(attempt)
    raise ReconciliationError(f"Detail fetch failed for {location_id} (last status {last_status})")


def _clean_and_verify_detail(location_id: str, detail: dict[str, Any]) -> dict[str, Any]:
    response_id = str(detail.get("locationId") or "")
    if response_id != location_id:
        raise ReconciliationError(
            f"CQC detail identity mismatch: requested {location_id}, received {response_id or '<missing>'}"
        )
    record = clean_location(detail)
    if not record or str(record.get("id") or "") != location_id:
        raise ReconciliationError(f"Cleaned CQC detail identity mismatch for {location_id}")
    last_updated = detail.get("lastUpdated") or detail.get("lastUpdatedDate") or detail.get("lastUpdatedTimestamp")
    if last_updated:
        record["last_updated"] = last_updated
    record["status"] = "ACTIVE"
    return record


def _record_for_json(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key in (ALLOWED_COLUMNS | {"last_updated"})}


def _prepare(args: argparse.Namespace, conn, cur) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    snapshot = fetch_snapshot(args.data_page_url)
    cur.execute("SELECT id, status FROM care_providers ORDER BY id")
    plan = build_plan(snapshot, cur.fetchall())
    manifest = build_manifest(
        snapshot,
        plan,
        batch_id=batch_id,
        shard_count=args.shard_count,
        max_deactivations=args.max_deactivations,
    )
    _write_manifest(_require_manifest_path(args.manifest), manifest)
    if args.dry_run:
        conn.rollback()
        print(json.dumps({"dryRun": True, **plan.counts(), "manifest": str(args.manifest)}, sort_keys=True))
        return 0
    _assert_write_confirmation(args, manifest)

    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-prepare', 0))")
    cur.execute(
        "SELECT id FROM cqc_reconciliation_batches WHERE status IN ('prepared', 'running') LIMIT 1"
    )
    active = cur.fetchone()
    if active:
        raise ReconciliationError(f"Batch {active[0]} is already active")
    cur.execute(
        "INSERT INTO pipeline_runs (run_type, status) VALUES ('reconciliation', 'running') RETURNING id"
    )
    pipeline_run_id = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO cqc_reconciliation_batches (
          id, pipeline_run_id, status, source_uri, source_published_at,
          source_retrieved_at, source_checksum_sha256, manifest_checksum_sha256, manifest,
          source_count, current_count, intersection_count, addition_count,
          reactivation_count, deactivation_count, deactivation_ids_sha256, shard_count
        ) VALUES (
          %s, %s, 'prepared', %s, %s, %s, %s, %s,
          %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            str(batch_id), pipeline_run_id, manifest["sourceUri"], manifest["sourcePublishedAt"],
            manifest["sourceRetrievedAt"], manifest["sourceChecksumSha256"],
            manifest["manifestChecksumSha256"], psycopg2.extras.Json(manifest),
            manifest["sourceCount"], manifest["currentCount"],
            manifest["intersectionCount"], manifest["additionCount"], manifest["reactivationCount"],
            manifest["deactivationCount"], manifest["deactivationIdsSha256"], manifest["shardCount"],
        ),
    )
    conn.commit()
    print(f"Prepared CQC reconciliation batch {batch_id}")
    return 0


def _validate_manifest_for_batch(cur, manifest: dict[str, Any], batch_id: uuid.UUID) -> None:
    cur.execute(
        """
        SELECT source_checksum_sha256, manifest_checksum_sha256, source_count,
               current_count, intersection_count, addition_count, reactivation_count,
               deactivation_count, deactivation_ids_sha256, shard_count
        FROM cqc_reconciliation_batches WHERE id = %s
        """,
        (str(batch_id),),
    )
    row = cur.fetchone()
    if not row:
        raise ReconciliationError(f"Batch {batch_id} does not exist")
    expected = (
        manifest["sourceChecksumSha256"], manifest["manifestChecksumSha256"], manifest["sourceCount"],
        manifest["currentCount"], manifest["intersectionCount"], manifest["additionCount"],
        manifest["reactivationCount"], manifest["deactivationCount"],
        manifest["deactivationIdsSha256"], manifest["shardCount"],
    )
    actual = tuple(str(value) if index in {0, 1, 8} else int(value) for index, value in enumerate(row))
    normalized_expected = tuple(
        str(value) if index in {0, 1, 8} else int(value) for index, value in enumerate(expected)
    )
    if actual != normalized_expected or manifest.get("batchId") != str(batch_id):
        raise ReconciliationError("Manifest does not match the prepared batch")


def _assert_live_plan_matches_manifest(
    plan: ReconciliationPlan,
    manifest: dict[str, Any],
) -> None:
    if plan.counts() != {
        key: int(manifest[key])
        for key in (
            "sourceCount",
            "currentCount",
            "intersectionCount",
            "additionCount",
            "reactivationCount",
            "deactivationCount",
        )
    }:
        raise ReconciliationError("Live provider classifications changed after approval")
    for category, manifest_key in (
        (plan.addition_ids, "additionIdsSha256"),
        (plan.reactivation_ids, "reactivationIdsSha256"),
        (plan.deactivation_ids, "deactivationIdsSha256"),
    ):
        if ids_sha256(category) != manifest[manifest_key]:
            raise ReconciliationError("Live provider identities changed after approval")


def _stage_record(cur, batch_id: uuid.UUID, shard_index: int, record: dict[str, Any]) -> None:
    payload = _record_for_json(record)
    payload_json = psycopg2.extras.Json(payload)
    cur.execute(
        """
        INSERT INTO cqc_reconciliation_records (
          batch_id, location_id, shard_index, record, record_sha256
        ) VALUES (
          %s, %s, %s, %s,
          encode(digest(convert_to((%s::jsonb)::text, 'UTF8'), 'sha256'), 'hex')
        )
        ON CONFLICT (batch_id, location_id) DO NOTHING
        """,
        (str(batch_id), record["id"], shard_index, payload_json, payload_json),
    )
    if cur.rowcount == 0:
        cur.execute(
            "SELECT shard_index, record FROM cqc_reconciliation_records WHERE batch_id = %s AND location_id = %s",
            (str(batch_id), record["id"]),
        )
        existing = cur.fetchone()
        existing_payload = existing[1] if existing and isinstance(existing[1], dict) else (
            json.loads(existing[1]) if existing else None
        )
        if not existing or int(existing[0]) != shard_index or existing_payload != payload:
            raise ReconciliationError(f"Staged record changed during replay: {record['id']}")


def _run_shard(args: argparse.Namespace, conn, cur, api_key: str) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    manifest = _load_durable_manifest(args, cur, batch_id)
    _validate_manifest_for_batch(cur, manifest, batch_id)
    _assert_write_confirmation(args, manifest)
    shard_count = int(manifest["shardCount"])
    validate_shard_coordinates(shard_count, args.shard_index)
    shard_index = int(args.shard_index)
    ids = partition_location_ids(manifest["locationIds"], shard_count)[shard_index]
    lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
    cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
    if not cur.fetchone()[0]:
        raise ShardBusy(f"Shard {shard_index} is already running")
    try:
        cur.execute(
            "SELECT status FROM cqc_reconciliation_batches WHERE id = %s FOR UPDATE",
            (str(batch_id),),
        )
        batch_state = cur.fetchone()
        if batch_state and batch_state[0] == "completed":
            cur.execute(
                """
                SELECT status, manifest_checksum_sha256, expected_count, next_offset
                FROM cqc_reconciliation_shards
                WHERE batch_id = %s AND shard_index = %s
                """,
                (str(batch_id), shard_index),
            )
            completed = cur.fetchone()
            if not completed or not (
                completed[0] == "completed"
                and str(completed[1]) == manifest["manifestChecksumSha256"]
                and int(completed[2]) == len(ids)
                and int(completed[3]) == len(ids)
            ):
                raise ReconciliationError("Completed batch shard state is inconsistent")
            conn.rollback()
            return 0
        if not batch_state or batch_state[0] not in {"prepared", "running"}:
            raise ReconciliationError("Batch is not eligible for shard execution")
        cur.execute(
            """
            INSERT INTO cqc_reconciliation_shards (
              batch_id, shard_index, status, manifest_checksum_sha256, expected_count
            ) VALUES (%s, %s, 'running', %s, %s)
            ON CONFLICT (batch_id, shard_index) DO NOTHING
            """,
            (str(batch_id), shard_index, manifest["manifestChecksumSha256"], len(ids)),
        )
        cur.execute(
            """
            SELECT status, manifest_checksum_sha256, expected_count, next_offset
            FROM cqc_reconciliation_shards
            WHERE batch_id = %s AND shard_index = %s FOR UPDATE
            """,
            (str(batch_id), shard_index),
        )
        state = cur.fetchone()
        if not state:
            raise ReconciliationError("Shard state could not be created")
        if str(state[1]) != manifest["manifestChecksumSha256"] or int(state[2]) != len(ids):
            raise ReconciliationError("Shard state does not match the manifest")
        if state[0] == "completed":
            conn.rollback()
            return 0
        offset = int(state[3])
        cur.execute(
            "UPDATE cqc_reconciliation_shards SET status = 'running', error_message = NULL, updated_at = NOW() WHERE batch_id = %s AND shard_index = %s",
            (str(batch_id), shard_index),
        )
        cur.execute("UPDATE cqc_reconciliation_batches SET status = 'running' WHERE id = %s", (str(batch_id),))
        conn.commit()

        for checkpoint_offset, checkpoint in checkpoint_slices(ids, offset, args.checkpoint_size):
            if checkpoint_offset != offset:
                raise ReconciliationError("Checkpoint offset moved unexpectedly")
            for location_id in checkpoint:
                detail = _fetch_detail(args.api_base_url, api_key, location_id)
                record = _clean_and_verify_detail(location_id, detail)
                _stage_record(cur, batch_id, shard_index, record)
                if args.sleep:
                    time.sleep(args.sleep)
            offset += len(checkpoint)
            cur.execute(
                """
                UPDATE cqc_reconciliation_shards
                SET next_offset = %s, updated_at = NOW()
                WHERE batch_id = %s AND shard_index = %s
                """,
                (offset, str(batch_id), shard_index),
            )
            conn.commit()

        cur.execute(
            """
            UPDATE cqc_reconciliation_shards
            SET status = 'completed', completed_at = NOW(), updated_at = NOW()
            WHERE batch_id = %s AND shard_index = %s
            """,
            (str(batch_id), shard_index),
        )
        conn.commit()
        return 0
    except Exception as exc:
        conn.rollback()
        cur.execute(
            """
            UPDATE cqc_reconciliation_shards
            SET status = 'failed', error_message = %s, updated_at = NOW()
            WHERE batch_id = %s AND shard_index = %s AND status != 'completed'
            """,
            (str(exc)[:4000], str(batch_id), shard_index),
        )
        conn.commit()
        raise
    finally:
        cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))
        conn.commit()


_PROVIDER_UPDATE_COLUMNS = tuple(sorted((ALLOWED_COLUMNS | {"last_updated"}) - {"id", "slug"}))


def _apply_provider_record(cur, record: dict[str, Any]) -> str:
    location_id = str(record["id"])
    safe = {key: record.get(key) for key in _PROVIDER_UPDATE_COLUMNS}
    cur.execute("SELECT id FROM care_providers WHERE id = %s", (location_id,))
    exists = cur.fetchone() is not None
    if not exists:
        slug = _make_slug(str(record.get("name") or ""), str(record.get("town") or ""), location_id)
        cur.execute("SELECT id FROM care_providers WHERE slug = %s", (slug,))
        collision = cur.fetchone()
        if collision and str(collision[0]) != location_id:
            suffix = _slugify(location_id, separator="-") or location_id.lower()
            slug = f"{slug}-{suffix}"
        columns = ["id", "slug", *_PROVIDER_UPDATE_COLUMNS]
        values = [location_id, slug, *(safe[column] for column in _PROVIDER_UPDATE_COLUMNS)]
        cur.execute(
            f"INSERT INTO care_providers ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})",
            values,
        )
        return "inserted"

    assignments = ", ".join(f"{column} = %s" for column in _PROVIDER_UPDATE_COLUMNS)
    differences = " OR ".join(f"{column} IS DISTINCT FROM %s" for column in _PROVIDER_UPDATE_COLUMNS)
    values = [safe[column] for column in _PROVIDER_UPDATE_COLUMNS]
    cur.execute(
        f"UPDATE care_providers SET {assignments} WHERE id = %s AND ({differences}) RETURNING id",
        [*values, location_id, *values],
    )
    return "updated" if cur.fetchone() else "unchanged"


def _sync_new_registration_ledger(cur) -> int:
    cur.execute(
        """
        INSERT INTO trusted_event_ledger (
          entity_type, entity_id, provider_id, location_id, event_type,
          effective_date, observed_at, old_value, new_value, source,
          confidence_score, dedupe_key, metadata
        )
        SELECT
          'care_provider', cp.id, cp.provider_id, cp.id, 'new_registration',
          cp.registration_date, COALESCE(cp.last_updated, cp.updated_at, cp.created_at, NOW()),
          NULL,
          jsonb_build_object(
            'name', cp.name, 'slug', cp.slug, 'status', cp.status, 'type', cp.type,
            'registration_date', cp.registration_date, 'region', cp.region,
            'local_authority', cp.local_authority, 'postcode', cp.postcode,
            'service_types', cp.service_types
          ),
          'cqc_reconciliation', 1.0000,
          CONCAT('new_registration:', cp.id, ':', cp.registration_date::text),
          jsonb_build_object(
            'name', cp.name, 'slug', cp.slug, 'town', cp.town, 'county', cp.county,
            'region', cp.region, 'local_authority', cp.local_authority,
            'postcode', cp.postcode, 'service_types', cp.service_types
          )
        FROM care_providers cp
        WHERE cp.registration_date IS NOT NULL AND UPPER(cp.status) = 'ACTIVE'
        ON CONFLICT (dedupe_key) DO NOTHING
        """
    )
    return cur.rowcount


def _verify_staged_records(cur, manifest: dict[str, Any], batch_id: uuid.UUID) -> None:
    shard_count = int(manifest["shardCount"])
    expected_shards = {
        location_id: shard_for_location(location_id, shard_count)
        for location_id in manifest["locationIds"]
    }
    cur.execute(
        """
        SELECT location_id, shard_index, record, record_sha256,
               encode(digest(convert_to(record::text, 'UTF8'), 'sha256'), 'hex')
        FROM cqc_reconciliation_records
        WHERE batch_id = %s
        ORDER BY location_id
        """,
        (str(batch_id),),
    )
    rows = cur.fetchall()
    if len(rows) != int(manifest["sourceCount"]):
        raise ReconciliationError("Staged record count does not match the manifest")
    if [str(row[0]) for row in rows] != manifest["locationIds"]:
        raise ReconciliationError("Staged record identities do not exactly match the manifest")
    for location_id, shard_index, record, stored_hash, computed_hash in rows:
        payload = record if isinstance(record, dict) else json.loads(record)
        if payload.get("id") != location_id:
            raise ReconciliationError(f"Staged payload identity mismatch: {location_id}")
        if int(shard_index) != expected_shards[str(location_id)]:
            raise ReconciliationError(f"Staged shard membership mismatch: {location_id}")
        if str(stored_hash) != str(computed_hash):
            raise ReconciliationError(f"Staged payload hash mismatch: {location_id}")


def _verify_completed_publication(
    cur,
    manifest: dict[str, Any],
    pipeline_run_id: int,
) -> None:
    cur.execute("SELECT id FROM care_providers WHERE UPPER(status) = 'ACTIVE' ORDER BY id")
    if [str(row[0]) for row in cur.fetchall()] != manifest["locationIds"]:
        raise ReconciliationError("Completed batch no longer matches the active provider set")
    cur.execute(
        """
        SELECT status, source_uri, source_published_at, source_retrieved_at,
               source_checksum_sha256, source_record_count, active_records_after
        FROM pipeline_runs WHERE id = %s
        """,
        (pipeline_run_id,),
    )
    run = cur.fetchone()
    if not run:
        raise ReconciliationError("Completed batch pipeline run is missing")
    actual = (
        run[0], str(run[1]), run[2].isoformat(),
        run[3].astimezone(timezone.utc).isoformat(),
        str(run[4]), int(run[5]), int(run[6]),
    )
    expected = (
        "completed", manifest["sourceUri"], manifest["sourcePublishedAt"],
        datetime.fromisoformat(manifest["sourceRetrievedAt"]).astimezone(timezone.utc).isoformat(),
        manifest["sourceChecksumSha256"], int(manifest["sourceCount"]),
        int(manifest["sourceCount"]),
    )
    if actual != expected:
        raise ReconciliationError("Completed batch watermark does not match its durable manifest")


def _finalize(args: argparse.Namespace, conn, cur) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    manifest = _load_durable_manifest(args, cur, batch_id)
    _validate_manifest_for_batch(cur, manifest, batch_id)
    _assert_write_confirmation(args, manifest)
    shard_count = int(manifest["shardCount"])
    cur.execute(
        """
        SELECT shard_index, status, expected_count, next_offset, manifest_checksum_sha256
        FROM cqc_reconciliation_shards WHERE batch_id = %s ORDER BY shard_index
        """,
        (str(batch_id),),
    )
    shards = cur.fetchall()
    expected_partitions = partition_location_ids(manifest["locationIds"], shard_count)
    if not (
        len(shards) == shard_count
        and [int(row[0]) for row in shards] == list(range(shard_count))
        and all(row[1] == "completed" for row in shards)
        and all(int(row[2]) == len(expected_partitions[index]) for index, row in enumerate(shards))
        and all(int(row[3]) == int(row[2]) for row in shards)
        and all(str(row[4]) == manifest["manifestChecksumSha256"] for row in shards)
    ):
        raise ReconciliationError("Shard coverage is incomplete or inconsistent")
    _verify_staged_records(cur, manifest, batch_id)

    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-finalize', 0))")
    cur.execute("SELECT pg_advisory_xact_lock(%s)", (INCREMENTAL_UPDATE_LOCK_ID,))
    cur.execute(
        "SELECT status, pipeline_run_id FROM cqc_reconciliation_batches WHERE id = %s FOR UPDATE",
        (str(batch_id),),
    )
    batch = cur.fetchone()
    if not batch:
        raise ReconciliationError("Batch is not eligible for finalization")
    pipeline_run_id = int(batch[1])

    # Serialize the complete classification check and publish against every
    # writer, including legacy jobs that do not take this reconciler's lock.
    cur.execute("LOCK TABLE care_providers IN SHARE ROW EXCLUSIVE MODE")
    if batch[0] == "completed":
        _verify_completed_publication(cur, manifest, pipeline_run_id)
        conn.commit()
        print(json.dumps({"batchId": str(batch_id), "idempotent": True, "status": "completed"}))
        return 0
    if batch[0] not in {"prepared", "running"}:
        raise ReconciliationError("Batch is not eligible for finalization")
    source_ids = manifest["locationIds"]
    cur.execute("SELECT id, status FROM care_providers ORDER BY id")
    live_snapshot = CqcSnapshot(
        source_uri=manifest["sourceUri"],
        source_published_at=date.fromisoformat(manifest["sourcePublishedAt"]),
        source_retrieved_at=datetime.fromisoformat(manifest["sourceRetrievedAt"]),
        source_checksum_sha256=manifest["sourceChecksumSha256"],
        location_ids=frozenset(source_ids),
    )
    live_plan = build_plan(live_snapshot, cur.fetchall())
    _assert_live_plan_matches_manifest(live_plan, manifest)
    deactivation_ids = sorted(live_plan.deactivation_ids)

    cur.execute(
        """
        SELECT source_published_at, source_checksum_sha256
        FROM pipeline_runs
        WHERE status = 'completed' AND source_published_at IS NOT NULL
        ORDER BY source_published_at DESC, completed_at DESC LIMIT 1
        """
    )
    latest = cur.fetchone()
    manifest_date = date.fromisoformat(manifest["sourcePublishedAt"])
    if latest:
        if manifest_date < latest[0]:
            raise ReconciliationError("Source publication date would regress the watermark")
        if manifest_date == latest[0] and manifest["sourceChecksumSha256"] != str(latest[1]):
            raise ReconciliationError("Same-date source checksum conflicts with the watermark")

    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    cur.execute(
        "SELECT record FROM cqc_reconciliation_records WHERE batch_id = %s ORDER BY location_id",
        (str(batch_id),),
    )
    for row in cur.fetchall():
        record = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        counts[_apply_provider_record(cur, record)] += 1
    if deactivation_ids:
        cur.execute(
            "UPDATE care_providers SET status = 'INACTIVE' WHERE id = ANY(%s) AND UPPER(status) = 'ACTIVE'",
            (deactivation_ids,),
        )
        if cur.rowcount != len(deactivation_ids):
            raise ReconciliationError("Deactivation update count changed during finalization")
    ledger_events = _sync_new_registration_ledger(cur)
    cur.execute("SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE'")
    active_after = int(cur.fetchone()[0])
    if active_after != int(manifest["sourceCount"]):
        raise ReconciliationError("Final active count does not match the source")
    cur.execute(
        "SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE' AND id = ANY(%s)",
        (source_ids,),
    )
    if int(cur.fetchone()[0]) != active_after:
        raise ReconciliationError("Final active IDs do not exactly match the source")

    cur.execute(
        """
        UPDATE cqc_reconciliation_batches
        SET status = 'completed', completed_at = NOW(), records_inserted = %s,
            records_updated = %s, records_unchanged = %s, records_deactivated = %s,
            ledger_events_inserted = %s, error_message = NULL
        WHERE id = %s
        """,
        (
            counts["inserted"], counts["updated"], counts["unchanged"], len(deactivation_ids),
            ledger_events, str(batch_id),
        ),
    )
    cur.execute(
        """
        UPDATE pipeline_runs
        SET status = 'completed', completed_at = NOW(), records_added = %s,
            records_updated = %s, records_deactivated = %s, source_uri = %s,
            source_published_at = %s, source_retrieved_at = %s,
            source_checksum_sha256 = %s, source_record_count = %s,
            active_records_before = %s, active_records_after = %s, error_message = NULL
        WHERE id = %s
        """,
        (
            counts["inserted"], counts["updated"], len(deactivation_ids), manifest["sourceUri"],
            manifest["sourcePublishedAt"], manifest["sourceRetrievedAt"],
            manifest["sourceChecksumSha256"], manifest["sourceCount"], manifest["currentCount"],
            active_after, pipeline_run_id,
        ),
    )
    conn.commit()
    print(json.dumps({"batchId": str(batch_id), **counts, "deactivated": len(deactivation_ids)}))
    return 0


def _abort(args: argparse.Namespace, conn, cur) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    manifest = _load_durable_manifest(args, cur, batch_id)
    _validate_manifest_for_batch(cur, manifest, batch_id)
    _assert_write_confirmation(args, manifest)
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-finalize', 0))")
    cur.execute(
        "SELECT shard_count, status, pipeline_run_id FROM cqc_reconciliation_batches WHERE id = %s FOR UPDATE",
        (str(batch_id),),
    )
    batch = cur.fetchone()
    if not batch:
        raise ReconciliationError("Batch is not eligible for abort")
    if batch[1] == "failed":
        conn.rollback()
        print(json.dumps({"batchId": str(batch_id), "idempotent": True, "status": "failed"}))
        return 0
    if batch[1] not in {"prepared", "running"}:
        raise ReconciliationError("Batch is not eligible for abort")
    held: list[str] = []
    try:
        for shard_index in range(int(batch[0])):
            lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
            cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
            if not cur.fetchone()[0]:
                raise ShardBusy(f"Shard {shard_index} is still running")
            held.append(lock_key)
        reason = "Reconciliation explicitly aborted before finalization"
        cur.execute(
            "UPDATE cqc_reconciliation_shards SET status = 'failed', error_message = %s, updated_at = NOW() WHERE batch_id = %s AND status != 'completed'",
            (reason, str(batch_id)),
        )
        cur.execute(
            "UPDATE cqc_reconciliation_batches SET status = 'failed', completed_at = NOW(), error_message = %s WHERE id = %s",
            (reason, str(batch_id)),
        )
        cur.execute(
            "UPDATE pipeline_runs SET status = 'failed', completed_at = NOW(), error_message = %s WHERE id = %s",
            (reason, int(batch[2])),
        )
        conn.commit()
        return 0
    finally:
        for lock_key in held:
            cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))
        conn.commit()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepare", "shard", "finalize", "abort"), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--batch-id")
    parser.add_argument("--manifest")
    parser.add_argument("--data-page-url", default=DEFAULT_DATA_PAGE_URL)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--shard-count", type=int, default=4)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--checkpoint-size", type=int, default=DEFAULT_CHECKPOINT_SIZE)
    parser.add_argument("--sleep", type=float, default=0.08)
    parser.add_argument("--max-deactivations", type=int, default=0)
    parser.add_argument("--confirm-phrase")
    parser.add_argument("--confirm-source-sha256")
    parser.add_argument("--confirm-source-published-at")
    parser.add_argument("--confirm-source-count", type=int)
    parser.add_argument("--confirm-current-count", type=int)
    parser.add_argument("--confirm-intersection-count", type=int)
    parser.add_argument("--confirm-addition-count", type=int)
    parser.add_argument("--confirm-reactivation-count", type=int)
    parser.add_argument("--confirm-deactivation-count", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.database_url:
        print("ERROR: DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1
    if args.dry_run and args.phase != "prepare":
        print("ERROR: only prepare supports --dry-run", file=sys.stderr)
        return 1
    if args.phase == "shard" and args.shard_index is None:
        print("ERROR: --shard-index is required", file=sys.stderr)
        return 1
    api_key = os.getenv("CQC_SUBSCRIPTION_KEY") or os.getenv("CQC_API_KEY")
    if args.phase == "shard" and not api_key:
        print("ERROR: CQC_API_KEY is required for shard execution", file=sys.stderr)
        return 1
    try:
        conn = psycopg2.connect(normalize_database_url(args.database_url))
        conn.autocommit = False
        cur = conn.cursor()
        try:
            if args.phase == "prepare":
                return _prepare(args, conn, cur)
            if args.phase == "shard":
                return _run_shard(args, conn, cur, str(api_key))
            if args.phase == "finalize":
                return _finalize(args, conn, cur)
            return _abort(args, conn, cur)
        finally:
            cur.close()
            conn.close()
    except (ReconciliationError, ValueError, psycopg2.Error) as exc:
        print(f"CQC reconciliation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
