#!/usr/bin/env python3
"""Seed the PostgreSQL database from directory_providers.csv using COPY."""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

import psycopg2

DEFAULT_CSV = "directory_providers.csv"

# Columns in the CSV that map to DB columns (order matters for COPY)
CSV_TO_DB = [
    ("id", "id"),
    ("provider_id", "provider_id"),
    ("name", "name"),
    ("slug", "slug"),
    ("type", "type"),
    ("status", "status"),
    ("registration_date", "registration_date"),
    ("address_line1", "address_line1"),
    ("address_line2", "address_line2"),
    ("town", "town"),
    ("county", "county"),
    ("postcode", "postcode"),
    ("region", "region"),
    ("local_authority", "local_authority"),
    ("country", "country"),
    ("latitude", "latitude"),
    ("longitude", "longitude"),
    ("phone", "phone"),
    ("website", "website"),
    ("email", "email"),
    ("overall_rating", "overall_rating"),
    ("rating_safe", "rating_safe"),
    ("rating_effective", "rating_effective"),
    ("rating_caring", "rating_caring"),
    ("rating_responsive", "rating_responsive"),
    ("rating_well_led", "rating_well_led"),
    ("last_inspection_date", "last_inspection_date"),
    ("inspection_report_url", "inspection_report_url"),
    ("service_types", "service_types"),
    ("specialisms", "specialisms"),
    ("regulated_activities", "regulated_activities"),
    ("number_of_beds", "number_of_beds"),
    ("ownership_type", "ownership_type"),
    ("quality_score", "quality_score"),
    ("quality_tier", "quality_tier"),
    ("meta_title", "meta_title"),
    ("meta_description", "meta_description"),
    ("geocode_source", "geocode_source"),
    ("last_updated", "last_updated"),
    ("data_source", "data_source"),
    ("data_attribution", "data_attribution"),
]

DB_COLUMNS = [db_col for _, db_col in CSV_TO_DB]
CSV_COLUMNS = [csv_col for csv_col, _ in CSV_TO_DB]


def clean_value(val: str) -> str:
    """Convert empty strings to \\N (NULL) for COPY format."""
    val = val.strip()
    if not val or val.upper() == "NULL":
        return "\\N"
    # Escape tabs, newlines, backslashes for COPY format
    return val.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "")


def seed(database_url: str, csv_path: Path, truncate: bool = False) -> int:
    """Load CSV into care_providers table via COPY."""
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        if truncate:
            cur.execute("TRUNCATE TABLE care_providers RESTART IDENTITY;")
            print("Truncated care_providers table")

        # Build tab-separated data for COPY
        buf = io.StringIO()
        row_count = 0

        with csv_path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                values = [clean_value(row.get(csv_col, "")) for csv_col in CSV_COLUMNS]
                buf.write("\t".join(values) + "\n")
                row_count += 1

        buf.seek(0)

        cols_str = ", ".join(DB_COLUMNS)
        cur.copy_expert(
            f"COPY care_providers ({cols_str}) FROM STDIN WITH (FORMAT text, NULL '\\N')",
            buf,
        )

        # Populate geometry column from lat/lon
        cur.execute("""
            UPDATE care_providers
            SET geom = ST_SetSRID(ST_MakePoint(longitude::float, latitude::float), 4326)
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL;
        """)
        geo_count = cur.rowcount

        conn.commit()
        print(f"Loaded {row_count} records into care_providers")
        print(f"Populated geometry for {geo_count} records")
        return row_count

    except Exception as exc:
        conn.rollback()
        print(f"Seed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        cur.close()
        conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed CareGist database from CSV")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to directory_providers.csv")
    parser.add_argument("--database-url", default=None, help="PostgreSQL connection URL")
    parser.add_argument("--truncate", action="store_true", help="Truncate table before loading")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        # Try loading from .env
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    database_url = line.split("=", 1)[1].strip()
    if not database_url:
        print("ERROR: DATABASE_URL not set. Pass --database-url or set in .env", file=sys.stderr)
        return 1

    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    seed(database_url, csv_path, truncate=args.truncate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
