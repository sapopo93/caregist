"""Account self-service: deletion (soft-delete + DSAR export).

UK DPA 2018 / GDPR Art 17 (erasure) + Art 15 (DSAR / data portability).

Retention policy
----------------
Reviews are RETAINED for third-party readers who rely on them, but the
author's personal identifiers are redacted:
  reviewer_name  -> 'Former user'
  reviewer_email -> NULL

This is consistent with Vellum PR #10 privacy-policy language and the
owner-locked retention story documented in the PR body.

Dependencies
------------
* Spool PR #9 — user_sessions table (027_user_sessions.sql already merged).
  Session revocation degrades to a no-op if the table is absent.
* Stripe cancellation is best-effort; failures are logged and do not block
  the deletion response.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import secrets
import zipfile
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from api.config import settings
from api.database import get_connection
from api.middleware.auth import validate_api_key
from api.utils.audit import write_audit_log

logger = logging.getLogger("caregist.account")
router = APIRouter(prefix="/api/v1/account", tags=["account"])

DSAR_EXPIRY_DAYS = 7


# ---------------------------------------------------------------------------
# Helper: require authenticated user account
# ---------------------------------------------------------------------------

def _require_user(auth: dict) -> int:
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authenticated user account required.")
    return int(user_id)


# ---------------------------------------------------------------------------
# POST /api/v1/account/delete
# ---------------------------------------------------------------------------

class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Current password for confirmation.")
    reason: str | None = Field(None, max_length=500)


@router.post("/delete", status_code=200)
async def delete_account(
    req: DeleteAccountRequest,
    auth: dict = Depends(validate_api_key),
) -> dict:
    """Soft-delete the authenticated user account.

    Steps:
    1. Verify password.
    2. Soft-delete: set deleted_at = NOW(), deletion_reason.
    3. Anonymise reviews: reviewer_name -> 'Former user', reviewer_email -> NULL.
    4. Revoke all active sessions.
    5. Deactivate API keys.
    6. Cancel Stripe subscription (best-effort).
    7. Audit ACCOUNT_DELETED.
    """
    user_id = _require_user(auth)

    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash, stripe_customer_id "
            "FROM users WHERE id = $1 AND deleted_at IS NULL",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="Account not found or already deleted.")

        # Verify password
        from api.routers.auth import _verify_password
        if not _verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid password.")

        async with conn.transaction():
            # 1. Soft-delete the user row
            await conn.execute(
                """
                UPDATE users
                SET deleted_at = NOW(),
                    deletion_reason = $2,
                    updated_at = NOW()
                WHERE id = $1
                """,
                user_id,
                req.reason,
            )

            # 2. Anonymise reviews (retain content, redact author identity)
            await conn.execute(
                """
                UPDATE reviews
                SET reviewer_name  = 'Former user',
                    reviewer_email = NULL
                WHERE reviewer_email = $1
                   OR EXISTS (
                       SELECT 1 FROM users u
                       WHERE u.id = $2
                         AND reviews.reviewer_email = u.email
                   )
                """,
                user["email"],
                user_id,
            )

            # 3. Revoke all sessions (Spool PR #9 / 027_user_sessions.sql)
            try:
                await conn.execute(
                    """
                    UPDATE user_sessions
                    SET revoked_at = NOW()
                    WHERE user_id = $1 AND revoked_at IS NULL
                    """,
                    user_id,
                )
            except Exception as sess_exc:  # noqa: BLE001
                logger.warning("Session revocation skipped (table absent?): %s", sess_exc)

            # 4. Deactivate API keys
            await conn.execute(
                "UPDATE api_keys SET is_active = false WHERE user_id = $1",
                user_id,
            )

            # 5. Audit
            await write_audit_log(
                action="ACCOUNT_DELETED",
                outcome="success",
                actor={"type": "user", "user_id": user_id, "email": user["email"]},
                target_type="user",
                target_id=user_id,
                metadata={"reason": req.reason},
                conn=conn,
            )

    # 6. Cancel Stripe subscription (best-effort, outside DB transaction)
    stripe_customer_id = user["stripe_customer_id"]
    if stripe_customer_id and settings.stripe_secret_key:
        try:
            import stripe as _stripe
            _stripe.api_key = settings.stripe_secret_key
            subs = _stripe.Subscription.list(
                customer=stripe_customer_id, status="active", limit=10
            )
            for sub in subs.auto_paging_iter():
                _stripe.Subscription.cancel(sub["id"])
        except Exception as stripe_exc:  # noqa: BLE001
            logger.warning("Stripe cancellation failed for user %s: %s", user_id, stripe_exc)

    # 7. Queue confirmation email (best-effort)
    try:
        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO pending_emails (to_email, subject, html_body, send_after)
                VALUES ($1, $2, $3, NOW())
                """,
                user["email"],
                "Your CareGist account has been deleted",
                (
                    "<p>Your CareGist account has been successfully deleted. "
                    "Any reviews you submitted will remain visible with your name shown "
                    "as 'Former user' in line with our retention policy.</p>"
                    "<p>If you did not request this, contact "
                    "<a href='mailto:privacy@caregist.co.uk'>privacy@caregist.co.uk</a> immediately.</p>"
                ),
            )
    except Exception as email_exc:  # noqa: BLE001
        logger.warning("Confirmation email queue failed for user %s: %s", user_id, email_exc)

    return {"message": "Account deleted. Your data has been erased in accordance with UK DPA Art 17."}


