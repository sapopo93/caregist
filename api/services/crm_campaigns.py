"""UK email-campaign eligibility, safe rendering, and suppression tokens."""

from __future__ import annotations

import hashlib
import secrets
from html import escape
from urllib.parse import quote

from api.config import settings
from api.database import get_connection


MAX_CAMPAIGN_RECIPIENTS = 500


def is_email_marketing_eligible(
    *, market_code: str, subscriber_type: str, marketing_basis: str, email: str | None
) -> bool:
    if market_code != "GB" or not email:
        return False
    if marketing_basis == "corporate_subscriber":
        return subscriber_type == "corporate"
    if marketing_basis in {"consent", "soft_opt_in"}:
        return True
    return False


def create_unsubscribe_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_unsubscribe_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def render_campaign_html(body_text: str, unsubscribe_token: str) -> str:
    paragraphs = "".join(
        f"<p>{escape(block.strip())}</p>"
        for block in body_text.replace("\r\n", "\n").split("\n\n")
        if block.strip()
    )
    unsubscribe_url = (
        settings.app_url.rstrip("/")
        + "/api/v1/crm/email/unsubscribe/"
        + quote(unsubscribe_token, safe="")
    )
    return (
        '<div style="font-family:Arial,sans-serif;line-height:1.55;color:#242424">'
        + paragraphs
        + '<hr style="margin-top:28px;border:0;border-top:1px solid #ddd">'
        + '<p style="font-size:12px;color:#666">'
        + escape(settings.crm_email_sender_postal_address)
        + ". "
        + f'<a href="{escape(unsubscribe_url, quote=True)}">Unsubscribe from CareGist marketing</a>.</p>'
        + "</div>"
    )


async def finalize_campaigns() -> int:
    """Mark campaigns complete after every queued email reaches a terminal state."""
    if not settings.crm_email_campaigns_enabled:
        return 0
    async with get_connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('caregist.worker', 'crm_campaigns', true)")
            result = await conn.execute(
                """
                UPDATE crm_email_campaigns campaign
                SET status = 'completed', updated_at = NOW()
                WHERE campaign.status IN ('queued', 'sending')
                  AND EXISTS (
                    SELECT 1 FROM crm_email_deliveries delivery
                    WHERE delivery.campaign_id = campaign.id
                  )
                  AND NOT EXISTS (
                    SELECT 1
                    FROM crm_email_deliveries delivery
                    JOIN pending_emails email ON email.id = delivery.queued_email_id
                    WHERE delivery.campaign_id = campaign.id
                      AND email.status IN ('pending', 'processing')
                  )
                """
            )
    return int(result.rsplit(" ", 1)[-1])
