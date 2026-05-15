"""User registration, login, and API key management."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

try:
    import bcrypt
except ImportError:  # pragma: no cover - local fallback when bcrypt is unavailable
    bcrypt = None
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from api.middleware.ip_rate_limit import check_ip_rate_limit

from api.config import get_max_users, get_subscription_entitlements, get_tier_config, settings
from api.database import get_connection
from api.middleware.auth import api_key_prefix, hash_api_key, validate_api_key
from api.utils.audit import actor_from_auth, write_audit_log

logger = logging.getLogger("caregist.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

FAILED_ATTEMPT_LIMIT = 5
FAILED_ATTEMPT_LOCK_SECONDS = 15 * 60
GENERIC_AUTH_FAILURE = "Invalid email or password."
_failed_auth_attempts: dict[tuple[str, str], dict[str, float | int]] = {}

if bcrypt:
    _DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()
else:
    _DUMMY_HASH = "fallback:dummy"


def _failed_attempt_key(email: str, action: str) -> tuple[str, str]:
    return (email.strip().casefold(), action)


def _check_failed_attempts(email: str, action: str) -> None:
    state = _failed_auth_attempts.get(_failed_attempt_key(email, action))
    if not state:
        return
    locked_until = float(state.get("locked_until", 0))
    if locked_until > time.monotonic():
        raise HTTPException(status_code=429, detail=GENERIC_AUTH_FAILURE)
    if locked_until:
        _failed_auth_attempts.pop(_failed_attempt_key(email, action), None)


def _record_failed_attempt(email: str, action: str) -> None:
    key = _failed_attempt_key(email, action)
    state = _failed_auth_attempts.setdefault(key, {"count": 0, "locked_until": 0})
    state["count"] = int(state["count"]) + 1
    if int(state["count"]) >= FAILED_ATTEMPT_LIMIT:
        state["locked_until"] = time.monotonic() + FAILED_ATTEMPT_LOCK_SECONDS


def _reset_failed_attempts(email: str, action: str) -> None:
    _failed_auth_attempts.pop(_failed_attempt_key(email, action), None)


async def _raise_auth_failure(email: str, action: str, audit_action: str | None = None) -> None:
    _record_failed_attempt(email, action)
    await write_audit_log(
        action=audit_action or action,
        outcome="failure",
        actor={"type": "anonymous", "email": email},
        target_type="user",
        target_id=email,
    )
    raise HTTPException(status_code=401, detail=GENERIC_AUTH_FAILURE)


def _hash_password(password: str) -> str:
    if bcrypt:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    salt = secrets.token_hex(16)
    return f"{salt}:{hashlib.sha256(f'{salt}:{password}'.encode()).hexdigest()}"


def _verify_password(password: str, stored: str) -> bool:
    # bcrypt hashes start with $2b$
    if bcrypt and stored.startswith("$2b$"):
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
    name: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TeamKeyCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


async def _get_key_capacity(conn, user_id: int, tier: str | None = None) -> tuple[int, int]:
    row = await conn.fetchrow(
        """
        SELECT
          (SELECT COUNT(*) FROM api_keys WHERE user_id = $1 AND is_active = true) AS active_keys,
          COALESCE(
            (SELECT max_users
             FROM subscriptions
             WHERE user_id = $1
             ORDER BY created_at DESC
             LIMIT 1),
            1
          ) AS max_users
        """,
        user_id,
    )
    active_keys = int(row["active_keys"] or 0)
    subscription_max = int(row["max_users"] or 1)
    tier_max = get_max_users(tier or "free")
    return active_keys, max(subscription_max, tier_max)


@router.post("/register")
async def register(req: RegisterRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Register a new user, provision free-tier access, and send verification email."""
    async with get_connection() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", req.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered.")

        password_hash = _hash_password(req.password)
        verification_token = secrets.token_urlsafe(32)
        api_key = f"cg_{secrets.token_urlsafe(32)}"
        api_key_hash = hash_api_key(api_key)

        async with conn.transaction():
            free_entitlements = get_subscription_entitlements("free")
            user = await conn.fetchrow(
                """INSERT INTO users (email, name, password_hash, verification_token, is_verified)
                   VALUES ($1, $2, $3, $4, false)
                   RETURNING id, email, name""",
                req.email, req.name, password_hash, verification_token,
            )

            await conn.execute(
                """INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
                   VALUES ($1, $2, $3, $4, 'free', $5, true, $6)""",
                api_key_hash, api_key_prefix(api_key), req.name, req.email, get_tier_config("free")["rate"], user["id"],
            )
            await write_audit_log(
                action="api_key.create",
                outcome="success",
                actor={"type": "user", "user_id": user["id"], "email": req.email, "name": req.name},
                target_type="api_key",
                metadata={"key_prefix": api_key_prefix(api_key), "source": "registration"},
                conn=conn,
            )

            await conn.execute(
                """INSERT INTO subscriptions (
                       user_id, tier, status, included_users, extra_seats, max_users, seat_price_gbp
                   )
                   VALUES ($1, 'free', 'active', $2, $3, $4, $5)""",
                user["id"],
                free_entitlements["included_users"],
                free_entitlements["extra_seats"],
                free_entitlements["max_users"],
                free_entitlements["seat_price_gbp"],
            )

    await _send_verification_email(req.email, req.name, verification_token)

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "tier": "free",
        "verification_required": True,
        "message": "Registration successful. Check your inbox to verify your email before you log in.",
    }


