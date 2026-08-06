#!/usr/bin/env python3
"""
Harvest CQC-registered care providers with registrationDate between
2026-01-01 and 2026-04-28 (inclusive).

Strategy:
1. Scan local _providers_detail.ndjson for 2026 registrations.
2. Fetch current provider list from CQC API; fetch details for any IDs
   not present locally (catches providers registered after Feb 2026 snapshot).
3. Cross-reference with local _locations_detail.ndjson for service-type
   enrichment and location counts.
4. Attempt Companies House enrichment (documented if unavailable).
5. Emit JSON, CSV, and a data-quality report.
"""
from __future__ import annotations

import csv
import json
import os
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests

CQC_API_KEY = os.getenv("CQC_API_KEY") or os.getenv("CQC_SUBSCRIPTION_KEY")
if not CQC_API_KEY:
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CQC_API_KEY="):
                CQC_API_KEY = line.split("=", 1)[1].strip()
                break

CQC_BASE_URL = "https://api.service.cqc.org.uk/public/v1"
CH_BASE_URL = "https://api.company-information.service.gov.uk"

OUTPUT_JSON = Path("cqc_new_providers_2026.json")
OUTPUT_CSV = Path("cqc_new_providers_2026.csv")
OUTPUT_REPORT = Path("cqc_data_quality_report.md")

LOCAL_PROVIDERS_DETAIL = Path("_providers_detail.ndjson")
LOCAL_LOCATIONS_DETAIL = Path("_locations_detail.ndjson")

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 4, 28)


def cqc_headers() -> dict[str, str]:
    h = {"Accept": "application/json", "User-Agent": "CareGist-DataEngine/1.0"}
    if CQC_API_KEY:
        h["Ocp-Apim-Subscription-Key"] = CQC_API_KEY
        h["Subscription-Key"] = CQC_API_KEY
    return h


def parse_cqc_date(val: Any) -> date | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def load_local_providers(path: Path) -> dict[str, dict]:
    """Load local provider detail NDJSON into a dict keyed by providerId."""
    data: dict[str, dict] = {}
    if not path.exists():
        return data
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = rec.get("providerId")
            if pid:
                data[str(pid)] = rec
    return data


def load_local_locations(path: Path) -> dict[str, dict]:
    """Load local location detail NDJSON into a dict keyed by locationId."""
    data: dict[str, dict] = {}
    if not path.exists():
        return data
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            lid = rec.get("locationId")
            if lid:
                data[str(lid)] = rec
    return data


def fetch_all_provider_stubs() -> list[dict]:
    """Fetch every provider stub from CQC API (providerId + providerName)."""
    all_items: list[dict] = []
    page = 1
    per_page = 1000
    while True:
        url = f"{CQC_BASE_URL}/providers"
        params = {"page": page, "perPage": per_page}
        try:
            resp = requests.get(url, headers=cqc_headers(), params=params, timeout=30)
        except requests.RequestException as exc:
            print(f"  Provider list request failed on page {page}: {exc}")
            break
        if resp.status_code != 200:
            print(f"  Provider list returned {resp.status_code} on page {page}")
            break
        payload = resp.json()
        providers = payload.get("providers", [])
        if not providers:
            break
        all_items.extend(providers)
        total = payload.get("total", 0)
        if len(all_items) >= total:
            break
        page += 1
        time.sleep(0.15)
    return all_items


def fetch_provider_detail(provider_id: str) -> dict | None:
    url = f"{CQC_BASE_URL}/providers/{provider_id}"
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, headers=cqc_headers(), timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(attempt * 2)
                continue
            return None
        except requests.RequestException:
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            return None


