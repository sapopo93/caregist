#!/usr/bin/env python3
"""Prepare, shard, resume, and finalize an authoritative CQC reconciliation batch.

Usage:
    python3 incremental_update.py --phase prepare --batch-id UUID --shard-count 8 --snapshot-manifest manifest.json
    python3 incremental_update.py --phase resume --batch-id UUID --snapshot-manifest manifest.json
    python3 incremental_update.py --phase shard --batch-id UUID --shard-count 8 --shard-index 0 --snapshot-manifest manifest.json
    python3 incremental_update.py --phase finalize --batch-id UUID --shard-count 8 --snapshot-manifest manifest.json
    python3 incremental_update.py --phase abort --batch-id UUID
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
import unicodedata
import uuid
import zlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Sequence
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import psycopg2
from psycopg2.extras import Json
import requests

from api.services.provider_state_events import ProviderStateEvent, build_provider_state_events
from api.services.rating_states import (
    NON_RATED_STATES,
    assess_location_rating,
    is_published_value,
    normalize_rating_text,
    stored_rating_is_published,
)
from cqc_common import normalize_whitespace, parse_any_date, to_float

try:
    from slugify import slugify as _slugify
except ImportError:
    def _slugify(value: str, separator: str = "-") -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        lowered = re.sub(r"[^a-z0-9]+", separator, normalized.lower()).strip(separator)
        return re.sub(rf"{re.escape(separator)}+", separator, lowered)


def _make_slug(name: str, town: str, location_id: str) -> str:
    """Generate a URL slug from name + town, falling back to location_id."""
    base = _slugify(f"{name}-{town}" if town else name, separator="-")
    if not base:
        base = _slugify(location_id, separator="-") or f"provider-{location_id.lower()}"
    return base

DEFAULT_BASE_URL = "https://api.service.cqc.org.uk/public/v1"
DEFAULT_DATA_PAGE_URL = "https://www.cqc.org.uk/about-us/transparency/using-cqc-data"
DEFAULT_SLEEP = 0.15
DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_MAX_RETRIES = 3
DETAIL_MAX_RETRIES = 5
DETAIL_MAX_BACKOFF_SECONDS = 30
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
LOCATION_LIST_RETRYABLE_STATUS_CODES = RETRYABLE_STATUS_CODES | {403}
LOCATION_LIST_MAX_RETRIES = 5
LOCATION_LIST_MAX_BACKOFF_SECONDS = 60.0
MIN_EXPECTED_ACTIVE_LOCATIONS = 50_000
MAX_ACTIVE_COUNT_DROP_RATIO = 0.05
DEFAULT_CHECKPOINT_SIZE = 250
# Must not exceed care_providers.phone (VARCHAR(50) as of migration 059).
PHONE_MAX_LENGTH = 50
_CQC_ID_RE = re.compile(r"^(?:1-\d{5,12}|[A-Z][A-Z0-9-]{1,19})$")


class ChangesFetchError(RuntimeError):
    """Raised when the CQC changes API cannot be fetched reliably."""


class ShardAlreadyRunning(ChangesFetchError):
    """Raised without mutating batch state when another worker owns the shard."""


def _location_list_retry_delay(
    retry_after: str | None,
    attempt: int,
    *,
    now: datetime | None = None,
) -> float:
    """Return a bounded delay for numeric or HTTP-date Retry-After values."""
    delay: float
    if retry_after is None:
        delay = 15.0 * attempt
    else:
        try:
            delay = float(retry_after)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                reference = now or datetime.now(timezone.utc)
                delay = (retry_at - reference).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = 15.0 * attempt
    return min(LOCATION_LIST_MAX_BACKOFF_SECONDS, max(0.0, delay))


@dataclass(frozen=True)
class CqcActiveSnapshot:
    source_uri: str
    source_published_at: str
    retrieved_at: datetime
    checksum_sha256: str
    location_ids: frozenset[str]


def validate_shard_coordinates(shard_count: int, shard_index: int | None = None) -> None:
    if shard_count < 1:
        raise ValueError("shard_count must be at least 1")
    if shard_index is not None and not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be between 0 and shard_count - 1")


def shard_for_location(location_id: str, shard_count: int) -> int:
    validate_shard_coordinates(shard_count)
    return zlib.crc32(location_id.encode("utf-8")) % shard_count


def partition_location_ids(location_ids: list[str], shard_count: int) -> list[list[str]]:
    """Return exhaustive, non-overlapping, deterministic shard partitions."""
    validate_shard_coordinates(shard_count)
    partitions: list[list[str]] = [[] for _ in range(shard_count)]
    for location_id in sorted(location_ids):
        partitions[shard_for_location(location_id, shard_count)].append(location_id)
    return partitions


def checkpoint_slices(location_ids: list[str], start_offset: int, checkpoint_size: int):
    """Yield resumable checkpoint boundaries without replaying committed offsets."""
    if checkpoint_size < 1:
        raise ValueError("checkpoint_size must be at least 1")
    if not 0 <= start_offset <= len(location_ids):
        raise ValueError("start_offset is outside the shard")
    offset = start_offset
    while offset < len(location_ids):
        checkpoint = location_ids[offset : offset + checkpoint_size]
        yield offset, checkpoint
        offset += len(checkpoint)


def _manifest_payload(snapshot: CqcActiveSnapshot, batch_id: uuid.UUID, shard_count: int) -> dict[str, Any]:
    validate_shard_coordinates(shard_count)
    return {
        "schemaVersion": 1,
        "batchId": str(batch_id),
        "sourceUri": snapshot.source_uri,
        "sourcePublishedAt": snapshot.source_published_at,
        "sourceRetrievedAt": snapshot.retrieved_at.isoformat(),
        "sourceChecksumSha256": snapshot.checksum_sha256,
        "shardCount": shard_count,
        "locationCount": len(snapshot.location_ids),
        "locationIds": sorted(snapshot.location_ids),
    }


def manifest_checksum(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_snapshot_manifest(snapshot: CqcActiveSnapshot, batch_id: uuid.UUID, shard_count: int) -> dict[str, Any]:
    payload = _manifest_payload(snapshot, batch_id, shard_count)
    return {**payload, "manifestChecksumSha256": manifest_checksum(payload)}


def load_snapshot_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ChangesFetchError(f"Unable to load snapshot manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ChangesFetchError("Snapshot manifest must be a JSON object.")
    supplied_checksum = manifest.pop("manifestChecksumSha256", None)
    calculated_checksum = manifest_checksum(manifest)
    manifest["manifestChecksumSha256"] = supplied_checksum
    if supplied_checksum != calculated_checksum:
        raise ChangesFetchError("Snapshot manifest checksum does not match its contents.")
    ids = manifest.get("locationIds")
    if not isinstance(ids, list) or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ChangesFetchError("Snapshot manifest location IDs must be sorted and unique.")
    if manifest.get("locationCount") != len(ids):
        raise ChangesFetchError("Snapshot manifest location count is inconsistent.")
    validate_shard_coordinates(int(manifest.get("shardCount", 0)))
    return manifest


def _request_with_retries(
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = 90,
) -> requests.Response:
    """GET an authoritative CQC resource with bounded retry/backoff."""
    last_error: Exception | None = None
    for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            if response.status_code == 200:
                final_url = response.url if isinstance(getattr(response, "url", None), str) else url
                if not _is_cqc_https_url(final_url):
                    raise ChangesFetchError("CQC source redirected outside the approved HTTPS host boundary.")
                return response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise ChangesFetchError(f"CQC resource returned {response.status_code}: {url}")
            last_error = ChangesFetchError(f"CQC resource returned {response.status_code}: {url}")
        except requests.RequestException as exc:
            last_error = exc
        if attempt < DEFAULT_MAX_RETRIES:
            time.sleep(attempt)
    raise ChangesFetchError(f"Unable to fetch CQC resource {url}: {last_error}")


def _is_cqc_https_url(value: str) -> bool:
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (hostname == "cqc.org.uk" or hostname.endswith(".cqc.org.uk"))


def fetch_active_location_snapshot(
    data_page_url: str = DEFAULT_DATA_PAGE_URL,
    *,
    min_expected: int = MIN_EXPECTED_ACTIVE_LOCATIONS,
) -> CqcActiveSnapshot:
    """Download and validate CQC's current active-location directory CSV.

    CQC removed the changes endpoint. Its public directory CSV is the bounded,
    authoritative active-location set used to discover additions and candidate
    deactivations. Individual API details are still fetched before any write --
    including in the finalize path, where a location absent from the snapshot is
    only deactivated once the live API confirms it is not registered (see
    confirm_deactivation_candidates).
    """
    headers = {"Accept": "text/html,text/csv", "User-Agent": "CareGist-Reconciler/1.0"}
    page = _request_with_retries(data_page_url, headers=headers)
    match = re.search(
        r'href=["\']([^"\']*CQC_directory\.csv(?:\?[^"\']*)?)["\']',
        page.text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ChangesFetchError("Current CQC directory CSV link was not found on the official data page.")

    source_uri = urljoin(data_page_url, match.group(1))
    if not _is_cqc_https_url(source_uri):
        raise ChangesFetchError("Refusing non-CQC or non-HTTPS directory source URI.")

    csv_response = _request_with_retries(source_uri, headers=headers)
    content = csv_response.content
    if not content:
        raise ChangesFetchError("CQC directory CSV was empty.")

    decoded = content.decode("utf-8-sig")
    lines = decoded.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if line.startswith("Name,Also known as,Address,")),
        None,
    )
    if header_index is None:
        raise ChangesFetchError("CQC directory CSV header was not recognised.")

    preamble = "\n".join(lines[:header_index])
    published_match = re.search(r"produced on\s+([^,\r\n]+)", preamble, flags=re.IGNORECASE)
    if not published_match:
        raise ChangesFetchError("CQC directory publication date was not found.")
    try:
        source_published_at = datetime.strptime(
            published_match.group(1).strip(), "%d %B %Y"
        ).date().isoformat()
    except ValueError as exc:
        raise ChangesFetchError("CQC directory publication date was invalid.") from exc

    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
    id_column = "CQC Location ID (for office use only)"
    if not reader.fieldnames or id_column not in reader.fieldnames:
        raise ChangesFetchError("CQC directory location ID column was missing.")

    ids: list[str] = []
    for row in reader:
        location_id = (row.get(id_column) or "").strip()
        if location_id:
            if not _CQC_ID_RE.fullmatch(location_id):
                raise ChangesFetchError(f"Invalid CQC location ID in snapshot: {location_id[:40]}")
            ids.append(location_id)

    unique_ids = frozenset(ids)
    if len(unique_ids) != len(ids):
        raise ChangesFetchError("CQC directory contains duplicate location IDs.")
    if len(unique_ids) < min_expected:
        raise ChangesFetchError(
            f"CQC directory contains only {len(unique_ids)} locations; expected at least {min_expected}."
        )

    return CqcActiveSnapshot(
        source_uri=source_uri,
        source_published_at=source_published_at,
        retrieved_at=datetime.now(timezone.utc),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        location_ids=unique_ids,
    )


def build_snapshot_reconciliation(
    snapshot: CqcActiveSnapshot,
    *,
    db_ids: frozenset[str],
    db_active_ids: frozenset[str],
) -> dict[str, frozenset[str]]:
    """Return deterministic detail-fetch sets for a full authoritative pass."""
    if db_active_ids:
        drop_ratio = len(db_active_ids - snapshot.location_ids) / len(db_active_ids)
        if drop_ratio > MAX_ACTIVE_COUNT_DROP_RATIO:
            raise ChangesFetchError(
                f"Snapshot would remove {drop_ratio:.1%} of active locations; refusing reconciliation."
            )
    return {
        "new_ids": snapshot.location_ids - db_ids,
        "candidate_deactivation_ids": db_active_ids - snapshot.location_ids,
        "detail_ids": snapshot.location_ids | (db_active_ids - snapshot.location_ids),
    }


def get_api_key() -> str | None:
    key = os.getenv("CQC_SUBSCRIPTION_KEY") or os.getenv("CQC_API_KEY")
    if key:
        return key
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CQC_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def get_database_url() -> str | None:
    url = os.getenv("DATABASE_URL")
    if url:
        return normalize_database_url(url)
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                # This project's .env quotes its values. Without stripping the
                # quotes the DSN reaches psycopg2 still wrapped in them, which
                # fails to parse AND puts the raw connection string -- password
                # included -- into the traceback.
                value = line.split("=", 1)[1].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                return normalize_database_url(value)
    return None


def normalize_database_url(url: str) -> str:
    """Use Neon's direct endpoint for session-locking maintenance jobs."""
    parts = urlsplit(url)
    hostname = parts.hostname or ""
    if "-pooler." not in hostname or not parts.netloc:
        return url

    direct_host = hostname.replace("-pooler.", ".", 1)
    direct_netloc = parts.netloc.replace(hostname, direct_host, 1)
    return urlunsplit((parts.scheme, direct_netloc, parts.path, parts.query, parts.fragment))


