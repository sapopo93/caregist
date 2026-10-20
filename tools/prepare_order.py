"""Prepare a CareGist order for checking and sending.

One command per step of the human-led sale (Business Terms v2.2):

  brief  quote    scope agreed by email -> build the Brief, check it, draft the
                  scope-confirmation email with the GBP 745 payment link
  brief  deliver  payment received      -> rebuild/check, draft the delivery
                  email with the PDF, CSV and source manifest attached
  digest quote    region and start agreed -> draft confirmation with the GBP 150 link
  digest deliver  each week             -> build issue N, draft the delivery email

The Brief is built from exactly the locations the buyer's coverage check
counted: the same directory query the website runs (status, region, service
aliases, provider group), read-only against production, with CQC evidence from
the local API export (extract_cqc.py). Checks run before any email is drafted;
a failed check stops with the reason and drafts nothing.

Drafts are saved to the outreach@caregist.co.uk Drafts folder over IMAP when
OUTREACH_IMAP_PASSWORD is set in .env (host mail.privateemail.com). Nothing is
ever sent: open the draft in Private Email, review it and press Send. Without
the password, the .eml file in the order folder can be opened instead.

Examples:
  .venv/bin/python -m tools.prepare_order brief quote --region "North West" \\
      --provider-group new_90 --buyer-email buyer@example.com --buyer-name "Sam" \\
      --company "Example Ltd"
  .venv/bin/python -m tools.prepare_order brief deliver --order-ref TOB-... ...
"""

from __future__ import annotations

import argparse
import asyncio
import imaplib
import json
import os
import re
import ssl
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_TAXONOMY = REPO_ROOT / "frontend" / "data" / "service-taxonomy.json"

FROM_ADDRESS = "outreach@caregist.co.uk"
FROM_NAME = "CareGist"
BRIEF_PAYMENT_LINK = "https://buy.stripe.com/bJe8wI7Xhd8YdYi2vl3AY04"
DIGEST_PAYMENT_LINK = "https://buy.stripe.com/3cI8wIfpJ4Csg6qfi73AY01"
TERMS_URL = "https://www.caregist.co.uk/terms"
BRIEF_PRICE = "£745 fixed fee. No VAT added."
DIGEST_PRICE = "£150 for four weekly digests. No VAT added. No automatic renewal."
SOURCE_MAX_AGE_DAYS = 8          # the documented source-freshness promise
MIN_SHORTLIST = 25               # the pricing page promises 25-50 organisations
DELIVERY_WORKING_DAYS = 3

REGIONS = (
    "East", "East Midlands", "London", "North East", "North West",
    "South East", "South West", "West Midlands", "Yorkshire & Humberside",
)

# Copied verbatim from frontend/lib/directory-query-clauses.ts so the Brief covers
# exactly what the coverage check counted. tests/test_prepare_order.py fails if
# the two ever drift apart.
OPPORTUNITY_SQL = {
    "new_90": "registration_date >= CURRENT_DATE - INTERVAL '90 days'",
    "inadequate": "overall_rating = 'Inadequate'",
    "requires_improvement": "lower(btrim(overall_rating)) = 'requires improvement'",
    "not_yet_inspected": "lower(btrim(coalesce(overall_rating, ''))) IN ('', 'not yet inspected', 'no published rating')",
    "stale_inspection": "(last_inspection_date IS NULL OR last_inspection_date < CURRENT_DATE - INTERVAL '3 years')",
}

SIGNATURE = """
--
CareGist
01202 023109
outreach@caregist.co.uk
www.caregist.co.uk

CareGist is a trading name of H-Kay Limited. Registered office: C/O Bilberry Accountants Ltd, Castle Court, 41 London Road, Reigate, England, RH2 9RJ.
"""


class CheckFailed(RuntimeError):
    """A pre-send check failed; nothing is drafted."""


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


def service_aliases(value: str | None) -> list[str]:
    """Mirror resolveServiceAliases in frontend/lib/service-taxonomy.ts."""
    cleaned = (value or "").strip()
    if not cleaned:
        return []
    registry = json.loads(SERVICE_TAXONOMY.read_text(encoding="utf-8"))
    for entry in registry:
        if entry["slug"] == cleaned:
            return list(entry["aliases"])
    for entry in registry:
        if any(alias.strip().casefold() == cleaned.casefold() for alias in entry["aliases"]):
            return list(entry["aliases"])
    return [cleaned]