def _set_session_cookie(response: Response, api_key: str, *, is_prod: bool) -> None:
    response.set_cookie(
        key="caregist_session",
        value=api_key,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
        max_age=30 * 24 * 3600,  # 30 days
    )


async def _create_session(conn, *, user_id: int, api_key_id: int, response: Response) -> None:
    session_token = f"cs_{secrets.token_urlsafe(32)}"
    session_token_hash = hash_api_key(session_token)
    await conn.execute(
        """
        INSERT INTO user_sessions (token_hash, user_id, api_key_id, expires_at)
        VALUES ($1, $2, $3, NOW() + INTERVAL '30 days')
        """,
        session_token_hash,
        user_id,
        api_key_id,
    )
    _set_session_cookie(response, session_token, is_prod="localhost" not in settings.database_url)


@router.post("/login")
async def login(req: LoginRequest, response: Response, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Login and retrieve API key."""
    _check_failed_attempts(req.email, "login")
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash, is_verified FROM users WHERE email = $1",
            req.email,
        )

    if not user:
        if bcrypt:
            bcrypt.checkpw(req.password.encode(), _DUMMY_HASH.encode())
        await _raise_auth_failure(req.email, "login")
    if not _verify_password(req.password, user["password_hash"]):
        await _raise_auth_failure(req.email, "login")
    if not user["is_verified"]:
        await write_audit_log(
            action="login",
            outcome="failure",
            actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
            target_type="user",
            target_id=user["id"],
        )
        raise HTTPException(status_code=403, detail="Verify your email before logging in.")
    _reset_failed_attempts(req.email, "login")

    # Upgrade legacy SHA-256 hash to bcrypt on successful login
    await _rehash_if_legacy(user["id"], req.password, user["password_hash"])

    async with get_connection() as conn:
        key_row = await conn.fetchrow(
            "SELECT id, key, tier, rate_limit FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )

    if not key_row:
        raise HTTPException(status_code=404, detail="No active API key found. Contact support.")

    async with get_connection() as conn:
        await _create_session(conn, user_id=int(user["id"]), api_key_id=int(key_row["id"]), response=response)
        await write_audit_log(
            action="login",
            outcome="success",
            actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
            target_type="user",
            target_id=user["id"],
            conn=conn,
        )

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "tier": key_row["tier"],
        "rate_limit": key_row["rate_limit"],
        "requires_key_rotation": key_row["key"] is None,
    }


@router.delete("/session")
async def logout_session(
    response: Response,
    caregist_session: str | None = Cookie(default=None),
) -> dict:
    """Revoke and clear the HttpOnly browser session."""
    if caregist_session:
        async with get_connection() as conn:
            await conn.execute(
                "UPDATE user_sessions SET revoked_at = NOW() WHERE token_hash = $1 AND revoked_at IS NULL",
                hash_api_key(caregist_session),
            )
    response.delete_cookie(key="caregist_session", path="/")
    return {"logged_out": True}


@router.get("/me")
async def get_me(_auth: dict = Depends(validate_api_key)) -> dict:
    """Return the current user's profile and tier (authenticated via header or cookie)."""
    return {
        "tier": _auth.get("tier"),
        "user_id": _auth.get("user_id"),
        "email": _auth.get("email"),
        "is_verified": _auth.get("is_verified", False),
    }


@router.post("/reveal-key")
async def reveal_key(req: LoginRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Return the current API key for an account after verifying the password.

    Requires password re-verification so XSS cannot silently exfiltrate the key
    without user interaction. The key is shown once in the response body — callers
    should store it securely and never embed it in client-side code.
    """
    _check_failed_attempts(req.email, "key-reveal")
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, password_hash, is_verified FROM users WHERE email = $1",
            req.email,
        )

    if not user or not _verify_password(req.password, user["password_hash"]):
        if bcrypt:
            bcrypt.checkpw(req.password.encode(), _DUMMY_HASH.encode())
        await _raise_auth_failure(req.email, "key-reveal", "api_key.reveal")
    if not user["is_verified"]:
        await write_audit_log(
            action="api_key.reveal",
            outcome="failure",
            actor={"type": "user", "user_id": user["id"], "email": req.email},
            target_type="user",
            target_id=user["id"],
        )
        raise HTTPException(status_code=403, detail="Verify your email before revealing an API key.")
    _reset_failed_attempts(req.email, "key-reveal")

    async with get_connection() as conn:
        key_row = await conn.fetchrow(
            "SELECT key, key_prefix, tier, rate_limit FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )

        if not key_row:
            await write_audit_log(
                action="api_key.reveal",
                outcome="failure",
                actor={"type": "user", "user_id": user["id"], "email": req.email},
                target_type="user",
                target_id=user["id"],
                conn=conn,
            )
            raise HTTPException(status_code=404, detail="No active API key found.")

        if not key_row["key"]:
            await write_audit_log(
                action="api_key.reveal",
                outcome="blocked",
                actor={"type": "user", "user_id": user["id"], "email": req.email},
                target_type="api_key",
                metadata={"key_prefix": key_row["key_prefix"]},
                conn=conn,
            )
            return {
                "api_key": None,
                "masked_key": f"{key_row['key_prefix']}…" if key_row["key_prefix"] else None,
                "tier": key_row["tier"],
                "rate_limit": key_row["rate_limit"],
                "message": "This key cannot be revealed. Rotate it to generate a new API key shown once.",
            }

        await write_audit_log(
            action="api_key.reveal",
            outcome="success",
            actor={"type": "user", "user_id": user["id"], "email": req.email},
            target_type="api_key",
            conn=conn,
        )
    return {"api_key": key_row["key"], "tier": key_row["tier"], "rate_limit": key_row["rate_limit"]}


@router.post("/rotate-key")
async def rotate_key(req: LoginRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Generate a new API key (invalidates old one). Requires password re-verification."""
    _check_failed_attempts(req.email, "key-rotate")
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash, is_verified FROM users WHERE email = $1",
            req.email,
        )

    if not user or not _verify_password(req.password, user["password_hash"]):
        if bcrypt:
            bcrypt.checkpw(req.password.encode(), _DUMMY_HASH.encode())
        await _raise_auth_failure(req.email, "key-rotate", "api_key.rotate")
    if not user["is_verified"]:
        await write_audit_log(
            action="api_key.rotate",
            outcome="failure",
            actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
            target_type="user",
            target_id=user["id"],
        )
        raise HTTPException(status_code=403, detail="Verify your email before rotating an API key.")
    _reset_failed_attempts(req.email, "key-rotate")

    new_key = f"cg_{secrets.token_urlsafe(32)}"
    new_key_hash = hash_api_key(new_key)

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
        await conn.execute(
            "UPDATE user_sessions SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL",
            user["id"],
        )

        # Create new key
        await conn.execute(
            """INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
               VALUES ($1, $2, $3, $4, $5, $6, true, $7)""",
            new_key_hash, api_key_prefix(new_key), user["name"], user["email"], tier, rate_limit, user["id"],
        )
        await write_audit_log(
            action="api_key.rotate",
            outcome="success",
            actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
            target_type="api_key",
            metadata={"key_prefix": api_key_prefix(new_key), "tier": tier},
            conn=conn,
        )

    return {"api_key": new_key, "tier": tier, "rate_limit": rate_limit}


@router.get("/team-keys")
async def list_team_keys(_auth: dict = Depends(validate_api_key)) -> dict:
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")

    async with get_connection() as conn:
        keys = await conn.fetch(
            """
            SELECT id, name, email, tier, created_at, last_used_at, key, key_prefix
            FROM api_keys
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at ASC
            """,
            user_id,
        )
        active_keys, max_users = await _get_key_capacity(conn, user_id, _auth.get("tier"))

    return {
        "keys": [
            {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "tier": row["tier"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
                "masked_key": (
                    f"{row['key'][:10]}…{row['key'][-4:]}"
                    if row["key"]
                    else f"{row['key_prefix']}…" if row["key_prefix"] else None
                ),
            }
            for row in keys
        ],
        "active_keys": active_keys,
        "max_users": max_users,
    }


@router.post("/team-keys", status_code=201)
async def create_team_key(req: TeamKeyCreateRequest, _auth: dict = Depends(validate_api_key)) -> dict:
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before creating additional access keys.")

    async with get_connection() as conn:
        active_keys, max_users = await _get_key_capacity(conn, user_id, _auth.get("tier"))
        if active_keys >= max_users:
            raise HTTPException(
                status_code=403,
                detail="You have used all named access seats on this plan. Add seats or upgrade to issue another key.",
            )
        new_key = f"cg_{secrets.token_urlsafe(32)}"
        new_key_hash = hash_api_key(new_key)
        await conn.execute(
            """
            INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
            VALUES ($1, $2, $3, $4, $5, $6, true, $7)
            """,
            new_key_hash,
            api_key_prefix(new_key),
            req.name,
            req.email,
            _auth["tier"],
            get_tier_config(_auth["tier"])["rate"],
            user_id,
        )
        await write_audit_log(
            action="api_key.create",
            outcome="success",
            actor=actor_from_auth(_auth),
            target_type="api_key",
            metadata={"key_prefix": api_key_prefix(new_key), "tier": _auth["tier"]},
            conn=conn,
        )

    return {
        "api_key": new_key,
        "name": req.name,
        "email": req.email,
        "message": "Named access key created. Store it securely — it is shown once.",
    }


@router.delete("/team-keys/{key_id}")
async def revoke_team_key(key_id: int, _auth: dict = Depends(validate_api_key)) -> dict:
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")
    if key_id == _auth.get("key_id"):
        raise HTTPException(status_code=400, detail="Use key rotation to replace the key you are currently using.")

    async with get_connection() as conn:
        active_keys, _ = await _get_key_capacity(conn, user_id, _auth.get("tier"))
        if active_keys <= 1:
            raise HTTPException(status_code=400, detail="You must keep at least one active key on the account.")
        result = await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE id = $1 AND user_id = $2",
            key_id,
            user_id,
        )
        if result != "UPDATE 0":
            await write_audit_log(
                action="api_key.revoke",
                outcome="success",
                actor=actor_from_auth(_auth),
                target_type="api_key",
                target_id=key_id,
                conn=conn,
            )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Access key not found.")
    return {"revoked": True}


# --- Password reset ---


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8)


