#!/usr/bin/env python3
"""Stripe subscription reconciliation tool.

Compares active subscriptions in Stripe against the local `subscriptions` table
and reports (or optionally fixes) divergences.

Run manually or as a weekly cron job:
    python3 tools/reconcile_stripe_subscriptions.py [--fix] [--database-url URL]

Divergence types detected:
  - Stripe subscription active, not in local DB (missed webhook)
  - Stripe subscription active, but local status is 'canceled' or 'past_due'
  - Stripe subscription canceled, but local status is 'active'
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("caregist.reconcile_stripe")


def resolve_database_url(cli_value: str | None) -> str | None:
    if cli_value:
        return cli_value
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    return None


def _init_stripe() -> bool:
    """Load Stripe API key from settings. Returns True if configured."""
    try:
        import stripe
        from api.config import settings
        if not settings.stripe_secret_key:
            logger.error("STRIPE_SECRET_KEY not set.")
            return False
        stripe.api_key = settings.stripe_secret_key
        return True
    except Exception as exc:
        logger.error("Failed to initialise Stripe: %s", exc)
        return False


async def reconcile(database_url: str, *, fix: bool = False) -> dict:
    """
    Main reconciliation loop.

    Returns a summary dict: {checked, missing_locally, status_mismatch, fixed}.
    """
    import stripe

    conn = await asyncpg.connect(database_url)
    try:
        # 1. Fetch all active Stripe subscriptions
        logger.info("Fetching active subscriptions from Stripe...")
        stripe_subs: dict[str, dict] = {}
        params: dict = {"status": "all", "limit": 100, "expand": ["data.customer"]}
        while True:
            page = stripe.Subscription.list(**params)
            for sub in page.data:
                stripe_subs[sub["id"]] = sub
            if not page.has_more:
                break
            params["starting_after"] = page.data[-1]["id"]
        logger.info("Fetched %d Stripe subscriptions.", len(stripe_subs))

        # 2. Load our local subscriptions
        local_rows = await conn.fetch(
            "SELECT stripe_subscription_id, status, tier, user_id FROM subscriptions"
        )
        local_by_stripe_id = {r["stripe_subscription_id"]: r for r in local_rows}

        missing_locally = []
        status_mismatch = []

        for stripe_id, stripe_sub in stripe_subs.items():
            stripe_status = stripe_sub["status"]  # active, past_due, canceled, etc.
            local = local_by_stripe_id.get(stripe_id)

            if local is None:
                if stripe_status in ("active", "trialing", "past_due"):
                    missing_locally.append(stripe_id)
                    logger.warning(
                        "MISSING LOCALLY: Stripe subscription %s is %s but has no local record.",
                        stripe_id, stripe_status,
                    )
            else:
                local_status = local["status"]
                # Divergence: active in Stripe, not active locally
                if stripe_status == "active" and local_status not in ("active", "trialing"):
                    status_mismatch.append((stripe_id, stripe_status, local_status))
                    logger.warning(
                        "STATUS MISMATCH: %s — Stripe=%s local=%s (user_id=%s tier=%s)",
                        stripe_id, stripe_status, local_status, local["user_id"], local["tier"],
                    )
                # Divergence: canceled in Stripe but still active locally
                elif stripe_status == "canceled" and local_status == "active":
                    status_mismatch.append((stripe_id, stripe_status, local_status))
                    logger.warning(
                        "STATUS MISMATCH: %s — Stripe=canceled local=active (user_id=%s tier=%s) — "
                        "user may still have paid-tier access.",
                        stripe_id, local["user_id"], local["tier"],
                    )
                    if fix:
                        await conn.execute(
                            "UPDATE subscriptions SET status = 'canceled' WHERE stripe_subscription_id = $1",
                            stripe_id,
                        )
                        await conn.execute(
                            "UPDATE api_keys SET tier = 'free' WHERE user_id = $1",
                            local["user_id"],
                        )
                        logger.info("FIXED: Downgraded user %s to free (sub %s).", local["user_id"], stripe_id)

        # 3. Check for local active subs whose Stripe sub no longer exists
        for local in local_rows:
            stripe_id = local["stripe_subscription_id"]
            if not stripe_id:
                continue
            if local["status"] == "active" and stripe_id not in stripe_subs:
                logger.warning(
                    "ORPHANED LOCAL SUB: %s has status=active but Stripe sub %s not found (user_id=%s).",
                    stripe_id, stripe_id, local["user_id"],
                )
                status_mismatch.append((stripe_id, "not_in_stripe", "active"))
                if fix:
                    await conn.execute(
                        "UPDATE subscriptions SET status = 'canceled' WHERE stripe_subscription_id = $1",
                        stripe_id,
                    )
                    await conn.execute(
                        "UPDATE api_keys SET tier = 'free' WHERE user_id = $1",
                        local["user_id"],
                    )
                    logger.info("FIXED: Downgraded orphaned user %s to free.", local["user_id"])

        return {
            "stripe_total": len(stripe_subs),
            "local_total": len(local_rows),
            "missing_locally": len(missing_locally),
            "status_mismatch": len(status_mismatch),
            "fixed": fix,
        }
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile Stripe subscriptions with local DB")
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply fixes: downgrade canceled/orphaned local subs to free tier",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = resolve_database_url(args.database_url)
    if not database_url:
        logger.error("DATABASE_URL not set.")
        return 1
    if not _init_stripe():
        return 1

    result = asyncio.run(reconcile(database_url, fix=args.fix))
    logger.info(
        "Reconciliation complete: stripe_total=%d local_total=%d "
        "missing_locally=%d status_mismatch=%d fixed=%s",
        result["stripe_total"],
        result["local_total"],
        result["missing_locally"],
        result["status_mismatch"],
        result["fixed"],
    )
    return 1 if (result["missing_locally"] or result["status_mismatch"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