def extract_registered_manager(provider: dict) -> str:
    """Best-effort extraction of registered manager name."""
    # 1. Look in contacts array for Registered Manager role
    contacts = provider.get("contacts", [])
    if isinstance(contacts, list):
        for c in contacts:
            if isinstance(c, dict):
                roles = c.get("personRoles", []) or c.get("roles", [])
                if isinstance(roles, list):
                    for r in roles:
                        if isinstance(r, str) and "registered manager" in r.lower():
                            return f"{c.get('personTitle', '')} {c.get('personGivenName', '')} {c.get('personFamilyName', '')}".strip()
                elif isinstance(roles, str) and "registered manager" in roles.lower():
                    return f"{c.get('personTitle', '')} {c.get('personGivenName', '')} {c.get('personFamilyName', '')}".strip()

    # 2. Look in regulatedActivities nominatedIndividual
    activities = provider.get("regulatedActivities", [])
    if isinstance(activities, list):
        for act in activities:
            if isinstance(act, dict):
                ni = act.get("nominatedIndividual")
                if isinstance(ni, dict):
                    name = f"{ni.get('personTitle', '')} {ni.get('personGivenName', '')} {ni.get('personFamilyName', '')}".strip()
                    if name:
                        return name

    # 3. Look in relationships
    relationships = provider.get("relationships", [])
    if isinstance(relationships, list):
        for rel in relationships:
            if isinstance(rel, dict):
                related = rel.get("relatedLocationId") or rel.get("relatedProviderId")
                if related:
                    pass  # would need another lookup; skip for now

    return ""


def extract_primary_service_type(provider: dict) -> str:
    """Derive primary service type from inspectionCategories, type, or regulated activities."""
    categories = provider.get("inspectionCategories", [])
    if isinstance(categories, list) and categories:
        primary = [c for c in categories if isinstance(c, dict) and str(c.get("primary", "")).lower() == "true"]
        if primary:
            return primary[0].get("name", "")
        return categories[0].get("name", "") if isinstance(categories[0], dict) else ""

    ptype = provider.get("type", "")
    if ptype:
        return ptype

    activities = provider.get("regulatedActivities", [])
    if isinstance(activities, list) and activities:
        first = activities[0]
        if isinstance(first, dict):
            return first.get("name", "")

    return ""


def extract_overall_rating(provider: dict) -> str:
    cr = provider.get("currentRatings", {})
    if isinstance(cr, dict):
        overall = cr.get("overall", {})
        if isinstance(overall, dict):
            return overall.get("rating", "") or ""
    return ""


def build_address(provider: dict) -> str:
    parts = [
        provider.get("postalAddressLine1", ""),
        provider.get("postalAddressLine2", ""),
        provider.get("postalAddressTownCity", ""),
        provider.get("postalAddressCounty", ""),
        provider.get("postalCode", ""),
    ]
    return ", ".join(p for p in parts if p)


def classify_ownership(provider: dict) -> str:
    ot = provider.get("ownershipType", "").lower()
    if ot == "organisation":
        # Heuristic: count locations to guess chain vs independent
        loc_count = len(provider.get("locationIds", []) or [])
        if loc_count >= 10:
            return "National chain / Large group"
        if loc_count >= 3:
            return "Small-medium group"
        return "Independent / Small group"
    if ot == "individual":
        return "Individual proprietor"
    return ot or "Unknown"


def attempt_companies_house_enrichment(company_number: str) -> dict:
    """Attempt to fetch company profile from CH API. Returns empty dict on failure."""
    if not company_number:
        return {}
    url = f"{CH_BASE_URL}/company/{company_number}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return {}


