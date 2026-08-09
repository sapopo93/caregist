#!/usr/bin/env python3
"""Build an immutable CQC CSV from Postgres and publish it to private Vercel Blob."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import asyncpg
from vercel.blob import AsyncBlobClient


OGL_ATTRIBUTION = "Contains public sector information licensed under the Open Government Licence v3.0"
OGL_URL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
COLUMNS = (
    "cqc_location_id", "cqc_provider_id", "name", "slug", "type", "status",
    "registration_date", "address_line1", "address_line2", "town", "county",
    "postcode", "region", "local_authority", "country", "latitude", "longitude",
    "phone", "website", "email", "overall_rating", "rating_safe", "rating_effective",
    "rating_caring", "rating_responsive", "rating_well_led", "last_inspection_date",
    "inspection_report_url", "service_types", "specialisms", "regulated_activities",
    "number_of_beds", "ownership_type", "data_completeness_score",
    "data_completeness_tier", "last_updated", "source_attribution",
)


def _safe_cell(value: object) -> object:
    if value is None:
        return ""
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    return f"'{text}" if text.lstrip().startswith(("=", "+", "-", "@")) else text


async def _file_chunks(path: Path, chunk_size: int = 8 * 1024 * 1024) -> AsyncIterator[bytes]:
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            yield chunk


async def publish(database_url: str, blob_token: str) -> None:
    conn = await asyncpg.connect(database_url)
    temp_path: Path | None = None
    try:
        artifacts_table = await conn.fetchval("SELECT to_regclass('public.full_dataset_artifacts')")
        if not artifacts_table:
            raise RuntimeError("Migration 048 must be applied before publishing a dataset")
        summary = await conn.fetchrow(
            """
            SELECT COUNT(*)::int AS record_count, MAX(last_updated) AS source_watermark
            FROM care_providers WHERE status = 'ACTIVE'
            """
        )
        if not summary or not summary["record_count"] or not summary["source_watermark"]:
            raise RuntimeError("Active provider data has no records or source watermark; refusing to publish")

        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", suffix=".csv", delete=False) as output:
            temp_path = Path(output.name)
            output.write(f"# {OGL_ATTRIBUTION} — {OGL_URL}\n")
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(COLUMNS)
            query = """
                SELECT id, provider_id, name, slug, type, status, registration_date,
                  address_line1, address_line2, town, county, postcode, region,
                  local_authority, country, latitude, longitude, phone, website, email,
                  overall_rating, rating_safe, rating_effective, rating_caring,
                  rating_responsive, rating_well_led, last_inspection_date,
                  inspection_report_url, service_types, specialisms, regulated_activities,
                  number_of_beds, ownership_type, data_completeness_score,
                  data_completeness_tier, last_updated
                FROM care_providers WHERE status = 'ACTIVE' ORDER BY id
            """
            async with conn.transaction():
                async for row in conn.cursor(query, prefetch=1000):
                    writer.writerow([*(_safe_cell(value) for value in row), OGL_ATTRIBUTION])

        digest = hashlib.sha256()
        with temp_path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        sha256 = digest.hexdigest()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        pathname = f"full-datasets/caregist-cqc-{timestamp}-{sha256[:12]}.csv"
        client = AsyncBlobClient(token=blob_token)
        await client.put(
            pathname,
            _file_chunks(temp_path),
            access="private",
            content_type="text/csv; charset=utf-8",
            multipart=True,
            add_random_suffix=False,
            overwrite=False,
        )

        async with conn.transaction():
            await conn.execute("UPDATE full_dataset_artifacts SET is_active = FALSE WHERE is_active")
            await conn.execute(
                """
                INSERT INTO full_dataset_artifacts (
                  blob_pathname, record_count, sha256, source_watermark,
                  ogl_attribution, is_active
                ) VALUES ($1, $2, $3, $4, $5, TRUE)
                """,
                pathname,
                summary["record_count"],
                sha256,
                summary["source_watermark"],
                OGL_ATTRIBUTION,
            )
        print(f"published {summary['record_count']:,} records: {pathname} sha256={sha256}")
    finally:
        await conn.close()
        if temp_path:
            temp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--blob-token", default=os.getenv("BLOB_READ_WRITE_TOKEN"))
    args = parser.parse_args()
    if not args.database_url or not args.blob_token:
        parser.error("DATABASE_URL and BLOB_READ_WRITE_TOKEN are required")
    asyncio.run(publish(args.database_url, args.blob_token))


if __name__ == "__main__":
    main()
