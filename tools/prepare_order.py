"""Prepare a CareGist order for checking and sending.

One command per step of the human-led sale (Business Terms v2.3):

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
import secrets
import ssl
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parsedate_to_datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_TAXONOMY = REPO_ROOT / "frontend" / "data" / "service-taxonomy.json"

FROM_ADDRESS = "outreach@caregist.co.uk"
FROM_NAME = "CareGist"
BRIEF_AMOUNT_PENCE = 74500
DIGEST_AMOUNT_PENCE = 15000
BRIEF_PAYMENT_LINK = "https://buy.stripe.com/bJe8wI7Xhd8YdYi2vl3AY04"
DIGEST_PAYMENT_LINK = "https://buy.stripe.com/3cI8wIfpJ4Csg6qfi73AY01"
TERMS_URL = "https://www.caregist.co.uk/terms"
BRIEF_PRICE = "£745 fixed fee. No VAT added."
DIGEST_PRICE = "£150 for four weekly digests. No VAT added. No automatic renewal."
SOURCE_MAX_AGE_DAYS = 8          # the documented source-freshness promise
MAX_SHORTLIST = 50               # Terms v2.3: up to 50, exact number confirmed before payment
DELIVERY_WORKING_DAYS = 3

REGIONS = (
    "East", "East Midlands", "London", "North East", "North West",
    "South East", "South West", "West Midlands", "Yorkshire & Humberside",
)

# Copied verbatim from frontend/lib/directory-query-clauses.ts so the Brief covers
# exactly what the coverage check counted. tests/test_prepare_order.py fails if
# the two ever drift apart.
#
# Ratings follow the CareGist rating rule (file first, a newer CQC page check
# wins where it differs, API only for the file's gaps); see
# frontend/lib/directory-query-clauses.ts, which this must match exactly.
RECONCILED_RATING_SQL = """(CASE
    WHEN site_check_rating IS NOT NULL AND site_check_rating IS DISTINCT FROM file_overall_rating AND (file_rating_edition_date IS NULL OR site_check_at::date >= file_rating_edition_date) THEN NULLIF(site_check_rating, 'none')
    WHEN file_overall_rating IS NOT NULL THEN file_overall_rating
    ELSE overall_rating
  END)"""

OPPORTUNITY_SQL = {
    "new_90": "registration_date >= CURRENT_DATE - INTERVAL '90 days'",
    "inadequate": f"{RECONCILED_RATING_SQL} = 'Inadequate'",
    "requires_improvement": f"lower(btrim({RECONCILED_RATING_SQL})) = 'requires improvement'",
    "not_yet_inspected": f"lower(btrim(coalesce({RECONCILED_RATING_SQL}, ''))) IN ('', 'not yet inspected', 'no published rating')",
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


async def fetch_file_ratings(database_url: str, ids: list[str]) -> dict[str, tuple[str | None, date | None]]:
    """Ratings the rule serves from the file or a newer CQC page check, per location.

    (rating, date) where the ratings file (or a CQC page check made after its
    edition) decides the rating; rating is None where the page shows none, which
    withholds the register's API rating too. Locations the file does not cover are
    absent, so the Brief keeps the API rating for them (rule 3).
    """
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(
                f"SELECT id, {RECONCILED_RATING_SQL} AS rating, "
                "CASE WHEN site_check_rating IS NOT NULL AND site_check_rating IS DISTINCT FROM file_overall_rating "
                "AND (file_rating_edition_date IS NULL OR site_check_at::date >= file_rating_edition_date) "
                "THEN site_check_at::date ELSE file_overall_rating_date END AS rated_on "
                "FROM care_providers WHERE id = ANY($1::text[]) "
                "AND (file_overall_rating IS NOT NULL OR site_check_rating IS NOT NULL)",
                ids,
            )
    finally:
        await conn.close()
    return {r["id"]: (r["rating"], r["rated_on"]) for r in rows}


def resolved_contract_enabled(env: dict[str, str]) -> bool:
    """RESOLVED_RATING_CONTRACT_ENABLED, read the way pydantic reads a bool flag."""
    return str(env.get("RESOLVED_RATING_CONTRACT_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}


async def fetch_rating_evidence(database_url: str, ids: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Ratings-file evidence and CQC page checks for the resolved rating contract.

    Returns ``(rating_evidence, website_observations)`` of
    :class:`api.services.rating_resolver.RatingEvidence`. Every page check
    becomes a dated observation the resolver weighs against the API and file
    values: one showing a rating can confirm or contradict them, and one showing
    ``'none'`` (no rating on the page) is kept with ``value=None`` so the
    resolver can mark the rating unresolved instead of the check disappearing.
    The file value is always kept as evidence; withholding is the resolver's
    decision, not the loader's.
    """
    import asyncpg

    from api.services.rating_resolver import SOURCE_FILE, SOURCE_WEBSITE, RatingEvidence, canonical_rating

    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(
                "SELECT id, file_overall_rating, file_overall_rating_date, file_rating_source_sha256, "
                "site_check_rating, site_check_at FROM care_providers "
                "WHERE id = ANY($1::text[]) AND file_overall_rating IS NOT NULL",
                ids,
            )
    finally:
        await conn.close()
    evidence: dict[str, Any] = {}
    observations: dict[str, Any] = {}
    for r in rows:
        checked = (r["site_check_rating"] or "").strip()
        evidence[r["id"]] = RatingEvidence(
            source=SOURCE_FILE, value=canonical_rating(r["file_overall_rating"]),
            publication_date=r["file_overall_rating_date"], source_sha256=r["file_rating_source_sha256"],
            raw_value=r["file_overall_rating"],
        )
        if checked and r["site_check_at"] is not None:
            observations[r["id"]] = RatingEvidence(
                source=SOURCE_WEBSITE, value=canonical_rating(checked), observed_on=r["site_check_at"].date(),
                raw_value=checked,
            )
    return evidence, observations


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


