"""User registration, login, and API key management."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from api.config import settings, get_tier_config
from api.database import get_connection

logger = logging.getLogger("caregist.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, stored: str) -> bool:
    # bcrypt hashes start with $2b$
    if stored.startswith("$2b$"):
        return bcrypt.checkpw(password.encode(), stored.encode())
    # Legacy SHA-256 fallback: "salt:hash" format
    if ":" in stored:
        salt, hashed = stored.split(":", 1)
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest() == hashed
    return False


async def _rehash_if_legacy(user_id: int, password: str, stored: str) -> None:
    """Re-hash a legacy SHA-256 password to bcrypt on successful login."""
    if not stored.startswith("$2b$"):
        new_hash = _hash_password(password)
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE id = $2",
                new_hash, user_id,
            )


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(req: RegisterRequest) -> dict:
    """Register a new user and generate a free-tier API key."""
    async with get_connection() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", req.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered.")

        password_hash = _hash_password(req.password)
        verification_token = secrets.token_urlsafe(32)
        api_key = f"cg_{secrets.token_urlsafe(32)}"

        async with conn.transaction():
            user = await conn.fetchrow(
                """INSERT INTO users (email, name, password_hash, verification_token, is_verified)
                   VALUES ($1, $2, $3, $4, true)
                   RETURNING id, email, name""",
                req.email, req.name, password_hash, verification_token,
            )

            await conn.execute(
                """INSERT INTO api_keys (key, name, email, tier, rate_limit, is_active, user_id)
                   VALUES ($1, $2, $3, 'free', $4, true, $5)""",
                api_key, req.name, req.email, get_tier_config("free")["rate"], user["id"],
            )

            await conn.execute(
                """INSERT INTO subscriptions (user_id, tier, status)
                   VALUES ($1, 'free', 'active')""",
                user["id"],
            )

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "api_key": api_key,
        "tier": "free",
        "rate_limit": get_tier_config("free")["rate"],
        "message": "Registration successful. Your API key is ready to use.",
    }


@router.post("/login")
async def login(req: LoginRequest) -> dict:
    """Login and retrieve API key."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash FROM users WHERE email = $1",
            req.email,
        )

    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Upgrade legacy SHA-256 hash to bcrypt on successful login
    await _rehash_if_legacy(user["id"], req.password, user["password_hash"])

    async with get_connection() as conn:
        key_row = await conn.fetchrow(
            "SELECT key, tier, rate_limit FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )

    if not key_row:
        raise HTTPException(status_code=404, detail="No active API key found. Contact support.")

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "api_key": key_row["key"],
        "tier": key_row["tier"],
        "rate_limit": key_row["rate_limit"],
    }


@router.post("/rotate-key")
async def rotate_key(req: LoginRequest) -> dict:
    """Generate a new API key (invalidates old one)."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash FROM users WHERE email = $1",
            req.email,
        )

    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    new_key = f"cg_{secrets.token_urlsafe(32)}"

    async with get_connection() as conn:
        # Get current tier
        current = await conn.fetchrow(
            "SELECT tier, rate_limit FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )
        tier = current["tier"] if current else "free"
        rate_limit = current["rate_limit"] if current else get_tier_config("free")["rate"]

        # Deactivate old keys
        await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE user_id = $1",
            user["id"],
        )

        # Create new key
        await conn.execute(
            """INSERT INTO api_keys (key, name, email, tier, rate_limit, is_active, user_id)
               VALUES ($1, $2, $3, $4, $5, true, $6)""",
            new_key, user["name"], user["email"], tier, rate_limit, user["id"],
        )

    return {"api_key": new_key, "tier": tier, "rate_limit": rate_limit}


# --- Password reset ---


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8)


MAX_RESET_ATTEMPTS = 5


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest) -> dict:
    """Generate a 6-digit reset code and email it via Resend."""
    # Always return success to avoid email enumeration
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", req.email)

    if not user:
        return {"message": "If that email is registered, a reset code has been sent."}

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    async with get_connection() as conn:
        await conn.execute(
            """INSERT INTO password_reset_tokens (token, email, expires_at)
               VALUES ($1, $2, $3)""",
            code, req.email, expires_at,
        )

    # Send email (best-effort)
    await _send_reset_email(req.email, code)

    return {"message": "If that email is registered, a reset code has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest) -> dict:
    """Validate reset code and update password."""
    async with get_connection() as conn:
        # Check for too many failed attempts in the last 15 minutes
        attempt_count = await conn.fetchval(
            """SELECT COUNT(*) FROM password_reset_tokens
               WHERE email = $1 AND used = false AND attempts >= $2
               AND expires_at > NOW()""",
            req.email, MAX_RESET_ATTEMPTS,
        )
        if attempt_count and attempt_count > 0:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

        token_row = await conn.fetchrow(
            """SELECT id, expires_at, used, attempts FROM password_reset_tokens
               WHERE email = $1 AND token = $2
               ORDER BY created_at DESC LIMIT 1""",
            req.email, req.token,
        )

        if not token_row or token_row["used"] or token_row["expires_at"] < datetime.now(timezone.utc):
            # Increment attempt counter on the most recent token for this email
            await conn.execute(
                """UPDATE password_reset_tokens SET attempts = attempts + 1
                   WHERE id = (
                       SELECT id FROM password_reset_tokens
                       WHERE email = $1 AND used = false
                       ORDER BY created_at DESC LIMIT 1
                   )""",
                req.email,
            )
            raise HTTPException(status_code=400, detail="Invalid or expired reset code.")

        new_hash = _hash_password(req.new_password)

        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE email = $2",
                new_hash, req.email,
            )
            await conn.execute(
                "UPDATE password_reset_tokens SET used = true WHERE id = $1",
                token_row["id"],
            )

    return {"message": "Password has been reset. You can now log in."}


async def _send_reset_email(email: str, code: str) -> None:
    """Send password reset code via Resend. Fails silently."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping password reset email for %s", email)
        return

    import httpx

    from_email = settings.enquiry_from_email or "noreply@caregist.co.uk"
    body = (
        f"Your CareGist password reset code is: {code}\n\n"
        f"This code expires in 15 minutes. If you didn't request this, ignore this email.\n\n"
        f"— The CareGist Team"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": from_email,
                    "to": [email],
                    "subject": "Your CareGist password reset code",
                    "text": body,
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("Resend API error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Failed to send reset email: %s", exc)
