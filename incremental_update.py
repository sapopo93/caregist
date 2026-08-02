#!/usr/bin/env python3
"""
Incremental update: fetch only changed providers from CQC API and upsert into database.

Uses the CQC /changes/location endpoint to detect changes since last run,
fetches updated detail records, cleans them, and upserts into PostgreSQL.

Usage:
    python3 incremental_update.py                          # Update since last pipeline run
    python3 incremental_update.py --since 2026-03-01       # Update since specific date
    python3 incremental_update.py --dry-run                # Show what would change without writing
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
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
INCREMENTAL_UPDATE_LOCK_ID = 802451201
DEFAULT_MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
MIN_EXPECTED_ACTIVE_LOCATIONS = 50_000
MAX_ACTIVE_COUNT_DROP_RATIO = 0.05
_CQC_ID_RE = re.compile(r"^(?:1-\d{5,12}|[A-Z][A-Z0-9-]{1,19})$")


class ChangesFetchError(RuntimeError):
    """Raised when the CQC changes API cannot be fetched reliably."""


@dataclass(frozen=True)
class CqcActiveSnapshot:
    source_uri: str
    source_published_at: str
    retrieved_at: datetime
    checksum_sha256: str
    location_ids: frozenset[str]


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
                return response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise ChangesFetchError(f"CQC resource returned {response.status_code}: {url}")
            last_error = ChangesFetchError(f"CQC resource returned {response.status_code}: {url}")
        except requests.RequestException as exc:
            last_error = exc
        if attempt < DEFAULT_MAX_RETRIES:
            time.sleep(attempt)
    raise ChangesFetchError(f"Unable to fetch CQC resource {url}: {last_error}")


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
    parsed_uri = urlparse(source_uri)
    if parsed_uri.scheme != "https" or not parsed_uri.hostname or not parsed_uri.hostname.endswith("cqc.org.uk"):
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


def _fetch_all_cqc_location_stubs(base_url: str, api_key: str | None, sleep: float) -> list[dict]:
    """Fetch all location stubs from GET /locations (returns locationId, locationName, postalCode)."""
    url = f"{base_url}/locations"
    headers = api_headers(api_key)
    all_items: list[dict] = []
    page = 1
    while True:
        try:
            resp = requests.get(url, headers=headers, params={"page": page, "perPage": 1000}, timeout=30)
            if resp.status_code != 200:
                raise ChangesFetchError(f"Location list scan returned {resp.status_code} on page {page}")
            data = resp.json()
            locations = data.get("locations", [])
            if not locations:
                break
            all_items.extend(locations)
            total = int(data.get("total", 0))
            if (page % 20) == 0:
                print(f"  Fetched {len(all_items)}/{total} location IDs from CQC list...")
            if len(all_items) >= total:
                break
            page += 1
            time.sleep(sleep)
        except ChangesFetchError:
            raise
        except Exception as exc:
            raise ChangesFetchError(f"Location list scan error on page {page}: {exc}") from exc
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


def acquire_run_lock(cur) -> bool:
    cur.execute("SELECT pg_try_advisory_lock(%s)", (INCREMENTAL_UPDATE_LOCK_ID,))
    row = cur.fetchone()
    return bool(row and row[0])


def release_run_lock(cur) -> None:
    cur.execute("SELECT pg_advisory_unlock(%s)", (INCREMENTAL_UPDATE_LOCK_ID,))


def create_pipeline_run(cur) -> int:
    cur.execute(
        "INSERT INTO pipeline_runs (run_type, started_at, status) VALUES ('incremental', NOW(), 'running') RETURNING id"
    )
    return int(cur.fetchone()[0])


def complete_pipeline_run(
    cur,
    run_id: int,
    *,
    inserted: int = 0,
    updated: int = 0,
    snapshot: CqcActiveSnapshot | None = None,
    active_before: int | None = None,
    active_after: int | None = None,
) -> None:
    cur.execute(
        """
        UPDATE pipeline_runs
        SET completed_at = NOW(),
            status = 'completed',
            records_added = %s,
            records_updated = %s,
            source_uri = %s,
            source_published_at = %s,
            source_retrieved_at = %s,
            source_checksum_sha256 = %s,
            source_record_count = %s,
            active_records_before = %s,
            active_records_after = %s,
            error_message = NULL
        WHERE id = %s
        """,
        (
            inserted,
            updated,
            snapshot.source_uri if snapshot else None,
            snapshot.source_published_at if snapshot else None,
            snapshot.retrieved_at if snapshot else None,
            snapshot.checksum_sha256 if snapshot else None,
            len(snapshot.location_ids) if snapshot else None,
            active_before,
            active_after,
            run_id,
        ),
    )


def fail_pipeline_run(cur, run_id: int, error_message: str) -> None:
    cur.execute(
        """
        UPDATE pipeline_runs
        SET completed_at = NOW(),
            status = 'failed',
            error_message = %s
        WHERE id = %s
        """,
        (error_message[:4000], run_id),
    )


def fetch_location_detail(base_url: str, api_key: str | None, location_id: str) -> dict[str, Any] | None:
    """Fetch full detail for a single location."""
    url = f"{base_url}/locations/{location_id}"
    for attempt in range(1, DEFAULT_MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=api_headers(api_key), timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in RETRYABLE_STATUS_CODES and attempt < DEFAULT_MAX_RETRIES:
                time.sleep(attempt)
                continue
            return None
        except Exception:
            if attempt < DEFAULT_MAX_RETRIES:
                time.sleep(attempt)
                continue
            return None


def clean_location(data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract and clean key fields from a location detail response."""
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

    reg_status = normalize_whitespace(data.get("registrationStatus", ""))
    status = "ACTIVE" if "register" in reg_status.lower() and "deregister" not in reg_status.lower() else "INACTIVE"

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
        "service_types": "|".join(service_types),
        "specialisms": "|".join(specialisms),
        "number_of_beds": data.get("numberOfBeds"),
        "ownership_type": normalize_whitespace(data.get("ownershipType", "")),
        "last_updated": data.get("lastUpdated") or data.get("lastUpdatedDate") or data.get("lastUpdatedTimestamp"),
    }


