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



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare directory-ready outputs from cleaned CQC data")
    parser.add_argument("--input", default=INPUT_CLEANED, help="Input cleaned CSV")
    parser.add_argument("--raw", default=INPUT_RAW_COMBINED, help="Input raw combined CSV for totals")
    parser.add_argument("--failed-ids", default=INPUT_FAILED_IDS, help="Failed IDs text file")
    parser.add_argument("--output-csv", default=OUTPUT_DIRECTORY_CSV, help="Output directory CSV")
    parser.add_argument("--output-json", default=OUTPUT_DIRECTORY_JSON, help="Output directory JSON")
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
    print("║ DB schema: db/init.sql                           ║")
    print("║ Report: quality_summary.txt                      ║")
    print("╚══════════════════════════════════════════════════╝")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
