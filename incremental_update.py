#!/usr/bin/env python3
"""Prepare, shard, resume, and finalize an authoritative CQC reconciliation batch.

Usage:
    python3 incremental_update.py --phase prepare --batch-id UUID --shard-count 4 --snapshot-manifest manifest.json
    python3 incremental_update.py --phase shard --batch-id UUID --shard-count 4 --shard-index 0 --snapshot-manifest manifest.json
    python3 incremental_update.py --phase finalize --batch-id UUID --shard-count 4 --snapshot-manifest manifest.json
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
from typing import Any
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import psycopg2
from psycopg2.extras import Json
import requests

from api.services.provider_state_events import ProviderStateEvent, build_provider_state_events
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
    deactivations. Individual API details are still fetched before any write.
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
                return normalize_database_url(line.split("=", 1)[1].strip())
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

    # Rating
    overall_rating = ""
    current_ratings = data.get("currentRatings", {})
    if isinstance(current_ratings, dict):
        overall_block = current_ratings.get("overall", {})
        if isinstance(overall_block, dict):
            overall_rating = overall_block.get("rating", "") or ""

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

    reg_status = normalize_whitespace(data.get("registrationStatus", ""))
    status = "ACTIVE" if directory_active else (
        "ACTIVE" if "register" in reg_status.lower() and "deregister" not in reg_status.lower() else "INACTIVE"
    )

    return {
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
        "phone": normalize_whitespace(data.get("mainPhoneNumber", "")),
        "website": normalize_whitespace(data.get("website", "")),
        "overall_rating": overall_rating,
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
    }


ALLOWED_COLUMNS = frozenset({
    "id", "provider_id", "name", "slug", "type", "status", "registration_date",
    "address_line1", "address_line2", "town", "county", "postcode",
    "region", "local_authority", "latitude", "longitude", "phone", "website",
    "overall_rating", "rating_safe", "rating_effective", "rating_caring",
    "rating_responsive", "rating_well_led", "last_inspection_date",
    "inspection_report_url", "registered_manager_absent_date",
    "service_types", "specialisms", "number_of_beds", "ownership_type",
    "last_updated",
})


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

    existing_columns = (
        "id", "provider_id", "overall_rating", "status", "ownership_type",
        "name", "slug", "town", "postcode", "region", "registration_date",
        "last_inspection_date", "last_updated",
    )
    cur.execute(
        f"SELECT {', '.join(existing_columns)} FROM care_providers WHERE id = %s",
        (safe_record["id"],),
    )
    existing_row = cur.fetchone()
    existing = dict(zip(existing_columns, existing_row, strict=True)) if existing_row else None

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

    current = dict(existing or {})
    current.update(safe_record)
    current.update(source_context)
    events = build_provider_state_events(existing, current)
    for event in events:
        inserted = _insert_trusted_provider_event(cur, event, current)
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
            _parse_watermark_datetime(current.get("source_checked_at")) or datetime.now(timezone.utc),
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

    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended('cqc-reconciliation-prepare', 0))")
    cur.execute(
        """
        SELECT id FROM reconciliation_batches
        WHERE status IN ('prepared', 'running')
        ORDER BY created_at DESC LIMIT 1
        """
    )
    active_batch = cur.fetchone()
    if active_batch:
        raise ChangesFetchError(f"Reconciliation batch {active_batch[0]} is still active.")

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
            }, sort_keys=True),
            snapshot.source_uri, snapshot.source_published_at, snapshot.retrieved_at,
            snapshot.checksum_sha256, len(snapshot.location_ids),
            json.dumps({
                "batchId": str(batch_id),
                "shardCount": args.shard_count,
                "restartable": True,
                "restarts": {},
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
    cur.execute("SELECT COUNT(*) FROM care_providers WHERE id = ANY(%s) AND UPPER(status) = 'ACTIVE'", (ids,))
    active_covered = int(cur.fetchone()[0])
    if active_covered != location_count:
        raise ChangesFetchError(
            f"Batch finalization refused: {location_count - active_covered} manifest locations are not active."
        )

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
    deactivation_ids = [str(row[0]) for row in cur.fetchall()]
    for location_id in deactivation_ids:
        upsert_provider(cur, {"id": location_id, "status": "INACTIVE"})
    deactivated = len(deactivation_ids)
    _repair_missing_slugs(cur)
    cur.execute("SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE'")
    active_after = int(cur.fetchone()[0])
    if active_after != location_count:
        raise ChangesFetchError("Final active-location count does not match the authoritative manifest.")
    inserted = sum(int(row[4]) for row in shards)
    updated = sum(int(row[5]) for row in shards)
    cur.execute(
        """
        UPDATE reconciliation_batches
        SET status = 'completed', completed_at = NOW(), active_records_after = %s,
            records_inserted = %s, records_updated = %s, records_deactivated = %s,
            error_message = NULL
        WHERE id = %s
        """,
        (active_after, inserted, updated, deactivated, str(batch_id)),
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
            json.dumps({"fullCoverage": True, "restartable": False}),
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
    print(f"Finalized batch {batch_id}: active={active_after}, deactivated={deactivated}")
    return 0


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
                    WHERE id = (SELECT pipeline_run_id FROM reconciliation_batches WHERE id = %s)
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
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument("--phase", choices=("prepare", "shard", "finalize", "abort"), required=True)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--batch-id")
    parser.add_argument("--snapshot-manifest")
    parser.add_argument("--checkpoint-size", type=int, default=DEFAULT_CHECKPOINT_SIZE)
    parser.add_argument(
        "--data-page-url",
        default=DEFAULT_DATA_PAGE_URL,
        help="Official CQC page containing the current directory CSV link",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

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