ALLOWED_COLUMNS = frozenset({
    "id", "provider_id", "name", "slug", "type", "status", "registration_date",
    "address_line1", "address_line2", "town", "county", "postcode",
    "region", "local_authority", "latitude", "longitude", "phone", "website",
    "overall_rating", "rating_safe", "rating_effective", "rating_caring",
    "rating_responsive", "rating_well_led", "last_inspection_date",
    "service_types", "specialisms", "number_of_beds", "ownership_type",
    "last_updated",
})


def upsert_provider(cur, record: dict[str, Any]) -> str:
    """Upsert a single provider record. Returns 'inserted', 'updated', or 'skipped'."""
    # Whitelist columns to prevent SQL injection via dict keys
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
    existing = dict(zip(existing_columns, existing_row)) if existing_row else None

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
        cur.execute(
            f"INSERT INTO care_providers ({cols_str}) VALUES ({placeholders})",
            vals + [now, now],
        )
        action = "inserted"

    current = dict(existing or {})
    current.update(safe_record)
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
          effective_date, old_value, new_value, source, confidence_score,
          dedupe_key, metadata, source_observed_at
        )
        VALUES (
          'care_provider', %s, %s, %s, %s,
          %s, %s, %s, 'cqc_api', 1.0000,
          %s, %s, %s
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
            json_value(event.old_value),
            json_value(event.new_value),
            event.dedupe_key,
            json_value(event.metadata),
            source_observed_at,
        ),
    )
    return cur.fetchone() is not None


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
        ON CONFLICT (event_dedupe_key) DO NOTHING
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incremental CQC data update")
    parser.add_argument("--since", help="ISO date to fetch changes from (default: last pipeline run)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="CQC API base URL")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Sleep between API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing to DB")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument(
        "--data-page-url",
        default=DEFAULT_DATA_PAGE_URL,
        help="Official CQC page containing the current directory CSV link",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    api_key = get_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: CQC_API_KEY not set.", file=sys.stderr)
        return 1

    database_url = normalize_database_url(args.database_url) if args.database_url else get_database_url()
    if not database_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set.")
        return 1

    conn = None
    cur = None
    run_id: int | None = None
    lock_acquired = False
    snapshot: CqcActiveSnapshot | None = None
    active_before: int | None = None

    try:
        if database_url:
            conn = psycopg2.connect(database_url)
            conn.autocommit = False
            cur = conn.cursor()

        since = args.since
        db_known_ids = frozenset()
        db_active_ids = frozenset()
        if cur is not None:
            since = resolve_since(cur, since)
            cur.execute("SELECT id, status FROM care_providers")
            db_rows = cur.fetchall()
            db_known_ids = frozenset(str(r[0]) for r in db_rows if r and r[0])
            db_active_ids = frozenset(
                str(r[0]) for r in db_rows if r and r[0] and str(r[1]).upper() == "ACTIVE"
            )
            active_before = len(db_active_ids)
        elif not since:
            since = (datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")

        if cur is not None and not args.dry_run:
            lock_acquired = acquire_run_lock(cur)
            if not lock_acquired:
                conn.rollback()
                print("Another incremental update is already running. Skipping.")
                return 0

            run_id = create_pipeline_run(cur)
            conn.commit()

        print(f"Fetching CQC changes since {since}...")
        used_list_scan_fallback = False
        changed_ids = fetch_changes(args.base_url, api_key, since, args.sleep)
        if changed_ids is None:
            print("WARNING: /changes/location endpoint unavailable (404/410). Using full CQC snapshot reconciliation.")
            used_list_scan_fallback = True
            if cur is None:
                raise RuntimeError("Database baseline is required for list-scan fallback.")
            if cur is not None and not args.dry_run:
                try:
                    cur.execute(
                        """
                        INSERT INTO pipeline_alert_log (alert_key, severity, details)
                        VALUES ('changes_endpoint_unavailable', 'warning',
                                '{"message": "CQC /changes/location returned 404/410; falling back to list scan"}'::jsonb)
                        """,
                    )
                    conn.commit()
                except Exception as alert_exc:
                    print(f"  (Could not log alert: {alert_exc})")
            snapshot = fetch_active_location_snapshot(args.data_page_url)
            reconciliation = build_snapshot_reconciliation(
                snapshot,
                db_ids=db_known_ids,
                db_active_ids=db_active_ids,
            )
            changed_ids = sorted(reconciliation["detail_ids"])
            print(
                "Snapshot reconciliation: "
                f"source_active={len(snapshot.location_ids)} "
                f"new={len(reconciliation['new_ids'])} "
                f"candidate_deactivations={len(reconciliation['candidate_deactivation_ids'])} "
                f"details_to_verify={len(changed_ids)}"
            )
            if args.dry_run:
                print("DRY RUN — no provider records or pipeline watermarks were changed.")
                return 0
        else:
            print(f"Found {len(changed_ids)} changed locations")

        if not changed_ids:
            if cur is not None and run_id is not None:
                complete_pipeline_run(cur, run_id, inserted=0, updated=0)
                conn.commit()
            print("No changes to process.")
            return 0

        # Fetch details and clean
        results = Counter()
        records: list[dict[str, Any]] = []

        for i, loc_id in enumerate(changed_ids):
            detail = fetch_location_detail(args.base_url, api_key, loc_id)
            if detail is None:
                results["fetch_failed"] += 1
                continue

            cleaned = clean_location(detail)
            if cleaned is None:
                results["clean_failed"] += 1
                continue

            records.append(cleaned)

            if (i + 1) % 50 == 0:
                print(f"  Fetched {i+1}/{len(changed_ids)} details...")
            time.sleep(args.sleep)

        print(f"Fetched {len(records)} valid records ({results['fetch_failed']} fetch failures)")

        if results.get("fetch_failed", 0) or results.get("clean_failed", 0):
            raise RuntimeError(
                "CQC reconciliation was incomplete: "
                f"fetch_failed={results.get('fetch_failed', 0)}, "
                f"clean_failed={results.get('clean_failed', 0)}. No records were committed."
            )

        if args.dry_run:
            print(f"\nDRY RUN — would upsert {len(records)} records:")
            for r in records[:10]:
                print(f"  {r['id']} | {r['name'][:40]} | {r['status']} | {r['overall_rating']}")
            if len(records) > 10:
                print(f"  ... and {len(records) - 10} more")
            return 0

        # Upsert into database
        if conn is None or cur is None:
            raise RuntimeError("Database connection not available for non-dry-run execution.")

        for record in records:
            action = upsert_provider(cur, record)
            results[action] += 1

        # Update geometry for changed records
        ids = [r["id"] for r in records if r.get("latitude") and r.get("longitude")]
        if ids:
            cur.execute("""
                UPDATE care_providers
                SET geom = ST_SetSRID(ST_MakePoint(longitude::float, latitude::float), 4326)
                WHERE id = ANY(%s) AND latitude IS NOT NULL AND longitude IS NOT NULL
            """, (ids,))

        # Backfill slugs for any providers that ended up with NULL slug (e.g. from a prior
        # incremental run before slug generation was added). Generates slug from name+town+id
        # with collision handling against the unique constraint.
        cur.execute("SELECT id, name, town FROM care_providers WHERE slug IS NULL OR slug = ''")
        null_slug_rows = cur.fetchall()
        if null_slug_rows:
            print(f"  Backfilling slugs for {len(null_slug_rows)} providers with NULL slug...")
            cur.execute("SELECT slug FROM care_providers WHERE slug IS NOT NULL AND slug != ''")
            used_slugs = {r[0] for r in cur.fetchall()}
            for row_id, row_name, row_town in null_slug_rows:
                base = _make_slug(row_name or "", row_town or "", row_id)
                slug = base
                if slug in used_slugs:
                    id_suffix = _slugify(row_id, separator="-") or row_id.lower()
                    slug = f"{base}-{id_suffix}"
                used_slugs.add(slug)
                cur.execute("UPDATE care_providers SET slug = %s WHERE id = %s", (slug, row_id))
            print("  Slug backfill complete.")

        cur.execute("SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE'")
        active_after = int(cur.fetchone()[0])
        complete_pipeline_run(
            cur,
            run_id,
            inserted=results.get("inserted", 0),
            updated=results.get("updated", 0),
            snapshot=snapshot,
            active_before=active_before,
            active_after=active_after,
        )
        conn.commit()

    except KeyboardInterrupt:
        if conn is not None:
            conn.rollback()
        if cur is not None and run_id is not None:
            try:
                fail_pipeline_run(cur, run_id, "Interrupted before commit")
                conn.commit()
            except Exception:
                if conn is not None:
                    conn.rollback()
        print("Update interrupted before commit.", file=sys.stderr)
        return 130
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        if cur is not None and run_id is not None:
            try:
                fail_pipeline_run(cur, run_id, str(exc))
                conn.commit()
            except Exception:
                if conn is not None:
                    conn.rollback()
        print(f"Update failed: {exc}")
        return 1
    finally:
        if cur is not None and lock_acquired:
            try:
                release_run_lock(cur)
                if conn is not None:
                    conn.commit()
            except Exception:
                if conn is not None:
                    conn.rollback()
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    print("\nIncremental update complete:")
    print(f"  Inserted: {results.get('inserted', 0)}")
    print(f"  Updated: {results.get('updated', 0)}")
    print(f"  Stale skipped: {results.get('stale_skipped', 0)}")
    print(f"  Fetch failures: {results.get('fetch_failed', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
