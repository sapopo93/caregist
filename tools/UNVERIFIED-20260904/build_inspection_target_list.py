#!/usr/bin/env python3
"""Build the outbound target list for the paid CQC inspection-readiness offer.

Source of truth is the production `care_providers` table (CQC public directory).
The ICP is an ACTIVE registered location whose published overall rating is
"Requires improvement" or "Inadequate": that provider has a dated, public,
commercially expensive problem and a re-inspection ahead of it.

The CQC directory carries no email addresses, so telephone is the only usable
channel. Rows are therefore loaded into the CRM with
`phone_screening_status = 'unknown'` so the existing CTPS/TPS screening
automation must clear each number before it may be dialled. Nothing here marks
a number as callable.

Usage:
    python3 tools/build_inspection_target_list.py --limit 250
    python3 tools/build_inspection_target_list.py --limit 250 --load-crm \
        --organization-id <uuid> --owner-user-id 1
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "outreach"

# Priority order drives call-list sequencing: worst rating first, then the
# service types that carry the highest contract value and the sharpest
# regulatory exposure.
SERVICE_WEIGHTS = {
    "Care home service with nursing": 40,
    "Care home service without nursing": 30,
    "Domiciliary care service": 20,
    "Supported living service": 15,
}

SELECT_TARGETS = """
SELECT
    id,
    provider_id,
    name,
    slug,
    overall_rating,
    rating_safe,
    rating_well_led,
    split_part(service_types, '|', 1) AS primary_service,
    number_of_beds,
    town,
    county,
    region,
    postcode,
    local_authority,
    phone,
    website,
    group_name,
    inspection_report_url
FROM care_providers
WHERE status = 'ACTIVE'
  AND overall_rating IN ('Requires improvement', 'Inadequate')
  AND COALESCE(phone, '') <> ''
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


def to_e164(raw: str | None) -> str | None:
    """Normalise a UK directory number to E.164, or None when it is unusable."""
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", raw)
    if digits.startswith("+"):
        return digits if 11 <= len(digits) <= 15 else None
    if digits.startswith("00"):
        digits = "+" + digits[2:]
        return digits if 11 <= len(digits) <= 15 else None
    if digits.startswith("0") and len(digits) == 11:
        return "+44" + digits[1:]
    if len(digits) == 10 and not digits.startswith("0"):
        return "+44" + digits
    return None


def score(row: asyncpg.Record) -> int:
    """Higher is a better first call."""
    value = 100 if row["overall_rating"] == "Inadequate" else 50
    value += SERVICE_WEIGHTS.get(row["primary_service"] or "", 5)
    beds = row["number_of_beds"] or 0
    value += min(int(beds), 120) // 10
    if row["rating_well_led"] in ("Requires improvement", "Inadequate"):
        value += 8  # leadership findings are what a mock inspection actually fixes
    if row["rating_safe"] in ("Requires improvement", "Inadequate"):
        value += 8
    if row["website"]:
        value += 5
    if row["group_name"]:
        value += 5  # a group win is repeatable across its other locations
    return value


