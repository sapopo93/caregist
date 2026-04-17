"""Lightweight email queue using pending_emails table."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from api.config import settings
from api.database import get_connection

logger = logging.getLogger("caregist.email_queue")

EMAIL_PROCESSING_STALE_SECONDS = 900
# Max concurrent Resend API calls per batch. Keeps us well under Resend's
# default 10 rps rate limit even on large batches.
_SEND_CONCURRENCY = 5


async def _claim_pending_emails(conn, batch_size: int) -> list[dict[str, Any]]:
    """Atomically claim a batch of pending emails for processing."""
    rows = await conn.fetch(
        """
        WITH candidates AS (
            SELECT id
            FROM pending_emails
            WHERE send_after <= NOW()
              AND attempts < 3
              AND (
                status = 'pending'
                OR (
                  status = 'processing'
                  AND processing_started_at IS NOT NULL
                  AND processing_started_at <= NOW() - make_interval(secs => $2)
                )
              )
            ORDER BY send_after ASC, id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT $1
        )
        UPDATE pending_emails pe
        SET status = 'processing',
            processing_started_at = NOW()
        FROM candidates
        WHERE pe.id = candidates.id
        RETURNING pe.id, pe.to_email, pe.subject, pe.html_body, pe.attempts
        """,
        batch_size,
        EMAIL_PROCESSING_STALE_SECONDS,
    )
    return [dict(row) for row in rows]


def _next_failure_status(attempts: int) -> str:
    return "failed" if attempts + 1 >= 3 else "pending"


async def queue_email(
    to_email: str,
    subject: str,
    html_body: str,
    *,
    send_after: datetime | None = None,
    idempotency_key: str | None = None,
) -> int | None:
    """Insert an email into the pending queue. Returns the row id.

    If idempotency_key is provided and a row with that key already exists, the
    INSERT is silently ignored and None is returned — preventing duplicate emails
    on retries or concurrent claim submissions.
    """
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO pending_emails (to_email, subject, html_body, send_after, idempotency_key)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
                RETURNING id
                """,
                to_email,
                subject,
                html_body,
                send_after or datetime.now(timezone.utc),
                idempotency_key,
            )
            return row["id"] if row else None
    except Exception as exc:
        logger.warning("Failed to queue email to %s: %s", to_email, exc)
        return None


async def process_email_queue(batch_size: int = 20) -> int:
    """Process pending emails via Resend. Returns count of emails sent.

    Three-phase design:
      Phase 1 — Claim: acquire emails with FOR UPDATE SKIP LOCKED (DB connection held briefly).
      Phase 2 — Send: dispatch HTTP requests concurrently with a bounded semaphore
                (DB connection released — no connection held during network I/O).
      Phase 3 — Update: write send outcomes back to DB in a single batch.

    This prevents a Resend API latency spike from holding Postgres connections
    open for the full send duration.
    """
    import httpx

    if not settings.resend_api_key:
        return 0

    # Phase 1: claim
    try:
        async with get_connection() as conn:
            rows = await _claim_pending_emails(conn, batch_size)
    except Exception as exc:
        logger.error("Email queue claim phase failed: %s", exc)
        return 0

    if not rows:
        return 0

    # Phase 2: send concurrently (no DB connection held)
    semaphore = asyncio.Semaphore(_SEND_CONCURRENCY)

    async def _send_one(client: httpx.AsyncClient, row: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            try:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                    json={
                        "from": settings.enquiry_from_email or "CareGist <noreply@caregist.co.uk>",
                        "to": [row["to_email"]],
                        "subject": row["subject"],
                        "html": row["html_body"],
                    },
                )
                success = resp.status_code in (200, 201)
                if not success:
                    logger.warning("Resend returned %s for email %s", resp.status_code, row["id"])
                return {"id": row["id"], "attempts": row["attempts"], "success": success}
            except Exception as exc:
                logger.warning("Failed to send email %s: %s", row["id"], exc)
                return {"id": row["id"], "attempts": row["attempts"], "success": False}

    async with httpx.AsyncClient(timeout=10) as client:
        results = await asyncio.gather(*[_send_one(client, row) for row in rows])

    # Phase 3: write outcomes
    sent = 0
    try:
        async with get_connection() as conn:
            for result in results:
                if result["success"]:
                    await conn.execute(
                        """
                        UPDATE pending_emails
                        SET status = 'sent',
                            sent_at = NOW(),
                            processing_started_at = NULL
                        WHERE id = $1
                        """,
                        result["id"],
                    )
                    sent += 1
                else:
                    await conn.execute(
                        """
                        UPDATE pending_emails
                        SET attempts = attempts + 1,
                            status = $2,
                            processing_started_at = NULL
                        WHERE id = $1
                        """,
                        result["id"],
                        _next_failure_status(int(result["attempts"] or 0)),
                    )
    except Exception as exc:
        logger.error("Email queue update phase failed: %s", exc)

    return sent
