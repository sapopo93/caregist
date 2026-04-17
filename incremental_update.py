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
import json
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import requests

from cqc_common import deep_get, first_non_empty, normalize_whitespace, parse_any_date, ensure_list, to_float

DEFAULT_BASE_URL = "https://api.service.cqc.org.uk/public/v1"
DEFAULT_SLEEP = 0.15
DEFAULT_LOOKBACK_DAYS = 7
INCREMENTAL_UPDATE_LOCK_ID = 802451201
DEFAULT_MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# ETL intermediate file written by extract_cqc.py — used as the "known IDs" baseline
LOCATIONS_LIST_CACHE = Path("_locations_list.ndjson")
# Safety cap: never fetch more than this many detail records in one list-scan fallback run
LIST_SCAN_MAX_DETAIL_FETCHES = 5000


class ChangesFetchError(RuntimeError):
    """Raised when the CQC changes API cannot be fetched reliably."""


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
        return url
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    return None


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


def _load_known_location_ids() -> frozenset[str]:
    """Load the set of location IDs seen in the last full ETL run from the cache file."""
    if not LOCATIONS_LIST_CACHE.exists():
        return frozenset()
    ids: set[str] = set()
    for line in LOCATIONS_LIST_CACHE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            loc_id = item.get("locationId") or item.get("id")
            if loc_id:
                ids.add(str(loc_id))
        except json.JSONDecodeError:
            pass
    return frozenset(ids)


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


def _append_to_locations_cache(new_stubs: list[dict]) -> None:
    """Append newly discovered location stubs to the ETL cache file."""
    if not new_stubs:
        return
    try:
        with LOCATIONS_LIST_CACHE.open("a", encoding="utf-8") as fh:
            for stub in new_stubs:
                fh.write(json.dumps(stub, ensure_ascii=True) + "\n")
    except OSError as exc:
        print(f"  Warning: could not update locations cache: {exc}")


def _parse_since_dt(since: str) -> datetime:
    """Parse the since string to a naive UTC datetime for comparison."""
    since_clean = since.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(since_clean)
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=DEFAULT_LOOKBACK_DAYS)


def fetch_recent_via_list_scan(
    base_url: str, api_key: str | None, since: str, sleep: float
) -> list[str]:
    """Fallback when /changes/location is unavailable.

    Strategy:
    1. Load the set of known location IDs from _locations_list.ndjson (written by the full ETL).
    2. Fetch all current location IDs from GET /locations (CQC list endpoint, no date filter).
    3. Diff: IDs in CQC now but not in the known set are candidates.
    4. Fetch the detail record for each candidate and filter by registrationDate >= since.
    5. Append new stubs to the cache so future runs don't re-process them.

    The CQC /locations list endpoint returns only (locationId, locationName, postalCode) —
    no registrationDate, no registrationStatus filter. Date filtering requires detail fetches.
    """
    since_dt = _parse_since_dt(since)

    # Step 1: Load known IDs from ETL cache
    known_ids = _load_known_location_ids()
    cache_source = f"ETL cache ({len(known_ids)} IDs)" if known_ids else "no ETL cache found"
    print(f"  List scan baseline: {cache_source}")

    # Step 2: Fetch all current location IDs from CQC
    print(f"  Fetching all current CQC location IDs...")
    all_stubs = _fetch_all_cqc_location_stubs(base_url, api_key, sleep)
    all_ids = {str(stub.get("locationId") or stub.get("id", "")) for stub in all_stubs if stub.get("locationId") or stub.get("id")}
    print(f"  CQC total: {len(all_ids)} | Known from last ETL: {len(known_ids)}")

    # Step 3: Compute new IDs (in CQC now but not in our last ETL snapshot or care_providers)
    candidate_ids = sorted(all_ids - known_ids)  # sorted for deterministic order
    print(f"  Candidates (not in last ETL snapshot): {len(candidate_ids)}")

    if not candidate_ids:
        print("  No new location IDs found since last ETL run.")
        return []

    if len(candidate_ids) > LIST_SCAN_MAX_DETAIL_FETCHES:
        print(f"  WARNING: {len(candidate_ids)} candidates exceeds safety cap ({LIST_SCAN_MAX_DETAIL_FETCHES}). "
              f"Run full ETL to rebuild baseline: ./run_enriched_pipeline.sh")
        candidate_ids = candidate_ids[:LIST_SCAN_MAX_DETAIL_FETCHES]

    # Step 4: Fetch details for each candidate, filter by registrationDate >= since
    matched_ids: list[str] = []
    new_stubs_to_cache: list[dict] = []
    stub_by_id = {str(s.get("locationId") or s.get("id", "")): s for s in all_stubs}

    for i, loc_id in enumerate(candidate_ids):
        detail = fetch_location_detail(base_url, api_key, loc_id)
        new_stubs_to_cache.append(stub_by_id.get(loc_id, {"locationId": loc_id}))
        if detail is None:
            continue
        reg_date = parse_any_date(detail.get("registrationDate"))
        if reg_date:
            if isinstance(reg_date, str):
                try:
                    reg_date = datetime.fromisoformat(reg_date)
                except ValueError:
                    reg_date = None
            if reg_date is not None:
                if hasattr(reg_date, "tzinfo") and reg_date.tzinfo is not None:
                    reg_date = reg_date.replace(tzinfo=None)
                if reg_date >= since_dt:
                    matched_ids.append(loc_id)
        if (i + 1) % 50 == 0:
            print(f"  Fetched {i + 1}/{len(candidate_ids)} candidate details, {len(matched_ids)} matched so far...")
        time.sleep(sleep)

    # Step 5: Update cache with all newly seen IDs (so next run won't re-process them)
    _append_to_locations_cache(new_stubs_to_cache)
    print(f"  List scan complete: {len(matched_ids)} new registrations since {since}")
    return matched_ids


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


