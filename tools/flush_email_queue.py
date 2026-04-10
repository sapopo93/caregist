#!/usr/bin/env python3
"""Process the pending_emails table and send any queued emails via Resend.

Run after run_new_registration_feed_cycle.py (or any job that queues emails)
to flush the queue and actually deliver.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg
import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("flush_email_queue")


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


async def flush(database_url: str, resend_api_key: str, from_email: str, batch_size: int = 50) -> int:
    conn = await asyncpg.connect(database_url)
    sent = 0
    try:
        rows = await conn.fetch(
            """
            SELECT id, to_email, subject, html_body, attempts
            FROM pending_emails
            WHERE status = 'pending' AND send_after <= NOW() AND attempts < 3
            ORDER BY send_after ASC
            LIMIT $1
            """,
            batch_size,
        )
        if not rows:
            logger.info("No pending emails to send.")
            return 0

        logger.info("Found %d pending email(s) to send.", len(rows))
        async with httpx.AsyncClient(timeout=15) as client:
            for row in rows:
                try:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {resend_api_key}"},
                        json={
                            "from": from_email,
                            "to": [row["to_email"]],
                            "subject": row["subject"],
                            "html": row["html_body"],
                        },
                    )
                    if resp.status_code in (200, 201):
                        await conn.execute(
                            "UPDATE pending_emails SET status = 'sent', sent_at = NOW() WHERE id = $1",
                            row["id"],
                        )
                        logger.info("Sent email id=%s to %s", row["id"], row["to_email"])
                        sent += 1
                    else:
                        await conn.execute(
                            "UPDATE pending_emails SET attempts = attempts + 1 WHERE id = $1",
                            row["id"],
                        )
                        logger.warning(
                            "Resend returned %s for email id=%s: %s",
                            resp.status_code, row["id"], resp.text[:200],
                        )
                except Exception as exc:
                    await conn.execute(
                        "UPDATE pending_emails SET attempts = attempts + 1 WHERE id = $1",
                        row["id"],
                    )
                    logger.warning("Failed to send email id=%s: %s", row["id"], exc)
    finally:
        await conn.close()
    return sent


def main() -> int:
    _load_env_file()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        return 1

    resend_api_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_api_key:
        print("ERROR: RESEND_API_KEY not set.", file=sys.stderr)
        return 1

    from_email = os.environ.get("ENQUIRY_FROM_EMAIL", "CareGist <noreply@caregist.co.uk>")

    sent = asyncio.run(flush(database_url, resend_api_key, from_email))
    print(f"flush_email_queue: sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