MAX_RESET_ATTEMPTS = 5
RESET_TOKEN_BYTES = 32


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Generate a high-entropy reset token and email it via Resend."""
    # Always return success to avoid email enumeration
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", req.email)

    if not user:
        return {"message": "If that email is registered, a reset token has been sent."}

    async with get_connection() as conn:
        recent_count = await conn.fetchval(
            """SELECT COUNT(*) FROM password_reset_tokens
               WHERE email = $1 AND created_at > NOW() - INTERVAL '1 hour'""",
            req.email,
        )
    if recent_count and recent_count >= 3:
        return {"message": "If that email is registered, a reset token has been sent."}

    reset_token = secrets.token_urlsafe(RESET_TOKEN_BYTES)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    async with get_connection() as conn:
        await conn.execute(
            """INSERT INTO password_reset_tokens (token, email, expires_at)
               VALUES ($1, $2, $3)""",
            reset_token, req.email, expires_at,
        )

    # Send email (best-effort)
    await _send_reset_email(req.email, reset_token)

    return {"message": "If that email is registered, a reset token has been sent."}


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Verify a user email using the one-time token."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, email
            FROM users
            WHERE verification_token = $1
              AND is_verified = false
            """,
            req.token,
        )
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification link.")
        await conn.execute(
            """
            UPDATE users
            SET is_verified = true,
                verification_token = NULL,
                updated_at = NOW()
            WHERE id = $1
            """,
            user["id"],
        )
    return {"message": "Email verified. You can now log in.", "email": user["email"]}


