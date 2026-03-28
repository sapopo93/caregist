#!/usr/bin/env python3
"""Prepare final directory-ready outputs from cleaned CQC data."""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests

try:
    from slugify import slugify as _slugify
except ImportError:  # pragma: no cover - fallback for restricted environments
    import unicodedata

    def _slugify(value: str, separator: str = "-") -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        lowered = normalized.lower()
        lowered = re.sub(r"[^a-z0-9]+", separator, lowered).strip(separator)
        lowered = re.sub(rf"{re.escape(separator)}+", separator, lowered)
        return lowered

from cqc_common import normalize_whitespace

INPUT_CLEANED = "cleaned_cqc.csv"
INPUT_RAW_COMBINED = "raw_combined.csv"
INPUT_FAILED_IDS = "failed_ids.txt"

OUTPUT_DIRECTORY_CSV = "directory_providers.csv"
OUTPUT_DIRECTORY_JSON = "directory_providers.json"
OUTPUT_DIRECTORY_SQL = "directory_providers.sql"
OUTPUT_IMPORT_SQL = "import_to_db.sql"


def is_blank(value: Any) -> bool:
    text = normalize_whitespace(value)
    return not text or text.upper() == "NULL"


def clean_value(value: Any) -> str | None:
    if is_blank(value):
        return None
    return normalize_whitespace(value)


def parse_int(value: Any) -> int | None:
    if is_blank(value):
        return None
    text = re.sub(r"[^0-9-]", "", str(value))
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_float(value: Any) -> float | None:
    if is_blank(value):
        return None
    try:
        return round(float(str(value).strip()), 7)
    except ValueError:
        return None


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def generate_slug(name: str, town: str, location_id: str, used: set[str]) -> str:
    base = _slugify(f"{name}-{town}" if town else name, separator="-")
    if not base:
        base = _slugify(location_id, separator="-") or f"provider-{location_id.lower()}"

    slug = base
    if slug in used:
        suffix = _slugify(location_id, separator="-")
        slug = f"{base}-{suffix}" if suffix else f"{base}-{len(used)}"
        n = 2
        while slug in used:
            slug = f"{base}-{suffix}-{n}" if suffix else f"{base}-{n}"
            n += 1

    used.add(slug)
    return slug


def choose_type(raw_type: Any, service_types: Any) -> str | None:
    raw = clean_value(raw_type)
    if raw:
        return raw

    services = clean_value(service_types)
    if services:
        return services.split("|")[0]

    return None


def inspection_url(location_id: str, existing_url: Any) -> str | None:
    url = clean_value(existing_url)
    if url:
        return url
    if location_id:
        return f"https://www.cqc.org.uk/location/{location_id}"
    return None


def normalize_rating(value: Any) -> str:
    text = normalize_whitespace(value)
    if not text:
        return "Not Yet Inspected"
    normalized = text.lower()
    mapping = {
        "outstanding": "Outstanding",
        "good": "Good",
        "requires improvement": "Requires Improvement",
        "requiresimprovement": "Requires Improvement",
        "inadequate": "Inadequate",
        "not yet inspected": "Not Yet Inspected",
        "unknown": "Unknown",
    }
    return mapping.get(normalized, text)


def geocode_from_postcode(postcode: str, timeout: int = 10) -> tuple[float | None, float | None]:
    url = f"https://api.postcodes.io/postcodes/{quote(postcode)}"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None, None
        payload = response.json()
        result = payload.get("result")
        if not isinstance(result, dict):
            return None, None
        lat = result.get("latitude")
        lon = result.get("longitude")
        if lat is None or lon is None:
            return None, None
        return float(lat), float(lon)
    except Exception:
        return None, None


BRAND_NAME = "CareGist"

# Map CQC provider types to user-friendly labels
_TYPE_LABELS = {
    "social care org": "Care Provider",
    "primary dental care": "Dental Practice",
    "primary medical services": "GP Surgery",
    "independent healthcare org": "Healthcare Provider",
    "nhs healthcare organisation": "NHS Service",
    "independent ambulance": "Ambulance Service",
}

# Map service type keywords to page category labels
_SERVICE_LABELS = {
    "residential homes": "Care Home",
    "nursing homes": "Nursing Home",
    "homecare agencies": "Home Care Agency",
    "supported living": "Supported Living Provider",
    "dentist": "Dental Practice",
    "doctors/gps": "GP Surgery",
}