PRODUCT_AMOUNTS = (BRIEF_AMOUNT_PENCE, DIGEST_AMOUNT_PENCE)
#: A sale counts only if it came through the product's own Payment Link, in GBP.
#: The Stripe account is shared with another business, so amount alone is not enough.
PRODUCT_PAYMENT_LINKS = {
    BRIEF_AMOUNT_PENCE: "plink_1UEkzy4mijLHzRRkWjk3pFVW",
    DIGEST_AMOUNT_PENCE: "plink_1UBt3M4mijLHzRRkz4joD0We",
}
CLOCK_SKEW = timedelta(minutes=2)


def _is_product_sale(amount: Any, currency: Any, payment_link: Any) -> bool:
    return (
        amount in PRODUCT_PAYMENT_LINKS
        and str(currency or "").lower() == "gbp"
        and payment_link == PRODUCT_PAYMENT_LINKS[amount]
    )


STRIPE_MAX_PAGES = 30           # 3,000 sessions per lookup; far beyond current volume


def _payments_from_sales_record(
    database_url: str, buyer_email: str | None, amount_pence: int | None, since_days: int
) -> list[dict[str, Any]]:
    """Paid Payment Link sales recorded by the billing webhook (manual_sale_paid), oldest first.

    Only used when Stripe is not configured: its time is when the webhook recorded the
    sale, not when the buyer paid.
    """
    import asyncpg

    async def query() -> list[dict[str, Any]]:
        conn = await asyncpg.connect(database_url)
        try:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(
                    """
                    SELECT created_at, email, (meta->>'amount_total')::int AS amount,
                           meta->>'stripe_checkout_session_id' AS session,
                           meta->>'currency' AS currency, meta->>'payment_link' AS payment_link,
                           meta->>'client_reference_id' AS order_ref
                    FROM analytics_events
                    WHERE event_type = 'manual_sale_paid'
                      AND meta->>'payment_status' = 'paid'
                      AND created_at >= NOW() - make_interval(days => $3)
                      AND ($1::text IS NULL OR lower(email) = lower($1))
                      AND ($2::int IS NULL OR (meta->>'amount_total')::int = $2)
                    ORDER BY created_at ASC
                    """,
                    buyer_email.strip() if buyer_email else None,
                    amount_pence,
                    since_days,
                )
        finally:
            await conn.close()
        return [
            {"source": "CareGist sales record", "session": r["session"], "paid_at": r["created_at"].isoformat(),
             "email": r["email"], "amount": r["amount"], "order_ref": r["order_ref"] or None}
            for r in rows
            if _is_product_sale(r["amount"], r["currency"], r["payment_link"])
        ]

    return asyncio.run(query())


