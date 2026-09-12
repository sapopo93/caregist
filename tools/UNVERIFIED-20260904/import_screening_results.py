#!/usr/bin/env python3
"""Import a TPS/CTPS bulk screening result file, offline, with full audit evidence.

Companion to `tools/export_screening_batch.py`. Mirrors
`POST /api/v1/crm/phone-screenings/import` (`api/routers/crm_extended.py:297`)
so a screening file can be applied from the CLI without a browser session,
writing exactly the same records:

  * `crm_phone_screening_imports` - the file, its SHA-256, and the counts.
  * `crm_phone_screening_cache`   - keyed HMAC per number, so a number that has
                                    been paid for is never paid for again.
  * `crm_phone_screening_events`  - a per-contact audit row naming the source.
  * `crm_contacts`                - the resulting screening status.
  * `crm_suppressions`            - every tps/ctps/invalid number blocked for
                                    the call channel; a `clear` result lifts a
                                    previous block.

Input CSV columns: phone_e164,status,screened_at
  status:      clear | tps | ctps | invalid
  screened_at: ISO-8601, not in the future

Requires CRM_SCREENING_HASH_KEY (>= 32 chars), the same value production uses,
so cache entries written here are readable by the running application.

Usage:
    python3 tools/import_screening_results.py --organization-id <uuid> --user-id 12 \
        --source approved_provider --reference 'Bureau X order 1234' --file results.csv
    # add --dry-run to validate the file and report the effect without writing
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]
E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
VALID_STATUS = {"clear", "tps", "ctps", "invalid"}
SUPPRESSING = {"tps", "ctps", "invalid"}


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")
    return values


ENV = load_env(REPO_ROOT / ".env")


def resolve(name: str) -> str | None:
    return os.environ.get(name) or ENV.get(name)


def hash_screening_number(phone_e164: str, key: str) -> str:
    """Identical to api/services/crm_calling.py:51 so both sides agree on the digest."""
    if len(key) < 32:
        raise SystemExit("CRM_SCREENING_HASH_KEY is missing or shorter than 32 characters. "
                         "It must match the value production uses, or the cache this writes "
                         "will be unreadable by the application.")
    if not E164.fullmatch(phone_e164):
        raise ValueError("Screening number must use E.164 format.")
    return hmac.new(key.encode("utf-8"), phone_e164.encode("utf-8"), hashlib.sha256).hexdigest()


def parse_file(path: Path) -> tuple[dict[str, tuple[str, datetime, int]], str]:
    raw = path.read_bytes()
    records: dict[str, tuple[str, datetime, int]] = {}
    reader = csv.DictReader(raw.decode("utf-8-sig").splitlines())
    for row_number, row in enumerate(reader, start=2):
        phone = (row.get("phone_e164") or "").strip()
        if not E164.fullmatch(phone):
            raise SystemExit(f"Row {row_number}: '{phone}' is not a valid E.164 number.")
        status = (row.get("status") or "").strip().lower()
        if status not in VALID_STATUS:
            raise SystemExit(f"Row {row_number}: status '{status}' is not one of {sorted(VALID_STATUS)}.")
        stamp = (row.get("screened_at") or "").strip().replace("Z", "+00:00")
        try:
            screened_at = datetime.fromisoformat(stamp)
        except ValueError:
            raise SystemExit(f"Row {row_number}: screened_at '{stamp}' is not ISO-8601.")
        if not screened_at.tzinfo:
            screened_at = screened_at.replace(tzinfo=timezone.utc)
        screened_at = screened_at.astimezone(timezone.utc)
        if screened_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise SystemExit(f"Row {row_number}: screened_at is in the future.")
        if phone in records:
            raise SystemExit(f"Row {row_number}: duplicate number {phone}.")
        records[phone] = (status, screened_at, row_number)
    if not records:
        raise SystemExit("The screening file has no data rows.")
    return records, hashlib.sha256(raw).hexdigest()


async def run(args: argparse.Namespace) -> int:
    path = Path(args.file)
    records, file_hash = parse_file(path)
    key = resolve("CRM_SCREENING_HASH_KEY") or ""
    # Validate the key before opening a transaction so a misconfiguration cannot
    # leave a half-applied import behind.
    hash_screening_number(next(iter(records)), key)

    database_url = resolve("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set.")
    conn = await asyncpg.connect(re.sub(r"\?.*$", "", database_url), ssl="require")
    try:
        by_status: dict[str, int] = {}
        for status, _stamp, _row in records.values():
            by_status[status] = by_status.get(status, 0) + 1
        contacts = await conn.fetch(
            "SELECT id, phone_e164, phone_screening_status, phone_screened_at FROM crm_contacts "
            "WHERE organization_id = $1 AND phone_e164 = ANY($2::text[])",
            args.organization_id, list(records),
        )
        print(f"File {path.name}  sha256={file_hash[:16]}...")
        print(f"Rows: {len(records)}  {by_status}")
        print(f"Matching contacts in this organization: {len(contacts)}")
        if args.dry_run:
            print("\n--dry-run: nothing written.")
            return 0

        clear_count = suppressed_count = 0
        async with conn.transaction():
            import_id = await conn.fetchval(
                """
                INSERT INTO crm_phone_screening_imports (
                  organization_id, imported_by_user_id, source, source_reference,
                  file_name, file_sha256, row_count, matched_count, clear_count, suppressed_count
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,0,0)
                RETURNING id
                """,
                args.organization_id, args.user_id, args.source, args.reference,
                path.name, file_hash, len(records), len(contacts),
            )
            await conn.executemany(
                """
                INSERT INTO crm_phone_screening_cache (
                  organization_id, import_id, phone_hmac, status, source, source_reference, screened_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (organization_id, phone_hmac) DO UPDATE SET
                  import_id = EXCLUDED.import_id, status = EXCLUDED.status,
                  source = EXCLUDED.source, source_reference = EXCLUDED.source_reference,
                  screened_at = EXCLUDED.screened_at, updated_at = NOW()
                WHERE EXCLUDED.screened_at >= crm_phone_screening_cache.screened_at
                """,
                [
                    (args.organization_id, import_id, hash_screening_number(phone, key),
                     status, args.source, args.reference, screened_at)
                    for phone, (status, screened_at, _row) in records.items()
                    # 'invalid' describes the number, not the register, so it is not cached
                    # as a register result.
                    if status != "invalid"
                ],
            )
            for contact in contacts:
                status, screened_at, row_number = records[contact["phone_e164"]]
                # A number the operator holds explicit consent for is never downgraded
                # by a register file, and an older file never overwrites a newer screen.
                if contact["phone_screening_status"] == "consent_override":
                    continue
                if contact["phone_screened_at"] and screened_at < contact["phone_screened_at"]:
                    continue
                evidence = {"source": args.source, "reference": args.reference,
                            "file_sha256": file_hash, "row": str(row_number)}
                event_id = await conn.fetchval(
                    """
                    INSERT INTO crm_phone_screening_events (
                      organization_id, contact_id, screened_by_user_id, import_id,
                      phone_e164, status, source, source_reference, screened_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id
                    """,
                    args.organization_id, contact["id"], args.user_id, import_id,
                    contact["phone_e164"], status, args.source, args.reference, screened_at,
                )
                await conn.execute(
                    "UPDATE crm_contacts SET phone_screening_status = $2, "
                    "phone_screening_evidence = $3::jsonb, phone_screened_at = $4, updated_at = NOW() "
                    "WHERE id = $1",
                    contact["id"], status, json.dumps(evidence), screened_at,
                )
                if status in SUPPRESSING:
                    suppressed_count += 1
                    await conn.execute(
                        """
                        INSERT INTO crm_suppressions (
                          organization_id, phone_e164, channel, reason, evidence, created_by_user_id
                        ) VALUES ($1,$2,'call',$3,$4::jsonb,$5)
                        ON CONFLICT (organization_id, phone_e164, channel) WHERE phone_e164 IS NOT NULL
                        DO UPDATE SET reason = EXCLUDED.reason, evidence = EXCLUDED.evidence
                        """,
                        args.organization_id, contact["phone_e164"], status,
                        json.dumps({**evidence, "screening_event_id": str(event_id)}), args.user_id,
                    )
                else:
                    clear_count += 1
                    await conn.execute(
                        "DELETE FROM crm_suppressions WHERE organization_id = $1 AND phone_e164 = $2 "
                        "AND channel = 'call' AND reason IN ('tps','ctps','invalid')",
                        args.organization_id, contact["phone_e164"],
                    )
            await conn.execute(
                "UPDATE crm_phone_screening_imports SET clear_count = $2, suppressed_count = $3 WHERE id = $1",
                import_id, clear_count, suppressed_count,
            )

        print(f"\nImport {import_id} applied.")
        print(f"  callable (clear): {clear_count}")
        print(f"  suppressed:       {suppressed_count}")
        callable_now = await conn.fetchval(
            "SELECT COUNT(*) FROM crm_contacts WHERE organization_id = $1 "
            "AND phone_screening_status = 'clear'", args.organization_id)
        print(f"  contacts now marked clear in this organization: {callable_now}")
        return 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--source", required=True, choices=("tps_ctps_licence", "approved_provider"))
    parser.add_argument("--reference", required=True, help="Bureau name and order reference.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