def _friendly_type(provider_type: str | None, service_types: str | None) -> str:
    """Derive a user-friendly type label from provider type and service types."""
    if service_types:
        first_service = service_types.split("|")[0].strip().lower()
        label = _SERVICE_LABELS.get(first_service)
        if label:
            return label
    if provider_type:
        label = _TYPE_LABELS.get(provider_type.strip().lower())
        if label:
            return label
    return "care provider"


def _location_text(town: str | None, county: str | None, region: str | None) -> str:
    """Build location string with fallback chain, no duplicates."""
    parts: list[str] = []
    if town:
        parts.append(town)
    if county and county != town:
        parts.append(county)
    if not parts and region:
        parts.append(region)
    if not parts:
        parts.append("England")
    return ", ".join(parts)


def meta_title(name: str, town: str | None, service_types: str | None = None, provider_type: str | None = None) -> str:
    place = town or "England"
    friendly = _friendly_type(provider_type, service_types)
    return f"{name} | {friendly.title()} in {place} | {BRAND_NAME}"


def meta_description(
    name: str,
    provider_type: str | None,
    town: str | None,
    county: str | None,
    rating: str,
    specialisms: str | None,
    region: str | None,
    service_types: str | None = None,
    beds: int | None = None,
) -> str:
    friendly = _friendly_type(provider_type, service_types)
    location = _location_text(town, county, region)

    # Vary description by provider category
    if service_types and any(k in service_types.lower() for k in ["nursing homes", "residential homes"]):
        beds_text = f" with {beds} beds" if beds else ""
        specialisms_text = specialisms.replace("|", ", ") if specialisms else "general care"
        return (
            f"{name} is a CQC-registered {friendly.lower()}{beds_text} in {location}. "
            f"Latest CQC rating: {rating}. Specialisms include {specialisms_text}. "
            f"View inspection history, ratings and contact details on {BRAND_NAME}."
        )

    if service_types and "homecare" in service_types.lower():
        specialisms_text = specialisms.replace("|", ", ") if specialisms else "general care"
        return (
            f"{name} provides domiciliary care services in {location}. "
            f"CQC rating: {rating}. Covers: {specialisms_text}. "
            f"Find contact details, inspection reports and ratings on {BRAND_NAME}."
        )

    if provider_type and "dental" in provider_type.lower():
        return (
            f"{name} is a CQC-registered dental practice in {location}. "
            f"CQC rating: {rating}. "
            f"Check inspection history and book details on {BRAND_NAME}."
        )

    if provider_type and "medical" in provider_type.lower():
        return (
            f"{name} is a GP surgery in {location}, registered with CQC. "
            f"Latest CQC rating: {rating}. "
            f"View inspection reports, ratings and practice details on {BRAND_NAME}."
        )

    # Default template
    specialisms_text = specialisms.replace("|", ", ") if specialisms else "Not specified"
    return (
        f"{name} is a {friendly.lower()} in {location}. "
        f"CQC rating: {rating}. Specialisms: {specialisms_text}. "
        f"Data source: Care Quality Commission (CQC)."
    )