def _payments_from_stripe(
    secret_key: str, buyer_email: str | None, amount_pence: int | None, since_days: int
) -> list[dict[str, Any]]:
    """Paid product sales from Stripe, oldest first, following pagination.

    ``paid_at`` is the checkout session's creation time (when the buyer opened the
    payment page). Orders are bound by ``client_reference_id``, so this time only
    matters for payments made through a link without an order reference.
    """
    import httpx

    params: dict[str, Any] = {
        "status": "complete",
        "limit": 100,
        "created[gte]": int((datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp()),
    }
    if buyer_email:
        params["customer_details[email]"] = buyer_email.strip()
    found = []
    for _page in range(STRIPE_MAX_PAGES):
        response = httpx.get("https://api.stripe.com/v1/checkout/sessions", params=params, auth=(secret_key, ""), timeout=30)
        response.raise_for_status()
        body = response.json()
        sessions = body.get("data", [])
        for session in sessions:
            amount = session.get("amount_total")
            if session.get("payment_status") != "paid" or not _is_product_sale(
                amount, session.get("currency"), session.get("payment_link")
            ):
                continue
            if amount_pence is not None and amount != amount_pence:
                continue
            found.append({
                "source": "Stripe",
                "session": session["id"],
                "paid_at": datetime.fromtimestamp(session["created"], tz=timezone.utc).isoformat(),
                "email": (session.get("customer_details") or {}).get("email") or "",
                "amount": amount,
                "order_ref": session.get("client_reference_id") or None,
            })
        if not body.get("has_more") or not sessions:
            break
        params["starting_after"] = sessions[-1]["id"]
    else:
        raise RuntimeError(f"Stripe returned more than {STRIPE_MAX_PAGES * 100} sessions; narrow the lookup")
    return sorted(found, key=lambda item: item["paid_at"])


def list_payments(
    env: dict[str, str], *, buyer_email: str | None = None, amount_pence: int | None = None, since_days: int = 365
) -> list[dict[str, Any]]:
    """Every paid product sale, de-duplicated by Stripe session, oldest first.

    Stripe is authoritative. When a Stripe key is configured and Stripe fails, the
    error propagates and the caller refuses (fail closed); CareGist's sales record
    is used only when no Stripe key is configured.
    """
    seen: dict[str, dict[str, Any]] = {}
    if env.get("STRIPE_SECRET_KEY"):
        for item in _payments_from_stripe(env["STRIPE_SECRET_KEY"], buyer_email, amount_pence, since_days):
            seen.setdefault(item["session"], item)
    elif env.get("DATABASE_URL"):
        for item in _payments_from_sales_record(env["DATABASE_URL"], buyer_email, amount_pence, since_days):
            if item["session"]:
                seen.setdefault(item["session"], item)
    return sorted(seen.values(), key=lambda item: item["paid_at"])


def find_payment(
    env: dict[str, str],
    buyer_email: str,
    amount_pence: int,
    *,
    order_ref: str | None = None,
    exclude_sessions: frozenset[str] | set[str] = frozenset(),
    not_before: str | None = None,
) -> dict[str, Any] | None:
    """The payment for this order.

    1. A paid sale whose client_reference_id is this order ref (from the quote's
       link) belongs to this order, whatever email the buyer paid with.
    2. Otherwise only a sale with *no* order reference can be used: same buyer email
       and amount, made after the order existed, not attached to another order.
    A sale carrying another order's reference is never used.
    """
    if order_ref:
        for item in list_payments(env, amount_pence=amount_pence):
            if item.get("order_ref") == order_ref and item["session"] not in exclude_sessions:
                return item
    floor = datetime.fromisoformat(not_before) - CLOCK_SKEW if not_before else None
    for item in list_payments(env, buyer_email=buyer_email, amount_pence=amount_pence):
        if item.get("order_ref") or item["session"] in exclude_sessions:
            continue
        if floor and datetime.fromisoformat(item["paid_at"]) < floor:
            continue
        return item
    return None


def payment_still_valid(env: dict[str, str], session_id: str) -> str | None:
    """None if the payment still stands; otherwise why not (refund, dispute, unpaid).

    Fails closed: without Stripe the payment cannot be re-checked.
    """
    if not env.get("STRIPE_SECRET_KEY"):
        return "Stripe is not configured, so the payment cannot be re-checked before delivery"
    import httpx

    response = httpx.get(
        f"https://api.stripe.com/v1/checkout/sessions/{session_id}",
        params={"expand[]": "payment_intent.latest_charge"},
        auth=(env["STRIPE_SECRET_KEY"], ""),
        timeout=30,
    )
    response.raise_for_status()
    session = response.json()
    if session.get("payment_status") != "paid":
        return f"the checkout is no longer paid ({session.get('payment_status')})"
    intent = session.get("payment_intent")
    charge = intent.get("latest_charge") if isinstance(intent, dict) else None
    if not isinstance(charge, dict) or "refunded" not in charge or "amount_refunded" not in charge:
        return "Stripe returned no charge for this payment, so refunds and disputes cannot be ruled out"
    if charge.get("refunded") or int(charge.get("amount_refunded") or 0) > 0:
        return "the payment has been refunded"
    if charge.get("disputed"):
        return "the payment is disputed"
    return None


def payment_link_for(amount_pence: int, order_ref: str) -> str:
    """The product's Payment Link carrying the order ref, so Stripe records which order was paid."""
    base = BRIEF_PAYMENT_LINK if amount_pence == BRIEF_AMOUNT_PENCE else DIGEST_PAYMENT_LINK
    return f"{base}?client_reference_id={order_ref}"


from tools.order_ledger import add_working_days  # noqa: E402  (shared with the ledger)


def new_order_ref(product: str) -> str:
    prefix = "TOB" if product == "brief" else "WDP"
    # A random suffix keeps refs unique when two orders are prepared in the same second.
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2).upper()}"


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


_LIST_LINE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$', re.IGNORECASE)


def special_mailbox(conn: imaplib.IMAP4_SSL, flag: str, default: str) -> str:
    """The mailbox carrying a special-use flag (e.g. \\Drafts), from LIST.

    Handles both quoted ("Drafts") and unquoted (Drafts) names; Private Email
    returns them unquoted.
    """
    status, folders = conn.list()
    if status == "OK":
        for raw in folders or []:
            match = _LIST_LINE.match(raw.decode("utf-8", "replace").strip())
            if match and flag.lower() in match["flags"].lower().split():
                name = match["name"].strip()
                if len(name) >= 2 and name[0] == name[-1] == '"':
                    name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                return name
    return default