@router.post("/resend-verification")
async def resend_verification(req: ResendVerificationRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Resend a verification email for accounts still waiting verification."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT name, verification_token, is_verified FROM users WHERE email = $1",
            req.email,
        )
    if not user or user["is_verified"]:
        return {"message": "If that email is waiting for verification, a new link has been sent."}

    token = user["verification_token"] or secrets.token_urlsafe(32)
    if not user["verification_token"]:
        async with get_connection() as conn:
            await conn.execute("UPDATE users SET verification_token = $1 WHERE email = $2", token, req.email)
    await _send_verification_email(req.email, user["name"] or "there", token)
    return {"message": "If that email is waiting for verification, a new link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Validate reset token and update password."""
    async with get_connection() as conn:
        # Check for too many failed attempts in the last 15 minutes
        attempt_count = await conn.fetchval(
            """SELECT COUNT(*) FROM password_reset_tokens
               WHERE email = $1 AND used = false AND attempts >= $2
               AND expires_at > NOW()""",
            req.email, MAX_RESET_ATTEMPTS,
        )
        if attempt_count and attempt_count > 0:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new token.")

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
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

        new_hash = _hash_password(req.new_password)

        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE email = $2",
                new_hash, req.email,
            )
            await conn.execute(
                """
                UPDATE user_sessions
                SET revoked_at = NOW()
                WHERE user_id = (SELECT id FROM users WHERE email = $1)
                  AND revoked_at IS NULL
                """,
                req.email,
            )
            await conn.execute(
                "UPDATE password_reset_tokens SET used = true WHERE id = $1",
                token_row["id"],
            )

    return {"message": "Password has been reset. You can now log in."}