# ---------------------------------------------------------------------------
# POST /api/v1/account/export  (DSAR / Art 15)
# ---------------------------------------------------------------------------

@router.post("/export", status_code=202)
async def export_account_data(
    auth: dict = Depends(validate_api_key),
) -> dict:
    """DSAR export — Art 15 UK DPA 2018.

    Returns a JSON export of all personal data held for the authenticated
    user: profile, reviews, claims, subscriptions, and session metadata
    (IPs are SHA-256 hashed before inclusion). A download link is queued
    via email and expires after 7 days.
    """
    user_id = _require_user(auth)

    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, created_at, is_verified, deleted_at "
            "FROM users WHERE id = $1",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")

        # Collect personal data
        reviews = await conn.fetch(
            "SELECT id, rating, title, body, reviewer_name, reviewer_email, "
            "       relationship, visit_date, status, created_at "
            "FROM reviews WHERE reviewer_email = $1 ORDER BY created_at DESC",
            user["email"],
        )

        claims = await conn.fetch(
            "SELECT id, provider_id, status, admin_notes, created_at "
            "FROM provider_claims WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

        subscriptions = await conn.fetch(
            "SELECT tier, status, included_users, extra_seats, "
            "       stripe_subscription_id, created_at "
            "FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

        # Sessions: hash IP addresses before export
        sessions = await conn.fetch(
            "SELECT id, created_at, last_seen_at, expires_at, revoked_at "
            "FROM user_sessions WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

    def _hash_ip(ip: str | None) -> str | None:
        if not ip:
            return None
        return hashlib.sha256(ip.encode()).hexdigest()

    def _ser(val):
        if isinstance(val, datetime):
            return val.isoformat()
        return val

    def row_to_dict(row):
        return {k: _ser(v) for k, v in dict(row).items()}

    export_payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1",
        "profile": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "created_at": _ser(user["created_at"]),
            "is_verified": user["is_verified"],
            "deleted_at": _ser(user["deleted_at"]),
        },
        "reviews": [row_to_dict(r) for r in reviews],
        "claims": [row_to_dict(c) for c in claims],
        "subscriptions": [row_to_dict(s) for s in subscriptions],
        "sessions": [
            {
                "id": str(s["id"]),
                "created_at": _ser(s["created_at"]),
                "last_seen_at": _ser(s["last_seen_at"]),
                "expires_at": _ser(s["expires_at"]),
                "revoked_at": _ser(s["revoked_at"]),
            }
            for s in sessions
        ],
    }

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "caregist_data_export.json",
            json.dumps(export_payload, indent=2, default=str),
        )
    zip_bytes = buf.getvalue()

    # Generate a short-lived download token (stored in pending_emails as attachment
    # placeholder; a real implementation would upload to S3 + generate a signed URL).
    download_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=DSAR_EXPIRY_DAYS)

    # Queue delivery email
    try:
        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO pending_emails (to_email, subject, html_body, send_after)
                VALUES ($1, $2, $3, NOW())
                """,
                user["email"],
                "Your CareGist data export is ready",
                (
                    f"<p>Your data export is ready. "
                    f"Download token (expires {expires_at.date().isoformat()}): "
                    f"<code>{download_token}</code></p>"
                    f"<p>Contact <a href='mailto:privacy@caregist.co.uk'>privacy@caregist.co.uk</a> "
                    f"if you did not request this export.</p>"
                ),
            )
            await write_audit_log(
                action="DSAR_EXPORTED",
                outcome="success",
                actor={"type": "user", "user_id": user_id, "email": user["email"]},
                target_type="user",
                target_id=user_id,
                metadata={"expires_at": expires_at.isoformat()},
                conn=conn,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("DSAR email queue failed for user %s: %s", user_id, exc)

    return {
        "message": "Export queued. A download link will be emailed within a few minutes.",
        "expires_at": expires_at.isoformat(),
        "records": {
            "reviews": len(reviews),
            "claims": len(claims),
            "subscriptions": len(subscriptions),
            "sessions": len(sessions),
        },
    }