def coverage_query(region: str, provider_group: str, service_type: str | None) -> tuple[str, list[Any]]:
    """The website's coverage WHERE clause (frontend/lib/directory-db.ts buildWhereClause)."""
    params: list[Any] = [region]
    clauses = ["status = 'ACTIVE'", "region = $1"]
    aliases = service_aliases(service_type)
    if aliases:
        params.append(aliases)
        clauses.append(
            "EXISTS (SELECT 1 FROM unnest(string_to_array(coalesce(service_types, ''), '|')) AS service_type "
            f"WHERE lower(btrim(service_type)) = ANY(SELECT lower(alias) FROM unnest(${len(params)}::text[]) AS alias))"
        )
    clauses.append(OPPORTUNITY_SQL[provider_group])
    return f"SELECT id FROM care_providers WHERE {' AND '.join(clauses)} ORDER BY id", params


async def fetch_scope_location_ids(database_url: str, region: str, provider_group: str, service_type: str | None) -> list[str]:
    import asyncpg

    sql, params = coverage_query(region, provider_group, service_type)
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction(readonly=True):
            return [row["id"] for row in await conn.fetch(sql, *params)]
    finally:
        await conn.close()


def latest_export(base: Path) -> Path:
    candidates = sorted(
        (p for p in base.glob("cqc-export-*-final") if (p / "RECEIPT.json").exists()),
        key=lambda p: p.name,
    )
    if not candidates:
        raise CheckFailed(
            f"No CQC export with RECEIPT.json under {base}. Run extract_cqc.py first (see workflows/fulfil-manual-orders.md)."
        )
    return candidates[-1]


def export_receipt(export_dir: Path) -> dict[str, Any]:
    receipt = json.loads((export_dir / "RECEIPT.json").read_text(encoding="utf-8"))
    retrieved = datetime.fromisoformat(receipt["source_retrieved_at"])
    if retrieved.tzinfo is None:
        raise CheckFailed("RECEIPT.json source_retrieved_at must include a timezone.")
    receipt["_retrieved"] = retrieved
    return receipt


def add_working_days(start: date, days: int) -> date:
    current = start
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


def new_order_ref(product: str) -> str:
    prefix = "TOB" if product == "brief" else "WDP"
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #


@dataclass
class Checks:
    results: list[dict[str, Any]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.results.append({"check": name, "ok": bool(ok), "detail": detail})

    @property
    def ok(self) -> bool:
        return all(item["ok"] for item in self.results)

    def failures(self) -> list[str]:
        return [f"{item['check']}: {item['detail']}" for item in self.results if not item["ok"]]


def check_export_fresh(checks: Checks, receipt: dict[str, Any], now: datetime) -> None:
    age = now - receipt["_retrieved"]
    checks.add(
        "source_fresh",
        age <= timedelta(days=SOURCE_MAX_AGE_DAYS),
        f"CQC export retrieved {receipt['_retrieved'].isoformat()} ({age.days} days old; limit {SOURCE_MAX_AGE_DAYS})",
    )


# --------------------------------------------------------------------------- #
# Email
# --------------------------------------------------------------------------- #


def build_email(*, to: str, subject: str, body: str, attachments: list[Path] = ()) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{FROM_NAME} <{FROM_ADDRESS}>"
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="caregist.co.uk")
    message.set_content(body.rstrip() + "\n" + SIGNATURE)
    for path in attachments:
        data = path.read_bytes()
        if path.suffix == ".pdf":
            maintype, subtype = "application", "pdf"
        elif path.suffix == ".csv":
            maintype, subtype = "text", "csv"
        elif path.suffix == ".json":
            maintype, subtype = "application", "json"
        else:
            maintype, subtype = "application", "octet-stream"
        message.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)
    return message


def _drafts_mailbox(conn: imaplib.IMAP4_SSL) -> str:
    status, folders = conn.list()
    if status == "OK":
        for raw in folders or []:
            line = raw.decode("utf-8", "replace")
            if "\\Drafts" in line:
                return line.rsplit(' "', 1)[-1].strip('"') if ' "' in line else line.split()[-1]
    return "Drafts"


def save_draft(message: EmailMessage, *, env: dict[str, str]) -> str:
    """Append the message to the outreach@ Drafts folder. Never sends."""
    password = env.get("OUTREACH_IMAP_PASSWORD") or ""
    if not password:
        return "not saved to Private Email (OUTREACH_IMAP_PASSWORD not set); open the .eml file instead"
    host = env.get("OUTREACH_IMAP_HOST") or "mail.privateemail.com"
    user = env.get("OUTREACH_IMAP_USER") or FROM_ADDRESS
    conn = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context())
    try:
        conn.login(user, password)
        mailbox = _drafts_mailbox(conn)
        status, _ = conn.append(
            mailbox, "(\\Draft)", imaplib.Time2Internaldate(time.time()), message.as_bytes()
        )
        if status != "OK":
            raise RuntimeError(f"IMAP APPEND to {mailbox} failed: {status}")
        return f"saved to {user} {mailbox}"
    finally:
        try:
            conn.logout()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Brief