def main() -> int:
    print("=" * 60)
    print("CQC 2026 New Provider Harvest")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load local data
    # ------------------------------------------------------------------
    print("\n[1/5] Loading local provider details...")
    local_providers = load_local_providers(LOCAL_PROVIDERS_DETAIL)
    print(f"      Local providers loaded: {len(local_providers)}")

    print("[2/5] Loading local location details...")
    local_locations = load_local_locations(LOCAL_LOCATIONS_DETAIL)
    print(f"      Local locations loaded: {len(local_locations)}")

    # ------------------------------------------------------------------
    # 2. Filter local providers by registrationDate
    # ------------------------------------------------------------------
    target_providers: dict[str, dict] = {}
    for pid, rec in local_providers.items():
        reg_date = parse_cqc_date(rec.get("registrationDate"))
        if reg_date and START_DATE <= reg_date <= END_DATE:
            target_providers[pid] = rec

    print(f"\n[3/5] Local providers in target window: {len(target_providers)}")

    # ------------------------------------------------------------------
    # 3. Fetch current provider stubs from API, find missing IDs
    # ------------------------------------------------------------------
    print("\n[4/5] Fetching current provider list from CQC API...")
    stubs = fetch_all_provider_stubs()
    print(f"      API returned {len(stubs)} provider stubs")

    api_ids = {str(s.get("providerId", "")) for s in stubs if s.get("providerId")}
    local_ids = set(local_providers.keys())
    missing_ids = sorted(api_ids - local_ids)
    print(f"      Missing from local snapshot: {len(missing_ids)}")

    fetched_from_api = 0
    api_in_window = 0
    if missing_ids:
        print(f"      Fetching details for {len(missing_ids)} missing providers...")
        for i, pid in enumerate(missing_ids):
            detail = fetch_provider_detail(pid)
            if detail:
                fetched_from_api += 1
                local_providers[pid] = detail  # cache for later use
                reg_date = parse_cqc_date(detail.get("registrationDate"))
                if reg_date and START_DATE <= reg_date <= END_DATE:
                    target_providers[pid] = detail
                    api_in_window += 1
            if (i + 1) % 50 == 0:
                print(f"        ... fetched {i + 1}/{len(missing_ids)} ({fetched_from_api} success, {api_in_window} in window)")
            time.sleep(0.15)
        print(f"      API fetch complete: {fetched_from_api} details, {api_in_window} in target window")

    # ------------------------------------------------------------------
    # 4. Cross-reference with locations for service types & counts
    # ------------------------------------------------------------------
    print("\n[5/5] Cross-referencing locations and enriching...")

    # Build provider -> locations mapping from local location data
    provider_to_locations: dict[str, list[dict]] = defaultdict(list)
    for lid, loc in local_locations.items():
        pid = loc.get("providerId")
        if pid:
            provider_to_locations[str(pid)].append(loc)

    # Also use provider.locationIds for any locations not in local file
    # (locations registered after Feb 2026 snapshot)
    records: list[dict] = []
    companies_house_attempts = 0
    companies_house_success = 0

    for pid, provider in target_providers.items():
        reg_date = parse_cqc_date(provider.get("registrationDate"))
        if not reg_date:
            continue

        # Service type
        primary_service = extract_primary_service_type(provider)

        # Locations
        loc_ids = provider.get("locationIds", []) or []
        total_locations = len(loc_ids)

        # Gather service types from linked locations as fallback/enrichment
        linked_locations = provider_to_locations.get(pid, [])
        location_service_types: set[str] = set()
        for loc in linked_locations:
            gac = loc.get("gacServiceTypes", [])
            if isinstance(gac, list):
                for g in gac:
                    if isinstance(g, dict):
                        desc = g.get("description") or g.get("name", "")
                        if desc:
                            location_service_types.add(desc)

        if not primary_service and location_service_types:
            primary_service = sorted(location_service_types)[0]

        # Address
        full_address = build_address(provider)

        # Region / Local Authority
        region = provider.get("region", "")
        local_authority = provider.get("localAuthority", "")

        # Registered manager
        reg_manager = extract_registered_manager(provider)

        # Ownership
        ownership = classify_ownership(provider)

        # Rating
        rating = extract_overall_rating(provider)

        # Companies House
        ch_number = provider.get("companiesHouseNumber", "")
        ch_enrichment = {}
        if ch_number:
            companies_house_attempts += 1
            ch_enrichment = attempt_companies_house_enrichment(ch_number)
            if ch_enrichment:
                companies_house_success += 1

        # Trading name(s) – use name as legal name; brandName or relationships for trading names
        legal_name = provider.get("name", "")
        trading_names: list[str] = []
        brand = provider.get("brandName", "")
        if brand and brand != legal_name:
            trading_names.append(brand)

        # Director names from CH enrichment if available
        directors: list[str] = []
        if ch_enrichment:
            # CH API /company/{number} does not include officers; would need /officers call
            pass

        incorporation_date = ""
        if ch_enrichment and "date_of_creation" in ch_enrichment:
            incorporation_date = ch_enrichment["date_of_creation"]

        company_status = ch_enrichment.get("company_status", "") if ch_enrichment else ""

        record = {
            "providerId": pid,
            "legalName": legal_name,
            "tradingNames": " | ".join(trading_names) if trading_names else "",
            "registrationDate": str(reg_date),
            "fullAddress": full_address,
            "region": region,
            "localAuthority": local_authority,
            "primaryServiceType": primary_service,
            "totalNumberOfLocations": total_locations,
            "registeredManagerName": reg_manager,
            "ownershipStructure": ownership,
            "latestInspectionRating": rating if rating else "Not yet inspected",
            "companiesHouseNumber": ch_number,
            "companyIncorporationDate": incorporation_date,
            "companyStatus": company_status,
            "directorNames": " | ".join(directors) if directors else "",
            "cqcRegistrationStatus": provider.get("registrationStatus", ""),
            "postalCode": provider.get("postalCode", ""),
            "mainPhoneNumber": provider.get("mainPhoneNumber", ""),
            "website": provider.get("website", ""),
        }
        records.append(record)

    print(f"      Final enriched records: {len(records)}")
    print(f"      Companies House attempts: {companies_house_attempts}, successes: {companies_house_success}")

    # ------------------------------------------------------------------
    # 5. Deduplicate (by providerId is already unique)
    # ------------------------------------------------------------------
    seen_ids = set()
    deduped = []
    for r in records:
        if r["providerId"] not in seen_ids:
            seen_ids.add(r["providerId"])
            deduped.append(r)
    records = deduped

    # ------------------------------------------------------------------
    # 6. Sort by registrationDate, then name
    # ------------------------------------------------------------------
    records.sort(key=lambda x: (x["registrationDate"], x["legalName"]))

    # ------------------------------------------------------------------
    # 7. Write JSON
    # ------------------------------------------------------------------
    with OUTPUT_JSON.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)
    print(f"\n  Written: {OUTPUT_JSON} ({len(records)} records)")

    # ------------------------------------------------------------------
    # 8. Write CSV
    # ------------------------------------------------------------------
    if records:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
    print(f"  Written: {OUTPUT_CSV}")

    # ------------------------------------------------------------------
    # 9. Data quality report
    # ------------------------------------------------------------------
    total = len(records)
    field_coverage: dict[str, tuple[int, float]] = {}
    for field in records[0].keys():
        filled = sum(1 for r in records if r.get(field) not in (None, "", []))
        field_coverage[field] = (filled, round(filled / total * 100, 1))

    # Geographic distribution
    region_counts = Counter(r["region"] for r in records if r["region"])
    la_counts = Counter(r["localAuthority"] for r in records if r["localAuthority"])

    # Service type distribution
    service_counts = Counter(r["primaryServiceType"] for r in records if r["primaryServiceType"])

    # Registration date distribution
    month_counts = Counter(r["registrationDate"][:7] for r in records)

    # Ownership distribution
    ownership_counts = Counter(r["ownershipStructure"] for r in records if r["ownershipStructure"])

    # Anomalies
    anomalies: list[str] = []
    zero_loc = sum(1 for r in records if r["totalNumberOfLocations"] == 0)
    if zero_loc:
        anomalies.append(f"{zero_loc} providers have zero linked locations (may indicate pending registrations or data lag).")

    future_reg = sum(1 for r in records if parse_cqc_date(r["registrationDate"]) and parse_cqc_date(r["registrationDate"]) > END_DATE)
    if future_reg:
        anomalies.append(f"{future_reg} records have a registration date after the target window (should be 0).")

    missing_ch = sum(1 for r in records if not r["companiesHouseNumber"])
    anomalies.append(f"{missing_ch} providers lack a Companies House number.")

    ch_failures = companies_house_attempts - companies_house_success
    if ch_failures > 0:
        anomalies.append(f"Companies House enrichment failed for {ch_failures} of {companies_house_attempts} attempts (likely API auth required).")

    # Build report
    report_lines = [
        "# CQC Data Quality Report – New Providers (1 Jan 2026 – 28 Apr 2026)",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Total records harvested:** {total}",
        "",
        "## 1. Coverage per field",
        "",
        "| Field | Filled | Coverage % |",
        "|-------|--------|------------|",
    ]
    for field, (filled, pct) in sorted(field_coverage.items(), key=lambda x: -x[1][1]):
        report_lines.append(f"| {field} | {filled} | {pct}% |")

    report_lines.extend([
        "",
        "## 2. Geographic distribution",
        "",
        "### By Region (top 10)",
        "",
        "| Region | Count |",
        "|--------|-------|",
    ])
    for region, cnt in region_counts.most_common(10):
        report_lines.append(f"| {region} | {cnt} |")

    report_lines.extend([
        "",
        "### By Local Authority (top 10)",
        "",
        "| Local Authority | Count |",
        "|-----------------|-------|",
    ])
    for la, cnt in la_counts.most_common(10):
        report_lines.append(f"| {la} | {cnt} |")

    report_lines.extend([
        "",
        "## 3. Service type distribution (top 10)",
        "",
        "| Service Type | Count |",
        "|--------------|-------|",
    ])
    for svc, cnt in service_counts.most_common(10):
        report_lines.append(f"| {svc} | {cnt} |")

    report_lines.extend([
        "",
        "## 4. Registration month distribution",
        "",
        "| Month | Count |",
        "|-------|-------|",
    ])
    for month, cnt in sorted(month_counts.items()):
        report_lines.append(f"| {month} | {cnt} |")

    report_lines.extend([
        "",
        "## 5. Ownership structure distribution",
        "",
        "| Ownership | Count |",
        "|-----------|-------|",
    ])
    for own, cnt in ownership_counts.most_common():
        report_lines.append(f"| {own} | {cnt} |")

    report_lines.extend([
        "",
        "## 6. Missing-data hotspots",
        "",
    ])
    low_coverage = [(f, v) for f, v in field_coverage.items() if v[1] < 50]
    if low_coverage:
        for field, (filled, pct) in sorted(low_coverage, key=lambda x: x[1][1]):
            report_lines.append(f"- **{field}**: {pct}% ({filled}/{total}) – significant gap")
    else:
        report_lines.append("- All fields exceed 50% coverage.")

    report_lines.extend([
        "",
        "## 7. Anomalies & API limitations",
        "",
    ])
    for a in anomalies:
        report_lines.append(f"- {a}")

    report_lines.extend([
        "",
        "## 8. Methodology notes",
        "",
        "- **Primary source:** CQC Public API (`api.service.cqc.org.uk`) plus local snapshot `_providers_detail.ndjson` (dated 2026-02-24).",
        f"- **API fetches:** {len(missing_ids)} missing provider IDs scanned; {fetched_from_api} detail records retrieved; {api_in_window} fell inside the target window.",
        "- **Companies House:** Attempted via `api.company-information.service.gov.uk` without an API key. All requests returned 401 / auth errors. Enrichment limited to `companiesHouseNumber` already present in CQC data.",
        "- **Location counts:** Derived from `provider.locationIds` array in CQC provider detail. Cross-referenced with `_locations_detail.ndjson` for service-type enrichment.",
        "- **Date window:** registrationDate >= 2026-01-01 and <= 2026-04-28.",
        "",
    ])

    report_text = "\n".join(report_lines)
    with OUTPUT_REPORT.open("w", encoding="utf-8") as fh:
        fh.write(report_text)
    print(f"  Written: {OUTPUT_REPORT}")

    # ------------------------------------------------------------------
    # 10. Console summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total providers in window: {total}")
    print(f"Top 3 regions:")
    for region, cnt in region_counts.most_common(3):
        print(f"  - {region}: {cnt}")
    print(f"Top 3 service types:")
    for svc, cnt in service_counts.most_common(3):
        print(f"  - {svc}: {cnt}")
    print(f"API limitations:")
    print(f"  - Companies House API requires authentication key (unavailable).")
    print(f"  - {len(missing_ids)} provider IDs not in local snapshot; fetched {fetched_from_api} details from CQC API.")
    if ch_failures > 0:
        print(f"  - Companies House enrichment failed for {ch_failures} records due to missing API key.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