async def _send_reset_email(email: str, reset_token: str) -> None:
    """Send password reset token via Resend. Fails silently."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping password reset email")
        return

    import httpx

    from_email = settings.enquiry_from_email or "noreply@caregist.co.uk"
    body = (
        f"Your CareGist password reset token is: {reset_token}\n\n"
        f"This token expires in 15 minutes. If you didn't request this, ignore this email.\n\n"
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
                    "subject": "Your CareGist password reset token",
                    "text": body,
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("Resend API error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Failed to send reset email: %s", exc)


async def _send_verification_email(email: str, name: str, token: str) -> None:
    """Send email verification link via Resend. Fails silently."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping verification email")
        return

    import httpx

    from_email = settings.enquiry_from_email or "noreply@caregist.co.uk"
    verify_link = f"{settings.app_url}/verify-email?token={token}"
    html = (
        f"<p>Hi {name},</p>"
        "<p>Verify your CareGist email to activate dashboard access, billing, and named access seats.</p>"
        f"<p><a href=\"{verify_link}\">Verify your email</a></p>"
        f"<p>If the button does not work, copy this link into your browser:</p><p>{verify_link}</p>"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": from_email,
                    "to": [email],
                    "subject": "Verify your CareGist email",
                    "html": html,
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.error("Resend verification email error %s: %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Failed to send verification email: %s", exc)


class DeleteAccountRequest(BaseModel):
    email: EmailStr
    password: str


@router.delete("/delete-account")
async def delete_account(req: DeleteAccountRequest) -> dict:
    """Delete user account and anonymize associated data (GDPR right to erasure)."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, password_hash FROM users WHERE email = $1",
            req.email,
        )

    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    async with get_connection() as conn:
        async with conn.transaction():
            user_id = user["id"]
            # Anonymize enquiries
            await conn.execute(
                "UPDATE enquiries SET enquirer_name = '[deleted]', enquirer_email = '[deleted]', enquirer_phone = NULL, message = '[deleted]' WHERE provider_id IN (SELECT id FROM care_providers) AND enquirer_email = $1",
                req.email,
            )
            # Anonymize reviews
            await conn.execute(
                "UPDATE reviews SET reviewer_name = '[deleted]', reviewer_email = '[deleted]' WHERE reviewer_email = $1",
                req.email,
            )
            # Anonymize claims
            await conn.execute(
                "UPDATE provider_claims SET claimant_name = '[deleted]', claimant_email = '[deleted]', claimant_phone = NULL WHERE claimant_email = $1",
                req.email,
            )
            # Delete API keys, subscriptions, then user (cascade should handle but be explicit)
            await conn.execute("DELETE FROM api_keys WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM subscriptions WHERE user_id = $1", user_id)
            await conn.execute("DELETE FROM password_reset_tokens WHERE email = $1", req.email)
            await conn.execute("DELETE FROM users WHERE id = $1", user_id)

    logger.info("Account deleted for user_id=%s", user["id"])
    return {"message": "Your account has been permanently deleted."}