# --------------------------------------------------------------------------- #


def build_brief(args: argparse.Namespace, *, env: dict[str, str], order_dir: Path, now: datetime) -> tuple[Checks, dict[str, Any], list[Path]]:
    from api.services.territory_brief import (
        PROVIDER_GROUP_LABELS,
        PurchaseContext,
        brief_to_csv,
        generate_territory_opportunity_brief,
    )
    from api.services.territory_brief_render import render_brief_pdf

    checks = Checks()
    export_dir = args.export_dir or latest_export(REPO_ROOT / ".tmp")
    receipt = export_receipt(export_dir)
    check_export_fresh(checks, receipt, now)

    ids = asyncio.run(
        fetch_scope_location_ids(env["DATABASE_URL"], args.region, args.provider_group, args.service_type)
    )
    detail = f"{len(ids)} active locations match the website coverage query"
    if args.expected_count is not None:
        detail += f" (buyer's enquiry said {args.expected_count})"
    checks.add("scope_has_locations", bool(ids), detail)

    brief = generate_territory_opportunity_brief(
        {"kind": "region", "name": args.region, "window_days": 90, "shortlist_target": args.shortlist},
        PurchaseContext(order_reference=args.order_ref, generated_at=now, terms_version="2.2"),
        locations_source=export_dir / "_locations_detail.ndjson",
        providers_source=export_dir / "_providers_detail.ndjson",
        location_ids=ids,
        provider_group=args.provider_group,
    )
    shortfall_ok = args.allow_shortfall and len(brief.shortlist) > 0
    checks.add(
        "shortlist_minimum",
        len(brief.shortlist) >= MIN_SHORTLIST or shortfall_ok,
        f"{len(brief.shortlist)} organisations shortlisted (pricing page promises {MIN_SHORTLIST}-50)"
        + ("; smaller shortlist agreed with the buyer (--allow-shortfall)" if shortfall_ok and len(brief.shortlist) < MIN_SHORTLIST else ""),
    )
    checks.add(
        "evidence_matches_scope",
        brief.considered_locations > 0 and brief.considered_locations <= max(len(ids), 1),
        f"{brief.considered_locations} of {len(ids)} matched locations carry dated CQC evidence in the export",
    )
    checks.add(
        "window_current",
        (now.date() - brief.window_end).days <= SOURCE_MAX_AGE_DAYS,
        f"evidence window ends {brief.window_end.isoformat()}",
    )

    slug = re.sub(r"[^a-z0-9]+", "-", f"{args.region}-{args.provider_group}".lower()).strip("-")
    pdf = order_dir / f"territory-opportunity-brief-{slug}.pdf"
    csv_path = order_dir / f"territory-opportunity-brief-{slug}.csv"
    manifest = order_dir / f"territory-opportunity-brief-{slug}-source-manifest.json"
    pdf.write_bytes(render_brief_pdf(brief))
    csv_path.write_text(brief_to_csv(brief), encoding="utf-8")
    manifest.write_text(json.dumps(brief.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "region": args.region,
        "provider_group": PROVIDER_GROUP_LABELS[args.provider_group],
        "service_type": args.service_type or "All",
        "locations_in_scope": len(ids),
        "shortlisted": len(brief.shortlist),
        "source_edition": brief.as_of_date.isoformat(),
        "export": str(export_dir),
    }
    return checks, summary, [pdf, csv_path, manifest]


def brief_quote_email(args: argparse.Namespace, summary: dict[str, Any], now: datetime) -> tuple[str, str]:
    delivery = add_working_days(now.date(), DELIVERY_WORKING_DAYS)
    subject = f"Your Territory Opportunity Brief scope: {summary['region']} · {summary['provider_group']}"
    body = f"""Hi {args.buyer_name or 'there'},

Thank you for your enquiry. I have checked the published CQC record for your scope and can confirm we can deliver it.

Confirmed scope (this email is the order form under our Business Terms v2.2):
- Territory: {summary['region']}
- Provider group: {summary['provider_group']}
- Service type: {summary['service_type']}
- Organisations in scope: {summary['locations_in_scope']}
- Ranked shortlist: {summary['shortlisted']} organisations, each with a stated reason and its CQC source
- Source: CQC published register edition dated {summary['source_edition']}
- Delivery: by email within {DELIVERY_WORKING_DAYS} working days of payment (if paid today, by {delivery.strftime('%A %d %B %Y')})

Price: {BRIEF_PRICE}

To place the order, pay here: {BRIEF_PAYMENT_LINK}

Our terms are at {TERMS_URL}. If you would like to change the scope before paying, just reply to this email.

Best wishes,
"""
    return subject, body


def brief_delivery_email(args: argparse.Namespace, summary: dict[str, Any]) -> tuple[str, str]:
    subject = f"Your Territory Opportunity Brief: {summary['region']} · {summary['provider_group']}"
    body = f"""Hi {args.buyer_name or 'there'},

Thank you for your order. Your Territory Opportunity Brief is attached:

- the PDF brief ({summary['shortlisted']} ranked organisations with the reason and CQC evidence for each);
- the CSV dataset, ready to map into your CRM;
- the source manifest recording the CQC edition ({summary['source_edition']}) behind every entry.

The Brief reflects the published CQC register edition, not a live lookup. Please check each organisation's current CQC page before contacting it.

If anything in the pack does not match the scope we agreed, reply to this email and we will put it right.

Best wishes,
"""
    return subject, body


# --------------------------------------------------------------------------- #
# Weekly Digest
# --------------------------------------------------------------------------- #


def digest_quote_email(args: argparse.Namespace) -> tuple[str, str]:
    start = date.fromisoformat(args.start_date)
    issues = [start + timedelta(weeks=i) for i in range(4)]
    subject = f"Your Weekly Digest pilot: {args.region}, starting {start.strftime('%d %B %Y')}"
    body = f"""Hi {args.buyer_name or 'there'},

Thank you for your enquiry. Here is the confirmed Weekly Digest pilot (this email is the order form under our Business Terms v2.2):

- Region: {args.region}
- Buyer type: {args.buyer_type or 'as discussed'}
- Four weekly digests by email and PDF, on {', '.join(d.strftime('%a %d %b') for d in issues)}
- Each digest lists new CQC registrations and newly published ratings in the region, with the CQC source edition and the observation window stated. CQC has published few new ratings since September 2026, so the ratings section may be short until it resumes.

Price: {DIGEST_PRICE}
Payment is due before the first digest. You can cancel by email before the first digest for a full refund.

To place the order, pay here: {DIGEST_PAYMENT_LINK}

Our terms are at {TERMS_URL}. Reply to this email if you would like to change anything first.

Best wishes,
"""
    return subject, body


def build_digest_issue(args: argparse.Namespace, *, env: dict[str, str], order_dir: Path, now: datetime) -> tuple[Checks, dict[str, Any], list[Path]]:
    from tools import build_weekly_digest_pilot as digest

    checks = Checks()
    export_dir = args.export_dir or latest_export(REPO_ROOT / ".tmp")
    receipt = export_receipt(export_dir)
    check_export_fresh(checks, receipt, now)
    week_ending = date.fromisoformat(args.week_ending)
    checks.add(
        "export_after_window",
        receipt["_retrieved"].astimezone(timezone.utc).date() > week_ending,
        f"export retrieved {receipt['_retrieved'].date().isoformat()}, window ends {week_ending.isoformat()}",
    )
    if not checks.ok:
        return checks, {}, []
    os.environ.setdefault("DATABASE_URL", env["DATABASE_URL"])
    code = digest.main([
        "--region", args.region, "--week-ending", args.week_ending, "--issue", str(args.issue),
        "--customer", args.company or args.buyer_name or args.buyer_email,
        "--locations-source", str(export_dir / "_locations_detail.ndjson"),
        "--source-retrieved-at", receipt["source_retrieved_at"],
        "--out-dir", str(order_dir),
    ])
    checks.add("digest_built", code == 0, f"build_weekly_digest_pilot exit code {code}")
    files = sorted(order_dir.glob(f"weekly-digest-*-issue{args.issue}.*"))
    manifest = next((p for p in files if p.name.endswith(".manifest.json")), None)
    counts = json.loads(manifest.read_text())["counts"] if manifest else {}
    return checks, {"region": args.region, "issue": args.issue, **counts}, files


def digest_delivery_email(args: argparse.Namespace, summary: dict[str, Any]) -> tuple[str, str]:
    subject = f"Your CareGist Weekly Digest: {args.region}, issue {args.issue} of 4"
    body = f"""Hi {args.buyer_name or 'there'},

Issue {args.issue} of 4 of your Weekly Digest for {args.region} is attached (PDF and CSV), covering the week ending {args.week_ending}.

This week: {summary.get('new_registrations', 0)} new registration(s) and {summary.get('ratings_published', 0)} newly published rating(s). Every item links to its CQC record. The digest reflects the published CQC register, not a live feed.

Best wishes,
"""
    return subject, body


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        from dotenv import dotenv_values

        for key, value in dotenv_values(env_file).items():
            if value is not None:
                env.setdefault(key, value)
    return env


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("product", choices=("brief", "digest"))
    p.add_argument("stage", choices=("quote", "deliver"))
    p.add_argument("--region", required=True, choices=REGIONS)
    p.add_argument("--buyer-email", required=True)
    p.add_argument("--buyer-name", default="")
    p.add_argument("--company", default="")
    p.add_argument("--order-ref", default=None, help="reuse the quote's reference when delivering")
    p.add_argument("--export-dir", type=Path, default=None)
    p.add_argument("--out-base", type=Path, default=REPO_ROOT / ".tmp" / "orders")
    p.add_argument("--no-draft", action="store_true", help="write the .eml only")
    # Brief
    p.add_argument("--provider-group", choices=tuple(OPPORTUNITY_SQL))
    p.add_argument("--service-type", default=None, help="as chosen on the website, e.g. 'Homecare Agencies'")
    p.add_argument("--shortlist", type=int, default=30)
    p.add_argument("--expected-count", type=int, default=None, help="'Providers in scope' from the enquiry email")
    p.add_argument(
        "--allow-shortfall", action="store_true",
        help="buyer has agreed in writing to fewer than 25 organisations; the email states the real number",
    )
    # Digest
    p.add_argument("--buyer-type", default="")
    p.add_argument("--start-date", default=None, help="first digest date (quote)")
    p.add_argument("--week-ending", default=None, help="last day of the week covered (deliver)")
    p.add_argument("--issue", type=int, choices=(1, 2, 3, 4), default=None)
    args = p.parse_args(argv)
    if args.product == "brief" and not args.provider_group:
        p.error("brief needs --provider-group")
    if args.product == "digest" and args.stage == "quote" and not args.start_date:
        p.error("digest quote needs --start-date")
    if args.product == "digest" and args.stage == "deliver" and not (args.week_ending and args.issue):
        p.error("digest deliver needs --week-ending and --issue")
    args.order_ref = args.order_ref or new_order_ref(args.product)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env = load_env()
    now = datetime.now(timezone.utc)
    order_dir = args.out_base / args.order_ref / f"{args.stage}-{now.strftime('%Y%m%dT%H%M%SZ')}"
    order_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    summary: dict[str, Any] = {}
    checks = Checks()
    try:
        if args.product == "brief":
            checks, summary, files = build_brief(args, env=env, order_dir=order_dir, now=now)
        elif args.stage == "deliver":
            checks, summary, files = build_digest_issue(args, env=env, order_dir=order_dir, now=now)
    except CheckFailed as exc:
        checks.add("inputs", False, str(exc))

    report = {
        "order_ref": args.order_ref,
        "product": args.product,
        "stage": args.stage,
        "buyer_email": args.buyer_email,
        "prepared_at": now.isoformat(),
        "summary": summary,
        "checks": checks.results,
        "ok": checks.ok,
    }
    (order_dir / "checks.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    if not checks.ok:
        print(f"NOT READY: {args.order_ref}. Nothing drafted. Fix and re-run:")
        for failure in checks.failures():
            print(f"  - {failure}")
        print(f"Details: {order_dir / 'checks.json'}")
        return 2

    # The email is written only once every check has passed.
    attachments: list[Path] = []
    if args.product == "brief" and args.stage == "quote":
        subject, body = brief_quote_email(args, summary, now)
    elif args.product == "brief":
        subject, body = brief_delivery_email(args, summary)
        attachments = files
    elif args.stage == "quote":
        subject, body = digest_quote_email(args)
    else:
        subject, body = digest_delivery_email(args, summary)
        attachments = [p for p in files if p.suffix in (".pdf", ".csv")]

    message = build_email(to=args.buyer_email, subject=subject, body=body, attachments=attachments)
    eml = order_dir / "email.eml"
    eml.write_bytes(message.as_bytes())
    draft = "not saved (--no-draft)" if args.no_draft else save_draft(message, env=env)
    report["draft"] = draft
    (order_dir / "checks.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"READY: {args.order_ref} ({args.product} {args.stage})")
    for item in checks.results:
        print(f"  ok  {item['check']}: {item['detail']}")
    print(f"Draft: {draft}")
    print(f"Folder: {order_dir}")
    print("Review the draft in outreach@caregist.co.uk, then press Send. Nothing has been sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
