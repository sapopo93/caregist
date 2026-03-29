#!/usr/bin/env python3
"""
CQC Full Provider Extract
- Pulls all providers via paginated API
- Pulls all locations via paginated API
- Pulls provider/location detail endpoints for enrichment
- Joins providers to locations
- Saves raw data to JSON and CSV
- Handles rate limiting with retries/backoff
- Logs failed IDs and checkpoints for resumability
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from cqc_common import as_json, deep_get, ensure_list, first_non_empty, flatten_json, ts_for_logs, utc_now_iso

DEFAULT_BASE_URL = "https://api.service.cqc.org.uk/public/v1"
DEFAULT_PER_PAGE = 1000
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_REQUEST_SLEEP = 0.1
DEFAULT_CHECKPOINT_EVERY = 500

OUTPUT_RAW_PROVIDERS = "raw_providers.json"
OUTPUT_RAW_LOCATIONS = "raw_locations.json"
OUTPUT_RAW_COMBINED = "raw_combined.csv"
OUTPUT_LOG = "extract_log.txt"
OUTPUT_FAILED_IDS = "failed_ids.txt"
OUTPUT_CHECKPOINT = "checkpoint.json"

INTERMEDIATE_PROVIDERS_LIST = "_providers_list.ndjson"
INTERMEDIATE_LOCATIONS_LIST = "_locations_list.ndjson"
INTERMEDIATE_PROVIDERS_DETAIL = "_providers_detail.ndjson"
INTERMEDIATE_LOCATIONS_DETAIL = "_locations_detail.ndjson"
INTERMEDIATE_PROVIDER_CACHE = "_provider_cache.sqlite"


def log_line(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{ts_for_logs()}] {message}\n")


def append_failed_id(failed: set[str], item: str) -> None:
    if item:
        failed.add(str(item))


@dataclass
class ApiClient:
    base_url: str
    timeout: int
    max_retries: int
    request_sleep: float
    log_path: Path
    subscription_key: str | None = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "CareGist-CQC-Extractor/1.0",
        }
        if self.subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = self.subscription_key
            headers["Subscription-Key"] = self.subscription_key
        return headers

    def get_json(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any] | None:
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._headers()
        for attempt in range(1, self.max_retries + 1):
            start = time.perf_counter()
            try:
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                log_line(
                    self.log_path,
                    f"API_CALL method=GET endpoint={endpoint} params={json.dumps(params or {}, ensure_ascii=True, sort_keys=True)} "
                    f"status={response.status_code} elapsed_ms={elapsed_ms} attempt={attempt}",
                )

                if response.status_code == 429:
                    backoff = 2 * (2 ** (attempt - 1))
                    log_line(self.log_path, f"RATE_LIMIT endpoint={endpoint} backoff={backoff}s")
                    time.sleep(backoff)
                    continue

                if response.status_code in (408, 500, 502, 503, 504):
                    if attempt < self.max_retries:
                        backoff = 2 ** attempt
                        log_line(self.log_path, f"RETRYABLE_HTTP status={response.status_code} endpoint={endpoint} backoff={backoff}s")
                        time.sleep(backoff)
                        continue

                if response.status_code >= 400:
                    body = response.text.strip().replace("\n", " ")[:400]
                    log_line(self.log_path, f"HTTP_ERROR status={response.status_code} endpoint={endpoint} body={body}")
                    return None

                try:
                    payload = response.json()
                except json.JSONDecodeError:
                    snippet = response.text.strip().replace("\n", " ")[:400]
                    log_line(self.log_path, f"JSON_PARSE_ERROR endpoint={endpoint} body={snippet}")
                    return None

                return payload

            except requests.RequestException as exc:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                log_line(
                    self.log_path,
                    f"REQUEST_EXCEPTION endpoint={endpoint} elapsed_ms={elapsed_ms} attempt={attempt} error={type(exc).__name__}:{exc}",
                )
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                else:
                    return None
            finally:
                time.sleep(self.request_sleep)

        return None


class CheckpointManager:
    def __init__(self, path: Path):
        self.path = path

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            "stage": "providers_list",
            "providers_list": {"next_page": 1, "records_fetched": 0, "total": None, "completed": False},
            "locations_list": {"next_page": 1, "records_fetched": 0, "total": None, "completed": False},
            "providers_detail": {"next_index": 0, "records_fetched": 0, "completed": False},
            "locations_detail": {"next_index": 0, "records_fetched": 0, "completed": False},
            "failed_ids": [],
            "last_updated": utc_now_iso(),
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.default()

        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            return self.default()

        defaults = self.default()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
        return data

    def save(self, checkpoint: dict[str, Any]) -> None:
        checkpoint["last_updated"] = utc_now_iso()
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as fh:
            json.dump(checkpoint, fh, indent=2, ensure_ascii=True, sort_keys=True)
        temp.replace(self.path)


def reset_outputs(output_dir: Path) -> None:
    for filename in [
        OUTPUT_RAW_PROVIDERS,
        OUTPUT_RAW_LOCATIONS,
        OUTPUT_RAW_COMBINED,
        OUTPUT_LOG,
        OUTPUT_FAILED_IDS,
        OUTPUT_CHECKPOINT,
        INTERMEDIATE_PROVIDERS_LIST,
        INTERMEDIATE_LOCATIONS_LIST,
        INTERMEDIATE_PROVIDERS_DETAIL,
        INTERMEDIATE_LOCATIONS_DETAIL,
        INTERMEDIATE_PROVIDER_CACHE,
    ]:
        path = output_dir / filename
        if path.exists():
            path.unlink()


def extract_total(payload: Any) -> int | None:
    candidates: list[Any] = []

    if isinstance(payload, dict):
        for key in ["total", "count", "totalCount", "totalRecords", "totalResults"]:
            if key in payload:
                candidates.append(payload.get(key))

        candidates.extend(
            [
                deep_get(payload, "pagination.total"),
                deep_get(payload, "paging.total"),
                deep_get(payload, "meta.total"),
            ]
        )

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            value = int(candidate)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            return value

    return None


def extract_items(payload: Any, resource: str) -> list[dict[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    singular = resource[:-1] if resource.endswith("s") else resource
    keys = [
        resource,
        resource.lower(),
        singular,
        singular.lower(),
        "items",
        "results",
        "data",
        "value",
    ]

    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value

    return []


def record_id(record: dict[str, Any], resource: str) -> str:
    if resource == "providers":
        candidates = ["providerId", "providerID", "provider_id", "id"]
    else:
        candidates = ["locationId", "locationID", "location_id", "id"]

    for key in candidates:
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text

    return ""


def append_ndjson(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def run_paginated_extraction(
    *,
    client: ApiClient,
    resource: str,
    ndjson_path: Path,
    checkpoint: dict[str, Any],
    checkpoint_key: str,
    checkpoint_mgr: CheckpointManager,
    checkpoint_every: int,
    per_page: int,
    failed_ids: set[str],
) -> int:
    state = checkpoint[checkpoint_key]
    if state.get("completed") and ndjson_path.exists():
        log_line(client.log_path, f"SKIP_STAGE stage={checkpoint_key} reason=already_completed")
        return int(state.get("records_fetched", 0) or 0)

    page = int(state.get("next_page", 1) or 1)
    total = state.get("total")
    if total is not None:
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = None

    records_fetched = int(state.get("records_fetched", 0) or 0)
    consecutive_failures = 0

    while True:
        payload = client.get_json(f"/{resource}", params={"page": page, "perPage": per_page})
        if payload is None:
            append_failed_id(failed_ids, f"{resource}:page:{page}")
            log_line(client.log_path, f"PAGE_FAILED resource={resource} page={page}")
            consecutive_failures += 1

            if total is not None:
                total_pages = max(1, math.ceil(total / per_page))
                if page >= total_pages:
                    break
            elif consecutive_failures >= 3:
                break

            page += 1
            state["next_page"] = page
            checkpoint_mgr.save(checkpoint)
            continue

        consecutive_failures = 0
        items = extract_items(payload, resource)

        if total is None:
            total = extract_total(payload)
            state["total"] = total

        if not items:
            log_line(client.log_path, f"NO_ITEMS resource={resource} page={page}")
            break

        for item in items:
            append_ndjson(ndjson_path, item)
            records_fetched += 1

        state["records_fetched"] = records_fetched
        page += 1
        state["next_page"] = page

        if records_fetched % checkpoint_every == 0:
            checkpoint_mgr.save(checkpoint)
            log_line(client.log_path, f"CHECKPOINT_SAVED stage={checkpoint_key} records={records_fetched}")

        if total is not None and records_fetched >= total:
            break

        if total is None and len(items) < per_page:
            break

    state["completed"] = True
    state["next_page"] = page
    state["records_fetched"] = records_fetched
    checkpoint_mgr.save(checkpoint)
    log_line(client.log_path, f"STAGE_COMPLETE stage={checkpoint_key} records={records_fetched} total={total}")
    return records_fetched


def load_ids(ndjson_path: Path, resource: str) -> list[str]:
    ids: set[str] = set()
    if not ndjson_path.exists():
        return []

    with ndjson_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            rid = record_id(item, resource)
            if rid:
                ids.add(rid)

    return sorted(ids)


def run_detail_extraction(
    *,
    client: ApiClient,
    resource: str,
    ids: list[str],
    output_path: Path,
    checkpoint: dict[str, Any],
    checkpoint_key: str,
    checkpoint_mgr: CheckpointManager,
    checkpoint_every: int,
    failed_ids: set[str],
    workers: int = 1,
) -> int:
    state = checkpoint[checkpoint_key]
    if state.get("completed") and output_path.exists():
        log_line(client.log_path, f"SKIP_STAGE stage={checkpoint_key} reason=already_completed")
        return int(state.get("records_fetched", 0) or 0)

    next_index = int(state.get("next_index", 0) or 0)
    records_fetched = int(state.get("records_fetched", 0) or 0)

    worker_count = max(1, int(workers))
    if worker_count == 1:
        for idx in range(next_index, len(ids)):
            rid = ids[idx]
            payload = client.get_json(f"/{resource}/{rid}", params=None)
            if payload is None:
                append_failed_id(failed_ids, f"{resource}:{rid}")
                log_line(client.log_path, f"DETAIL_FAILED resource={resource} id={rid}")
            else:
                if isinstance(payload, dict):
                    append_ndjson(output_path, payload)
                    records_fetched += 1
                else:
                    append_failed_id(failed_ids, f"{resource}:{rid}")
                    log_line(client.log_path, f"DETAIL_INVALID_PAYLOAD resource={resource} id={rid}")

            state["next_index"] = idx + 1
            state["records_fetched"] = records_fetched
            if (idx + 1) % checkpoint_every == 0:
                checkpoint_mgr.save(checkpoint)
                log_line(client.log_path, f"CHECKPOINT_SAVED stage={checkpoint_key} index={idx + 1}")
    else:
        def fetch_detail(detail_id: str) -> tuple[str, dict[str, Any] | None]:
            payload = client.get_json(f"/{resource}/{detail_id}", params=None)
            if isinstance(payload, dict):
                return detail_id, payload
            return detail_id, None

        idx = next_index
        while idx < len(ids):
            batch_end = min(len(ids), idx + worker_count * 10)
            batch_ids = ids[idx:batch_end]
            results: list[tuple[str, dict[str, Any] | None]] = []
            with ThreadPoolExecutor(max_workers=worker_count) as pool:
                futures = {pool.submit(fetch_detail, detail_id): detail_id for detail_id in batch_ids}
                for future in as_completed(futures):
                    detail_id = futures[future]
                    try:
                        rid, payload = future.result()
                    except Exception:
                        rid, payload = detail_id, None
                    results.append((rid, payload))

            result_map = {rid: payload for rid, payload in results}
            for detail_id in batch_ids:
                payload = result_map.get(detail_id)
                if payload is None:
                    append_failed_id(failed_ids, f"{resource}:{detail_id}")
                    log_line(client.log_path, f"DETAIL_FAILED resource={resource} id={detail_id}")
                else:
                    append_ndjson(output_path, payload)
                    records_fetched += 1

            idx = batch_end
            state["next_index"] = idx
            state["records_fetched"] = records_fetched
            checkpoint_mgr.save(checkpoint)
            log_line(
                client.log_path,
                f"CHECKPOINT_SAVED stage={checkpoint_key} index={idx} workers={worker_count} records={records_fetched}",
            )

    state["completed"] = True
    state["records_fetched"] = records_fetched
    checkpoint_mgr.save(checkpoint)
    log_line(client.log_path, f"STAGE_COMPLETE stage={checkpoint_key} records={records_fetched}")
    return records_fetched


def ndjson_record_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def ndjson_to_json_array(ndjson_path: Path, json_path: Path) -> None:
    with ndjson_path.open("r", encoding="utf-8") as src, json_path.open("w", encoding="utf-8") as dst:
        dst.write("[\n")
        first = True
        for line in src:
            line = line.strip()
            if not line:
                continue
            if not first:
                dst.write(",\n")
            dst.write(line)
            first = False
        dst.write("\n]\n")


def pick_value(location: dict[str, Any], provider: dict[str, Any], paths: list[str]) -> Any:
    candidates: list[tuple[Any, str]] = []
    for path in paths:
        candidates.append((location, path))
        candidates.append((provider, path))
    return first_non_empty(candidates, default="")


def normalize_list_field(value: Any) -> str:
    values = []
    for item in ensure_list(value):
        if isinstance(item, dict):
            text = first_non_empty([
                item.get("name"),
                item.get("value"),
                item.get("description"),
                item.get("title"),
                item.get("code"),
            ], default="")
        else:
            text = str(item)
        text = str(text).strip()
        if text:
            values.append(text)

    if not values:
        return ""
    return "|".join(values)


def extract_key_question_ratings(location: dict[str, Any], provider: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    kq = first_non_empty(
        [
            (location, "currentRatings.overall.keyQuestionRatings"),
            (location, "keyQuestionRatings"),
            (location, "currentRatings.keyQuestionRatings"),
            (provider, "currentRatings.overall.keyQuestionRatings"),
            (provider, "keyQuestionRatings"),
            (provider, "currentRatings.keyQuestionRatings"),
        ],
        default={},
    )

    if isinstance(kq, str):
        try:
            kq = json.loads(kq)
        except json.JSONDecodeError:
            kq = {}

    parsed: dict[str, str] = {}

    # CQC API returns a list: [{"name": "Safe", "rating": "Good"}, ...]
    if isinstance(kq, list):
        for item in kq:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().lower().replace("-", "_").replace(" ", "_")
            rating = str(item.get("rating", "")).strip()
            if name and rating:
                parsed[name] = rating

    # Fallback: dict format {"safe": {"rating": "Good"}, ...}
    elif isinstance(kq, dict):
        for key, value in kq.items():
            key_norm = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if isinstance(value, dict):
                rating = first_non_empty([
                    value.get("rating"),
                    value.get("overall"),
                    value.get("value"),
                    value.get("score"),
                ], default="")
            else:
                rating = value
            parsed[key_norm] = str(rating).strip()

    safe = parsed.get("safe", "")
    effective = parsed.get("effective", "")
    caring = parsed.get("caring", "")
    responsive = parsed.get("responsive", "")
    well_led = parsed.get("well_led", "") or parsed.get("wellled", "") or parsed.get("well_led_", "")

    return as_json(kq), safe, effective, caring, responsive, well_led


def build_combined_row(location: dict[str, Any], provider: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    kq_raw, rating_safe, rating_effective, rating_caring, rating_responsive, rating_well_led = extract_key_question_ratings(
        location, provider
    )

    row = {
        "providerId": pick_value(location, provider, ["providerId", "providerID", "provider_id", "id"]),
        "locationId": first_non_empty([
            deep_get(location, "locationId"),
            deep_get(location, "locationID"),
            deep_get(location, "location_id"),
            deep_get(location, "id"),
        ], default=""),
        "name": pick_value(location, provider, ["name"]),
        "brandName": pick_value(location, provider, ["brandName", "brand", "tradingName"]),
        "type": pick_value(location, provider, ["type", "providerType", "organisationType"]),
        "registrationStatus": pick_value(location, provider, ["registrationStatus", "status"]),
        "registrationDate": pick_value(location, provider, ["registrationDate"]),
        "deregistrationDate": pick_value(location, provider, ["deregistrationDate"]),
        "expectedDeregistrationDate": pick_value(location, provider, ["expectedDeregistrationDate"]),
        "postalAddressLine1": pick_value(location, provider, ["postalAddressLine1", "postalAddress.line1", "addressLine1"]),
        "postalAddressLine2": pick_value(location, provider, ["postalAddressLine2", "postalAddress.line2", "addressLine2"]),
        "postalAddressTownCity": pick_value(location, provider, ["postalAddressTownCity", "postalAddress.townCity", "town", "city"]),
        "postalAddressCounty": pick_value(location, provider, ["postalAddressCounty", "postalAddress.county", "county"]),
        "postalCode": pick_value(location, provider, ["postalCode", "postcode", "postalAddress.postalCode", "postalAddress.postcode"]),
        "region": pick_value(location, provider, ["region", "region.name"]),
        "localAuthority": pick_value(location, provider, ["localAuthority", "localAuthority.name"]),
        "latitude": pick_value(location, provider, ["latitude", "onspdLatitude", "geo.latitude", "coordinates.latitude"]),
        "longitude": pick_value(location, provider, ["longitude", "onspdLongitude", "geo.longitude", "coordinates.longitude"]),
        "mainPhoneNumber": pick_value(location, provider, ["mainPhoneNumber", "phone", "contact.phone", "contacts.phone"]),
        "website": pick_value(location, provider, ["website", "webSite", "url", "contact.website"]),
        "email": pick_value(location, provider, ["email", "contact.email", "contacts.email"]),
        "regulatedActivities": normalize_list_field(
            first_non_empty(
                [
                    deep_get(location, "regulatedActivities"),
                    deep_get(provider, "regulatedActivities"),
                ],
                default=[],
            )
        ),
        "serviceTypes": normalize_list_field(
            first_non_empty([
                deep_get(location, "gacServiceTypes"),
                deep_get(location, "serviceTypes"),
                deep_get(provider, "gacServiceTypes"),
                deep_get(provider, "serviceTypes"),
            ], default=[])
        ),
        "specialisms": normalize_list_field(
            first_non_empty([
                deep_get(location, "specialisms"),
                deep_get(provider, "specialisms"),
            ], default=[])
        ),
        "numberOfBeds": pick_value(location, provider, ["numberOfBeds", "beds", "capacityBeds"]),
        "overallRating": pick_value(
            location,
            provider,
            [
                "overallRating",
                "currentRatings.overall.rating",
                "ratings.overall",
            ],
        ),
        "reportDate": pick_value(location, provider, ["reportDate", "lastReport.publicationDate", "currentRatings.reportDate", "latestReportDate", "inspectionReportDate"]),
        "lastInspectionDate": pick_value(location, provider, ["lastInspectionDate", "lastInspection.date", "inspectionDate", "latestInspectionDate"]),
        "inspectionCategories": normalize_list_field(
            first_non_empty([
                deep_get(location, "inspectionCategories"),
                deep_get(provider, "inspectionCategories"),
            ], default=[])
        ),
        "keyQuestionRatings": kq_raw,
        "rating_safe": rating_safe,
        "rating_effective": rating_effective,
        "rating_caring": rating_caring,
        "rating_responsive": rating_responsive,
        "rating_well_led": rating_well_led,
        "ownershipType": pick_value(location, provider, ["ownershipType", "ownerType", "organisationType"]),
        "companiesHouseNumber": pick_value(location, provider, ["companiesHouseNumber", "companyNumber"]),
        "charitiesCommissionNumber": pick_value(location, provider, ["charitiesCommissionNumber", "charityNumber"]),
        "suspensionFlag": pick_value(location, provider, ["suspensionFlag", "isSuspended", "suspended"]),
        "careHome": pick_value(location, provider, ["careHome"]),
        "dormancy": pick_value(location, provider, ["dormancy"]),
        "inspectionDirectorate": pick_value(location, provider, ["inspectionDirectorate"]),
        "uprn": pick_value(location, provider, ["uprn"]),
        "odsCode": pick_value(location, provider, ["odsCode"]),
        "constituency": pick_value(location, provider, ["constituency"]),
        "onspdIcbCode": pick_value(location, provider, ["onspdIcbCode"]),
        "onspdIcbName": pick_value(location, provider, ["onspdIcbName"]),
        "cqcUrl": first_non_empty(
            [
                deep_get(location, "url"),
                deep_get(location, "links.self"),
                deep_get(provider, "url"),
                deep_get(provider, "links.self"),
            ],
            default="",
        ),
        "provider_raw_json": as_json(provider),
        "location_raw_json": as_json(location),
    }

    provider_flat = flatten_json(provider)
    location_flat = flatten_json(location)
    return row, provider_flat, location_flat


def build_provider_cache(provider_ndjson: Path, sqlite_path: Path, log_path: Path) -> None:
    if sqlite_path.exists():
        sqlite_path.unlink()

    conn = sqlite3.connect(sqlite_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("CREATE TABLE providers (provider_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    inserted = 0
    with provider_ndjson.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                provider = json.loads(line)
            except json.JSONDecodeError:
                continue

            pid = record_id(provider, "providers")
            if not pid:
                continue

            conn.execute(
                "INSERT OR REPLACE INTO providers (provider_id, payload) VALUES (?, ?)",
                (pid, json.dumps(provider, ensure_ascii=True, sort_keys=True)),
            )
            inserted += 1
            if inserted % 1000 == 0:
                conn.commit()

    conn.commit()
    conn.close()
    log_line(log_path, f"PROVIDER_CACHE_BUILT records={inserted} path={sqlite_path}")


def load_provider(conn: sqlite3.Connection, provider_id: str, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not provider_id:
        return {}
    if provider_id in cache:
        return cache[provider_id]

    row = conn.execute("SELECT payload FROM providers WHERE provider_id = ?", (provider_id,)).fetchone()
    if row is None:
        cache[provider_id] = {}
        return {}

    try:
        payload = json.loads(row[0])
    except json.JSONDecodeError:
        payload = {}

    if len(cache) > 5000:
        cache.clear()
    cache[provider_id] = payload
    return payload


def combined_columns(
    location_ndjson: Path,
    provider_cache_db: Path,
    log_path: Path,
) -> list[str]:
    base_cols = [
        "providerId",
        "locationId",
        "name",
        "brandName",
        "type",
        "registrationStatus",
        "registrationDate",
        "deregistrationDate",
        "expectedDeregistrationDate",
        "postalAddressLine1",
        "postalAddressLine2",
        "postalAddressTownCity",
        "postalAddressCounty",
        "postalCode",
        "region",
        "localAuthority",
        "latitude",
        "longitude",
        "mainPhoneNumber",
        "website",
        "email",
        "regulatedActivities",
        "serviceTypes",
        "specialisms",
        "numberOfBeds",
        "overallRating",
        "reportDate",
        "lastInspectionDate",
        "inspectionCategories",
        "keyQuestionRatings",
        "rating_safe",
        "rating_effective",
        "rating_caring",
        "rating_responsive",
        "rating_well_led",
        "ownershipType",
        "companiesHouseNumber",
        "charitiesCommissionNumber",
        "suspensionFlag",
        "careHome",
        "dormancy",
        "inspectionDirectorate",
        "uprn",
        "odsCode",
        "constituency",
        "onspdIcbCode",
        "onspdIcbName",
        "cqcUrl",
        "provider_raw_json",
        "location_raw_json",
    ]

    dynamic: set[str] = set()

    conn = sqlite3.connect(provider_cache_db)
    provider_cache: dict[str, dict[str, Any]] = {}

    scanned = 0
    with location_ndjson.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                location = json.loads(line)
            except json.JSONDecodeError:
                continue

            pid = str(first_non_empty([
                deep_get(location, "providerId"),
                deep_get(location, "providerID"),
                deep_get(location, "provider_id"),
            ], default="")).strip()
            provider = load_provider(conn, pid, provider_cache)
            _, provider_flat, location_flat = build_combined_row(location, provider)
            dynamic.update({f"provider.{k}" for k in provider_flat.keys()})
            dynamic.update({f"location.{k}" for k in location_flat.keys()})
            scanned += 1

    conn.close()
    log_line(log_path, f"COMBINED_COLUMNS_DISCOVERED locations_scanned={scanned} dynamic_columns={len(dynamic)}")
    return base_cols + sorted(dynamic)


def build_combined_csv(
    *,
    provider_ndjson: Path,
    location_ndjson: Path,
    output_csv: Path,
    provider_cache_db: Path,
    log_path: Path,
) -> int:
    build_provider_cache(provider_ndjson, provider_cache_db, log_path)
    fieldnames = combined_columns(location_ndjson, provider_cache_db, log_path)

    conn = sqlite3.connect(provider_cache_db)
    provider_cache: dict[str, dict[str, Any]] = {}

    rows_written = 0
    with output_csv.open("w", newline="", encoding="utf-8") as fh_out:
        writer = csv.DictWriter(fh_out, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        with location_ndjson.open("r", encoding="utf-8") as fh_in:
            for line in fh_in:
                line = line.strip()
                if not line:
                    continue
                try:
                    location = json.loads(line)
                except json.JSONDecodeError:
                    continue

                pid = str(first_non_empty([
                    deep_get(location, "providerId"),
                    deep_get(location, "providerID"),
                    deep_get(location, "provider_id"),
                ], default="")).strip()
                provider = load_provider(conn, pid, provider_cache)

                row, provider_flat, location_flat = build_combined_row(location, provider)
                for key, value in provider_flat.items():
                    row[f"provider.{key}"] = value
                for key, value in location_flat.items():
                    row[f"location.{key}"] = value

                writer.writerow(row)
                rows_written += 1

                if rows_written % 500 == 0:
                    log_line(log_path, f"COMBINED_PROGRESS rows_written={rows_written}")

    conn.close()
    log_line(log_path, f"COMBINED_COMPLETE rows_written={rows_written} output={output_csv}")
    return rows_written


def write_failed_ids(path: Path, failed_ids: set[str]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for item in sorted(failed_ids):
            fh.write(f"{item}\n")


def pick_best_source(detail_path: Path, list_path: Path) -> Path:
    if detail_path.exists() and ndjson_record_count(detail_path) > 0:
        return detail_path
    return list_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract CQC providers and locations with checkpoint/resume.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="CQC API base URL")
    parser.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE, help="Page size for list endpoints")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout seconds")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help="Retries per API request")
    parser.add_argument("--sleep", type=float, default=DEFAULT_REQUEST_SLEEP, help="Sleep between API calls")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=DEFAULT_CHECKPOINT_EVERY,
        help="Persist checkpoint every N records",
    )
    parser.add_argument("--disable-details", action="store_true", help="Skip /providers/{id} and /locations/{id} calls")
    parser.add_argument("--detail-workers", type=int, default=1, help="Parallel workers for detail endpoints")
    parser.add_argument("--output-dir", default=".", help="Directory to write outputs")
    parser.add_argument("--reset", action="store_true", help="Remove existing outputs before starting")
    parser.add_argument("--rebuild-csv", action="store_true", help="Rebuild raw_combined.csv from cached NDJSON without API calls")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / OUTPUT_LOG
    checkpoint_path = output_dir / OUTPUT_CHECKPOINT
    failed_ids_path = output_dir / OUTPUT_FAILED_IDS

    if args.reset:
        reset_outputs(output_dir)

    log_line(log_path, "=== CQC EXTRACTION START ===")

    checkpoint_mgr = CheckpointManager(checkpoint_path)
    checkpoint = checkpoint_mgr.load()

    failed_ids = set(str(item) for item in checkpoint.get("failed_ids", []))

    # Rebuild CSV from cached NDJSON without making API calls
    if args.rebuild_csv:
        providers_detail = output_dir / INTERMEDIATE_PROVIDERS_DETAIL
        locations_detail = output_dir / INTERMEDIATE_LOCATIONS_DETAIL
        providers_list = output_dir / INTERMEDIATE_PROVIDERS_LIST
        locations_list = output_dir / INTERMEDIATE_LOCATIONS_LIST
        raw_combined_csv = output_dir / OUTPUT_RAW_COMBINED
        provider_cache_db = output_dir / INTERMEDIATE_PROVIDER_CACHE

        provider_source = pick_best_source(providers_detail, providers_list)
        location_source = pick_best_source(locations_detail, locations_list)

        if not location_source.exists() or not provider_source.exists():
            print("Cannot rebuild: cached NDJSON files not found. Run full extraction first.")
            return 1

        log_line(log_path, "REBUILD_CSV_START (from cached NDJSON)")
        combined_count = build_combined_csv(
            provider_ndjson=provider_source,
            location_ndjson=location_source,
            output_csv=raw_combined_csv,
            provider_cache_db=provider_cache_db,
            log_path=log_path,
        )
        log_line(log_path, f"REBUILD_CSV_COMPLETE rows_written={combined_count}")
        print(f"Rebuilt raw_combined.csv from cached NDJSON: {combined_count} rows")
        return 0

    client = ApiClient(
        base_url=args.base_url,
        timeout=args.timeout,
        max_retries=args.max_retries,
        request_sleep=args.sleep,
        log_path=log_path,
        subscription_key=os.getenv("CQC_SUBSCRIPTION_KEY") or os.getenv("CQC_API_KEY"),
    )

    providers_list = output_dir / INTERMEDIATE_PROVIDERS_LIST
    locations_list = output_dir / INTERMEDIATE_LOCATIONS_LIST
    providers_detail = output_dir / INTERMEDIATE_PROVIDERS_DETAIL
    locations_detail = output_dir / INTERMEDIATE_LOCATIONS_DETAIL

    raw_providers_json = output_dir / OUTPUT_RAW_PROVIDERS
    raw_locations_json = output_dir / OUTPUT_RAW_LOCATIONS
    raw_combined_csv = output_dir / OUTPUT_RAW_COMBINED
    provider_cache_db = output_dir / INTERMEDIATE_PROVIDER_CACHE

    try:
        providers_count = run_paginated_extraction(
            client=client,
            resource="providers",
            ndjson_path=providers_list,
            checkpoint=checkpoint,
            checkpoint_key="providers_list",
            checkpoint_mgr=checkpoint_mgr,
            checkpoint_every=args.checkpoint_every,
            per_page=args.per_page,
            failed_ids=failed_ids,
        )

        locations_count = run_paginated_extraction(
            client=client,
            resource="locations",
            ndjson_path=locations_list,
            checkpoint=checkpoint,
            checkpoint_key="locations_list",
            checkpoint_mgr=checkpoint_mgr,
            checkpoint_every=args.checkpoint_every,
            per_page=args.per_page,
            failed_ids=failed_ids,
        )

        detail_provider_count = 0
        detail_location_count = 0

        if not args.disable_details:
            provider_ids = load_ids(providers_list, "providers")
            location_ids = load_ids(locations_list, "locations")
            log_line(log_path, f"DETAIL_IDS providers={len(provider_ids)} locations={len(location_ids)}")

            detail_provider_count = run_detail_extraction(
                client=client,
                resource="providers",
                ids=provider_ids,
                output_path=providers_detail,
                checkpoint=checkpoint,
                checkpoint_key="providers_detail",
                checkpoint_mgr=checkpoint_mgr,
                checkpoint_every=args.checkpoint_every,
                failed_ids=failed_ids,
                workers=args.detail_workers,
            )
            detail_location_count = run_detail_extraction(
                client=client,
                resource="locations",
                ids=location_ids,
                output_path=locations_detail,
                checkpoint=checkpoint,
                checkpoint_key="locations_detail",
                checkpoint_mgr=checkpoint_mgr,
                checkpoint_every=args.checkpoint_every,
                failed_ids=failed_ids,
                workers=args.detail_workers,
            )

        provider_source = pick_best_source(providers_detail, providers_list)
        location_source = pick_best_source(locations_detail, locations_list)

        if provider_source.exists():
            ndjson_to_json_array(provider_source, raw_providers_json)
        else:
            raw_providers_json.write_text("[]\n", encoding="utf-8")

        if location_source.exists():
            ndjson_to_json_array(location_source, raw_locations_json)
        else:
            raw_locations_json.write_text("[]\n", encoding="utf-8")

        if location_source.exists() and provider_source.exists() and ndjson_record_count(location_source) > 0:
            combined_count = build_combined_csv(
                provider_ndjson=provider_source,
                location_ndjson=location_source,
                output_csv=raw_combined_csv,
                provider_cache_db=provider_cache_db,
                log_path=log_path,
            )
        else:
            combined_count = 0
            with raw_combined_csv.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["providerId", "locationId", "name"])

        checkpoint["failed_ids"] = sorted(failed_ids)
        checkpoint["stage"] = "complete"
        checkpoint_mgr.save(checkpoint)
        write_failed_ids(failed_ids_path, failed_ids)

        log_line(
            log_path,
            "EXTRACTION_SUMMARY "
            f"providers_list={providers_count} locations_list={locations_count} "
            f"providers_detail={detail_provider_count} locations_detail={detail_location_count} "
            f"combined_rows={combined_count} failed_ids={len(failed_ids)}",
        )

        print("CQC extraction complete")
        print(f"Providers extracted (list): {providers_count}")
        print(f"Locations extracted (list): {locations_count}")
        if not args.disable_details:
            print(f"Providers extracted (detail): {detail_provider_count}")
            print(f"Locations extracted (detail): {detail_location_count}")
        print(f"Joined rows written: {combined_count}")
        print(f"Failed IDs/pages: {len(failed_ids)}")

        if providers_count == 0 and locations_count == 0:
            print(
                "Warning: no records extracted. If API returns 403, set CQC_SUBSCRIPTION_KEY and re-run with --reset."
            )

    except KeyboardInterrupt:
        checkpoint["failed_ids"] = sorted(failed_ids)
        checkpoint_mgr.save(checkpoint)
        write_failed_ids(failed_ids_path, failed_ids)
        log_line(log_path, "INTERRUPTED_BY_USER")
        print("Extraction interrupted; checkpoint saved.")
        return 1
    except Exception as exc:
        checkpoint["failed_ids"] = sorted(failed_ids)
        checkpoint_mgr.save(checkpoint)
        write_failed_ids(failed_ids_path, failed_ids)
        log_line(log_path, f"FATAL_ERROR {type(exc).__name__}: {exc}")
        print(f"Extraction failed: {type(exc).__name__}: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