def complete_pipeline_run(cur, run_id: int, *, inserted: int = 0, updated: int = 0) -> None:
    cur.execute(
        """
        UPDATE pipeline_runs
        SET completed_at = NOW(),
            status = 'completed',
            records_added = %s,
            records_updated = %s,
            error_message = NULL
        WHERE id = %s
        """,
        (inserted, updated, run_id),
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

    # Dates
    last_inspection = data.get("lastInspection", {})
    inspection_date = ""
    if isinstance(last_inspection, dict):
        inspection_date = last_inspection.get("date", "") or ""

    reg_status = normalize_whitespace(data.get("registrationStatus", ""))
    status = "ACTIVE" if "register" in reg_status.lower() and "deregister" not in reg_status.lower() else "INACTIVE"

    return {
        "id": location_id,
        "provider_id": data.get("providerId", ""),
        "name": name,
        "type": normalize_whitespace(data.get("type", "")),
        "status": status,
        "registration_date": parse_any_date(data.get("registrationDate")),
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
    }


ALLOWED_COLUMNS = frozenset({
    "id", "provider_id", "name", "type", "status", "registration_date",
    "address_line1", "address_line2", "town", "county", "postcode",
    "region", "local_authority", "latitude", "longitude", "phone", "website",
    "overall_rating", "rating_safe", "rating_effective", "rating_caring",
    "rating_responsive", "rating_well_led", "last_inspection_date",
    "service_types", "specialisms", "number_of_beds", "ownership_type",
})


def upsert_provider(cur, record: dict[str, Any]) -> str:
    """Upsert a single provider record. Returns 'inserted', 'updated', or 'skipped'."""
    # Whitelist columns to prevent SQL injection via dict keys
    safe_record = {k: v for k, v in record.items() if k in ALLOWED_COLUMNS}
    if "id" not in safe_record:
        return "skipped"

    cur.execute(
        "SELECT id, overall_rating, name, slug, town, postcode, region FROM care_providers WHERE id = %s",
        (safe_record["id"],),
    )
    existing = cur.fetchone()

    cols = list(safe_record.keys())
    vals = [safe_record[c] for c in cols]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if existing:
        old_rating = existing[1]
        new_rating = safe_record.get("overall_rating")

        # Detect rating change and log it
        if (new_rating and old_rating and new_rating != old_rating
                and old_rating not in ("", "Not Yet Inspected")
                and new_rating not in ("", "Not Yet Inspected")):
            try:
                cur.execute(
                    """INSERT INTO rating_changes
                       (provider_id, provider_name, slug, town, postcode, region, old_rating, new_rating, inspection_date)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (safe_record["id"], existing[2] or safe_record.get("name"),
                     existing[3] or safe_record.get("slug"),
                     existing[4] or safe_record.get("town"),
                     existing[5] or safe_record.get("postcode"),
                     existing[6] or safe_record.get("region"),
                     old_rating, new_rating,
                     safe_record.get("last_inspection_date")),
                )
                # Also log to rating history
                cur.execute(
                    """INSERT INTO provider_rating_history (provider_id, overall_rating, inspection_date)
                       VALUES (%s, %s, %s) ON CONFLICT (provider_id, inspection_date) DO NOTHING""",
                    (safe_record["id"], new_rating, safe_record.get("last_inspection_date")),
                )
            except Exception as exc:
                print(f"  Warning: Failed to log rating change for {safe_record['id']}: {exc}")

        set_clause = ", ".join(f"{c} = %s" for c in cols)
        cur.execute(
            f"UPDATE care_providers SET {set_clause}, updated_at = %s WHERE id = %s",
            vals + [now, safe_record["id"]],
        )
        return "updated"
    else:
        cols_str = ", ".join(cols + ["updated_at", "created_at"])
        placeholders = ", ".join(["%s"] * (len(cols) + 2))
        cur.execute(
            f"INSERT INTO care_providers ({cols_str}) VALUES ({placeholders})",
            vals + [now, now],
        )
        return "inserted"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Incremental CQC data update")
    parser.add_argument("--since", help="ISO date to fetch changes from (default: last pipeline run)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="CQC API base URL")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP, help="Sleep between API calls")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing to DB")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    api_key = get_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: CQC_API_KEY not set.", file=sys.stderr)
        return 1

    database_url = args.database_url or get_database_url()
    if not database_url and not args.dry_run:
        print("ERROR: DATABASE_URL not set.")
        return 1

    conn = None
    cur = None
    run_id: int | None = None
    lock_acquired = False

    try:
        if database_url:
            conn = psycopg2.connect(database_url)
            conn.autocommit = False
            cur = conn.cursor()

        since = args.since
        if cur is not None:
            since = resolve_since(cur, since)
        elif not since:
            since = (datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")

        if cur is not None:
            lock_acquired = acquire_run_lock(cur)
            if not lock_acquired:
                conn.rollback()
                print("Another incremental update is already running. Skipping.")
                return 0

            run_id = create_pipeline_run(cur)
            conn.commit()

        print(f"Fetching CQC changes since {since}...")
        changed_ids = fetch_changes(args.base_url, api_key, since, args.sleep)
        if changed_ids is None:
            print("WARNING: /changes/location endpoint unavailable (404/410). Falling back to location list scan.")
            if cur is not None:
                try:
                    cur.execute(
                        """
                        INSERT INTO pipeline_alert_log (alert_key, severity, details)
                        VALUES ('changes_endpoint_unavailable', 'warning',
                                '{"message": "CQC /changes/location returned 404 — falling back to list scan"}'::jsonb)
                        """,
                    )
                    conn.commit()
                except Exception as alert_exc:
                    print(f"  (Could not log alert: {alert_exc})")
            changed_ids = fetch_recent_via_list_scan(args.base_url, api_key, since, args.sleep)
            print(f"List scan found {len(changed_ids)} potentially new/changed locations")
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

        if changed_ids and not records and (results.get("fetch_failed", 0) or results.get("clean_failed", 0)):
            raise RuntimeError("All changed records failed to fetch or clean.")

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

        complete_pipeline_run(
            cur,
            run_id,
            inserted=results.get("inserted", 0),
            updated=results.get("updated", 0),
        )
        conn.commit()

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

    print(f"\nIncremental update complete:")
    print(f"  Inserted: {results.get('inserted', 0)}")
    print(f"  Updated: {results.get('updated', 0)}")
    print(f"  Fetch failures: {results.get('fetch_failed', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
