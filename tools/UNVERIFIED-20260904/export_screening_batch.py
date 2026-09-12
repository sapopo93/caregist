#!/usr/bin/env python3
"""Export the smallest possible batch of numbers for TPS/CTPS bulk screening.

Why this exists
---------------
There are two ways to screen a number against TPS/CTPS in this codebase, and
only one of them is affordable at our volume.

The expensive path is `api/services/crm_tps_automation.py`: a paid per-lookup
TPSCheck API, gated behind both a tenant row and `CRM_TPS_AUTOMATION_ENABLED`.
It also seeds candidates from the new-registration feed only
(`event.event_type = 'new_registration'`, line 193), so it structurally cannot
screen an existing-provider cohort such as the inspection target list.

The cheap path is already built and unused: `POST /api/v1/crm/phone-screenings/import`
(`api/routers/crm_extended.py:297`) accepts a bulk screening result file from a
`tps_ctps_licence` or `approved_provider` source. It writes
`crm_phone_screening_cache` (UNIQUE on organization_id + phone_hmac, so a
number is never paid for twice), raises a `crm_phone_screening_events` audit
row per contact, updates `crm_contacts.phone_screening_status`, and adds every
`tps`/`ctps`/`invalid` number to `crm_suppressions` for the call channel.

At reseller rates of roughly £10 per 1,000 numbers across both registers,
screening the whole 2,254-number inspection cohort is a one-off cost of about
£23. The licence route (~£3,300/yr) and flat unlimited subscriptions
(~£150-200/mo) are not worth buying until call volume is far higher.

This tool emits only the numbers that actually need paying for: distinct
E.164 numbers, excluding anything screened within the TPS 28-day window, and
excluding numbers already carrying a manual consent override.

Usage:
    python3 tools/export_screening_batch.py --organization-id <uuid>
    python3 tools/export_screening_batch.py --organization-id <uuid> --limit 300
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "outreach"

# TPS/CTPS screening is only valid for 28 days; anything older must be re-screened
# before the number may be called again.
SCREENING_VALID_DAYS = 28

NEEDS_SCREENING = """
SELECT DISTINCT ON (c.phone_e164)
       c.phone_e164,
       c.company_name,
       c.phone_screening_status,
       c.phone_screened_at
FROM crm_contacts c
WHERE c.organization_id = $1
  AND c.phone_e164 IS NOT NULL
  AND c.phone_e164 <> ''
  -- A number the operator has explicit consent for is never re-screened.
  AND c.phone_screening_status <> 'consent_override'
  AND (
        c.phone_screened_at IS NULL
     OR c.phone_screened_at < NOW() - ($2 || ' days')::interval
  )
  -- Never pay for a number that already has a valid screen recorded against
  -- any contact in this organization.
  AND NOT EXISTS (
        SELECT 1 FROM crm_phone_screening_events e
        WHERE e.organization_id = c.organization_id
          AND e.phone_e164 = c.phone_e164
          AND e.screened_at >= NOW() - ($2 || ' days')::interval
  )
ORDER BY c.phone_e164, c.created_at
"""


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


def resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or load_env(REPO_ROOT / ".env").get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set and .env does not define it.")
    return re.sub(r"\?.*$", "", url)


async def run(args: argparse.Namespace) -> int:
    conn = await asyncpg.connect(resolve_database_url(), ssl="require")
    try:
        rows = await conn.fetch(NEEDS_SCREENING, args.organization_id, str(SCREENING_VALID_DAYS))
        total_contacts = await conn.fetchval(
            "SELECT COUNT(*) FROM crm_contacts WHERE organization_id = $1 "
            "AND phone_e164 IS NOT NULL AND phone_e164 <> ''",
            args.organization_id,
        )
        already_valid = await conn.fetchval(
            "SELECT COUNT(DISTINCT phone_e164) FROM crm_phone_screening_events "
            "WHERE organization_id = $1 AND screened_at >= NOW() - ($2 || ' days')::interval",
            args.organization_id, str(SCREENING_VALID_DAYS),
        )

        selected = rows[: args.limit] if args.limit else rows
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"screening_batch_{stamp}.csv"

        with out_path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["phone_e164"])
            for row in selected:
                writer.writerow([row["phone_e164"]])

        cost_low = len(selected) * 0.005   # single register, volume rate
        cost_high = len(selected) * 0.010  # both registers
        print(f"Contacts with a number in this organization: {total_contacts}")
        print(f"Numbers already carrying a valid screen (<{SCREENING_VALID_DAYS}d): {already_valid}")
        print(f"Distinct numbers needing a paid screen: {len(rows)}")
        print(f"Exported: {len(selected)} -> {out_path}")
        print(f"Indicative one-off cost at reseller rates: £{cost_low:.2f}-£{cost_high:.2f}")
        print()
        print("Next: submit that single column to a TPS/CTPS bulk screening bureau, then")
        print("import the returned file (columns phone_e164,status,screened_at) with:")
        print("  python3 tools/import_screening_results.py --organization-id "
              f"{args.organization_id} --user-id <id> \\")
        print("      --source approved_provider --reference '<bureau + order ref>' \\")
        print("      --file <returned.csv>")
        return 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 exports everything that needs screening.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
