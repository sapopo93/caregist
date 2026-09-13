#!/usr/bin/env python3
"""What has been sold, and what is actually in the account.

Answers two questions from authoritative sources rather than from a dashboard
someone has to remember to open:

  * Money  - Stripe balance (available and pending), settled charges over a
             window, and live recurring revenue from active subscriptions.
  * Sold   - CRM pipeline by stage, closed-won value, and paid entitlements
             recorded in the application database.

Reads only. Never writes to Stripe or the database. Designed to be run on a
schedule by Hermes and delivered to Telegram, so revenue is visible without
anyone logging in.

Usage:
    python3 tools/revenue_snapshot.py
    python3 tools/revenue_snapshot.py --days 30 --organization-id <uuid>
    python3 tools/revenue_snapshot.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _f(obj, name, default=None):
    """Field access that works for stripe-python v15 objects (no .get) and plain dicts."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    value = getattr(obj, name, default)
    return default if value is None else value


def money(pence: int, symbol: str = "£") -> str:
    return f"{symbol}{pence / 100:,.2f}"


def stripe_side(days: int) -> dict:
    """Balance, settled charges and live MRR straight from Stripe."""
    key = resolve("STRIPE_SECRET_KEY")
    if not key:
        return {"available": False, "reason": "STRIPE_SECRET_KEY is not set."}
    try:
        import stripe
    except ImportError:
        return {"available": False, "reason": "The stripe package is not installed."}
    stripe.api_key = key
    out: dict = {"available": True, "mode": "live" if key.startswith("sk_live") else "test"}
    try:
        balance = stripe.Balance.retrieve()
        out["balance_available"] = {_f(b, "currency"): _f(b, "amount", 0)
                                    for b in _f(balance, "available", [])}
        out["balance_pending"] = {_f(b, "currency"): _f(b, "amount", 0)
                                  for b in _f(balance, "pending", [])}

        since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
        gross = refunded = count = 0
        currency = "gbp"
        for charge in stripe.Charge.list(created={"gte": since}, limit=100).auto_paging_iter():
            if _f(charge, "status") != "succeeded":
                continue
            count += 1
            gross += _f(charge, "amount", 0)
            refunded += _f(charge, "amount_refunded", 0)
            currency = _f(charge, "currency", currency)
        out["charges"] = {"count": count, "gross": gross, "refunded": refunded,
                          "net": gross - refunded, "currency": currency, "days": days}

        mrr = 0
        subs = 0
        for sub in stripe.Subscription.list(status="active", limit=100).auto_paging_iter():
            subs += 1
            for item in _f(_f(sub, "items", {}), "data", []):
                price = _f(item, "price", {}) or {}
                amount = (_f(price, "unit_amount", 0) or 0) * (_f(item, "quantity", 1) or 1)
                interval = _f(_f(price, "recurring", {}) or {}, "interval")
                if interval == "year":
                    amount = amount // 12
                elif interval == "week":
                    amount = amount * 52 // 12
                elif interval == "day":
                    amount = amount * 365 // 12
                mrr += amount
        out["active_subscriptions"] = subs
        out["mrr"] = mrr
    except Exception as exc:  # surfaced, never swallowed
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return out


async def db_side(days: int, organization_id: str | None) -> dict:
    url = resolve("DATABASE_URL")
    if not url:
        return {"available": False, "reason": "DATABASE_URL is not set."}
    conn = await asyncpg.connect(re.sub(r"\?.*$", "", url), ssl="require")
    try:
        out: dict = {"available": True}
        where = "WHERE organization_id = $1" if organization_id else ""
        args = [organization_id] if organization_id else []
        rows = await conn.fetch(
            f"SELECT stage, COUNT(*) n, COALESCE(SUM(value_pence),0) v FROM crm_deals {where} "
            "GROUP BY stage ORDER BY v DESC", *args)
        out["pipeline"] = [{"stage": r["stage"], "deals": r["n"], "value_pence": r["v"]} for r in rows]
        out["pipeline_open_pence"] = sum(
            r["value_pence"] for r in out["pipeline"] if r["stage"] not in ("won", "lost", "suppressed"))
        won = next((r for r in out["pipeline"] if r["stage"] == "won"), None)
        out["won_deals"] = won["deals"] if won else 0
        out["won_value_pence"] = won["value_pence"] if won else 0
        out["won_recent"] = await conn.fetchval(
            f"SELECT COUNT(*) FROM crm_deals {'WHERE organization_id = $2 AND' if organization_id else 'WHERE'} "
            "stage = 'won' AND closed_at >= NOW() - ($1 || ' days')::interval",
            str(days), *args)
        try:
            out["paid_entitlements"] = [
                dict(r) for r in await conn.fetch(
                    "SELECT tier, status, COUNT(*) n FROM subscriptions GROUP BY 1,2 ORDER BY n DESC")]
        except Exception as exc:
            out["paid_entitlements"] = f"unavailable: {type(exc).__name__}"
        out["stripe_events_processed"] = await conn.fetchval(
            "SELECT COUNT(*) FROM stripe_processed_events")
        out["emails_unsent"] = await conn.fetchval(
            "SELECT COUNT(*) FROM pending_emails WHERE sent_at IS NULL")
        return out
    finally:
        await conn.close()


def render(stripe_data: dict, db: dict, days: int) -> str:
    lines = [f"REVENUE SNAPSHOT  {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC  (window: {days}d)", ""]

    lines.append("IN THE ACCOUNT")
    if not stripe_data.get("available"):
        lines.append(f"  unavailable - {stripe_data.get('reason')}")
    elif stripe_data.get("error"):
        lines.append(f"  Stripe error - {stripe_data['error']}")
    else:
        avail = stripe_data.get("balance_available", {})
        pend = stripe_data.get("balance_pending", {})
        lines.append(f"  mode: {stripe_data['mode']}")
        lines.append("  available: " + (", ".join(f"{money(v)} {c.upper()}" for c, v in avail.items()) or "nothing"))
        lines.append("  pending:   " + (", ".join(f"{money(v)} {c.upper()}" for c, v in pend.items()) or "nothing"))
        ch = stripe_data.get("charges", {})
        lines.append(f"  settled in {ch.get('days', days)}d: {ch.get('count', 0)} charges, "
                     f"net {money(ch.get('net', 0))}")
        lines.append(f"  active subscriptions: {stripe_data.get('active_subscriptions', 0)}  "
                     f"MRR {money(stripe_data.get('mrr', 0))}")

    lines += ["", "SOLD"]
    if not db.get("available"):
        lines.append(f"  unavailable - {db.get('reason')}")
    else:
        lines.append(f"  closed won: {db['won_deals']} deals, {money(db['won_value_pence'])} "
                     f"({db['won_recent']} in the last {days}d)")
        lines.append(f"  open pipeline: {money(db['pipeline_open_pence'])}")
        for row in db["pipeline"]:
            lines.append(f"    {row['stage']:<20} {row['deals']:>4}  {money(row['value_pence'])}")
        lines.append(f"  paid entitlements: {db['paid_entitlements']}")
        lines.append(f"  stripe events processed: {db['stripe_events_processed']}")
        if db["emails_unsent"]:
            lines.append(f"  WARNING: {db['emails_unsent']} fulfilment emails unsent")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--organization-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    stripe_data = stripe_side(args.days)
    db = asyncio.run(db_side(args.days, args.organization_id))
    if args.json:
        print(json.dumps({"stripe": stripe_data, "database": db}, indent=1, default=str))
    else:
        print(render(stripe_data, db, args.days))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
