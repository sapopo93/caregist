"""Lightweight email queue using pending_emails table."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from api.config import settings
from api.database import get_connection

logger = logging.getLogger("caregist.email_queue")


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
        async with get_connection() as conn:
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

            if not rows or not settings.resend_api_key:
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
                                "UPDATE pending_emails SET status = 'sent', sent_at = NOW() WHERE id = $1",
                                row["id"],
                            )
                            sent += 1
                        else:
                            await conn.execute(
                                "UPDATE pending_emails SET attempts = attempts + 1 WHERE id = $1",
                                row["id"],
                            )
                            logger.warning("Resend returned %s for email %s", resp.status_code, row["id"])
                    except Exception as exc:
                        await conn.execute(
                            "UPDATE pending_emails SET attempts = attempts + 1 WHERE id = $1",
                            row["id"],
                        )
                        logger.warning("Failed to send email %s: %s", row["id"], exc)
    except Exception as exc:
        logger.error("Email queue processing failed: %s", exc)

    return sent
