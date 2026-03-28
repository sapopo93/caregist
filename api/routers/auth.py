"""User registration, login, and API key management."""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from api.database import get_connection

logger = logging.getLogger("caregist.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

TIER_LIMITS = {
    "free": 100,
    "starter": 1000,
    "pro": 5000,
}


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def _verify_password(password: str, stored: str) -> bool:
    salt, hashed = stored.split(":", 1)
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest() == hashed


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

        user = await conn.fetchrow(
            """INSERT INTO users (email, name, password_hash, verification_token, is_verified)
               VALUES ($1, $2, $3, $4, true)
               RETURNING id, email, name""",
            req.email, req.name, password_hash, verification_token,
        )

        # Generate API key
        api_key = f"cg_{secrets.token_urlsafe(32)}"
        await conn.execute(
            """INSERT INTO api_keys (key, name, email, tier, rate_limit, is_active, user_id)
               VALUES ($1, $2, $3, 'free', $4, true, $5)""",
            api_key, req.name, req.email, TIER_LIMITS["free"], user["id"],
        )

        # Create free subscription record
        await conn.execute(
            """INSERT INTO subscriptions (user_id, tier, status)
               VALUES ($1, 'free', 'active')""",
            user["id"],
        )

    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "api_key": api_key,
        "tier": "free",
        "rate_limit": TIER_LIMITS["free"],
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
        rate_limit = current["rate_limit"] if current else TIER_LIMITS["free"]

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
