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
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from api.middleware.ip_rate_limit import check_ip_rate_limit

from api.config import get_max_users, get_subscription_entitlements, get_tier_config, settings
from api.database import get_connection
from api.middleware.auth import api_key_prefix, hash_api_key, validate_api_key
from api.utils.audit import actor_from_auth, write_audit_log
from api.utils.sessions import create_session, revoke_session

logger = logging.getLogger("caregist.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

FAILED_ATTEMPT_LIMIT = 5
FAILED_ATTEMPT_LOCK_SECONDS = 15 * 60
GENERIC_AUTH_FAILURE = "Invalid email or password."
RESET_TOKEN_BYTES = 32
_failed_auth_attempts: dict[tuple[str, str], dict[str, float | int]] = {}

if bcrypt:
    _DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()
else:
    _DUMMY_HASH = "fallback:dummy"

# ---------------------------------------------------------------------------
# Session TTL (seconds). Default: 30 days.
# ---------------------------------------------------------------------------
_SESSION_TTL_SECONDS: int = int(getattr(settings, "session_ttl_seconds", 2592000))


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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8)


class DeleteAccountRequest(BaseModel):
    email: EmailStr
    password: str


MAX_RESET_ATTEMPTS = 5


async def _get_key_capacity(conn, user_id: int, tier: str | None = None):
    """Return (active_key_count, max_allowed) for a user."""
    tier = tier or "free"
    active = await conn.fetchval(
        "SELECT COUNT(*) FROM api_keys WHERE user_id = $1 AND is_active = true",
        user_id,
    )
    sub = await conn.fetchrow(
        "SELECT max_users FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
        user_id,
    )
    sub_max = int(sub["max_users"]) if sub else 1
    return int(active), max(sub_max, get_max_users(tier))


async def _send_verification_email(email: str, name: str, token: str) -> None:
    from api.utils.email_queue import enqueue_email  # local import avoids circular
    await enqueue_email(
        to=email,
        subject="Verify your CareGist email",
        template="verify_email",
        context={"name": name, "token": token},
    )


async def _send_reset_email(email: str, token: str) -> None:
    from api.utils.email_queue import enqueue_email
    await enqueue_email(
        to=email,
        subject="Reset your CareGist password",
        template="reset_password",
        context={"token": token},
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    """Write the opaque session ID into the caregist_session cookie.

    Cookie attributes (F#1 fix):
    - HttpOnly: JS cannot read the value.
    - Secure: HTTPS-only (set samesite=lax for normal nav flows).
    - SameSite=Lax: protects against CSRF while allowing top-level GET nav.
    - Path=/: applies to all routes.
    - Max-Age: matches server-side TTL.

    The value is a 32-byte URL-safe-base64 opaque session ID — NOT the
    bearer token.  This is the fix for audit finding F#1.
    """
    response.set_cookie(
        key="caregist_session",
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=_SESSION_TTL_SECONDS,
    )


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


@router.post("/login")
async def login(
    req: LoginRequest,
    response: Response,
    request: Request,
    _ip=Depends(check_ip_rate_limit),
) -> dict:
    """Authenticate, create an opaque server-side session, set HttpOnly cookie.

    F#1 fix: cookie value is a 32-byte opaque session_id from the ``sessions``
    table — NOT the bearer token.  The bearer key never appears in a cookie.
    """
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

    # --- F#1 fix (lines 211-235 in original): generate opaque session ID ---
    # Previously: cookie value = bearer token (live credential exposure risk).
    # Now: generate a 32-byte random session_id, store it in the sessions
    # table, and write ONLY the session_id into the HttpOnly cookie.
    user_agent = request.headers.get("user-agent")
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else None)
    )
    session_id = await create_session(
        user_id=int(user["id"]),
        user_agent=user_agent,
        ip=client_ip or None,
    )
    # Write opaque session_id — NOT the bearer token — into the cookie.
    _set_session_cookie(response, session_id)
    # --- end F#1 fix ---

    await write_audit_log(
        action="login",
        outcome="success",
        actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
        target_type="user",
        target_id=user["id"],
    )

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "tier": key_row["tier"],
        "rate_limit": key_row["rate_limit"],
        "requires_key_rotation": key_row["key"] is None,
    }


@router.post("/logout")
async def logout_session(
    response: Response,
    caregist_session: str | None = Cookie(default=None),
) -> dict:
    """Revoke the server-side session and clear the cookie."""
    if caregist_session:
        await revoke_session(caregist_session)
    # Clear the cookie regardless of whether a session existed.
    response.delete_cookie(
        key="caregist_session",
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"logged_out": True}