def sql_literal(value: Any, numeric: bool = False) -> str:
    if value is None:
        return "NULL"
    if numeric:
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def write_import_sql(path: Path) -> None:
    sql = """-- import_to_db.sql
-- This file contains both PostgreSQL and MySQL table definitions.
-- Run only the section for your target database.

/* ========================
   PostgreSQL DDL
   ======================== */
CREATE TABLE IF NOT EXISTS care_providers (
  id VARCHAR(20) PRIMARY KEY,
  provider_id VARCHAR(20),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(300) UNIQUE,
  type VARCHAR(100),
  status VARCHAR(20),
  registration_date DATE,
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  town VARCHAR(100),
  county VARCHAR(100),
  postcode VARCHAR(10),
  region VARCHAR(100),
  local_authority VARCHAR(100),
  country VARCHAR(50) DEFAULT 'England',
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  phone VARCHAR(20),
  website VARCHAR(500),
  email VARCHAR(255),
  overall_rating VARCHAR(50),
  rating_safe VARCHAR(50),
  rating_effective VARCHAR(50),
  rating_caring VARCHAR(50),
  rating_responsive VARCHAR(50),
  rating_well_led VARCHAR(50),
  last_inspection_date DATE,
  inspection_report_url VARCHAR(500),
  service_types TEXT,
  specialisms TEXT,
  regulated_activities TEXT,
  number_of_beds INT,
  ownership_type VARCHAR(50),
  quality_score INT,
  quality_tier VARCHAR(20),
  meta_title VARCHAR(300),
  meta_description VARCHAR(500),
  geocode_source VARCHAR(20),
  last_updated TIMESTAMP,
  data_source VARCHAR(50),
  data_attribution VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_postcode ON care_providers (postcode);
CREATE INDEX IF NOT EXISTS idx_region ON care_providers (region);
CREATE INDEX IF NOT EXISTS idx_local_authority ON care_providers (local_authority);
CREATE INDEX IF NOT EXISTS idx_overall_rating ON care_providers (overall_rating);
CREATE INDEX IF NOT EXISTS idx_quality_tier ON care_providers (quality_tier);
CREATE INDEX IF NOT EXISTS idx_status ON care_providers (status);
CREATE INDEX IF NOT EXISTS idx_slug ON care_providers (slug);
CREATE INDEX IF NOT EXISTS idx_search ON care_providers
USING GIN (to_tsvector('english', coalesce(name,'') || ' ' || coalesce(town,'') || ' ' || coalesce(county,'') || ' ' || coalesce(service_types,'') || ' ' || coalesce(specialisms,'')));

/* ========================
   MySQL DDL
   ======================== */
CREATE TABLE IF NOT EXISTS care_providers (
  id VARCHAR(20) PRIMARY KEY,
  provider_id VARCHAR(20),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(300) UNIQUE,
  type VARCHAR(100),
  status VARCHAR(20),
  registration_date DATE,
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  town VARCHAR(100),
  county VARCHAR(100),
  postcode VARCHAR(10),
  region VARCHAR(100),
  local_authority VARCHAR(100),
  country VARCHAR(50) DEFAULT 'England',
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  phone VARCHAR(20),
  website VARCHAR(500),
  email VARCHAR(255),
  overall_rating VARCHAR(50),
  rating_safe VARCHAR(50),
  rating_effective VARCHAR(50),
  rating_caring VARCHAR(50),
  rating_responsive VARCHAR(50),
  rating_well_led VARCHAR(50),
  last_inspection_date DATE,
  inspection_report_url VARCHAR(500),
  service_types TEXT,
  specialisms TEXT,
  regulated_activities TEXT,
  number_of_beds INT,
  ownership_type VARCHAR(50),
  quality_score INT,
  quality_tier VARCHAR(20),
  meta_title VARCHAR(300),
  meta_description VARCHAR(500),
  geocode_source VARCHAR(20),
  last_updated DATETIME,
  data_source VARCHAR(50),
  data_attribution VARCHAR(200),
  INDEX idx_postcode (postcode),
  INDEX idx_region (region),
  INDEX idx_local_authority (local_authority),
  INDEX idx_overall_rating (overall_rating),
  INDEX idx_quality_tier (quality_tier),
  INDEX idx_status (status),
  INDEX idx_slug (slug),
  FULLTEXT INDEX idx_search (name, town, county, service_types, specialisms)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
    path.write_text(sql, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare directory-ready outputs from cleaned CQC data")
    parser.add_argument("--input", default=INPUT_CLEANED, help="Input cleaned CSV")
    parser.add_argument("--raw", default=INPUT_RAW_COMBINED, help="Input raw combined CSV for totals")
    parser.add_argument("--failed-ids", default=INPUT_FAILED_IDS, help="Failed IDs text file")
    parser.add_argument("--output-csv", default=OUTPUT_DIRECTORY_CSV, help="Output directory CSV")
    parser.add_argument("--output-json", default=OUTPUT_DIRECTORY_JSON, help="Output directory JSON")
    parser.add_argument("--output-sql", default=OUTPUT_DIRECTORY_SQL, help="Output SQL inserts file")
    parser.add_argument("--import-sql", default=OUTPUT_IMPORT_SQL, help="Output DB import DDL file")
    parser.add_argument("--enable-geocode", action="store_true", help="Geocode missing coordinates via postcodes.io")
    parser.add_argument("--geocode-sleep", type=float, default=0.1, help="Sleep seconds between geocode calls")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input).resolve()
    raw_path = Path(args.raw).resolve()
    failed_ids_path = Path(args.failed_ids).resolve()

    output_csv = Path(args.output_csv).resolve()
    output_json = Path(args.output_json).resolve()
    output_sql = Path(args.output_sql).resolve()
    import_sql = Path(args.import_sql).resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)

    fieldnames = [
        "id",
        "provider_id",
        "name",
        "slug",
        "type",
        "status",
        "registration_date",
        "address_line1",
        "address_line2",
        "town",
        "county",
        "postcode",
        "region",
        "local_authority",
        "country",
        "latitude",
        "longitude",
        "phone",
        "website",
        "email",
        "overall_rating",
        "rating_safe",
        "rating_effective",
        "rating_caring",
        "rating_responsive",
        "rating_well_led",
        "last_inspection_date",
        "inspection_report_url",
        "service_types",
        "specialisms",
        "regulated_activities",
        "number_of_beds",
        "ownership_type",
        "quality_score",
        "quality_tier",
        "meta_title",
        "meta_description",
        "geocode_source",
        "last_updated",
        "data_source",
        "data_attribution",
    ]

    last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    used_slugs: set[str] = set()
    output_rows: list[dict[str, Any]] = []

    tier_counts = {"COMPLETE": 0, "GOOD": 0, "PARTIAL": 0, "SPARSE": 0}

    for record in df.to_dict(orient="records"):
        status = clean_value(record.get("directoryStatus")) or "ACTIVE"

        location_id = clean_value(record.get("locationId")) or ""
        provider_id = clean_value(record.get("providerId"))
        name = clean_value(record.get("name")) or "Unknown Provider"
        town = clean_value(record.get("postalAddressTownCity"))
        county = clean_value(record.get("postalAddressCounty"))
        postcode = clean_value(record.get("postalCode"))
        website = clean_value(record.get("website"))
        phone = clean_value(record.get("mainPhoneNumber"))
        email = clean_value(record.get("email"))

        overall_rating = normalize_rating(record.get("overallRating"))
        provider_type = choose_type(record.get("type"), record.get("serviceTypes"))

        lat = parse_float(record.get("latitude"))
        lon = parse_float(record.get("longitude"))
        geocode_source = "CQC_API" if lat is not None and lon is not None else "MISSING"

        if lat is None or lon is None:
            if args.enable_geocode and postcode:
                geo_lat, geo_lon = geocode_from_postcode(postcode)
                if geo_lat is not None and geo_lon is not None:
                    lat = round(geo_lat, 7)
                    lon = round(geo_lon, 7)
                    geocode_source = "POSTCODE_IO"
                time.sleep(args.geocode_sleep)

        slug = generate_slug(name, town or "", location_id, used_slugs)

        quality_score = parse_int(record.get("qualityScore"))
        quality_tier = clean_value(record.get("qualityTier")) or "SPARSE"
        if quality_tier not in tier_counts:
            tier_counts[quality_tier] = 0
        tier_counts[quality_tier] += 1

        out_row = {
            "id": location_id,
            "provider_id": provider_id,
            "name": name,
            "slug": slug,
            "type": provider_type,
            "status": status,
            "registration_date": clean_value(record.get("registrationDate")),
            "address_line1": clean_value(record.get("postalAddressLine1")),
            "address_line2": clean_value(record.get("postalAddressLine2")),
            "town": town,
            "county": county,
            "postcode": postcode,
            "region": clean_value(record.get("region")),
            "local_authority": clean_value(record.get("localAuthority")),
            "country": "England",
            "latitude": lat,
            "longitude": lon,
            "phone": phone,
            "website": website,
            "email": email,
            "overall_rating": overall_rating,
            "rating_safe": clean_value(record.get("rating_safe")),
            "rating_effective": clean_value(record.get("rating_effective")),
            "rating_caring": clean_value(record.get("rating_caring")),
            "rating_responsive": clean_value(record.get("rating_responsive")),
            "rating_well_led": clean_value(record.get("rating_well_led")),
            "last_inspection_date": clean_value(record.get("lastInspectionDate")),
            "inspection_report_url": inspection_url(location_id, record.get("cqcUrl")),
            "service_types": clean_value(record.get("serviceTypes")),
            "specialisms": clean_value(record.get("specialisms")),
            "regulated_activities": clean_value(record.get("regulatedActivities")),
            "number_of_beds": parse_int(record.get("numberOfBeds")),
            "ownership_type": clean_value(record.get("ownershipType")),
            "quality_score": quality_score,
            "quality_tier": quality_tier,
            "meta_title": meta_title(name, town, service_types=clean_value(record.get("serviceTypes")), provider_type=provider_type),
            "meta_description": meta_description(
                name,
                provider_type,
                town,
                county,
                overall_rating,
                clean_value(record.get("specialisms")),
                clean_value(record.get("region")),
                service_types=clean_value(record.get("serviceTypes")),
                beds=parse_int(record.get("numberOfBeds")),
            ),
            "geocode_source": geocode_source,
            "last_updated": last_updated,
            "data_source": "CQC API v1",
            "data_attribution": "Source: Care Quality Commission (CQC). This is not an official CQC service.",
        }

        output_rows.append(out_row)

    with output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in output_rows:
            writer.writerow({k: "" if v is None else v for k, v in row.items()})

    with output_json.open("w", encoding="utf-8") as fh:
        json.dump(output_rows, fh, indent=2, ensure_ascii=True)

    with output_sql.open("w", encoding="utf-8") as fh:
        fh.write("-- directory_providers.sql\n")
        fh.write("-- Generated INSERT statements for PostgreSQL/MySQL\n\n")
        cols = ", ".join(fieldnames)
        for row in output_rows:
            values = [
                sql_literal(row["id"]),
                sql_literal(row["provider_id"]),
                sql_literal(row["name"]),
                sql_literal(row["slug"]),
                sql_literal(row["type"]),
                sql_literal(row["status"]),
                sql_literal(row["registration_date"]),
                sql_literal(row["address_line1"]),
                sql_literal(row["address_line2"]),
                sql_literal(row["town"]),
                sql_literal(row["county"]),
                sql_literal(row["postcode"]),
                sql_literal(row["region"]),
                sql_literal(row["local_authority"]),
                sql_literal(row["country"]),
                sql_literal(row["latitude"], numeric=row["latitude"] is not None),
                sql_literal(row["longitude"], numeric=row["longitude"] is not None),
                sql_literal(row["phone"]),
                sql_literal(row["website"]),
                sql_literal(row["email"]),
                sql_literal(row["overall_rating"]),
                sql_literal(row["rating_safe"]),
                sql_literal(row["rating_effective"]),
                sql_literal(row["rating_caring"]),
                sql_literal(row["rating_responsive"]),
                sql_literal(row["rating_well_led"]),
                sql_literal(row["last_inspection_date"]),
                sql_literal(row["inspection_report_url"]),
                sql_literal(row["service_types"]),
                sql_literal(row["specialisms"]),
                sql_literal(row["regulated_activities"]),
                sql_literal(row["number_of_beds"], numeric=row["number_of_beds"] is not None),
                sql_literal(row["ownership_type"]),
                sql_literal(row["quality_score"], numeric=row["quality_score"] is not None),
                sql_literal(row["quality_tier"]),
                sql_literal(row["meta_title"]),
                sql_literal(row["meta_description"]),
                sql_literal(row["geocode_source"]),
                sql_literal(row["last_updated"]),
                sql_literal(row["data_source"]),
                sql_literal(row["data_attribution"]),
            ]
            fh.write(f"INSERT INTO care_providers ({cols}) VALUES ({', '.join(values)});\n")

    write_import_sql(import_sql)

    total_extracted = count_csv_rows(raw_path)
    active_count = len(output_rows)
    failed_count = count_lines(failed_ids_path)

    print("╔══════════════════════════════════════════════════╗")
    print("║     CQC DIRECTORY BUILD — COMPLETE               ║")
    print("╠══════════════════════════════════════════════════╣")
    print(f"║ Total providers extracted:  {str(total_extracted).ljust(22)}║")
    print(f"║ Active (directory-ready):   {str(active_count).ljust(22)}║")
    print(f"║ COMPLETE data records:      {str(tier_counts.get('COMPLETE', 0)).ljust(22)}║")
    print(f"║ GOOD data records:         {str(tier_counts.get('GOOD', 0)).ljust(22)}║")
    print(f"║ PARTIAL data records:      {str(tier_counts.get('PARTIAL', 0)).ljust(22)}║")
    print(f"║ SPARSE data records:       {str(tier_counts.get('SPARSE', 0)).ljust(22)}║")
    print(f"║ Failed extractions:         {str(failed_count).ljust(22)}║")
    print("║                                                  ║")
    print("║ Output: directory_providers.csv                  ║")
    print("║ Output: directory_providers.json                 ║")
    print("║ Output: directory_providers.sql                  ║")
    print("║ Report: quality_summary.txt                      ║")
    print("╚══════════════════════════════════════════════════╝")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
