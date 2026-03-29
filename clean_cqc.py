#!/usr/bin/env python3
"""Clean and normalize CQC raw combined dataset."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from urllib.parse import urlparse

try:
    import phonenumbers
except ImportError:  # pragma: no cover - fallback for restricted environments
    phonenumbers = None

try:
    import validators
except ImportError:  # pragma: no cover - fallback for restricted environments
    validators = None

from cqc_common import ensure_list, normalize_whitespace, parse_any_date, to_float, ts_for_logs

INPUT_RAW_COMBINED = "raw_combined.csv"
OUTPUT_CLEANED = "cleaned_cqc.csv"
OUTPUT_INACTIVE = "inactive_providers.csv"
OUTPUT_DUPLICATES = "duplicates_removed.csv"
OUTPUT_LOG = "clean_log.txt"
TEMP_STAGE = "_clean_stage.csv"

NAME_ALLOWED_RE = re.compile(r"^[A-Za-z0-9 '&.\-]+$")
POSTCODE_RE = re.compile(r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s[0-9][A-Z]{2}$")

RATING_MAP = {
    "outstanding": "Outstanding",
    "good": "Good",
    "requires improvement": "Requires Improvement",
    "requiresimprovement": "Requires Improvement",
    "ri": "Requires Improvement",
    "inadequate": "Inadequate",
    "not yet inspected": "Not Yet Inspected",
    "not yet rated": "Not Yet Inspected",
    "not inspected": "Not Yet Inspected",
    "unknown": "Unknown",
    "": "",
}

SERVICE_TYPE_MAP = {
    "care home service with nursing": "Care Home Service With Nursing",
    "care home service without nursing": "Care Home Service Without Nursing",
    "domiciliary care service": "Domiciliary Care Service",
    "extra care housing": "Extra Care Housing",
    "supported living": "Supported Living",
    "shared lives": "Shared Lives",
    "community healthcare": "Community Healthcare",
}

SPECIALISM_MAP = {
    "dementia": "Dementia",
    "learning disabilities": "Learning Disabilities",
    "learning disability": "Learning Disabilities",
    "mental health": "Mental Health",
    "older people": "Older People",
    "physical disabilities": "Physical Disabilities",
    "sensory impairments": "Sensory Impairments",
    "substance misuse": "Substance Misuse",
}

REGULATED_ACTIVITY_MAP = {
    "accommodation for persons who require nursing or personal care": "Accommodation For Persons Who Require Nursing Or Personal Care",
    "treatment of disease, disorder or injury": "Treatment Of Disease, Disorder Or Injury",
    "diagnostic and screening procedures": "Diagnostic And Screening Procedures",
    "surgical procedures": "Surgical Procedures",
}


def log_line(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{ts_for_logs()}] {message}\n")


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.upper() == "NULL"


def title_case_if_caps(name: str) -> str:
    alpha = re.sub(r"[^A-Za-z]", "", name)
    if alpha and alpha.isupper():
        return name.title()
    return name


def normalize_name(value: Any) -> tuple[str, str]:
    name = normalize_whitespace(value)
    if not name:
        return "", ""
    name = title_case_if_caps(name)
    if not NAME_ALLOWED_RE.fullmatch(name):
        return name, "INVALID_NAME_CHARS"
    return name, ""


def normalize_phone(value: Any) -> tuple[str, str]:
    if is_blank(value):
        return "NULL", ""

    raw = str(value).strip()
    cleaned = re.sub(r"(?!^\+)\D", "", raw)
    digits = re.sub(r"\D", "", cleaned)

    if digits.startswith("44") and len(digits) in (12, 13):
        digits = "0" + digits[2:]

    if phonenumbers is not None:
        try:
            number = phonenumbers.parse(raw, "GB")
            if phonenumbers.is_valid_number(number):
                national = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
                only_digits = re.sub(r"\D", "", national)
                if len(only_digits) in (10, 11):
                    return national, ""
        except phonenumbers.NumberParseException:
            pass

    if len(digits) not in (10, 11):
        return raw, "INVALID_PHONE"

    if len(digits) == 11:
        if digits.startswith("07"):
            formatted = f"{digits[:5]} {digits[5:]}"
        else:
            formatted = f"{digits[:5]} {digits[5:]}"
    else:
        formatted = digits

    return formatted, ""


def normalize_postcode(value: Any) -> tuple[str, str]:
    if is_blank(value):
        return "", ""

    postcode = normalize_whitespace(value).upper().replace(" ", "")
    if len(postcode) > 3:
        postcode = f"{postcode[:-3]} {postcode[-3:]}"

    if not POSTCODE_RE.fullmatch(postcode):
        return postcode, "INVALID_POSTCODE"

    return postcode, ""


def normalize_website(value: Any) -> tuple[str, str]:
    if is_blank(value):
        return "NULL", ""

    website = normalize_whitespace(value).lower().rstrip("/")
    if not website.startswith("http://") and not website.startswith("https://"):
        website = f"https://{website}"

    if validators is not None:
        if validators.url(website) is not True:
            return website, "INVALID_URL"
    else:
        parsed = urlparse(website)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return website, "INVALID_URL"

    return website, ""


def normalize_address(value: Any) -> tuple[str, str]:
    text = normalize_whitespace(value)
    if not text:
        return "", ""

    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*;\s*", "; ", text)

    if len(text) < 10:
        return text, "SUSPECT_ADDRESS"

    return text, ""


def normalize_rating(value: Any, registration_status: str) -> str:
    text = normalize_whitespace(value)
    key = text.lower()
    if key in RATING_MAP and RATING_MAP[key]:
        return RATING_MAP[key]

    if key in RATING_MAP:
        pass
    elif key:
        if key == "requiresimprovement":
            return "Requires Improvement"
        if key == "notyetinspected":
            return "Not Yet Inspected"
        return text.title()

    if normalize_whitespace(registration_status).lower() == "registered":
        return "Not Yet Inspected"
    return "Unknown"


def normalize_date(value: Any, field_name: str) -> tuple[str, str]:
    if is_blank(value):
        return "", ""

    parsed = parse_any_date(value)
    if not parsed:
        return "", "SUSPECT_DATE"

    parsed_dt = date.fromisoformat(parsed)
    if field_name != "expectedDeregistrationDate" and parsed_dt > date.today():
        return parsed, "SUSPECT_DATE"

    if field_name == "registrationDate" and parsed_dt.year < 1990:
        return parsed, "SUSPECT_DATE"

    return parsed, ""


def normalize_coordinates(lat_value: Any, lon_value: Any) -> tuple[str, str, str]:
    lat = to_float(lat_value)
    lon = to_float(lon_value)

    if lat is None or lon is None:
        return "", "", "MISSING_COORDS"

    if not (49.0 <= lat <= 61.0 and -8.0 <= lon <= 2.0):
        return f"{lat:.7f}", f"{lon:.7f}", "INVALID_COORDS"

    return f"{lat:.7f}", f"{lon:.7f}", ""


def _parse_list(value: Any) -> list[str]:
    parsed = ensure_list(value)
    output: list[str] = []

    for item in parsed:
        if isinstance(item, dict):
            text = (
                item.get("name")
                or item.get("description")
                or item.get("value")
                or item.get("title")
                or item.get("code")
                or ""
            )
        else:
            text = item

        text = normalize_whitespace(text)
        if not text:
            continue
        output.append(text)

    if len(output) == 1 and output[0].startswith("[") and output[0].endswith("]"):
        try:
            decoded = json.loads(output[0])
            return _parse_list(decoded)
        except json.JSONDecodeError:
            pass

    return output


def normalize_taxonomy(value: Any, mapping: dict[str, str]) -> str:
    entries = _parse_list(value)
    normalized: set[str] = set()

    for entry in entries:
        key = entry.lower()
        canonical = mapping.get(key)
        if canonical:
            normalized.add(canonical)
        else:
            normalized.add(entry.title())

    if not normalized:
        return ""

    return "|".join(sorted(normalized))


def parse_bool(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "suspended", "active suspension"}


def compute_directory_status(registration_status: Any, deregistration_date: Any, suspension_flag: Any) -> str:
    if parse_bool(suspension_flag):
        return "SUSPENDED"

    status = normalize_whitespace(registration_status).lower()
    dereg = normalize_whitespace(deregistration_date)

    if not status and not dereg:
        return "ACTIVE"

    if "deregister" in status:
        return "INACTIVE"
    if any(token in status for token in ["suspend", "cancel", "inactive", "closed"]):
        return "INACTIVE"

    if "register" in status and not dereg:
        return "ACTIVE"

    if dereg:
        return "INACTIVE"

    return "INACTIVE"


def clean_record(row: dict[str, Any], log_path: Path, issue_counter: Counter[str]) -> dict[str, Any]:
    record = dict(row)

    location_id = normalize_whitespace(record.get("locationId", ""))

    issues: set[str] = set()

    raw_name = record.get("name")
    if is_blank(raw_name):
        raw_name = record.get("location.locationName", "")
    name, name_issue = normalize_name(raw_name)
    if name_issue:
        issues.add(name_issue)
        issue_counter[name_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=name issue={name_issue} value={record.get('name', '')}")

    line1, line1_issue = normalize_address(record.get("postalAddressLine1"))
    line2, _ = normalize_address(record.get("postalAddressLine2"))
    if line1_issue:
        issues.add(line1_issue)
        issue_counter[line1_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=postalAddressLine1 issue={line1_issue}")

    town = normalize_whitespace(record.get("postalAddressTownCity"))
    county = normalize_whitespace(record.get("postalAddressCounty"))

    phone, phone_issue = normalize_phone(record.get("mainPhoneNumber"))
    if phone_issue:
        issues.add(phone_issue)
        issue_counter[phone_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=mainPhoneNumber issue={phone_issue} value={record.get('mainPhoneNumber', '')}")

    postcode, postcode_issue = normalize_postcode(record.get("postalCode"))
    if postcode_issue:
        issues.add(postcode_issue)
        issue_counter[postcode_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=postalCode issue={postcode_issue} value={record.get('postalCode', '')}")

    website, website_issue = normalize_website(record.get("website"))
    if website_issue:
        issues.add(website_issue)
        issue_counter[website_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=website issue={website_issue} value={record.get('website', '')}")

    registration_status = normalize_whitespace(record.get("registrationStatus"))
    overall_rating = normalize_rating(record.get("overallRating"), registration_status)

    reg_date, reg_date_issue = normalize_date(record.get("registrationDate"), "registrationDate")
    if reg_date_issue:
        issues.add(reg_date_issue)
        issue_counter[reg_date_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=registrationDate issue={reg_date_issue} value={record.get('registrationDate', '')}")

    dereg_date, dereg_date_issue = normalize_date(record.get("deregistrationDate"), "deregistrationDate")
    if dereg_date_issue:
        issues.add(dereg_date_issue)
        issue_counter[dereg_date_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=deregistrationDate issue={dereg_date_issue}")

    report_date, report_date_issue = normalize_date(record.get("reportDate"), "reportDate")
    if report_date_issue:
        issues.add(report_date_issue)
        issue_counter[report_date_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=reportDate issue={report_date_issue}")

    inspection_date, inspection_date_issue = normalize_date(record.get("lastInspectionDate"), "lastInspectionDate")
    if inspection_date_issue:
        issues.add(inspection_date_issue)
        issue_counter[inspection_date_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=lastInspectionDate issue={inspection_date_issue}")

    expected_dereg, expected_dereg_issue = normalize_date(
        record.get("expectedDeregistrationDate"), "expectedDeregistrationDate"
    )
    if expected_dereg_issue:
        issues.add(expected_dereg_issue)
        issue_counter[expected_dereg_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=expectedDeregistrationDate issue={expected_dereg_issue}")

    latitude, longitude, coords_issue = normalize_coordinates(record.get("latitude"), record.get("longitude"))
    if coords_issue:
        issues.add(coords_issue)
        issue_counter[coords_issue] += 1
        log_line(log_path, f"VALIDATION_FAILURE id={location_id} field=coords issue={coords_issue}")

    service_types = normalize_taxonomy(record.get("serviceTypes"), SERVICE_TYPE_MAP)
    specialisms = normalize_taxonomy(record.get("specialisms"), SPECIALISM_MAP)
    regulated_activities = normalize_taxonomy(record.get("regulatedActivities"), REGULATED_ACTIVITY_MAP)

    region = normalize_whitespace(record.get("region"))
    local_authority = normalize_whitespace(record.get("localAuthority"))
    ownership = normalize_whitespace(record.get("ownershipType"))

    beds_raw = normalize_whitespace(record.get("numberOfBeds"))
    if beds_raw and beds_raw.isdigit():
        number_of_beds = beds_raw
    elif beds_raw:
        digits = re.sub(r"\D", "", beds_raw)
        number_of_beds = digits if digits else ""
    else:
        number_of_beds = ""

    directory_status = compute_directory_status(registration_status, dereg_date, record.get("suspensionFlag"))

    record.update(
        {
            "name": name,
            "postalAddressLine1": line1,
            "postalAddressLine2": line2,
            "postalAddressTownCity": town,
            "postalAddressCounty": county,
            "postalCode": postcode,
            "mainPhoneNumber": phone,
            "website": website,
            "registrationStatus": registration_status,
            "registrationDate": reg_date,
            "deregistrationDate": dereg_date,
            "expectedDeregistrationDate": expected_dereg,
            "reportDate": report_date,
            "lastInspectionDate": inspection_date,
            "overallRating": overall_rating,
            "latitude": latitude,
            "longitude": longitude,
            "serviceTypes": service_types,
            "specialisms": specialisms,
            "regulatedActivities": regulated_activities,
            "region": region,
            "localAuthority": local_authority,
            "ownershipType": ownership,
            "numberOfBeds": number_of_beds,
            "directoryStatus": directory_status,
            "name_issue": name_issue,
            "postalCode_issue": postcode_issue,
            "mainPhoneNumber_issue": phone_issue,
            "website_issue": website_issue,
            "address_issue": line1_issue,
            "date_issue": "SUSPECT_DATE" if "SUSPECT_DATE" in issues else "",
            "coords_issue": coords_issue,
            "record_issues": "|".join(sorted(issues)),
            "possibleDuplicateNamePostcode": "False",
        }
    )

    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean raw CQC combined CSV")
    parser.add_argument("--input", default=INPUT_RAW_COMBINED, help="Input raw combined CSV")
    parser.add_argument("--output", default=OUTPUT_CLEANED, help="Output cleaned active CSV")
    parser.add_argument("--inactive-output", default=OUTPUT_INACTIVE, help="Output inactive providers CSV")
    parser.add_argument("--duplicates-output", default=OUTPUT_DUPLICATES, help="Output removed duplicates CSV")
    parser.add_argument("--log", default=OUTPUT_LOG, help="Transformation log file")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size for processing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    inactive_path = Path(args.inactive_output).resolve()
    duplicates_path = Path(args.duplicates_output).resolve()
    log_path = Path(args.log).resolve()
    stage_path = output_path.parent / TEMP_STAGE

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    if stage_path.exists():
        stage_path.unlink()

    log_line(log_path, "=== CQC CLEANING START ===")
    issue_counter: Counter[str] = Counter()

    total_processed = 0
    first_write = True

    try:
        for chunk in pd.read_csv(input_path, dtype=str, chunksize=args.chunk_size, keep_default_na=False):
            cleaned_rows = [clean_record(row, log_path, issue_counter) for row in chunk.to_dict(orient="records")]
            cleaned_df = pd.DataFrame(cleaned_rows)
            cleaned_df.to_csv(stage_path, mode="w" if first_write else "a", header=first_write, index=False)
            first_write = False
            total_processed += len(cleaned_rows)

            if total_processed % 1000 == 0:
                log_line(log_path, f"CLEAN_PROGRESS processed={total_processed}")

        if total_processed == 0:
            try:
                raw_header_df = pd.read_csv(input_path, dtype=str, keep_default_na=False, nrows=0)
                base_columns = list(raw_header_df.columns)
            except Exception:
                base_columns = ["providerId", "locationId", "name"]

            appended_columns = [
                "directoryStatus",
                "name_issue",
                "postalCode_issue",
                "mainPhoneNumber_issue",
                "website_issue",
                "address_issue",
                "date_issue",
                "coords_issue",
                "record_issues",
                "possibleDuplicateNamePostcode",
            ]
            output_columns = base_columns + [c for c in appended_columns if c not in base_columns]

            pd.DataFrame(columns=output_columns).to_csv(output_path, index=False)
            pd.DataFrame(columns=output_columns).to_csv(inactive_path, index=False)
            pd.DataFrame(columns=output_columns + ["duplicateReason"]).to_csv(duplicates_path, index=False)
            if stage_path.exists():
                stage_path.unlink()
            print("No rows found in raw input; wrote empty outputs.")
            return 0

        df = pd.read_csv(stage_path, dtype=str, keep_default_na=False)

        if "locationId" not in df.columns:
            df["locationId"] = ""

        df["_lastInspectionParsed"] = pd.to_datetime(df.get("lastInspectionDate", ""), errors="coerce")
        df_sorted = df.sort_values(by=["locationId", "_lastInspectionParsed"], ascending=[True, False], na_position="last")

        dup_mask = df_sorted.duplicated(subset=["locationId"], keep="first")
        duplicates_removed = df_sorted[dup_mask].copy()
        duplicates_removed["duplicateReason"] = "DUPLICATE_LOCATION_ID"

        deduped = df_sorted[~dup_mask].copy()

        deduped["_dup_name"] = deduped["name"].fillna("").str.strip().str.lower()
        deduped["_dup_postcode"] = deduped["postalCode"].fillna("").str.strip().str.upper()

        dup_group_counts = deduped.groupby(["_dup_name", "_dup_postcode"])["locationId"].transform("count")
        secondary_mask = (
            deduped["_dup_name"].ne("")
            & deduped["_dup_postcode"].ne("")
            & dup_group_counts.gt(1)
        )
        deduped.loc[secondary_mask, "possibleDuplicateNamePostcode"] = "True"

        active_mask = deduped["directoryStatus"].eq("ACTIVE")
        active_df = deduped[active_mask].copy()
        inactive_df = deduped[~active_mask].copy()

        for frame in (active_df, inactive_df, duplicates_removed):
            for col in ["_lastInspectionParsed", "_dup_name", "_dup_postcode"]:
                if col in frame.columns:
                    frame.drop(columns=[col], inplace=True)

        active_df.sort_values(by=["locationId"], inplace=True)
        inactive_df.sort_values(by=["locationId"], inplace=True)
        duplicates_removed.sort_values(by=["locationId"], inplace=True)

        active_df.to_csv(output_path, index=False)
        inactive_df.to_csv(inactive_path, index=False)
        duplicates_removed.to_csv(duplicates_path, index=False)

        if stage_path.exists():
            stage_path.unlink()

        issue_summary = ", ".join([f"{k}={v}" for k, v in sorted(issue_counter.items())])
        log_line(
            log_path,
            f"CLEAN_COMPLETE processed={total_processed} active={len(active_df)} inactive={len(inactive_df)} "
            f"duplicates_removed={len(duplicates_removed)} issues={issue_summary}",
        )

        print("CQC cleaning complete")
        print(f"Total records processed: {total_processed}")
        print(f"ACTIVE records: {len(active_df)}")
        print(f"INACTIVE/SUSPENDED records: {len(inactive_df)}")
        print(f"Duplicates removed: {len(duplicates_removed)}")

    except Exception as exc:
        log_line(log_path, f"CLEAN_FATAL_ERROR {type(exc).__name__}: {exc}")
        print(f"Cleaning failed: {type(exc).__name__}: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
