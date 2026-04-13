"""Lightweight email queue using pending_emails table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from api.config import settings
from api.database import get_connection

logger = logging.getLogger("caregist.email_queue")

EMAIL_PROCESSING_STALE_SECONDS = 900


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
) -> int | None:
    """Insert an email into the pending queue. Returns the row id."""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO pending_emails (to_email, subject, html_body, send_after)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                to_email,
                subject,
                html_body,
                send_after or datetime.now(timezone.utc),
            )
            return row["id"] if row else None
    except Exception as exc:
        logger.warning("Failed to queue email to %s: %s", to_email, exc)
        return None


async def process_email_queue(batch_size: int = 10) -> int:
    """Process pending emails via Resend. Returns count of emails sent.

    Call this periodically (e.g. from a BackgroundTasks dependency or cron).
    """
    import httpx

    sent = 0
    try:
        if not settings.resend_api_key:
            return 0

        async with get_connection() as conn:
            rows = await _claim_pending_emails(conn, batch_size)
            if not rows:
                return 0

            async with httpx.AsyncClient(timeout=10) as client:
                for row in rows:
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
                        if resp.status_code in (200, 201):
                            await conn.execute(
                                """
                                UPDATE pending_emails
                                SET status = 'sent',
                                    sent_at = NOW(),
                                    processing_started_at = NULL
                                WHERE id = $1
                                """,
                                row["id"],
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
                                row["id"],
                                _next_failure_status(int(row["attempts"] or 0)),
                            )
                            logger.warning("Resend returned %s for email %s", resp.status_code, row["id"])
                    except Exception as exc:
                        await conn.execute(
                            """
                            UPDATE pending_emails
                            SET attempts = attempts + 1,
                                status = $2,
                                processing_started_at = NULL
                            WHERE id = $1
                            """,
                            row["id"],
                            _next_failure_status(int(row["attempts"] or 0)),
                        )
                        logger.warning("Failed to send email %s: %s", row["id"], exc)
    except Exception as exc:
        logger.error("Email queue processing failed: %s", exc)

    return sent