@router.post("/reveal-key")
async def reveal_key(req: LoginRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Return the current API key for an account after verifying the password.

    Requires password re-verification so XSS cannot silently exfiltrate the key
    without user interaction.
    """
    _check_failed_attempts(req.email, "reveal-key")
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash, is_verified FROM users WHERE email = $1",
            req.email,
        )

    if not user or not _verify_password(req.password, user["password_hash"]):
        if bcrypt:
            bcrypt.checkpw(req.password.encode(), _DUMMY_HASH.encode())
        await _raise_auth_failure(req.email, "reveal-key", "api_key.reveal")
    _reset_failed_attempts(req.email, "reveal-key")

    async with get_connection() as conn:
        key_row = await conn.fetchrow(
            "SELECT key, key_prefix, tier, rate_limit FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )

    if not key_row:
        raise HTTPException(status_code=404, detail="No active API key found.")

    if key_row["key"] is None:
        return {
            "api_key": None,
            "masked_key": f"{key_row['key_prefix']}\u2026",
            "tier": key_row["tier"],
            "message": "Rotate your key to receive the plaintext once.",
        }
    return {
        "api_key": key_row["key"],
        "tier": key_row["tier"],
        "rate_limit": key_row["rate_limit"],
    }


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
        old_row = await conn.fetchrow(
            "SELECT id, tier, rate_limit FROM api_keys WHERE user_id = $1 AND is_active = true ORDER BY created_at DESC LIMIT 1",
            user["id"],
        )
        if not old_row:
            raise HTTPException(status_code=404, detail="No active API key to rotate.")

        await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE id = $1",
            old_row["id"],
        )
        await conn.execute(
            """INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
               VALUES ($1, $2, $3, $4, $5, $6, true, $7)""",
            new_key_hash,
            api_key_prefix(new_key),
            user["name"],
            user["email"],
            old_row["tier"],
            old_row["rate_limit"],
            user["id"],
        )
        await write_audit_log(
            action="api_key.rotate",
            outcome="success",
            actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
            target_type="api_key",
            metadata={"key_prefix": api_key_prefix(new_key), "api_key": new_key},
            conn=conn,
        )

    return {
        "api_key": new_key,
        "tier": old_row["tier"],
        "rate_limit": old_row["rate_limit"],
        "message": "Key rotated. Store it now — it will not be shown again.",
    }


@router.post("/team-keys", status_code=201)
async def create_team_key(req: TeamKeyCreateRequest, _auth: dict = Depends(validate_api_key)) -> dict:
    user_id = _auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User account required.")
    if not _auth.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email before creating additional access keys.")

    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, tier FROM users u JOIN subscriptions s ON s.user_id = u.id WHERE u.id = $1 ORDER BY s.created_at DESC LIMIT 1",
            user_id,
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        active_keys, max_keys = await _get_key_capacity(conn, user_id, _auth.get("tier"))
        if active_keys >= max_keys:
            raise HTTPException(
                status_code=403,
                detail=f"You have reached your plan's named access seats ({max_keys}). Revoke a key or upgrade.",
            )

        new_key = f"cg_{secrets.token_urlsafe(32)}"
        new_key_hash = hash_api_key(new_key)
        await conn.execute(
            """INSERT INTO api_keys (key_hash, key_prefix, name, email, tier, rate_limit, is_active, user_id)
               VALUES ($1, $2, $3, $4, $5, $6, true, $7)""",
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
            metadata={"key_prefix": api_key_prefix(new_key), "source": "team_key"},
            conn=conn,
        )

    return {
        "api_key": new_key,
        "tier": _auth["tier"],
        "message": "Team key created. Store it now — it will not be shown again.",
    }


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
            """SELECT COUNT(*)
               FROM password_reset_tokens
               WHERE email = $1
                 AND created_at > NOW() - INTERVAL '15 minutes'""",
            req.email,
        )
        if recent_count and recent_count >= 3:
            return {"message": "If that email is registered, a reset token has been sent."}

        token = secrets.token_urlsafe(RESET_TOKEN_BYTES)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await conn.execute(
            """INSERT INTO password_reset_tokens (email, token, expires_at, used, attempts)
               VALUES ($1, $2, $3, false, 0)""",
            req.email,
            token,
            expires_at,
        )

    await _send_reset_email(req.email, token)
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
    """Resend verification email."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, name, verification_token FROM users WHERE email = $1 AND is_verified = false",
            req.email,
        )
    if not user:
        return {"message": "If that email is pending verification, a new link has been sent."}
    await _send_verification_email(req.email, user["name"], user["verification_token"])
    return {"message": "If that email is pending verification, a new link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, _ip=Depends(check_ip_rate_limit)) -> dict:
    """Validate reset token and update password."""
    async with get_connection() as conn:
        attempt_count = await conn.fetchval(
            """SELECT COUNT(*) FROM password_reset_tokens
               WHERE email = $1 AND used = false AND attempts >= $2
               AND expires_at > NOW()""",
            req.email, MAX_RESET_ATTEMPTS,
        )
        if attempt_count and attempt_count > 0:
            raise HTTPException(status_code=429, detail="Too many reset attempts. Request a new token.")

        token_row = await conn.fetchrow(
            """SELECT id FROM password_reset_tokens
               WHERE email = $1 AND token = $2 AND used = false AND expires_at > NOW()""",
            req.email, req.token,
        )
        if not token_row:
            await conn.execute(
                "UPDATE password_reset_tokens SET attempts = attempts + 1 WHERE email = $1 AND used = false AND expires_at > NOW()",
                req.email,
            )
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

        new_hash = _hash_password(req.new_password)
        await conn.execute(
            "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE email = $2",
            new_hash, req.email,
        )
        await conn.execute(
            "UPDATE password_reset_tokens SET used = true WHERE id = $1",
            token_row["id"],
        )

    return {"message": "Password reset successfully. You can now log in."}


@router.delete("/delete-account")
async def delete_account(req: DeleteAccountRequest) -> dict:
    """Delete user account and anonymize associated data (GDPR right to erasure)."""
    async with get_connection() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, name, password_hash FROM users WHERE email = $1",
            req.email,
        )
    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_FAILURE)

    async with get_connection() as conn:
        await conn.execute(
            "UPDATE api_keys SET is_active = false WHERE user_id = $1",
            user["id"],
        )
        # Revoke all sessions on account deletion
        await conn.execute(
            "UPDATE sessions SET revoked_at = NOW() WHERE user_id = $1 AND revoked_at IS NULL",
            user["id"],
        )
        await conn.execute(
            "DELETE FROM users WHERE id = $1",
            user["id"],
        )
        await write_audit_log(
            action="account.delete",
            outcome="success",
            actor={"type": "user", "user_id": user["id"], "email": user["email"], "name": user["name"]},
            target_type="user",
            target_id=user["id"],
            conn=conn,
        )

    return {"message": "Account deleted."}