def api_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": "CareGist-Updater/1.0"}
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = api_key
        headers["Subscription-Key"] = api_key
    return headers


def fetch_changes(base_url: str, api_key: str | None, since: str, sleep: float) -> list[str] | None:
    """Fetch location IDs changed since a given date.

    Returns a list of changed location IDs, or None if the changes endpoint is
    unavailable (404/410) — caller should fall back to fetch_recent_via_list_scan().
    Raises ChangesFetchError for other non-retryable failures.
    """
    url = f"{base_url}/changes/location"
    headers = api_headers(api_key)
    changed_ids: list[str] = []
    page = 1

    while True:
        params = {"startTimestamp": since, "page": page, "perPage": 1000}
        try:
            resp = None
            for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                if page == 1:
                    print(f"  /changes/location response code: {resp.status_code}")
                if resp.status_code == 200:
                    break
                if resp.status_code in RETRYABLE_STATUS_CODES and attempt < DEFAULT_MAX_RETRIES:
                    time.sleep(max(sleep, attempt))
                    continue
                if resp.status_code in (404, 410):
                    return None  # Endpoint gone — caller should use list scan fallback
                raise ChangesFetchError(f"Changes API returned {resp.status_code} on page {page}")
            data = resp.json()
            changes = data.get("changes", [])
            if not changes:
                break
            for change in changes:
                loc_id = change.get("locationId") or change.get("id", "")
                if loc_id:
                    changed_ids.append(str(loc_id))
            total = data.get("total", 0)
            print(f"  Changes page {page}: {len(changes)} changes (total: {total})")
            if len(changed_ids) >= total:
                break
            page += 1
            time.sleep(sleep)
        except Exception as exc:
            if isinstance(exc, ChangesFetchError):
                raise
            raise ChangesFetchError(f"Error fetching changes page {page}: {exc}") from exc

    return list(set(changed_ids))


def _fetch_all_cqc_location_stubs(
    base_url: str,
    api_key: str | None,
    sleep: float,
    *,
    min_expected: int = MIN_EXPECTED_ACTIVE_LOCATIONS,
) -> list[dict]:
    """Fetch a complete, internally consistent snapshot from GET /locations."""
    url = f"{base_url}/locations"
    headers = api_headers(api_key)
    all_items: list[dict] = []
    seen_ids: set[str] = set()
    expected_total: int | None = None
    page = 1
    while True:
        resp = None
        last_network_error: requests.RequestException | None = None
        for attempt in range(1, LOCATION_LIST_MAX_RETRIES + 1):
            try:
                resp = requests.get(
                    url,
                    headers=headers,
                    params={"page": page, "perPage": 1000},
                    timeout=30,
                )
            except requests.RequestException as exc:
                last_network_error = exc
                if attempt == LOCATION_LIST_MAX_RETRIES:
                    raise ChangesFetchError(
                        f"Location list scan network failure on page {page} after {attempt} attempts"
                    ) from exc
            else:
                if resp.status_code == 200:
                    break
                if (
                    resp.status_code not in LOCATION_LIST_RETRYABLE_STATUS_CODES
                    or attempt == LOCATION_LIST_MAX_RETRIES
                ):
                    raise ChangesFetchError(
                        f"Location list scan returned {resp.status_code} on page {page} "
                        f"after {attempt} attempts"
                    )

            retry_after = None if resp is None else resp.headers.get("Retry-After")
            time.sleep(_location_list_retry_delay(retry_after, attempt))
        else:  # pragma: no cover - defensive; loop either breaks or raises
            raise ChangesFetchError(
                f"Location list scan failed on page {page}: {last_network_error or 'retry budget exhausted'}"
            )

        try:
            assert resp is not None
            data = resp.json()
            locations = data.get("locations")
            if not isinstance(locations, list):
                raise ChangesFetchError(f"Location list scan returned an invalid payload on page {page}")
            total = int(data.get("total", 0))
            if total < min_expected:
                raise ChangesFetchError(
                    f"Location list scan reported only {total} records on page {page}; "
                    f"expected at least {min_expected}"
                )
            if expected_total is None:
                expected_total = total
            elif total != expected_total:
                raise ChangesFetchError(
                    f"Location list scan total changed from {expected_total} to {total} on page {page}"
                )
            if not locations:
                raise ChangesFetchError(
                    f"Location list scan ended early on page {page} after "
                    f"{len(all_items)}/{expected_total} records"
                )

            page_ids: list[str] = []
            for item in locations:
                if not isinstance(item, dict):
                    raise ChangesFetchError(f"Location list scan returned a malformed record on page {page}")
                location_id = str(item.get("locationId") or item.get("id") or "").strip()
                if not location_id:
                    raise ChangesFetchError(f"Location list scan returned a record without an ID on page {page}")
                page_ids.append(location_id)
            duplicates = seen_ids.intersection(page_ids)
            if len(page_ids) != len(set(page_ids)) or duplicates:
                raise ChangesFetchError(f"Location list scan returned duplicate IDs on page {page}")

            all_items.extend(locations)
            seen_ids.update(page_ids)
            if (page % 20) == 0:
                print(f"  Fetched {len(all_items)}/{total} location IDs from CQC list...")
            if len(all_items) > total:
                raise ChangesFetchError(
                    f"Location list scan exceeded its reported total on page {page}: {len(all_items)}/{total}"
                )
            if len(all_items) == total:
                break
            page += 1
            time.sleep(sleep)
        except ChangesFetchError:
            raise
        except Exception as exc:
            raise ChangesFetchError(f"Location list scan error on page {page}: {exc}") from exc
    if expected_total is None or len(all_items) != expected_total or len(seen_ids) != expected_total:
        raise ChangesFetchError("Location list scan did not produce a complete unique snapshot")
    return all_items


def fetch_recent_via_list_scan(
    base_url: str,
    api_key: str | None,
    since: str,
    sleep: float,
    *,
    db_known_ids: frozenset[str],
) -> list[str]:
    """Fallback when /changes/location is unavailable.

    Strategy:
    1. Use care_providers IDs from the database as the known baseline.
    2. Fetch all current location IDs from GET /locations.
    3. Return IDs present in CQC but absent from the database.

    Detail fetch, cleaning, date filtering, and upsert are handled by main().
    No file cache is read or written because the database is the source of truth.
    """
    _ = since
    print(f"  List scan baseline: care_providers table ({len(db_known_ids)} IDs)")

    print("  Fetching all current CQC location IDs...")
    all_stubs = _fetch_all_cqc_location_stubs(base_url, api_key, sleep)
    all_ids = {str(stub.get("locationId") or stub.get("id", "")) for stub in all_stubs if stub.get("locationId") or stub.get("id")}
    print(f"  CQC total: {len(all_ids)} | Known in database: {len(db_known_ids)}")

    candidate_ids = sorted(all_ids - db_known_ids)
    print(f"  Candidates (not in care_providers): {len(candidate_ids)}")

    if not candidate_ids:
        print("  No CQC location IDs found outside the database baseline.")
        return []

    print(f"  List scan complete: {len(candidate_ids)} IDs require detail processing")
    return candidate_ids