async def build(args: argparse.Namespace) -> int:
    conn = await asyncpg.connect(resolve_database_url(), ssl="require")
    try:
        rows = await conn.fetch(SELECT_TARGETS)
        ranked = []
        skipped_unusable_phone = 0
        for row in rows:
            phone = to_e164(row["phone"])
            if not phone:
                skipped_unusable_phone += 1
                continue
            ranked.append((score(row), phone, row))
        ranked.sort(key=lambda item: (-item[0], item[2]["name"]))
        selected = ranked[: args.limit]

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"inspection_targets_{stamp}.csv"
        with out_path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "rank", "score", "location_id", "provider_id", "name", "overall_rating",
                "rating_safe", "rating_well_led", "primary_service", "beds", "town",
                "county", "region", "postcode", "local_authority", "phone_e164",
                "website", "group_name", "cqc_report_url", "caregist_profile",
            ])
            for index, (value, phone, row) in enumerate(selected, start=1):
                writer.writerow([
                    index, value, row["id"], row["provider_id"], row["name"],
                    row["overall_rating"], row["rating_safe"], row["rating_well_led"],
                    row["primary_service"], row["number_of_beds"], row["town"],
                    row["county"], row["region"], row["postcode"], row["local_authority"],
                    phone, row["website"], row["group_name"], row["inspection_report_url"],
                    f"https://www.caregist.co.uk/provider/{row['slug']}" if row["slug"] else "",
                ])

        print(f"Eligible ACTIVE RI/Inadequate locations with a phone number: {len(rows)}")
        print(f"Dropped for an unparseable number: {skipped_unusable_phone}")
        print(f"Wrote {len(selected)} ranked targets to {out_path}")
        if selected:
            print("Top 5:")
            for index, (value, phone, row) in enumerate(selected[:5], start=1):
                print(f"  {index}. [{value}] {row['name']} — {row['overall_rating']} — "
                      f"{row['primary_service']} — {row['town']} — {phone}")

        if not args.load_crm:
            print("\nCRM load skipped (pass --load-crm to write the pipeline).")
            return 0
        if not args.organization_id or not args.owner_user_id:
            raise SystemExit("--load-crm requires --organization-id and --owner-user-id.")

        inserted_contacts = 0
        inserted_deals = 0
        skipped_existing = 0
        async with conn.transaction():
            for value, phone, row in selected:
                existing = await conn.fetchval(
                    "SELECT id FROM crm_contacts WHERE organization_id = $1 AND phone_e164 = $2",
                    args.organization_id, phone,
                )
                if existing:
                    skipped_existing += 1
                    continue
                # Provider names repeat across the CQC register ("The Limes" appears many
                # times), and crm_companies is unique on (organization_id, lower(name)).
                # Disambiguate with the town so distinct locations stay distinct rows.
                company_name = row["name"]
                if row["town"]:
                    company_name = f"{row['name']} ({row['town']})"
                company_id = await conn.fetchval(
                    """
                    INSERT INTO crm_companies (organization_id, name, website, phone_e164, address,
                                               notes, owner_user_id, created_by_user_id)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$7)
                    ON CONFLICT (organization_id, lower(name)) DO UPDATE
                       SET updated_at = NOW()
                    RETURNING id
                    """,
                    args.organization_id, company_name, row["website"], phone,
                    ", ".join(p for p in [row["town"], row["county"], row["postcode"]] if p),
                    (f"CQC overall rating: {row['overall_rating']}. "
                     f"Safe: {row['rating_safe'] or 'n/a'}. Well-led: {row['rating_well_led'] or 'n/a'}. "
                     f"Service: {row['primary_service']}. Beds: {row['number_of_beds'] or 'n/a'}. "
                     f"CQC report: {row['inspection_report_url'] or 'n/a'}. "
                     f"Target score {value}."),
                    args.owner_user_id,
                )
                contact_id = await conn.fetchval(
                    """
                    INSERT INTO crm_contacts (organization_id, provider_id, owner_user_id,
                        created_by_user_id, first_name, last_name, job_title, company_name,
                        phone_e164, lifecycle_stage, market_code, subscriber_type,
                        phone_screening_status)
                    VALUES ($1,$2,$3,$3,$4,$5,$6,$7,$8,'new','GB','unknown','unknown')
                    RETURNING id
                    """,
                    args.organization_id, row["id"], args.owner_user_id,
                    "Registered", "Manager", "Registered Manager", row["name"], phone,
                )
                inserted_contacts += 1
                await conn.execute(
                    """
                    INSERT INTO crm_deals (organization_id, contact_id, owner_user_id, title,
                                           stage, value_pence)
                    VALUES ($1,$2,$3,$4,'new',$5)
                    """,
                    args.organization_id, contact_id, args.owner_user_id,
                    f"Inspection readiness review — {row['name']}", args.deal_value_pence,
                )
                inserted_deals += 1
                await conn.execute(
                    """
                    INSERT INTO crm_activities (organization_id, contact_id, actor_user_id,
                                                activity_type, body, metadata)
                    VALUES ($1,$2,$3,'note',$4,$5::jsonb)
                    """,
                    args.organization_id, contact_id, args.owner_user_id,
                    (f"Sourced from CQC public directory. Overall rating "
                     f"{row['overall_rating']} at {row['town'] or 'unknown town'}. "
                     "Number requires CTPS screening before any call."),
                    ('{"source":"cqc_public_directory","campaign":"inspection_readiness",'
                     f'"target_score":{value}}}'),
                )
            _ = company_id  # company rows are written for reporting; contact carries the pipeline

        print(f"\nCRM load complete: {inserted_contacts} contacts, {inserted_deals} deals, "
              f"{skipped_existing} skipped as already present.")
        print("All contacts are phone_screening_status='unknown' — CTPS screening must clear "
              "each number before it is dialled.")
        return 0
    finally:
        await conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--load-crm", action="store_true")
    parser.add_argument("--organization-id")
    parser.add_argument("--owner-user-id", type=int)
    parser.add_argument("--deal-value-pence", type=int, default=95000)
    return asyncio.run(build(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