def _drafts_mailbox(conn: imaplib.IMAP4_SSL) -> str:
    return special_mailbox(conn, "\\Drafts", "Drafts")


def draft_exists(message_id: str, *, env: dict[str, str]) -> bool:
    """Whether a draft with this Message-ID is in outreach@ Drafts. Raises if it cannot tell."""
    if not env.get("OUTREACH_IMAP_PASSWORD"):
        raise RuntimeError("OUTREACH_IMAP_PASSWORD is not set, so outreach@ Drafts cannot be checked")
    host = env.get("OUTREACH_IMAP_HOST") or "mail.privateemail.com"
    user = env.get("OUTREACH_IMAP_USER") or FROM_ADDRESS
    conn = imaplib.IMAP4_SSL(host, 993, ssl_context=ssl.create_default_context())
    try:
        conn.login(user, env["OUTREACH_IMAP_PASSWORD"])
        status, _ = conn.select(f'"{_drafts_mailbox(conn)}"', readonly=True)
        if status != "OK":
            raise RuntimeError("could not open the Drafts folder")
        status, data = conn.search(None, "HEADER", "Message-ID", message_id)
        if status != "OK":
            raise RuntimeError("Drafts search failed")
        return bool(data and data[0] and data[0].split())
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def save_draft(message: EmailMessage, *, env: dict[str, str]) -> str:
    """Append the message to the outreach@ Drafts folder. Never sends."""
    password = env.get("OUTREACH_IMAP_PASSWORD") or ""
    if not password:
        raise RuntimeError("OUTREACH_IMAP_PASSWORD is not set")
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

    if resolved_contract_enabled(env):
        evidence, observations = (
            asyncio.run(fetch_rating_evidence(env["DATABASE_URL"], ids)) if ids else ({}, {})
        )
        rating_inputs: dict[str, Any] = {"rating_evidence": evidence, "website_observations": observations}
        checks.add(
            "rating_contract", True,
            f"resolved rating contract: {len(evidence)} ratings-file values, {len(observations)} CQC page checks",
        )
    else:
        rating_inputs = {"file_ratings": asyncio.run(fetch_file_ratings(env["DATABASE_URL"], ids)) if ids else {}}
    brief = generate_territory_opportunity_brief(
        {"kind": "region", "name": args.region, "window_days": 90, "shortlist_target": args.shortlist},
        PurchaseContext(order_reference=args.order_ref, generated_at=now, terms_version="2.3"),
        locations_source=export_dir / "_locations_detail.ndjson",
        providers_source=export_dir / "_providers_detail.ndjson",
        location_ids=ids,
        provider_group=args.provider_group,
        **rating_inputs,
    )
    checks.add(
        "shortlist_not_empty",
        0 < len(brief.shortlist) <= MAX_SHORTLIST,
        f"{len(brief.shortlist)} organisations shortlisted (terms: up to {MAX_SHORTLIST}, exact number stated in the quote)",
    )
    if args.stage == "deliver":
        quoted = getattr(args, "quoted_count", None)
        if quoted is None:
            checks.add("matches_quote", False, "the order has no recorded quote; quote it first")
        else:
            checks.add(
                "matches_quote",
                len(brief.shortlist) == quoted,
                f"quote promised exactly {quoted} organisations; this build has {len(brief.shortlist)}",
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
    subject = f"Your Territory Opportunity Brief scope: {summary['region']} · {summary['provider_group']} (ref {args.order_ref})"
    body = f"""Hi {args.buyer_name or 'there'},

Thank you for your enquiry. I have checked the published CQC record for your scope and can confirm we can deliver it.

Confirmed scope (this email is the order form under our Business Terms v2.3):
- Territory: {summary['region']}
- Provider group: {summary['provider_group']}
- Service type: {summary['service_type']}
- Organisations in scope: {summary['locations_in_scope']}
- Ranked shortlist: {summary['shortlisted']} organisations (the exact number your Brief will contain), each with a stated reason and its CQC source
- Source: CQC published register edition dated {summary['source_edition']}
- Delivery: by email within {DELIVERY_WORKING_DAYS} working days of payment (if paid today, by {delivery.strftime('%A %d %B %Y')})

Price: {BRIEF_PRICE}

To place the order, pay here: {payment_link_for(BRIEF_AMOUNT_PENCE, args.order_ref)}

Our terms are at {TERMS_URL}. If you would like to change the scope before paying, just reply to this email.

Best wishes,
"""
    return subject, body


def brief_delivery_email(args: argparse.Namespace, summary: dict[str, Any]) -> tuple[str, str]:
    subject = f"Your Territory Opportunity Brief: {summary['region']} · {summary['provider_group']} (ref {args.order_ref})"
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
    subject = f"Your Weekly Digest pilot: {args.region}, starting {start.strftime('%d %B %Y')} (ref {args.order_ref})"
    body = f"""Hi {args.buyer_name or 'there'},

Thank you for your enquiry. Here is the confirmed Weekly Digest pilot (this email is the order form under our Business Terms v2.3):

- Region: {args.region}
- Buyer type: {args.buyer_type or 'as discussed'}
- Four weekly digests by email and PDF, on {', '.join(d.strftime('%a %d %b') for d in issues)}
- Each digest lists new CQC registrations and newly published ratings in the region, with the CQC source edition and the observation window stated. CQC has published few new ratings since September 2026, so the ratings section may be short until it resumes.

Price: {DIGEST_PRICE}
Payment is due before the first digest. You can cancel by email before the first digest for a full refund.

To place the order, pay here: {payment_link_for(DIGEST_AMOUNT_PENCE, args.order_ref)}

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
    subject = f"Your CareGist Weekly Digest: {args.region}, issue {args.issue} of 4 (ref {args.order_ref})"
    body = f"""Hi {args.buyer_name or 'there'},

Issue {args.issue} of 4 of your Weekly Digest for {args.region} is attached (PDF and CSV), covering the week ending {args.week_ending}.

This week: {summary.get('new_registrations', 0)} new registration(s) and {summary.get('ratings_published', 0)} newly published rating(s). Every item links to its CQC record. The digest reflects the published CQC register, not a live feed.

Best wishes,
"""
    return subject, body


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def record_in_ledger(
    args: argparse.Namespace,
    *,
    summary: dict[str, Any],
    message: EmailMessage,
    draft: str,
    order_dir: Path,
    payment: dict[str, Any] | None,
) -> None:
    """Log the drafted email against its order in the local ledger (tools/orders.py)."""
    from tools import order_ledger

    if args.product == "brief":
        scope = f"{args.region} · {summary.get('provider_group', args.provider_group)} · {args.service_type or 'All services'}"
        scope_args = {"region": args.region, "provider_group": args.provider_group, "service_type": args.service_type}
        amount = BRIEF_AMOUNT_PENCE
        quoted = summary.get("shortlisted") if args.stage == "quote" else None
    else:
        scope = f"{args.region} · from {args.start_date}" if args.start_date else args.region
        scope_args = {"region": args.region, "start_date": args.start_date, "buyer_type": args.buyer_type}
        amount = DIGEST_AMOUNT_PENCE
        quoted = None
    order_ledger.record_email(
        order_ref=args.order_ref,
        product=args.product,
        stage=args.stage,
        buyer_email=args.buyer_email,
        buyer_name=args.buyer_name,
        company=args.company,
        scope=scope,
        scope_args=scope_args,
        amount_pence=amount,
        quoted_count=quoted,
        message_id=str(message["Message-ID"]),
        subject=str(message["Subject"]),
        # The email's own Date header: a mail client that keeps it on Send produces a
        # sent copy dated exactly this, so "sent at or after drafted" still matches.
        drafted_at=parsedate_to_datetime(str(message["Date"])).astimezone(timezone.utc).isoformat(timespec="microseconds"),
        draft_location=draft,
        folder=str(order_dir),
        issue=args.issue if args.product == "digest" and args.stage == "deliver" else None,
        payment=payment,
        supersede_email_id=getattr(args, "supersede", None),
        allow_new_order=bool(getattr(args, "new_order", False)),
    )


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        from dotenv import dotenv_values

        for key, value in dotenv_values(env_file).items():
            if value is not None:
                env.setdefault(key, value)
    return env


USAGE = """
  Quote (after agreeing scope by email):
    prepare_order quote brief  --region R --provider-group G [--service-type S] --buyer-email E [--buyer-name N] [--company C]
    prepare_order quote digest --region R --start-date YYYY-MM-DD --buyer-email E [--buyer-type T] [--buyer-name N] [--company C]
  Deliver (after payment; everything else comes from the order record):
    prepare_order deliver --order-ref REF
"""

DELIVER_FORBIDDEN = (
    "region", "buyer_email", "buyer_name", "company", "provider_group", "service_type",
    "start_date", "buyer_type", "week_ending", "issue", "expected_count",
)


def _normalise_argv(argv: list[str]) -> list[str]:
    """Accept 'quote brief', 'brief quote' and 'deliver' (product read from the order)."""
    if len(argv) >= 2 and argv[0] in ("brief", "digest") and argv[1] in ("quote", "deliver"):
        return [argv[1], argv[0], *argv[2:]]
    if argv and argv[0] == "deliver" and (len(argv) < 2 or argv[1] not in ("brief", "digest")):
        return ["deliver", "auto", *argv[1:]]
    return argv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    import sys

    argv = _normalise_argv(list(sys.argv[1:] if argv is None else argv))
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0], usage=USAGE)
    p.add_argument("stage", choices=("quote", "deliver"))
    p.add_argument("product", choices=("brief", "digest", "auto"))
    p.add_argument("--order-ref", default=None, help="deliver: the order's reference; quote: re-quote that order")
    p.add_argument("--region", default=None, choices=REGIONS)
    p.add_argument("--buyer-email", default=None)
    p.add_argument("--buyer-name", default=None)
    p.add_argument("--company", default=None)
    p.add_argument("--export-dir", type=Path, default=None)
    p.add_argument("--out-base", type=Path, default=REPO_ROOT / ".tmp" / "orders")
    p.add_argument("--no-draft", action="store_true", help="write the .eml only")
    p.add_argument("--redraft", action="store_true", help="replace an unsent draft for this step")
    p.add_argument("--new-order", action="store_true", help="the buyer genuinely wants a second, separate order")
    # Brief
    p.add_argument("--provider-group", default=None, choices=tuple(OPPORTUNITY_SQL))
    p.add_argument("--service-type", default=None, help="as chosen on the website, e.g. 'Homecare Agencies'")
    p.add_argument("--shortlist", type=int, default=30)
    p.add_argument("--expected-count", type=int, default=None, help="'Providers in scope' from the enquiry email")
    # Digest
    p.add_argument("--buyer-type", default=None)
    p.add_argument("--start-date", default=None, help="first digest date")
    p.add_argument("--week-ending", default=None)
    p.add_argument("--issue", type=int, default=None)
    args = p.parse_args(argv)

    if args.stage == "deliver":
        if not args.order_ref:
            p.error("deliver needs --order-ref (see: .venv/bin/python -m tools.orders)")
        typed = [name for name in DELIVER_FORBIDDEN if getattr(args, name) not in (None, "")]
        if typed:
            flags = ", ".join("--" + name.replace("_", "-") for name in typed)
            p.error(f"deliver takes only --order-ref; remove {flags}. The scope and buyer come from the order record.")
        return args

    if args.product == "auto":
        p.error("quote needs a product: quote brief ... or quote digest ...")
    if not args.region or not args.buyer_email:
        p.error("quote needs --region and --buyer-email")
    if "@" not in args.buyer_email or " " in args.buyer_email.strip():
        p.error(f"--buyer-email {args.buyer_email!r} is not an email address")
    if args.product == "brief" and not args.provider_group:
        p.error("quote brief needs --provider-group")
    if args.product == "digest":
        if not args.start_date:
            p.error("quote digest needs --start-date")
        try:
            date.fromisoformat(args.start_date)
        except ValueError:
            p.error("--start-date must be YYYY-MM-DD")
    args.buyer_name = args.buyer_name or ""
    args.company = args.company or ""
    args.buyer_type = args.buyer_type or ""
    return args


def _refuse(message: str) -> int:
    print(f"NOT READY: {message}")
    print("Nothing was built or drafted.")
    return 2


def _load_for_delivery(args: argparse.Namespace, today: date) -> str | None:
    """Fill args from the order record. Returns a refusal message, or None."""
    from tools import order_ledger

    with order_ledger.connect() as conn:
        order = order_ledger.get_order(conn, args.order_ref)
        if order is None:
            return f"there is no order {args.order_ref!r}. Copy the ref from: .venv/bin/python -m tools.orders"
        args.claimed = order_ledger.claimed_sessions(conn) - ({order["payment_session"]} if order["payment_session"] else set())
    args.order = order
    args.product = order["product"]
    args.order_ref = order["order_ref"]
    args.buyer_email = order["buyer_email"]
    args.buyer_name = order["buyer_name"] or ""
    args.company = order["company"] or ""
    scope = order["scope_args"]
    args.region = scope.get("region")
    if not order_ledger.live(order["emails"], "quote"):
        return f"{args.order_ref} has no quote on record; quote it first."
    if order_ledger.is_complete(order):
        return f"{args.order_ref} is already fully delivered ({order_ledger.order_status(order, today)})."

    deliveries = order_ledger.live(order["emails"], "deliver")
    if args.product == "brief":
        args.provider_group = scope.get("provider_group")
        args.service_type = scope.get("service_type")
        args.quoted_count = order["quoted_count"]
        if order["quoted_count"]:
            args.shortlist = order["quoted_count"]  # the exact number the quote promised
        args.issue = None
        current = deliveries
    else:
        args.start_date = scope.get("start_date")
        args.buyer_type = scope.get("buyer_type") or ""
        unsent = [e for e in deliveries if not e["sent_at"]]
        args.issue = unsent[0]["issue"] if unsent else len(order_ledger.sent_issues(order)) + 1
        due = order_ledger.digest_issue_due(order, args.issue)
        if due and today < due:
            return f"issue {args.issue} of {args.order_ref} is not due until {due.isoformat()}."
        args.week_ending = ((due or today) - timedelta(days=1)).isoformat()
        current = [e for e in deliveries if (e["issue"] or 1) == args.issue]

    if any(e["sent_at"] for e in current):
        return f"{args.order_ref} delivery{'' if args.issue is None else f' issue {args.issue}'} was already sent."
    unsent_draft = next((e for e in current if not e["sent_at"]), None)
    if unsent_draft and not args.redraft:
        return (
            f"a delivery draft for {args.order_ref} already exists (drafted {unsent_draft['drafted_at'][:16]}). "
            "Send it from outreach@ Drafts. Only if you deleted it, re-run with --redraft."
        )
    if unsent_draft:
        refusal = _replaceable(unsent_draft, order["buyer_email"])
        if refusal:
            return refusal
    args.supersede = unsent_draft["id"] if unsent_draft else None
    return None


def _replaceable(email_row: dict[str, Any], buyer_email: str) -> str | None:
    """None if the old draft is provably gone (not in Drafts, not sent); otherwise why not."""
    from tools.orders import find_sent

    env = load_env()
    try:
        in_drafts = draft_exists(email_row["message_id"], env=env)
        sent = find_sent(env, [{**email_row, "buyer_email": buyer_email}], strict=True)
    except Exception as exc:
        return f"could not confirm the earlier draft is gone ({type(exc).__name__}: {exc}); nothing replaced."
    if sent:
        return "the earlier draft has been sent; run tools.orders to record it. Nothing replaced."
    if in_drafts:
        return (f"the earlier draft is still in outreach@ Drafts (\"{email_row['subject']}\"). "
                "Send it, or delete it and re-run with --redraft.")
    return None


def _check_new_quote(args: argparse.Namespace) -> str | None:
    """Stop accidental duplicate orders and duplicate quote drafts."""
    from tools import order_ledger

    with order_ledger.connect() as conn:
        if args.order_ref:
            order = order_ledger.get_order(conn, args.order_ref)
            if order is None:
                return f"there is no order {args.order_ref!r} to re-quote; leave out --order-ref for a new order."
            if order["product"] != args.product or order["buyer_email"].lower() != args.buyer_email.strip().lower():
                return f"{args.order_ref} belongs to {order['buyer_email']} ({order['product']}); check the ref."
            if order["paid_at"]:
                return f"{args.order_ref} is already paid; its scope cannot be changed by a new quote."
            try:
                paid_now = find_payment(load_env(), order["buyer_email"], order["amount_pence"],
                                        order_ref=order["order_ref"], not_before=order["created_at"])
            except Exception as exc:
                return f"could not check whether {args.order_ref} is paid ({type(exc).__name__}); try again."
            if paid_now:
                return f"{args.order_ref} has been paid ({paid_now['session']}); its scope cannot be changed."
            if any(e["sent_at"] for e in order["emails"] if e["stage"] == "quote"):
                return (f"a quote for {args.order_ref} has been sent, so its scope and payment link are fixed. "
                        "For a different scope, quote a new order with --new-order (leave out --order-ref).")
            unsent = [e for e in order_ledger.live(order["emails"], "quote") if not e["sent_at"]]
            if unsent and not args.redraft:
                return (f"an unsent quote draft for {args.order_ref} exists (drafted {unsent[-1]['drafted_at'][:16]}). "
                        "Send or delete it; to replace a deleted draft re-run with --redraft.")
            if unsent:
                refusal = _replaceable(unsent[-1], order["buyer_email"])
                if refusal:
                    return refusal
            args.supersede = unsent[-1]["id"] if unsent else None
            return None
        open_orders = order_ledger.open_orders_for(conn, args.buyer_email, args.product)
    if open_orders and not args.new_order:
        refs = ", ".join(f"{o['order_ref']} ({order_ledger.order_status(o)})" for o in open_orders)
        return (f"{args.buyer_email} already has an open {args.product} order: {refs}. "
                "To change it: add --order-ref <that ref>. For a genuinely separate order: add --new-order.")
    args.order_ref = new_order_ref(args.product)
    args.supersede = None
    return None


def main(argv: list[str] | None = None) -> int:
    """One order run at a time: a second run while another is mid-save could
    replace its draft and leave two drafts in outreach@."""
    import fcntl

    from tools import order_ledger

    lock_path = order_ledger.ledger_path().with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return _refuse("another prepare_order run is in progress; wait for it to finish, then re-run.")
        try:
            return _main(argv)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _main(argv: list[str] | None = None) -> int:
    from tools import order_ledger

    args = parse_args(argv)
    env = load_env()
    now = datetime.now(timezone.utc)
    args.supersede = None

    if not args.no_draft and not env.get("OUTREACH_IMAP_PASSWORD"):
        return _refuse("OUTREACH_IMAP_PASSWORD is not set in .env, so the draft cannot be saved to outreach@.")
    refusal = _load_for_delivery(args, now.date()) if args.stage == "deliver" else _check_new_quote(args)
    if refusal:
        return _refuse(refusal)

    order_dir = args.out_base / args.order_ref / f"{args.stage}-{now.strftime('%Y%m%dT%H%M%SZ')}"
    order_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    summary: dict[str, Any] = {}
    checks = Checks()
    payment: dict[str, Any] | None = None
    if args.stage == "deliver":
        # Nothing is prepared for delivery until this order is paid, by a payment
        # no other order has claimed.
        amount = BRIEF_AMOUNT_PENCE if args.product == "brief" else DIGEST_AMOUNT_PENCE
        order = args.order
        try:
            if order["paid_at"]:
                payment = {"paid_at": order["paid_at"], "session": order["payment_session"], "source": order["payment_source"]}
            else:
                payment = find_payment(env, args.buyer_email, amount, order_ref=args.order_ref,
                                       exclude_sessions=args.claimed, not_before=order["created_at"])
            problem = payment_still_valid(env, payment["session"]) if payment else None
        except Exception as exc:  # Stripe or the database unreachable: never deliver on a guess
            payment, problem = None, None
            checks.add("payment_received", False, f"payment could not be checked ({type(exc).__name__}); try again")
        if payment is None and not checks.results:
            checks.add("payment_received", False,
                       f"no paid £{amount // 100} sale found for {args.order_ref} ({args.buyer_email})")
        elif payment is not None and problem:
            checks.add("payment_received", False, f"{payment['session']}: {problem}")
            payment = None
        elif payment is not None:
            checks.add("payment_received", True,
                       f"£{amount // 100} paid {payment['paid_at'][:16]} ({payment['source']}, {payment['session']})")
    try:
        if args.stage == "deliver" and payment is None:
            pass
        elif args.product == "brief":
            built, summary, files = build_brief(args, env=env, order_dir=order_dir, now=now)
            checks.results.extend(built.results)
        elif args.stage == "deliver":
            built, summary, files = build_digest_issue(args, env=env, order_dir=order_dir, now=now)
            checks.results.extend(built.results)
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
    if args.no_draft:
        # A dry run: nothing goes to outreach@ and nothing is recorded as an order or a draft.
        print(f"DRY RUN: {args.order_ref}. Email written to {eml}; nothing saved to outreach@ or recorded.")
        return 0
    try:
        record_in_ledger(args, summary=summary, message=message, draft="pending", order_dir=order_dir, payment=payment)
    except order_ledger.LedgerError as exc:
        return _refuse(str(exc))
    try:
        draft = save_draft(message, env=env)
    except Exception as exc:
        # The server may have saved the draft even though the reply was lost, and it
        # may even have been sent since. Only "not in Drafts and not in Sent" frees
        # the step for a re-run; anything unclear keeps it tracked.
        from tools.orders import find_sent

        message_id = str(message["Message-ID"])
        try:
            saved = draft_exists(message_id, env=env)
            if saved is False:
                with order_ledger.connect() as conn:
                    row = conn.execute("SELECT * FROM order_emails WHERE message_id = ?", (message_id,)).fetchone()
                    columns = [c[0] for c in conn.execute("SELECT * FROM order_emails LIMIT 0").description]
                sent = find_sent(env, [{**dict(zip(columns, row, strict=True)), "buyer_email": args.buyer_email}], strict=True)
                if sent:
                    with order_ledger.connect() as conn:
                        order_ledger.mark_sent(conn, message_id, sent[message_id])
                    print(f"ALREADY SENT: the {args.stage} email for {args.order_ref} was saved and has been sent; "
                          "recorded as sent. Nothing more to do for this step.")
                    return 0
        except Exception:
            saved = None
        with order_ledger.connect() as conn:
            if saved:
                conn.execute("UPDATE order_emails SET draft_location = ? WHERE message_id = ?",
                             ("saved to outreach@ Drafts (confirmed after a connection error)", message_id))
            elif saved is False:
                conn.execute(
                    "UPDATE order_emails SET superseded_at = ?, draft_location = ? WHERE message_id = ?",
                    (now.isoformat(timespec="seconds"), f"failed: {type(exc).__name__}", message_id),
                )
            else:
                conn.execute("UPDATE order_emails SET draft_location = ? WHERE message_id = ?",
                             (f"uncertain: {type(exc).__name__}; check outreach@ Drafts", message_id))
        if saved is False:
            return _refuse(f"could not save the draft to outreach@ ({type(exc).__name__}: {exc}). Nothing was drafted; re-run.")
        if saved is None:
            print(f"NOT CONFIRMED: the draft may or may not be in outreach@ Drafts ({type(exc).__name__}).")
            print(f"Look for subject \"{message['Subject']}\": if it is there, send it; "
                  "only if it is not, re-run with --redraft.")
            return 2
        draft = "saved to outreach@ Drafts (confirmed after a connection error)"
    else:
        with order_ledger.connect() as conn:
            conn.execute("UPDATE order_emails SET draft_location = ? WHERE message_id = ?", (draft, str(message["Message-ID"])))
    report["draft"] = draft
    (order_dir / "checks.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"READY: {args.order_ref} ({args.product} {args.stage}{'' if not args.issue else f', issue {args.issue} of 4'})")
    print(f"  To: {args.buyer_email}")
    for item in checks.results:
        print(f"  ok  {item['check']}: {item['detail']}")
    print(f"Draft: {draft}")
    print(f"Folder: {order_dir}")
    print("Check the To address and the ref in the subject, then press Send in outreach@. Nothing has been sent.")
    print("Track it with: .venv/bin/python -m tools.orders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