def _parse_watermark_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        date_text = parse_any_date(text)
        if not date_text:
            return None
        parsed = datetime.fromisoformat(date_text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def should_process_list_scan_record(record: dict[str, Any], since: str) -> bool:
    """Return true when a list-scan detail record is new or updated since the watermark."""
    since_dt = _parse_watermark_datetime(since)
    if since_dt is None:
        return False

    for key in ("registration_date", "last_updated"):
        value_dt = _parse_watermark_datetime(record.get(key))
        if value_dt is not None and value_dt >= since_dt:
            return True

    return False


def resolve_since(cur, explicit_since: str | None, *, now: datetime | None = None) -> str:
    """Resolve the incremental-update watermark from explicit input or DB state."""
    if explicit_since:
        return explicit_since

    cur.execute(
        """
        SELECT completed_at
        FROM pipeline_runs
        WHERE run_type = 'incremental' AND status = 'completed' AND completed_at IS NOT NULL
        ORDER BY completed_at DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row and row[0]:
        return row[0].strftime("%Y-%m-%dT%H:%M:%S")

    cur.execute("SELECT MAX(last_updated) FROM care_providers")
    row = cur.fetchone()
    if row and row[0]:
        return row[0].strftime("%Y-%m-%dT%H:%M:%S")

    reference_now = now or datetime.now(timezone.utc)
    return (reference_now - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")


def fetch_location_detail(base_url: str, api_key: str | None, location_id: str) -> dict[str, Any] | None:
    """Fetch full detail for a single location."""
    url = f"{base_url}/locations/{location_id}"
    attempts: list[str] = []
    for attempt in range(1, DETAIL_MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=api_headers(api_key), timeout=30)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError as exc:
                    attempts.append(f"{attempt}:json:{type(exc).__name__}")
                    if attempt == DETAIL_MAX_RETRIES:
                        break
            elif resp.status_code not in RETRYABLE_STATUS_CODES:
                raise ChangesFetchError(
                    f"Detail fetch failed for {location_id}: status={resp.status_code}; "
                    f"attempts={','.join(attempts) or '1'}"
                )
            else:
                attempts.append(f"{attempt}:status:{resp.status_code}")
            if attempt < DETAIL_MAX_RETRIES:
                retry_after = resp.headers.get("Retry-After")
                try:
                    delay = min(float(retry_after), DETAIL_MAX_BACKOFF_SECONDS) if retry_after else 0.0
                except (TypeError, ValueError):
                    delay = 0.0
                time.sleep(max(delay, min(2 ** (attempt - 1), DETAIL_MAX_BACKOFF_SECONDS)))
                continue
        except ChangesFetchError:
            raise
        except requests.RequestException as exc:
            attempts.append(f"{attempt}:exception:{type(exc).__name__}")
            if attempt < DETAIL_MAX_RETRIES:
                time.sleep(min(2 ** (attempt - 1), DETAIL_MAX_BACKOFF_SECONDS))
                continue
    raise ChangesFetchError(
        f"Detail fetch failed for {location_id}: exhausted retries; attempts={','.join(attempts)}"
    )


# --- Candidate deactivation confirmation ------------------------------------
# The directory snapshot is authoritative for the *active set*, but it is
# published on a schedule. A location registered after the snapshot was produced
# is absent from it while being legitimately registered, so absence from the
# snapshot is a candidate for deactivation, never proof of it. Every candidate
# is confirmed against the live API before any write; the batch expectation is
# then derived from that confirmed classification, which keeps the end-state
# equality guard strict instead of weakening it.

DEACTIVATION_DEACTIVATE = "deactivate"
DEACTIVATION_KEEP = "keep"

CLASSIFICATION_DEREGISTERED = "deregistered"
CLASSIFICATION_REGISTERED = "registered"
CLASSIFICATION_UNCONFIRMED = "unconfirmed"

DEACTIVATION_ACTIONS = frozenset({DEACTIVATION_DEACTIVATE, DEACTIVATION_KEEP})

#: Classification buckets recorded per batch (batch row / run checkpoint).
DEACTIVATION_CLASSIFICATIONS = (
    CLASSIFICATION_DEREGISTERED,
    CLASSIFICATION_REGISTERED,
    CLASSIFICATION_UNCONFIRMED,
)


@dataclass(frozen=True)
class DeactivationDecision:
    """The API-confirmed verdict for one candidate deactivation."""

    location_id: str
    action: str
    classification: str
    registration_status: str | None
    detail: str

    @property
    def deactivates(self) -> bool:
        return self.action == DEACTIVATION_DEACTIVATE


#: ``registrationStatus`` values that are AFFIRMATIVE proof of deregistration.
#:
#: Source of the vocabulary — the real CQC records held in this repository, which
#: anyone can re-check without network access:
#:   * ``raw_providers.json`` (a 97.7 MB CQC dump) contains exactly two distinct
#:     ``registrationStatus`` values: "Registered" (36,942 occurrences) and
#:     "Deregistered" (26,202).
#:   * ``artifacts/cqc-nightly/2026-09-20-reconciliation-detail.json`` holds
#:     117 "Registered" / 71 "Deregistered", and
#:     ``artifacts/cqc-nightly/2026-09-20-unrated-classification.json`` holds
#:     299 "Registered" / 1 "Deregistered".
#: No other value appears anywhere in that evidence, and the live public API was
#: not reachable when this was written (HTTP 502), so no live confirmation of any
#: value is claimed here. Values such as "Suspended", "Deregistering" or "Not
#: registered" therefore have no evidence behind them and are NOT treated as
#: deregistration proof.
#:
#: Deactivation therefore requires an exact (case- and whitespace-insensitive)
#: match against this list. Substring matching is never used: "Not registered"
#: contains "registered" and is neither affirmative proof of registration nor of
#: deregistration, so it keeps the location ACTIVE and is counted unconfirmed.
DEREGISTERED_STATUS_VALUES = frozenset({"deregistered"})

#: ``registrationStatus`` values that are AFFIRMATIVE proof of registration,
#: from the same evidence as ``DEREGISTERED_STATUS_VALUES``. Only these ids may
#: be added to the finalizer's expected active count: an unrecognised status is
#: never treated as confirmed-registered, so it can never absorb an
#: unexplained active-set mismatch.
REGISTERED_STATUS_VALUES = frozenset({"registered"})


def classify_registration_status(raw_status: Any) -> tuple[str, str]:
    """Classify one live ``registrationStatus`` value into (action, class).

    Deactivation requires affirmative proof of deregistration: only an exact
    match against ``DEREGISTERED_STATUS_VALUES`` may deactivate a location.
    Every other value — missing, empty, non-string, malformed, unfamiliar such
    as "Suspended", or registered-like text such as "Not registered" — resolves
    to ``DEACTIVATION_KEEP`` and is classified ``unconfirmed``, so the location
    stays ACTIVE and the batch summary records that it was never confirmed.
    """
    status = normalize_whitespace(raw_status if isinstance(raw_status, str) else "") or ""
    normalized = status.casefold()
    if normalized in DEREGISTERED_STATUS_VALUES:
        return (DEACTIVATION_DEACTIVATE, CLASSIFICATION_DEREGISTERED)
    if normalized in REGISTERED_STATUS_VALUES:
        return (DEACTIVATION_KEEP, CLASSIFICATION_REGISTERED)
    return (DEACTIVATION_KEEP, CLASSIFICATION_UNCONFIRMED)


def confirm_deactivation_candidates(
    candidate_ids: Sequence[str],
    *,
    base_url: str,
    api_key: str | None,
    fetch_detail: Callable[[str, str | None, str], dict[str, Any] | None] | None = None,
) -> list[DeactivationDecision]:
    """Confirm every candidate deactivation against the live CQC API.

    ``fetch_detail`` is injectable and defaults to the live location-detail
    fetch, resolved at call time so a test can replace the transport without
    changing the decision logic under test.

    One unreadable candidate never aborts the batch and never becomes a write:
    it is recorded as ``unconfirmed`` and left ACTIVE. The caller deactivates
    exactly the ids this function classifies as not registered, and derives its
    expected active count from the same result, so a genuine surprise still
    fails the run.
    """
    decisions: list[DeactivationDecision] = []
    fetch = fetch_detail or fetch_location_detail
    for location_id in candidate_ids:
        try:
            detail = fetch(base_url, api_key, location_id)
        except Exception as exc:  # noqa: BLE001 - one unconfirmed id must not abort the batch
            decisions.append(
                DeactivationDecision(
                    str(location_id),
                    DEACTIVATION_KEEP,
                    CLASSIFICATION_UNCONFIRMED,
                    None,
                    f"detail fetch failed ({type(exc).__name__}); not deactivated",
                )
            )
            continue
        if not isinstance(detail, dict):
            decisions.append(
                DeactivationDecision(
                    str(location_id),
                    DEACTIVATION_KEEP,
                    CLASSIFICATION_UNCONFIRMED,
                    None,
                    "detail payload was not an object; not deactivated",
                )
            )
            continue
        raw_status = detail.get("registrationStatus")
        action, classification = classify_registration_status(raw_status)
        status_text = normalize_whitespace(raw_status) if isinstance(raw_status, str) else ""
        decisions.append(
            DeactivationDecision(
                str(location_id),
                action,
                classification,
                status_text or None,
                f"registrationStatus={status_text or 'absent'}",
            )
        )
    return decisions


def summarise_deactivation_decisions(
    decisions: Sequence[DeactivationDecision],
) -> dict[str, Any]:
    """Per-classification counts for the batch row / run checkpoint."""
    counts = Counter(decision.classification for decision in decisions)
    summary: dict[str, Any] = {name: counts.get(name, 0) for name in DEACTIVATION_CLASSIFICATIONS}
    summary["candidates"] = len(decisions)
    summary["deactivated"] = sum(1 for decision in decisions if decision.deactivates)
    summary["kept_active"] = sum(1 for decision in decisions if not decision.deactivates)
    summary["not_deactivated_ids"] = [
        decision.location_id for decision in decisions if not decision.deactivates
    ]
    # Split the kept-active bucket: only ``confirmed_still_registered_ids`` may
    # complete the finalizer's expected active count. ``unconfirmed_ids`` stay
    # ACTIVE but are never absorbed into the expectation — the finalizer refuses
    # the batch while they exist unless the operator explicitly acknowledges
    # them, in which case it records them on the batch row and still fails on any
    # residual mismatch.
    summary["confirmed_still_registered_ids"] = [
        decision.location_id
        for decision in decisions
        if decision.classification == CLASSIFICATION_REGISTERED
    ]
    summary["unconfirmed_ids"] = [
        decision.location_id
        for decision in decisions
        if decision.classification == CLASSIFICATION_UNCONFIRMED
    ]
    return summary


def clean_location(data: dict[str, Any], *, directory_active: bool = False) -> dict[str, Any] | None:
    """Extract and clean key fields from a location detail response.

    ``directory_active`` is used only when the record came from the current
    CQC active-location directory snapshot.  That snapshot is the authority
    for the active set; detail ``registrationStatus`` can lag during CQC
    directory publication and must not turn an in-snapshot location inactive.
    """
    location_id = data.get("locationId", "")
    if not location_id:
        return None

    name = normalize_whitespace(data.get("name", ""))
    if not name:
        return None

    # Rating ---------------------------------------------------------------
    # CQC returns a real rating, a *sentinel* string that is not a rating
    # ("Not Yet Inspected", "No Published Rating", "Inspected but not rated"),
    # or no rating field at all, through the same path. Storing a sentinel (or
    # "") as the rating is what produced ~24k destination-less rating_changed
    # events: representation churn was being read as rating movement. The
    # payload is therefore classified into a rating *state* (see
    # api/services/rating_states.py) and only a real published rating is ever
    # written to the rating column.
    rating = assess_location_rating(data)
    current_ratings = data.get("currentRatings", {})

    # Key question ratings
    kq_ratings = {}
    if isinstance(current_ratings, dict):
        overall_block = current_ratings.get("overall", {})
        if isinstance(overall_block, dict):
            kq_list = overall_block.get("keyQuestionRatings", [])
            if isinstance(kq_list, list):
                for item in kq_list:
                    if isinstance(item, dict):
                        kq_name = str(item.get("name", "")).strip().lower().replace(" ", "_")
                        kq_rating = str(item.get("rating", "")).strip()
                        if kq_name and kq_rating:
                            kq_ratings[kq_name] = kq_rating

    # Service types from gacServiceTypes
    service_types = []
    gac = data.get("gacServiceTypes", [])
    if isinstance(gac, list):
        for item in gac:
            if isinstance(item, dict):
                desc = item.get("description") or item.get("name", "")
                if desc:
                    service_types.append(str(desc).strip())

    # Specialisms
    specialisms = []
    specs = data.get("specialisms", [])
    if isinstance(specs, list):
        for item in specs:
            if isinstance(item, dict):
                spec_name = item.get("name", "")
            else:
                spec_name = str(item)
            if spec_name:
                specialisms.append(str(spec_name).strip())

    # Coordinates
    lat = to_float(data.get("onspdLatitude"))
    lon = to_float(data.get("onspdLongitude"))

    # Dates — use None rather than "" so PostgreSQL DATE columns don't reject empty strings
    last_inspection = data.get("lastInspection", {})
    inspection_date = None
    if isinstance(last_inspection, dict):
        inspection_date = last_inspection.get("date") or None

    report_url = None
    report_candidates = [data.get("lastReport")]
    reports = data.get("reports")
    if isinstance(reports, list):
        report_candidates.extend(reports)
    for candidate in report_candidates:
        if not isinstance(candidate, dict):
            continue
        report_url = candidate.get("reportUri") or candidate.get("url")
        if report_url:
            break

    # Deactivation requires affirmative proof of deregistration (FIX 2): only an
    # explicit allow-listed 'Deregistered' status may turn a location INACTIVE.
    # Every other value — unfamiliar ('Suspended'), missing, non-string or
    # registered-like ('Not registered') — keeps the location ACTIVE and is
    # recorded as unconfirmed so the summary shows it was never confirmed.
    registration_action, registration_classification = classify_registration_status(
        data.get("registrationStatus")
    )
    status = (
        "ACTIVE"
        if directory_active or registration_action == DEACTIVATION_KEEP
        else "INACTIVE"
    )

    record = {
        "id": location_id,
        "provider_id": data.get("providerId", ""),
        "name": name,
        "type": normalize_whitespace(data.get("type", "")),
        "status": status,
        "registration_date": parse_any_date(data.get("registrationDate")) or None,
        "address_line1": normalize_whitespace(data.get("postalAddressLine1", "")),
        "address_line2": normalize_whitespace(data.get("postalAddressLine2", "")),
        "town": normalize_whitespace(data.get("postalAddressTownCity", "")),
        "county": normalize_whitespace(data.get("postalAddressCounty", "")),
        "postcode": normalize_whitespace(data.get("postalCode", "")),
        "region": normalize_whitespace(data.get("region", "")),
        "local_authority": normalize_whitespace(data.get("localAuthority", "")),
        "latitude": lat,
        "longitude": lon,
        # CQC publishes mainPhoneNumber as free text and it is sometimes
        # malformed (1-29250185054 carried the same number typed twice, 22
        # chars). An oversized value used to abort the entire shard mid-batch,
        # so clamp to the column width: one bad upstream record must never stop
        # a reconciliation. See db/migrations/059_widen_provider_phone.sql.
        "phone": normalize_whitespace(data.get("mainPhoneNumber", ""))[:PHONE_MAX_LENGTH],
        "website": normalize_whitespace(data.get("website", "")),
        "rating_safe": kq_ratings.get("safe", ""),
        "rating_effective": kq_ratings.get("effective", ""),
        "rating_caring": kq_ratings.get("caring", ""),
        "rating_responsive": kq_ratings.get("responsive", ""),
        "rating_well_led": kq_ratings.get("well_led", ""),
        "last_inspection_date": inspection_date,
        "inspection_report_url": normalize_whitespace(report_url or "") or None,
        "service_types": "|".join(service_types),
        "specialisms": "|".join(specialisms),
        "number_of_beds": data.get("numberOfBeds"),
        "ownership_type": normalize_whitespace(data.get("ownershipType", "")),
        "registered_manager_absent_date": parse_any_date(data.get("registeredManagerAbsentDate")) or None,
        "last_updated": data.get("lastUpdated") or data.get("lastUpdatedDate") or data.get("lastUpdatedTimestamp"),
        # The state is always recorded, even when there is no rating to record.
        "rating_state": rating.state,
        # Evidence only (there is no column for it): lets the batch/shard
        # summary count locations whose registration status could not be
        # confirmed rather than silently treating them as expected.
        "registration_status_classification": registration_classification,
    }
    # Only a rating the current payload itself publishes is written here. Every
    # other case is decided by apply_rating_write_policy inside upsert_provider,
    # which clears a stale rating column when the payload positively reports
    # that no rating is published now, and writes nothing at all when the source
    # could not be read.
    if is_published_value(rating.state) and rating.value is not None:
        record["overall_rating"] = rating.value
    # Evidence, not columns: why the state is what it is, and the last rating
    # the source still reports. upsert_provider carries these to the rating
    # event so the ledger records the previous value, the destination state,
    # the source reference and the publication date.
    record["rating_evidenced"] = rating.evidenced
    record["rating_evidence"] = rating.evidence
    record["historic_rating"] = rating.historic_rating
    record["historic_rating_state"] = rating.historic_rating_state
    record["historic_rating_date"] = rating.historic_rating_date
    record["rating_report_date"] = rating.report_date
    return record


ALLOWED_COLUMNS = frozenset({
    "id", "provider_id", "name", "slug", "type", "status", "registration_date",
    "address_line1", "address_line2", "town", "county", "postcode",
    "region", "local_authority", "latitude", "longitude", "phone", "website",
    "overall_rating", "rating_state", "rating_state_source",
    # FIX 1 evidence columns: the last rating the source actually published, kept
    # separately (with its own date) so clearing ``overall_rating`` when the
    # current payload publishes no rating loses nothing. See migration 062.
    "last_published_rating", "last_published_rating_date",
    "rating_safe", "rating_effective",
    "rating_caring", "rating_responsive", "rating_well_led",
    "last_inspection_date", "inspection_report_url",
    "registered_manager_absent_date", "service_types", "specialisms",
    "number_of_beds", "ownership_type", "last_updated",
})

#: Rating evidence produced by clean_location that has no column of its own.
#: It is carried with the observation (never written to care_providers) so a
#: rating event can record the previous value, the destination state, the
#: source reference and the publication date instead of a bare value.
RATING_EVIDENCE_KEYS = (
    "rating_evidenced",
    "rating_evidence",
    "historic_rating",
    "historic_rating_state",
    "historic_rating_date",
    "rating_report_date",
)


def last_published_rating_evidence(
    source: dict[str, Any] | None,
) -> tuple[str, str | None] | None:
    """Return ``(rating, date)`` for evidence of the last rating the source published.

    Accepts either an explicit ``last_published_rating`` field (the dedicated
    evidence column) or a legacy ``overall_rating`` still holding a real
    published rating. A sentinel, a blank or a non-string never counts: only a
    value ``stored_rating_is_published`` accepts is retained, and the date is
    only ever one we were given (never invented).
    """
    if not source:
        return None
    rating = source.get("last_published_rating")
    if not isinstance(rating, str) or not rating.strip():
        rating = source.get("overall_rating")
    if not isinstance(rating, str) or not stored_rating_is_published(rating):
        return None
    date = source.get("last_published_rating_date")
    date_text = str(date).strip() if date else None
    return (rating.strip(), date_text or None)


def apply_rating_write_policy(
    safe_record: dict[str, Any],
    existing: dict[str, Any] | None,
    *,
    full_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide what one cleaned record may write to the rating columns.

    ``safe_record`` holds the columns this write may touch. ``full_record`` is
    the whole cleaned record, which also carries the rating evidence that has no
    column of its own (``rating_report_date``, ``historic_rating``,
    ``historic_rating_date``) — it is read here, never written to the table.

    The current source payload is the only authority for what is published
    *now*:

    * the payload published a rating -> ``overall_rating`` holds it, and the
      last-published evidence columns are refreshed with the source's own
      publication date. A date is only ever one that describes the rating being
      stored: a new rating published without its own report date clears
      ``last_published_rating_date`` (the stored date belonged to the previous
      rating), and the evidence is refreshed with no date rather than a stale
      one;
    * the payload positively reports the location is not currently rated (an
      absent or blank current overall rating, a sentinel such as
      ``Not Yet Inspected``, or any other non-rated state) ->
      ``overall_rating`` is cleared to NULL. Leaving the previous value there
      asserted a rating the source no longer publishes, which suppressed the
      real rated -> not-currently-rated transition and produced a false movement
      later. The old value is preserved as ``last_published_rating`` (+ date),
      which is evidence about the past and is never read as the current rating.
      A historic rating's date is only stored next to that same historic
      rating, never next to another rating;
    * the payload could not be read ('unknown') -> no rating column is written:
      an evidence gap is not a statement about the rating, and the recorded
      state ('unknown') already stops the event classifier treating the row as
      rated. A successfully read payload only reaches this state for rating text
      this build does not recognise (see rating_states.classify_rating).

    A rating value is never invented here, a date is never reused for a
    different rating, and a negative claim is only ever made from the payload's
    own state.
    """
    if "rating_state" not in safe_record:
        return safe_record

    amended = dict(safe_record)
    # Provenance marker: what wrote this rating_state. Migration 061 only backfills
    # rows still marked 'unclassified', so stamping 'pipeline' here is what keeps
    # that one-time backfill from ever rewriting a row ingestion has cleaned.
    amended["rating_state_source"] = "pipeline"
    state = safe_record["rating_state"]
    # The evidence that has no column of its own travels on the whole record.
    payload_evidence = full_record or {}

    if is_published_value(state) and safe_record.get("overall_rating"):
        amended["last_published_rating"] = safe_record["overall_rating"]
        # The date must date the rating stored just above. assess_location_rating
        # only reports a date it actually read for the *current* rating (it never
        # falls back to a historic rating's date for a rated state), so "no date"
        # here means the payload published this rating without a report date.
        # The date already on the row then belongs to a different (previous)
        # rating and is cleared rather than reused: the reviewed revision kept
        # it, pairing 'Requires improvement' with the old 'Good' date. When the
        # rating itself is unchanged, the stored date is left alone -- it still
        # dates the same value.
        report_date = payload_evidence.get("rating_report_date")
        if report_date:
            amended["last_published_rating_date"] = report_date
        elif (
            normalize_rating_text(amended["last_published_rating"])
            != normalize_rating_text((existing or {}).get("last_published_rating"))
        ):
            amended["last_published_rating_date"] = None
        return amended

    if state not in NON_RATED_STATES:
        # 'unknown': the rating could not be read from this payload (unrecognised
        # text), which is not a statement that the location has no rating. No
        # rating column is written, so any previous value stays as it is and no
        # date is moved.
        return amended

    # The source positively says no rating is published right now: stop
    # asserting one, and keep what it last published as labelled evidence.
    amended["overall_rating"] = None
    evidence = last_published_rating_evidence(existing) or last_published_rating_evidence(
        {
            "last_published_rating": payload_evidence.get("historic_rating"),
            "last_published_rating_date": payload_evidence.get("historic_rating_date"),
        }
    )
    if evidence:
        amended["last_published_rating"] = evidence[0]
        # The recorded date wins. The payload's own historic date is used only to
        # date the value it actually describes: it is CQC's date for the
        # payload's historic rating, so it may date the stored evidence only when
        # that is the same rating. Neither date is invented, and neither is
        # paired with a different rating.
        date = evidence[1]
        if date is None and normalize_rating_text(
            payload_evidence.get("historic_rating")
        ) == normalize_rating_text(evidence[0]):
            date = payload_evidence.get("historic_rating_date")
        if date:
            amended["last_published_rating_date"] = date
        elif (
            normalize_rating_text(amended["last_published_rating"])
            != normalize_rating_text((existing or {}).get("last_published_rating"))
        ):
            # A different rating is now the stored evidence, so the previous
            # rating's date must not travel with it.
            amended["last_published_rating_date"] = None
    return amended


def upsert_provider(cur, record: dict[str, Any]) -> str:
    """Upsert a single provider record. Returns 'inserted', 'updated', or 'skipped'."""
    # Whitelist columns to prevent SQL injection via dict keys
    source_context = {
        key: record.get(key)
        for key in (
            "source_snapshot_id", "source_snapshot_sha256", "source_url",
            "source_checked_at", "source_published_at",
        )
        if record.get(key) is not None
    }
    safe_record = {k: v for k, v in record.items() if k in ALLOWED_COLUMNS}
    if "id" not in safe_record:
        return "skipped"

    existing_columns: tuple[str, ...] = (
        "id", "provider_id", "overall_rating", "rating_state", "status",
        "ownership_type", "name", "slug", "town", "postcode", "region",
        "registration_date", "last_inspection_date", "last_updated",
        # Read the last-published evidence too: when the incoming payload
        # publishes no current rating, that evidence is what preserves the value
        # as history instead of leaving it asserting a current rating.
        "last_published_rating", "last_published_rating_date",
    )
    cur.execute(
        f"SELECT {', '.join(existing_columns)} FROM care_providers WHERE id = %s",
        (safe_record["id"],),
    )
    existing_row = cur.fetchone()
    existing: dict[str, Any] | None = (
        dict(zip(existing_columns, existing_row, strict=True)) if existing_row else None
    )

    safe_record = apply_rating_write_policy(safe_record, existing, full_record=record)

    # Generate slug for new inserts; never overwrite an existing slug on update
    if not existing and not safe_record.get("slug"):
        base_slug = _make_slug(
            safe_record.get("name", ""),
            safe_record.get("town", ""),
            safe_record["id"],
        )
        # Ensure uniqueness: if base slug is taken by a different provider, append location_id
        cur.execute("SELECT id FROM care_providers WHERE slug = %s", (base_slug,))
        collision = cur.fetchone()
        if collision and collision[0] != safe_record["id"]:
            id_suffix = _slugify(safe_record["id"], separator="-") or safe_record["id"].lower()
            safe_record["slug"] = f"{base_slug}-{id_suffix}"
        else:
            safe_record["slug"] = base_slug

    cols = list(safe_record.keys())
    vals = [safe_record[c] for c in cols]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if existing:
        set_clause = ", ".join(f"{c} = %s" for c in cols)
        cur.execute(
            f"UPDATE care_providers SET {set_clause}, updated_at = %s WHERE id = %s",
            vals + [now, safe_record["id"]],
        )
        action = "updated"
    else:
        cols_str = ", ".join(cols + ["updated_at", "created_at"])
        placeholders = ", ".join(["%s"] * (len(cols) + 2))
        insert_sql = f"INSERT INTO care_providers ({cols_str}) VALUES ({placeholders})"
        cur.execute("SAVEPOINT provider_slug_insert")
        try:
            cur.execute(insert_sql, vals + [now, now])
        except psycopg2.errors.UniqueViolation as exc:
            # Concurrent shards can both observe a free base slug. Retry only
            # slug collisions with the immutable location ID suffix; all other
            # uniqueness failures remain fatal and fail closed.
            if "care_providers_slug_key" not in str(exc):
                cur.execute("ROLLBACK TO SAVEPOINT provider_slug_insert")
                raise
            cur.execute("ROLLBACK TO SAVEPOINT provider_slug_insert")
            id_suffix = _slugify(safe_record["id"], separator="-") or safe_record["id"].lower()
            safe_record["slug"] = f"{safe_record['slug']}-{id_suffix}"
            cols = list(safe_record.keys())
            vals = [safe_record[c] for c in cols]
            cols_str = ", ".join(cols + ["updated_at", "created_at"])
            placeholders = ", ".join(["%s"] * (len(cols) + 2))
            cur.execute(
                f"INSERT INTO care_providers ({cols_str}) VALUES ({placeholders})",
                vals + [now, now],
            )
            cur.execute("RELEASE SAVEPOINT provider_slug_insert")
        else:
            cur.execute("RELEASE SAVEPOINT provider_slug_insert")
        action = "inserted"

    current: dict[str, Any] = dict(existing) if existing else {}
    current.update(safe_record)
    current.update(source_context)
    # Rating evidence has no column of its own: carry it with the observation
    # so the rating event can name its previous value, destination state,
    # source reference and publication date.
    current.update(
        {key: record[key] for key in RATING_EVIDENCE_KEYS if record.get(key) is not None}
    )
    events = build_provider_state_events(existing, current)
    for event in events:
        inserted = _insert_trusted_provider_event(cur, event, current)
        # Only a movement between two published ratings is projected into the
        # customer-facing rating-change record. rating_status_changed is
        # deliberately excluded (see api/services/provider_state_events.py).
        if inserted and event.event_type == "rating_changed":
            _project_rating_change(cur, event, current)

    return action


def _insert_trusted_provider_event(
    cur,
    event: ProviderStateEvent,
    current: dict[str, Any],
) -> bool:
    source_observed_at = _parse_watermark_datetime(current.get("last_updated"))

    def json_value(value: Any) -> Json:
        return Json(value, dumps=lambda obj: json.dumps(obj, default=str))

    cur.execute(
        """
        INSERT INTO trusted_event_ledger (
          entity_type, entity_id, provider_id, location_id, event_type,
          effective_date, effective_at, effective_date_source,
          old_value, new_value, source, confidence_score,
          dedupe_key, metadata, source_observed_at, entity_level,
          source_snapshot_id, source_published_at, source_checked_at,
          source_url, source_snapshot_sha256
        )
        VALUES (
          'care_provider', %s, %s, %s, %s,
          %s, %s, %s, %s, %s, 'cqc_api', 1.0000,
          %s, %s, %s, 'location',
          %s, %s, %s, %s, %s
        )
        ON CONFLICT (dedupe_key) DO NOTHING
        RETURNING id
        """,
        (
            event.location_id,
            event.provider_id,
            event.location_id,
            event.event_type,
            event.effective_date,
            event.effective_at,
            event.effective_date_source,
            json_value(event.old_value),
            json_value(event.new_value),
            event.dedupe_key,
            json_value(event.metadata),
            source_observed_at,
            current.get("source_snapshot_id"),
            _parse_watermark_datetime(current.get("source_published_at")) or source_observed_at,
            _parse_watermark_datetime(current.get("source_checked_at")),
            current.get("source_url") or f"https://api.service.cqc.org.uk/public/v1/locations/{event.location_id}",
            current.get("source_snapshot_sha256"),
        ),
    )
    inserted = cur.fetchone()
    if not inserted:
        return False
    event_id = int(inserted[0])
    cur.execute(
        """
        INSERT INTO delivery_outbox (
          organization_id, delivery_subscription_id, event_id
        )
        SELECT ds.organization_id, ds.id, %s
        FROM delivery_subscriptions ds
        WHERE ds.active = TRUE
          AND %s = ANY(ds.event_types)
        ON CONFLICT (delivery_subscription_id, event_id) DO NOTHING
        """,
        (event_id, event.event_type),
    )
    return True


def _project_rating_change(
    cur,
    event: ProviderStateEvent,
    current: dict[str, Any],
) -> None:
    cur.execute(
        """
        INSERT INTO rating_changes (
          provider_id, provider_name, slug, town, postcode, region,
          old_rating, new_rating, inspection_date, event_dedupe_key
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_dedupe_key)
        WHERE event_dedupe_key IS NOT NULL
        DO NOTHING
        """,
        (
            event.location_id,
            current.get("name"),
            current.get("slug"),
            current.get("town"),
            current.get("postcode"),
            current.get("region"),
            event.old_value,
            event.new_value,
            current.get("last_inspection_date"),
            event.dedupe_key,
        ),
    )
    if current.get("last_inspection_date"):
        cur.execute(
            """
            INSERT INTO provider_rating_history (provider_id, overall_rating, inspection_date)
            VALUES (%s, %s, %s)
            ON CONFLICT (provider_id, inspection_date) DO NOTHING
            """,
            (
                event.location_id,
                event.new_value,
                current.get("last_inspection_date"),
            ),
        )


def _parse_batch_id(value: str | None) -> uuid.UUID:
    if not value:
        raise ValueError("--batch-id is required for reconciliation phases")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("--batch-id must be a valid UUID") from exc
    if str(parsed) != value.lower():
        raise ValueError("--batch-id must use canonical UUID form")
    return parsed


def _require_manifest_path(value: str | None) -> Path:
    if not value:
        raise ValueError("--snapshot-manifest is required for reconciliation phases")
    return Path(value)


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record_alert_state(cur, alert_key: str, severity: str, details: dict[str, Any]) -> None:
    cur.execute(
        """
        INSERT INTO pipeline_alert_state (alert_key, severity, details)
        VALUES (%s, %s, %s)
        ON CONFLICT (alert_key) DO UPDATE
        SET severity = EXCLUDED.severity,
            details = EXCLUDED.details,
            last_seen_at = NOW(),
            occurrence_count = pipeline_alert_state.occurrence_count + 1,
            resolved_at = NULL
        """,
        (alert_key, severity, Json(details)),
    )


def _sync_reconciliation_run_evidence(cur, batch_id: uuid.UUID) -> None:
    """Derive bounded run coverage from committed shard checkpoints."""
    cur.execute(
        """
        UPDATE pipeline_runs AS p
        SET checked_count = evidence.processed + evidence.failed,
            success_count = evidence.processed,
            failure_count = evidence.failed,
            checkpoint_state = p.checkpoint_state || jsonb_build_object(
              'shards', evidence.shards,
              'restartable', evidence.failed > 0 OR evidence.processed < b.location_count
            )
        FROM reconciliation_batches AS b
        CROSS JOIN LATERAL (
          SELECT
            COALESCE(SUM(s.processed_count), 0)::int AS processed,
            COUNT(*) FILTER (
              WHERE s.status = 'failed' AND s.processed_count < s.expected_count
            )::int AS failed,
            COALESCE(
              jsonb_agg(
                jsonb_build_object(
                  'shardIndex', s.shard_index,
                  'status', s.status,
                  'expectedCount', s.expected_count,
                  'nextOffset', s.next_offset,
                  'processedCount', s.processed_count
                ) ORDER BY s.shard_index
              ),
              '[]'::jsonb
            ) AS shards
          FROM reconciliation_shards AS s
          WHERE s.batch_id = b.id
        ) AS evidence
        WHERE b.id = %s AND p.id = b.pipeline_run_id
        """,
        (str(batch_id),),
    )


def _prepare_batch(args: argparse.Namespace, conn, cur) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    manifest_path = _require_manifest_path(args.snapshot_manifest)
    validate_shard_coordinates(args.shard_count)
    snapshot = fetch_active_location_snapshot(args.data_page_url)
    manifest = build_snapshot_manifest(snapshot, batch_id, args.shard_count)

    cur.execute("SELECT id, status FROM care_providers")
    rows = cur.fetchall()
    active_before = sum(1 for row in rows if row and str(row[1]).upper() == "ACTIVE")
    build_snapshot_reconciliation(
        snapshot,
        db_ids=frozenset(str(row[0]) for row in rows if row and row[0]),
        db_active_ids=frozenset(
            str(row[0]) for row in rows if row and row[0] and str(row[1]).upper() == "ACTIVE"
        ),
    )

    if args.dry_run:
        print(
            f"DRY RUN — validated batch {batch_id}: {len(snapshot.location_ids)} locations, "
            f"{args.shard_count} shards; no files or database rows were written."
        )
        return 0

    _ensure_no_active_reconciliation_batch(args, conn, cur)

    cur.execute(
        """
        INSERT INTO pipeline_runs (
          run_type, status, source_total_count, source_provenance,
          source_uri, source_published_at, source_retrieved_at,
          source_checksum_sha256, source_record_count, checkpoint_state,
          counts_reconciled, reconciled_at
        )
        VALUES (
          'reconciliation', 'running', %s, %s::jsonb,
          %s, %s, %s, %s, %s, %s::jsonb, FALSE, NULL
        )
        RETURNING id
        """,
        (
            len(snapshot.location_ids),
            json.dumps({
                "kind": "cqc_directory_csv",
                "uri": snapshot.source_uri,
                "publishedAt": snapshot.source_published_at,
                "retrievedAt": snapshot.retrieved_at.isoformat(),
                "checksumSha256": snapshot.checksum_sha256,
                "manifestChecksumSha256": manifest["manifestChecksumSha256"],
                "execution": {
                    "gitSha": getattr(args, "release_sha", None),
                    "workflowRunId": getattr(args, "workflow_run_id", None),
                    "workflowRunAttempt": getattr(args, "workflow_run_attempt", None),
                },
            }, sort_keys=True),
            snapshot.source_uri, snapshot.source_published_at, snapshot.retrieved_at,
            snapshot.checksum_sha256, len(snapshot.location_ids),
            json.dumps({
                "batchId": str(batch_id),
                "shardCount": args.shard_count,
                "restartable": True,
                "resumeWaves": 0,
                "restarts": {},
                "prepareExecution": {
                    "gitSha": getattr(args, "release_sha", None),
                    "workflowRunId": getattr(args, "workflow_run_id", None),
                    "workflowRunAttempt": getattr(args, "workflow_run_attempt", None),
                },
            }),
        ),
    )
    pipeline_run_id = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO reconciliation_batches (
          id, pipeline_run_id, source_uri, source_published_at, source_retrieved_at,
          source_checksum_sha256, manifest_checksum_sha256, location_count,
          shard_count, status, active_records_before
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'prepared', %s)
        """,
        (
            str(batch_id), pipeline_run_id, snapshot.source_uri, snapshot.source_published_at,
            snapshot.retrieved_at, snapshot.checksum_sha256,
            manifest["manifestChecksumSha256"], len(snapshot.location_ids),
            args.shard_count, active_before,
        ),
    )
    conn.commit()
    try:
        _write_manifest(manifest_path, manifest)
    except Exception:
        cur.execute(
            "UPDATE reconciliation_batches SET status = 'failed', error_message = %s WHERE id = %s",
            ("Manifest file could not be published after batch creation", str(batch_id)),
        )
        cur.execute(
            """UPDATE pipeline_runs
               SET status = 'failed', completed_at = NOW(), error_message = %s,
                   counts_reconciled = FALSE, reconciled_at = NULL,
                   checkpoint_state = checkpoint_state || '{"restartable": true}'::jsonb
               WHERE id = %s""",
            ("Manifest file could not be published after batch creation", pipeline_run_id),
        )
        conn.commit()
        raise
    print(f"Prepared reconciliation batch {batch_id} at {manifest_path}")
    return 0


def _validate_manifest_for_batch(cur, manifest: dict[str, Any], batch_id: uuid.UUID) -> tuple[int, int]:
    cur.execute(
        """
        SELECT shard_count, location_count, manifest_checksum_sha256, source_checksum_sha256
        FROM reconciliation_batches WHERE id = %s
        """,
        (str(batch_id),),
    )
    row = cur.fetchone()
    if not row:
        raise ChangesFetchError(f"Reconciliation batch {batch_id} does not exist.")
    shard_count, location_count, stored_checksum, source_checksum = (
        int(row[0]), int(row[1]), str(row[2]), str(row[3])
    )
    if manifest.get("batchId") != str(batch_id):
        raise ChangesFetchError("Snapshot manifest references a different batch.")
    if int(manifest.get("shardCount", 0)) != shard_count:
        raise ChangesFetchError("Snapshot manifest shard count disagrees with the batch.")
    if int(manifest.get("locationCount", -1)) != location_count:
        raise ChangesFetchError("Snapshot manifest location count disagrees with the batch.")
    if manifest.get("manifestChecksumSha256") != stored_checksum:
        raise ChangesFetchError("Snapshot manifest checksum disagrees with the batch.")
    if manifest.get("sourceChecksumSha256") != source_checksum:
        raise ChangesFetchError("Snapshot source checksum disagrees with the batch.")
    return shard_count, location_count


def _resume_batch(args: argparse.Namespace, conn, cur) -> int:
    """Authorize exactly one manual resume wave for an incomplete immutable batch."""
    if args.dry_run:
        raise ValueError("The resume phase does not support --dry-run.")
    batch_id = _parse_batch_id(args.batch_id)
    manifest = load_snapshot_manifest(_require_manifest_path(args.snapshot_manifest))
    shard_count, _ = _validate_manifest_for_batch(cur, manifest, batch_id)

    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-finalizer', 0))")
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-prepare', 0))")
    cur.execute(
        """
        SELECT b.status, b.pipeline_run_id, p.checkpoint_state
        FROM reconciliation_batches AS b
        JOIN pipeline_runs AS p ON p.id = b.pipeline_run_id
        WHERE b.id = %s
        FOR UPDATE OF b, p
        """,
        (str(batch_id),),
    )
    row = cur.fetchone()
    if not row:
        raise ChangesFetchError(f"Reconciliation batch {batch_id} does not exist.")
    status, pipeline_run_id, checkpoint_state = str(row[0]), int(row[1]), row[2] or {}
    if status != "failed":
        raise ChangesFetchError(
            f"Reconciliation batch {batch_id} must be failed before resume; status is {status}."
        )
    prepare_execution = checkpoint_state.get("prepareExecution")
    if not isinstance(prepare_execution, dict):
        raise ChangesFetchError(
            "Reconciliation resume refused because original prepare execution evidence is missing."
        )
    prepared_sha = str(prepare_execution.get("gitSha") or "").lower()
    prepared_run_id = str(prepare_execution.get("workflowRunId") or "")
    resume_sha = str(getattr(args, "release_sha", "") or "").lower()
    source_run_id = str(getattr(args, "resume_source_run_id", "") or "")
    if resume_sha != prepared_sha or source_run_id != prepared_run_id:
        raise ChangesFetchError(
            "Reconciliation resume must use the original prepare code SHA and workflow run artifact."
        )
    resume_waves = int(checkpoint_state.get("resumeWaves", 0))
    if resume_waves >= 1:
        raise ChangesFetchError(
            f"Reconciliation batch {batch_id} already used its single resume wave."
        )

    for shard_index in range(shard_count):
        lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
        cur.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,))
        if not cur.fetchone()[0]:
            raise ShardAlreadyRunning(
                f"Shard {shard_index} is still running; reconciliation resume refused."
            )
    cur.execute(
        """SELECT COUNT(*) FROM reconciliation_shards
           WHERE batch_id = %s AND status = 'running'""",
        (str(batch_id),),
    )
    if int(cur.fetchone()[0]) > 0:
        raise ShardAlreadyRunning("A shard is still marked running; reconciliation resume refused.")

    resume_execution = json.dumps(
        {
            "gitSha": getattr(args, "release_sha", None),
            "workflowRunId": getattr(args, "workflow_run_id", None),
            "workflowRunAttempt": getattr(args, "workflow_run_attempt", None),
        },
        sort_keys=True,
    )

    cur.execute(
        """
        UPDATE reconciliation_batches
        SET status = 'prepared', completed_at = NULL, error_message = NULL
        WHERE id = %s
        """,
        (str(batch_id),),
    )
    cur.execute(
        """
        UPDATE pipeline_runs
        SET status = 'running', completed_at = NULL, error_message = NULL,
            counts_reconciled = FALSE, reconciled_at = NULL,
            checkpoint_state = jsonb_set(
              jsonb_set(
                checkpoint_state || '{"restartable": true, "fullCoverage": false}'::jsonb,
                '{resumeWaves}', to_jsonb(%s::int), TRUE
              ),
              '{resumeExecution}', %s::jsonb, TRUE
            )
        WHERE id = %s
        """,
        (resume_waves + 1, resume_execution, pipeline_run_id),
    )
    conn.commit()
    print(f"Authorized the single resume wave for reconciliation batch {batch_id}")
    return 0


def _run_shard(args: argparse.Namespace, conn, cur, api_key: str | None) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    manifest = load_snapshot_manifest(_require_manifest_path(args.snapshot_manifest))
    shard_count, _ = _validate_manifest_for_batch(cur, manifest, batch_id)
    validate_shard_coordinates(shard_count, args.shard_index)
    if args.shard_count != shard_count:
        raise ChangesFetchError("--shard-count disagrees with the prepared batch.")
    shard_index = int(args.shard_index)
    ids = partition_location_ids(manifest["locationIds"], shard_count)[shard_index]

    if args.dry_run:
        print(f"DRY RUN — shard {shard_index} would process {len(ids)} records; zero writes performed.")
        return 0

    lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
    cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
    if not cur.fetchone()[0]:
        raise ShardAlreadyRunning(f"Shard {shard_index} is already running.")

    try:
        cur.execute(
            """
            INSERT INTO reconciliation_shards (
              batch_id, shard_index, status, manifest_checksum_sha256, expected_count
            ) VALUES (%s, %s, 'running', %s, %s)
            ON CONFLICT (batch_id, shard_index) DO NOTHING
            """,
            (str(batch_id), shard_index, manifest["manifestChecksumSha256"], len(ids)),
        )
        cur.execute(
            """
            SELECT status, manifest_checksum_sha256, expected_count, next_offset,
                   records_inserted, records_updated
            FROM reconciliation_shards WHERE batch_id = %s AND shard_index = %s
            FOR UPDATE
            """,
            (str(batch_id), shard_index),
        )
        shard = cur.fetchone()
        if not shard:
            raise ChangesFetchError("Shard state could not be created.")
        if str(shard[1]) != manifest["manifestChecksumSha256"] or int(shard[2]) != len(ids):
            raise ChangesFetchError("Existing shard state disagrees with the immutable manifest.")
        if shard[0] == "completed":
            print(f"Shard {shard_index} is already complete.")
            conn.rollback()
            return 0
        offset = int(shard[3])
        totals = Counter(inserted=int(shard[4]), updated=int(shard[5]))
        cur.execute(
            "UPDATE reconciliation_shards SET status = 'running', error_message = NULL, updated_at = NOW() WHERE batch_id = %s AND shard_index = %s",
            (str(batch_id), shard_index),
        )
        cur.execute("UPDATE reconciliation_batches SET status = 'running' WHERE id = %s", (str(batch_id),))
        cur.execute(
            """
            UPDATE pipeline_runs
            SET status = 'running', completed_at = NULL, error_message = NULL,
                failure_count = 0, counts_reconciled = FALSE, reconciled_at = NULL,
                checkpoint_state = jsonb_set(
                  checkpoint_state,
                  ARRAY['restarts', %s],
                  to_jsonb(COALESCE((checkpoint_state #>> ARRAY['restarts', %s])::int, 0) + %s),
                  TRUE
                )
            WHERE id = (SELECT pipeline_run_id FROM reconciliation_batches WHERE id = %s)
            """,
            (str(shard_index), str(shard_index), int(offset > 0), str(batch_id)),
        )
        _sync_reconciliation_run_evidence(cur, batch_id)
        conn.commit()

        for checkpoint_offset, checkpoint in checkpoint_slices(ids, offset, args.checkpoint_size):
            if checkpoint_offset != offset:
                raise ChangesFetchError("Shard checkpoint offset changed unexpectedly.")
            checkpoint_counts: Counter[str] = Counter()
            for location_id in checkpoint:
                detail = fetch_location_detail(args.base_url, api_key, location_id)
                if detail is None:
                    raise ChangesFetchError(f"Detail fetch failed for {location_id}")
                # The immutable manifest is built from CQC's active-location
                # directory.  Detail registration status may lag that source;
                # preserve directory membership as the authoritative status.
                record = clean_location(detail, directory_active=True)
                if record is None:
                    raise ChangesFetchError(f"Detail cleaning failed for {location_id}")
                checkpoint_counts[upsert_provider(cur, record)] += 1
                if record.get("latitude") is not None and record.get("longitude") is not None:
                    cur.execute(
                        """
                        UPDATE care_providers
                        SET geom = ST_SetSRID(ST_MakePoint(longitude::float, latitude::float), 4326)
                        WHERE id = %s
                        """,
                        (location_id,),
                    )
                time.sleep(args.sleep)

            offset += len(checkpoint)
            totals.update(checkpoint_counts)
            cur.execute(
                """
                UPDATE reconciliation_shards
                SET next_offset = %s, processed_count = %s, records_inserted = %s,
                    records_updated = %s, updated_at = NOW()
                WHERE batch_id = %s AND shard_index = %s
                """,
                (offset, offset, totals["inserted"], totals["updated"], str(batch_id), shard_index),
            )
            _sync_reconciliation_run_evidence(cur, batch_id)
            conn.commit()
            print(f"Shard {shard_index}: committed {offset}/{len(ids)}")

        cur.execute(
            """
            UPDATE reconciliation_shards
            SET status = 'completed', completed_at = NOW(), updated_at = NOW()
            WHERE batch_id = %s AND shard_index = %s
            """,
            (str(batch_id), shard_index),
        )
        _sync_reconciliation_run_evidence(cur, batch_id)
        conn.commit()
        return 0
    except Exception as exc:
        conn.rollback()
        cur.execute(
            """
            UPDATE reconciliation_shards
            SET status = 'failed', error_message = %s, updated_at = NOW(),
                fetch_failures = fetch_failures + %s,
                clean_failures = clean_failures + %s
            WHERE batch_id = %s AND shard_index = %s
            """,
            (
                str(exc)[:4000], int("fetch" in str(exc).lower()), int("clean" in str(exc).lower()),
                str(batch_id), shard_index,
            ),
        )
        _record_alert_state(
            cur, f"reconciliation_shard_failed:{batch_id}:{shard_index}", "error",
            {"batchId": str(batch_id), "shardIndex": shard_index, "error": str(exc)[:1000]},
        )
        _sync_reconciliation_run_evidence(cur, batch_id)
        conn.commit()
        raise
    finally:
        cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))
        conn.commit()


def _repair_missing_slugs(cur) -> None:
    cur.execute("SELECT id, name, town FROM care_providers WHERE slug IS NULL OR slug = '' ORDER BY id")
    missing = cur.fetchall()
    if not missing:
        return
    cur.execute("SELECT slug FROM care_providers WHERE slug IS NOT NULL AND slug != ''")
    used = {row[0] for row in cur.fetchall()}
    for location_id, name, town in missing:
        base = _make_slug(name or "", town or "", location_id)
        slug = base
        if slug in used:
            slug = f"{base}-{_slugify(location_id, separator='-') or location_id.lower()}"
        used.add(slug)
        cur.execute("UPDATE care_providers SET slug = %s WHERE id = %s", (slug, location_id))



def _summarise_ids(ids: list[str], limit: int = 10) -> str:
    """Name ids in a refusal without letting the message grow without bound."""
    if not ids:
        return "none"
    shown = ", ".join(ids[:limit])
    if len(ids) > limit:
        shown += f", ... ({len(ids)} total)"
    return shown


def _finalize_batch(args: argparse.Namespace, conn, cur) -> int:
    batch_id = _parse_batch_id(args.batch_id)
    manifest = load_snapshot_manifest(_require_manifest_path(args.snapshot_manifest))
    shard_count, location_count = _validate_manifest_for_batch(cur, manifest, batch_id)
    validate_shard_coordinates(shard_count)
    ids = manifest["locationIds"]

    if not args.dry_run:
        # Freeze shard ownership before evaluating completion. Shard workers use
        # the same advisory keys, so no worker can still be committing (or
        # restart) between the coverage proof and the atomic watermark write.
        cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-finalizer', 0))")
        for shard_index in range(shard_count):
            lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
            cur.execute(
                "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))",
                (lock_key,),
            )
            if not cur.fetchone()[0]:
                raise ChangesFetchError(
                    f"Batch finalization refused: shard {shard_index} is still running."
                )

    cur.execute(
        """
        SELECT shard_index, status, expected_count, processed_count, records_inserted, records_updated,
               fetch_failures, clean_failures, manifest_checksum_sha256
        FROM reconciliation_shards WHERE batch_id = %s ORDER BY shard_index
        """,
        (str(batch_id),),
    )
    shards = cur.fetchall()
    expected_partitions = partition_location_ids(ids, shard_count)
    complete = (
        len(shards) == shard_count
        and [int(row[0]) for row in shards] == list(range(shard_count))
        and all(row[1] == "completed" for row in shards)
        and all(int(row[2]) == len(expected_partitions[index]) for index, row in enumerate(shards))
        and all(int(row[3]) == int(row[2]) for row in shards)
        and sum(int(row[2]) for row in shards) == location_count
        and all(str(row[8]) == manifest["manifestChecksumSha256"] for row in shards)
    )
    if not complete:
        raise ChangesFetchError("Batch finalization refused: shard coverage is incomplete or inconsistent.")

    batch_select = "SELECT active_records_before, pipeline_run_id FROM reconciliation_batches WHERE id = %s"
    if not args.dry_run:
        batch_select += " FOR UPDATE"
    cur.execute(batch_select, (str(batch_id),))
    batch = cur.fetchone()
    active_before, pipeline_run_id = int(batch[0]), int(batch[1])
    if active_before and max(active_before - location_count, 0) / active_before > MAX_ACTIVE_COUNT_DROP_RATIO:
        raise ChangesFetchError("Batch finalization refused: active-count drop exceeds the safety threshold.")
    # A manifest location that is not ACTIVE is not evidence of reconciliation failure.
    # The shard-coverage check above already proves this batch wrote every manifest
    # location, and every one of those writes forces status 'ACTIVE' because directory
    # membership is authoritative. The only other writer of care_providers.status is the
    # source poll, which derives status from the detailed registrationStatus field and so
    # deregisters locations the snapshot still lists. Requiring exact equality therefore
    # refused legitimate batches whenever the poll flipped a location inside the batch
    # window. Divergence is bounded instead: an unexplained loss above
    # MAX_ACTIVE_COUNT_DROP_RATIO still refuses the batch, and the end-state equality below
    # is retargeted to the covered count.
    # The three-way split below keeps a missing row, a NULL status and any status other than
    # ACTIVE/INACTIVE out of the tolerated divergence: the source poll always writes a status,
    # so it cannot account for them, and they still fail closed.
    # FIX 2: the coverage read returns the ACTIVE ids as well as their count, so
    # the end-state guard below can compare identities instead of a total. Equal
    # counts hide one location leaving the ACTIVE set while another enters it, and
    # the count guard accepted exactly that.
    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE UPPER(status) = 'ACTIVE'),
            COUNT(*) FILTER (WHERE UPPER(status) = 'INACTIVE'),
            COALESCE(
                ARRAY_AGG(id::text ORDER BY id) FILTER (WHERE UPPER(status) = 'ACTIVE'),
                ARRAY[]::text[]
            )
        FROM care_providers
        WHERE id = ANY(%s)
        """,
        (ids,),
    )
    (
        active_manifest_covered,
        inactive_manifest_covered,
        active_manifest_id_rows,
    ) = cur.fetchone()
    active_manifest_covered = int(active_manifest_covered)
    inactive_manifest_covered = int(inactive_manifest_covered)
    active_manifest_ids = [str(value) for value in active_manifest_id_rows]
    unattributable_manifest = (
        location_count - active_manifest_covered - inactive_manifest_covered
    )
    if unattributable_manifest:
        raise ChangesFetchError(
            f"Batch finalization refused: {unattributable_manifest} manifest locations are "
            "missing or carry a status the source cannot produce."
        )
    if (
        inactive_manifest_covered
        and inactive_manifest_covered / location_count > MAX_ACTIVE_COUNT_DROP_RATIO
    ):
        raise ChangesFetchError(
            f"Batch finalization refused: {inactive_manifest_covered} of {location_count} "
            "manifest locations are not active."
        )
    # The active expectation is completed below, once candidate deactivations
    # have been confirmed against the live API: locations that are still
    # registered stay ACTIVE and are counted explicitly rather than dropped
    # from the expectation, so the end-state equality guard stays strict.
    expected_active = active_manifest_covered

    if args.dry_run:
        print(f"DRY RUN — batch {batch_id} is finalizable; no deactivations or watermarks were written.")
        conn.rollback()
        return 0

    cur.execute(
        """
        SELECT source_published_at, source_checksum_sha256
        FROM pipeline_runs
        WHERE run_type = 'reconciliation' AND status = 'completed'
          AND counts_reconciled = TRUE AND reconciled_at IS NOT NULL
          AND source_published_at IS NOT NULL
        ORDER BY source_published_at DESC, completed_at DESC LIMIT 1
        """
    )
    latest_source = cur.fetchone()
    manifest_date = datetime.fromisoformat(manifest["sourcePublishedAt"]).date()
    if latest_source:
        if manifest_date < latest_source[0]:
            raise ChangesFetchError("Batch finalization refused: source publication would regress the watermark.")
        if manifest_date == latest_source[0] and manifest["sourceChecksumSha256"] != str(latest_source[1]):
            raise ChangesFetchError("Batch finalization refused: same-date source checksum conflicts with the watermark.")

    cur.execute(
        "SELECT id FROM care_providers WHERE UPPER(status) = 'ACTIVE' AND NOT (id = ANY(%s)) ORDER BY id",
        (ids,),
    )
    candidate_deactivation_ids = [str(row[0]) for row in cur.fetchall()]
    # Absence from the snapshot is a candidate for deactivation, never proof of
    # it: the snapshot is published on a schedule, so a location registered
    # after it was produced is legitimately ACTIVE while missing from the
    # manifest. Every candidate is confirmed against the live API before any
    # write, exactly as the shard path confirms individual details, and an id
    # that cannot be confirmed is never deactivated.
    if candidate_deactivation_ids:
        decisions = confirm_deactivation_candidates(
            candidate_deactivation_ids,
            base_url=getattr(args, "base_url", None) or DEFAULT_BASE_URL,
            api_key=getattr(args, "api_key", None) or get_api_key(),
        )
    else:
        decisions = []
    deactivation_summary = summarise_deactivation_decisions(decisions)
    deactivation_ids = [decision.location_id for decision in decisions if decision.deactivates]
    unconfirmed_ids = list(deactivation_summary["unconfirmed_ids"])
    # FIX 3: only ids the live API affirmatively confirmed as still REGISTERED
    # may complete the expectation. A candidate whose status was missing,
    # non-string, malformed, unfamiliar ("Suspended") or unreadable (API error)
    # stays ACTIVE — we never deactivate on a guess — but it is never absorbed
    # into the expectation either, because absorbing it would let an API failure
    # or an unfamiliar status silently become the explanation for a change in
    # the active set, which is precisely what this guard exists to catch.
    confirmed_still_registered = len(deactivation_summary["confirmed_still_registered_ids"])
    acknowledged_unconfirmed = 0
    if unconfirmed_ids:
        if not getattr(args, "acknowledge_unconfirmed_deactivations", False):
            raise ChangesFetchError(
                "Batch finalization refused: "
                f"{len(unconfirmed_ids)} deactivation candidate(s) could not be confirmed as "
                "deregistered against the live CQC API (unconfirmed ids: "
                f"{', '.join(unconfirmed_ids[:10])}"
                f"{', ...' if len(unconfirmed_ids) > 10 else ''}). They remain ACTIVE and are "
                "NOT counted as expected; re-run with "
                "--acknowledge-unconfirmed-deactivations to record them as explicitly "
                "unconfirmed and finalize anyway."
            )
        acknowledged_unconfirmed = len(unconfirmed_ids)
    # Every ACTIVE row after this transaction must be accounted for by exactly
    # one of: a manifest location, an API-confirmed still-registered candidate,
    # or an unconfirmed candidate the operator explicitly acknowledged (recorded
    # on the batch row below). FIX 2: that accounting is done on IDs, not on a
    # total, because equal counts still allow one location to be substituted for
    # another.
    #
    # Deactivated candidates deliberately do NOT appear here: they were never
    # counted in ``active_manifest_covered`` (they are active rows *absent* from
    # the manifest), so they leave the ACTIVE set without changing this
    # expectation. Subtracting them would understate the expectation and let a
    # real divergence through — the failure mode this guard exists to catch.
    expected_active = (
        active_manifest_covered
        + confirmed_still_registered
        + acknowledged_unconfirmed
    )
    expected_active_ids = set(active_manifest_ids)
    expected_active_ids.update(deactivation_summary["confirmed_still_registered_ids"])
    if acknowledged_unconfirmed:
        expected_active_ids.update(unconfirmed_ids)
    if len(expected_active_ids) != expected_active:
        # The three buckets are disjoint by construction: a candidate is an
        # ACTIVE row absent from the manifest, and confirmed/unconfirmed are the
        # two halves of one classification. If they are not disjoint the
        # expectation itself is unsound, so refuse rather than compare against it.
        raise ChangesFetchError(
            "Batch finalization refused: the expected active identities are not disjoint "
            f"({len(expected_active_ids)} distinct ids for an expected {expected_active})."
        )
    for location_id in deactivation_ids:
        upsert_provider(cur, {"id": location_id, "status": "INACTIVE"})
    deactivated = len(deactivation_ids)
    # FIX 2: compare identities, not the total. The read below is the end state
    # of this batch's own writes, taken with this transaction's snapshot
    # visibility (READ COMMITTED, the connection's mode): any identity
    # substituted by a transaction that *committed* before this read is visible
    # to it, and refuses the batch -- which is the case the reviewer reproduced.
    _repair_missing_slugs(cur)
    # FIX 4: hold that comparison under a lock that prevents a concurrent
    # identity substitution from committing between the read below and this
    # transaction's commit. The attestation is written from this read and
    # committed at the same instant as the rest of this transaction, so a read
    # that is not protected for that whole span can certify a set the estate no
    # longer has.
    #
    # Mechanism: SHARE ROW EXCLUSIVE on care_providers. It conflicts with the
    # ROW EXCLUSIVE that every INSERT, UPDATE and DELETE on this table takes, so
    # *every* writer of care_providers.status is held off without having to
    # cooperate -- the ingestion poll path, the shard path, and ad-hoc operator
    # SQL alike -- while plain readers (ACCESS SHARE) are unaffected. An
    # isolation-level change was rejected instead: under REPEATABLE READ or
    # SERIALIZABLE the read would take this transaction's snapshot from its
    # *first* statement, which is before the deactivation writes even start, so
    # a substitution committed after that point would become invisible to the
    # guard and the guarded refusal below would silently stop firing -- that
    # weakens an existing refusal path rather than protecting it. A cooperative
    # advisory lock was rejected because its guarantee evaporates the moment any
    # writer path forgets to take it, which is the same class of defect as the
    # one being fixed.
    #
    # Placement matters and is load-bearing: the lock is requested after the
    # last care_providers write this transaction makes (the deactivations above
    # and _repair_missing_slugs) and after the API confirmation work, so it is
    # neither requested while holding care_providers row locks a writer is
    # already waiting on, nor held across network I/O. The held window is one
    # SELECT plus the batch/pipeline status updates that commit with it.
    #
    # Residual, stated explicitly: this transaction's commit releases the lock,
    # so a substitution committed *after* that commit is not covered by this
    # attestation. That is a genuinely later change rather than evidence this
    # batch certified falsely, and it is caught by the next batch's coverage
    # check. If the lock cannot be acquired (a writer in flight, or an
    # operator's own lock on this table) the finalize waits, and on the caller's
    # statement_timeout it aborts: a batch that is not finalized, not a batch
    # finalized without its evidence.
    cur.execute("LOCK TABLE care_providers IN SHARE ROW EXCLUSIVE MODE")
    cur.execute(
        "SELECT id::text FROM care_providers WHERE UPPER(status) = 'ACTIVE' ORDER BY id"
    )
    active_after_ids = {str(row[0]) for row in cur.fetchall()}
    active_after = len(active_after_ids)
    missing_active_ids = sorted(expected_active_ids - active_after_ids)
    extra_active_ids = sorted(active_after_ids - expected_active_ids)
    if missing_active_ids or extra_active_ids:
        drift = {
            "expected_active_ids_count": len(expected_active_ids),
            "active_after_ids_count": len(active_after_ids),
            "missing_active_ids": missing_active_ids,
            "extra_active_ids": extra_active_ids,
        }
        message = (
            "Final active-location identity does not match the authoritative manifest: "
            f"expected {len(expected_active_ids)} active ids "
            f"(manifest_active={active_manifest_covered}, "
            f"confirmed_registered={confirmed_still_registered}, "
            f"acknowledged_unconfirmed={acknowledged_unconfirmed}, deactivated={deactivated}) "
            f"but found {len(active_after_ids)} "
            f"({len(missing_active_ids)} missing, {len(extra_active_ids)} extra). "
            "missing ids (expected ACTIVE, not ACTIVE after the writes): "
            f"{_summarise_ids(missing_active_ids)}. "
            "extra ids (ACTIVE but accounted for by neither the manifest nor a confirmed "
            f"candidate): {_summarise_ids(extra_active_ids)}."
        )
        # Record the drift on the batch row, missing and extra separately, before
        # refusing. The finalizer's own transaction is abandoned — its
        # deactivations were never verified — so the evidence is committed on its
        # own; the caller then marks the batch failed with this same message.
        conn.rollback()
        try:
            cur.execute(
                """
                UPDATE reconciliation_batches
                SET deactivation_confirmation =
                        COALESCE(deactivation_confirmation, '{}'::jsonb) || %s::jsonb,
                    error_message = %s
                WHERE id = %s
                """,
                (
                    Json({"active_identity_drift": drift}),
                    message[:4000],
                    str(batch_id),
                ),
            )
            conn.commit()
        except Exception:  # pragma: no cover - evidence is best effort; the refusal is not
            conn.rollback()
        raise ChangesFetchError(message)
    inserted = sum(int(row[4]) for row in shards)
    updated = sum(int(row[5]) for row in shards)
    deactivation_record = {
        **deactivation_summary,
        # FIX 3: the operator acknowledgement and the unconfirmed ids are
        # recorded on the batch row itself, so a reader can see exactly which
        # active locations the batch could not confirm.
        "unconfirmed_count": len(unconfirmed_ids),
        "unconfirmed_ids": unconfirmed_ids,
        "acknowledged": bool(acknowledged_unconfirmed),
        "expected_active_after": expected_active,
        "active_after": active_after,
        # FIX 2: the end state was verified on identities, not on a total. Both
        # lists are empty on the success path — a non-empty one refuses above —
        # and their presence records that the comparison happened.
        "active_identity_verified": True,
        "expected_active_ids_count": len(expected_active_ids),
        "active_after_ids_count": len(active_after_ids),
        "missing_active_ids": missing_active_ids,
        "extra_active_ids": extra_active_ids,
    }
    cur.execute(
        """
        UPDATE reconciliation_batches
        SET status = 'completed', completed_at = NOW(), active_records_after = %s,
            records_inserted = %s, records_updated = %s, records_deactivated = %s,
            deactivation_unconfirmed_count = %s, deactivation_confirmation = %s,
            error_message = NULL
        WHERE id = %s
        """,
        (
            active_after,
            inserted,
            updated,
            deactivated,
            len(unconfirmed_ids),
            Json(deactivation_record),
            str(batch_id),
        ),
    )
    cur.execute(
        """
        UPDATE pipeline_runs
        SET status = 'completed', completed_at = NOW(), records_added = %s,
            records_updated = %s, source_uri = %s, source_published_at = %s,
            source_retrieved_at = %s, source_checksum_sha256 = %s,
            source_record_count = %s, active_records_before = %s,
            active_records_after = %s,
            source_total_count = %s, checked_count = %s,
            success_count = %s, failure_count = 0,
            counts_reconciled = TRUE, reconciled_at = NOW(),
            checkpoint_state = checkpoint_state || %s::jsonb,
            error_message = NULL
        WHERE id = %s
        """,
        (
            inserted, updated, manifest["sourceUri"], manifest["sourcePublishedAt"],
            manifest["sourceRetrievedAt"], manifest["sourceChecksumSha256"], location_count,
            active_before, active_after,
            location_count, location_count, location_count,
            json.dumps(
                {
                    "fullCoverage": True,
                    "restartable": False,
                    # Per-batch record of how candidate deactivations were
                    # classified from the live API before any write.
                    "deactivationConfirmation": deactivation_summary,
                }
            ),
            pipeline_run_id,
        ),
    )
    cur.execute(
        """
        UPDATE pipeline_alert_state SET resolved_at = NOW()
        WHERE alert_key LIKE %s AND resolved_at IS NULL
        """,
        (f"reconciliation_shard_failed:{batch_id}:%",),
    )
    conn.commit()
    print(
        f"Finalized batch {batch_id}: active={active_after}, deactivated={deactivated}, "
        f"inactive_in_manifest={inactive_manifest_covered} "
        f"({inactive_manifest_covered / location_count:.2%} of {location_count} manifest locations); "
        f"deactivation candidates={deactivation_summary['candidates']} "
        f"confirmed deregistered={deactivation_summary[CLASSIFICATION_DEREGISTERED]}, "
        f"kept active: registered={deactivation_summary[CLASSIFICATION_REGISTERED]} "
        f"unconfirmed={deactivation_summary[CLASSIFICATION_UNCONFIRMED]}"
    )
    return 0


def _ensure_no_active_reconciliation_batch(args: argparse.Namespace, conn, cur) -> None:
    """Fail-close an idle prepared/running batch so a new prepare is not deadlocked.

    Live shard workers still refuse the abort. Completed batches are never touched.
    Abort commits on its own connection transaction, so the prepare advisory lock
    is taken again afterwards and the active-batch check is repeated.
    """
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-prepare', 0))")
    cur.execute(
        """
        SELECT id FROM reconciliation_batches
        WHERE status IN ('prepared', 'running')
        ORDER BY created_at DESC LIMIT 1
        """
    )
    active_batch = cur.fetchone()
    if not active_batch:
        return
    stale_id = str(active_batch[0])
    saved_batch_id = args.batch_id
    args.batch_id = stale_id
    try:
        _abort_batch(args, conn, cur)
    except ShardAlreadyRunning as exc:
        raise ChangesFetchError(f"Reconciliation batch {stale_id} is still active.") from exc
    finally:
        args.batch_id = saved_batch_id
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-prepare', 0))")
    cur.execute(
        """
        SELECT id FROM reconciliation_batches
        WHERE status IN ('prepared', 'running')
        ORDER BY created_at DESC LIMIT 1
        """
    )
    remaining = cur.fetchone()
    if remaining:
        raise ChangesFetchError(f"Reconciliation batch {remaining[0]} is still active.")


def _abort_batch(args: argparse.Namespace, conn, cur) -> int:
    """Close an incomplete batch only after proving that no shard worker still owns a lock."""
    batch_id = _parse_batch_id(args.batch_id)
    if args.dry_run:
        raise ValueError("The abort phase does not support --dry-run.")
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-finalizer', 0))")
    cur.execute(
        "SELECT shard_count, status, pipeline_run_id FROM reconciliation_batches WHERE id = %s FOR UPDATE",
        (str(batch_id),),
    )
    batch = cur.fetchone()
    if not batch:
        raise ChangesFetchError(f"Reconciliation batch {batch_id} does not exist.")
    shard_count, status, pipeline_run_id = int(batch[0]), str(batch[1]), int(batch[2])
    if status == "completed":
        raise ChangesFetchError("A completed reconciliation batch cannot be aborted.")
    held_locks: list[str] = []
    try:
        for shard_index in range(shard_count):
            lock_key = f"cqc-reconciliation:{batch_id}:{shard_index}"
            cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (lock_key,))
            if not cur.fetchone()[0]:
                raise ShardAlreadyRunning(f"Shard {shard_index} is still running; batch abort refused.")
            held_locks.append(lock_key)
        reason = "Workflow ended before every shard completed"
        cur.execute(
            """
            UPDATE reconciliation_shards
            SET status = 'failed', updated_at = NOW(), error_message = %s
            WHERE batch_id = %s AND status = 'running'
            """,
            (reason, str(batch_id)),
        )
        cur.execute(
            """
            UPDATE reconciliation_batches
            SET status = 'failed', completed_at = NOW(), error_message = %s
            WHERE id = %s
            """,
            (reason, str(batch_id)),
        )
        cur.execute(
            """
            UPDATE pipeline_runs
            SET status = 'failed', completed_at = NOW(), error_message = %s,
                counts_reconciled = FALSE, reconciled_at = NULL,
                checkpoint_state = checkpoint_state || '{"restartable": true, "fullCoverage": false}'::jsonb
            WHERE id = %s
            """,
            (reason, pipeline_run_id),
        )
        conn.commit()
        print(f"Aborted incomplete reconciliation batch {batch_id}")
        return 0
    finally:
        for lock_key in held_locks:
            cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (lock_key,))
        conn.commit()


def _run_reconciliation_phase(args: argparse.Namespace, api_key: str | None, database_url: str) -> int:
    if args.checkpoint_size < 1:
        raise ValueError("--checkpoint-size must be at least 1")
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        try:
            if args.phase == "prepare":
                return _prepare_batch(args, conn, cur)
            if args.phase == "resume":
                return _resume_batch(args, conn, cur)
            if args.phase == "shard":
                if args.shard_index is None:
                    raise ValueError("--shard-index is required for the shard phase")
                return _run_shard(args, conn, cur, api_key)
            if args.phase == "finalize":
                return _finalize_batch(args, conn, cur)
            if args.phase == "abort":
                return _abort_batch(args, conn, cur)
            raise ValueError(f"Unsupported reconciliation phase: {args.phase}")
        except ShardAlreadyRunning:
            conn.rollback()
            raise
        except Exception as exc:
            conn.rollback()
            if not args.dry_run and args.batch_id:
                cur.execute(
                    """
                    UPDATE reconciliation_batches
                    SET status = 'failed', error_message = %s
                    WHERE id = %s AND status != 'completed'
                    """,
                    (str(exc)[:4000], args.batch_id),
                )
                cur.execute(
                    """
                    UPDATE pipeline_runs
                    SET status = 'failed', completed_at = NOW(), error_message = %s,
                        counts_reconciled = FALSE, reconciled_at = NULL,
                        checkpoint_state = checkpoint_state || '{"restartable": true, "fullCoverage": false}'::jsonb
                    WHERE id = (
                      SELECT pipeline_run_id FROM reconciliation_batches
                      WHERE id = %s AND status != 'completed'
                    ) AND status != 'completed'
                    """,
                    (str(exc)[:4000], args.batch_id),
                )
                conn.commit()
            raise
    finally:
        cur.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incremental CQC data update")
    parser.add_argument("--since", help="ISO date to fetch changes from (default: last pipeline run)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="CQC API base URL")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Sleep between API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing to DB")
    parser.add_argument(
        "--acknowledge-unconfirmed-deactivations",
        action="store_true",
        help=(
            "Finalize even when a deactivation candidate's live registration status could not "
            "be confirmed as deregistered. Unconfirmed candidates stay ACTIVE; their ids and "
            "count are recorded on the batch row and are never absorbed into the expected "
            "active count, so a residual mismatch still refuses the batch."
        ),
    )
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--phase",
        choices=("prepare", "resume", "shard", "finalize", "abort"),
        required=True,
    )
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--batch-id")
    parser.add_argument("--snapshot-manifest")
    parser.add_argument("--release-sha")
    parser.add_argument("--workflow-run-id")
    parser.add_argument("--workflow-run-attempt")
    parser.add_argument("--resume-source-run-id")
    parser.add_argument("--checkpoint-size", type=int, default=DEFAULT_CHECKPOINT_SIZE)
    parser.add_argument(
        "--data-page-url",
        default=DEFAULT_DATA_PAGE_URL,
        help="Official CQC page containing the current directory CSV link",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.dry_run and args.phase in {"prepare", "resume"}:
        execution_identity = (
            args.release_sha,
            args.workflow_run_id,
            args.workflow_run_attempt,
        )
        valid_execution_identity = (
            all(execution_identity)
            and re.fullmatch(r"[0-9a-f]{40}", args.release_sha.lower()) is not None
            and args.workflow_run_id.isdigit()
            and int(args.workflow_run_id) > 0
            and args.workflow_run_attempt.isdigit()
            and int(args.workflow_run_attempt) > 0
        )
        valid_resume_source = (
            args.phase != "resume"
            or (
                bool(args.resume_source_run_id)
                and args.resume_source_run_id.isdigit()
                and int(args.resume_source_run_id) > 0
            )
        )
        if not valid_execution_identity or not valid_resume_source:
            print(
                "ERROR: prepare/resume writes require valid execution identity and resume source lineage.",
                file=sys.stderr,
            )
            return 1

    api_key = get_api_key()
    if not api_key and not args.dry_run and args.phase == "shard":
        print("ERROR: CQC_API_KEY not set.", file=sys.stderr)
        return 1

    database_url = normalize_database_url(args.database_url) if args.database_url else get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL is required for reconciliation phases.", file=sys.stderr)
        return 1

    try:
        return _run_reconciliation_phase(args, api_key, database_url)
    except (ChangesFetchError, ValueError) as exc:
        print(f"Reconciliation {args.phase} failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
