"""Tests for email verification and gated authentication flows."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import Response as FastAPIResponse
from pydantic import ValidationError

from api.routers.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RESET_TOKEN_BYTES,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    _failed_auth_attempts,
    _hash_password,
    forgot_password,
    login,
    logout_session,
    register,
    reveal_key,
    reset_password,
    rotate_key,
    verify_email,
    purchase_intent_continuation,
)


@asynccontextmanager
async def _noop_transaction():
    yield


@pytest.fixture(autouse=True)
def clear_failed_auth_attempts():
    _failed_auth_attempts.clear()
    yield
    _failed_auth_attempts.clear()


@pytest.mark.asyncio
async def test_register_requires_email_verification_and_sends_email():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": 1, "email": "alice@example.com", "name": "Alice"},
        ]
    )
    conn.execute = AsyncMock()
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._send_verification_email", AsyncMock()) as send_email:
        response = await register(
            RegisterRequest(
                email="alice@example.com",
                name="Alice",
                password="SuperSecret123",
            )
        )

    assert response["tier"] == "free"
    assert response["verification_required"] is True
    assert "verify your email" in response["message"].lower()
    send_email.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_kwargs", "intent_type", "intent_value"),
    [
        ({"plan": "data-pro"}, "plan", "data-pro"),
        ({"provider_tier": "sponsored"}, "provider_tier", "sponsored"),
    ],
)
async def test_register_persists_structured_purchase_intent(request_kwargs, intent_type, intent_value):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            None,
            {"id": 7, "email": "buyer@example.com", "name": "Buyer"},
        ]
    )
    conn.execute = AsyncMock()
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._send_verification_email", AsyncMock()):
        await register(
            RegisterRequest(
                email="buyer@example.com",
                name="Buyer",
                password="SuperSecret123",
                **request_kwargs,
            )
        )

    insert_user = conn.fetchrow.await_args_list[1].args
    assert "signup_intent_type" in insert_user[0]
    assert insert_user[5:] == (intent_type, intent_value)


def test_register_rejects_multiple_or_unapproved_purchase_intents():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="buyer@example.com",
            name="Buyer",
            password="SuperSecret123",
            plan="data-pro",
            provider_tier="enhanced",
        )

    with pytest.raises(ValidationError):
        RegisterRequest(
            email="buyer@example.com",
            name="Buyer",
            password="SuperSecret123",
            plan="https://evil.example/steal",
        )


@pytest.mark.asyncio
async def test_login_blocks_unverified_user():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "email": "alice@example.com",
            "name": "Alice",
            "password_hash": _hash_password("SuperSecret123"),
            "is_verified": False,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await login(LoginRequest(email="alice@example.com", password="SuperSecret123"), FastAPIResponse())

    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail


@pytest.mark.asyncio
async def test_repeated_failed_logins_trigger_cooldown(monkeypatch):
    monkeypatch.setattr("api.routers.auth.FAILED_ATTEMPT_LIMIT", 2)
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "email": "alice@example.com",
            "name": "Alice",
            "password_hash": _hash_password("SuperSecret123"),
            "is_verified": True,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", return_value=False):
        for _ in range(2):
            with pytest.raises(HTTPException) as exc:
                await login(LoginRequest(email="alice@example.com", password="wrong-password"), FastAPIResponse())
            assert exc.value.status_code == 401
            assert exc.value.detail == "Invalid email or password."

        with pytest.raises(HTTPException) as exc:
            await login(LoginRequest(email="alice@example.com", password="wrong-password"), FastAPIResponse())

    assert exc.value.status_code == 429
    assert exc.value.detail == "Invalid email or password."


@pytest.mark.asyncio
async def test_successful_login_resets_failed_attempt_counter(monkeypatch):
    monkeypatch.setattr("api.routers.auth.FAILED_ATTEMPT_LIMIT", 2)
    user = {
        "id": 1,
        "email": "alice@example.com",
        "name": "Alice",
        "password_hash": "$2b$already-bcrypt",
        "is_verified": True,
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            user,
            user,
            {"id": 7, "key": "cg_legacy_key", "tier": "free", "rate_limit": 2},
        ]
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", side_effect=[False, True]):
        with pytest.raises(HTTPException) as exc:
            await login(LoginRequest(email="alice@example.com", password="wrong-password"), FastAPIResponse())
        assert exc.value.detail == "Invalid email or password."

        response = await login(LoginRequest(email="alice@example.com", password="SuperSecret123"), FastAPIResponse())

    assert response["tier"] == "free"
    assert _failed_auth_attempts == {}


@pytest.mark.asyncio
async def test_login_sets_revocable_session_and_logout_revokes_it():
    user = {
        "id": 1,
        "email": "alice@example.com",
        "name": "Alice",
        "password_hash": "$2b$already-bcrypt",
        "is_verified": True,
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        side_effect=[
            user,
            {"id": 7, "key": None, "tier": "free", "rate_limit": 2},
        ]
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    response = FastAPIResponse()
    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", return_value=True):
        login_result = await login(LoginRequest(email="alice@example.com", password="SuperSecret123"), response)

    assert login_result["tier"] == "free"
    assert "caregist_session=" in response.headers["set-cookie"]
    insert_call = next(call.args for call in conn.execute.await_args_list if "INSERT INTO user_sessions" in call.args[0])
    assert "INSERT INTO user_sessions" in insert_call[0]
    assert insert_call[2] == 1
    assert insert_call[3] == 7
    audit_call = next(call.args for call in conn.execute.await_args_list if "INSERT INTO audit_log" in call.args[0])
    assert audit_call[1] == "login"
    assert audit_call[2] == "success"

    session_token = response.headers["set-cookie"].split("caregist_session=", 1)[1].split(";", 1)[0]
    logout_response = FastAPIResponse()
    with patch("api.routers.auth.get_connection", mock_get_connection):
        logout_result = await logout_session(logout_response, caregist_session=session_token)

    assert logout_result == {"logged_out": True}
    revoke_call = conn.execute.await_args.args
    assert "UPDATE user_sessions SET revoked_at" in revoke_call[0]


@pytest.mark.asyncio
async def test_reveal_key_blocks_unverified_user():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "password_hash": _hash_password("SuperSecret123"),
            "is_verified": False,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await reveal_key(LoginRequest(email="alice@example.com", password="SuperSecret123"))

    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail


@pytest.mark.asyncio
async def test_repeated_failed_reveal_key_auth_triggers_cooldown(monkeypatch):
    monkeypatch.setattr("api.routers.auth.FAILED_ATTEMPT_LIMIT", 2)
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "password_hash": _hash_password("SuperSecret123"),
            "is_verified": True,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._verify_password", return_value=False):
        for _ in range(2):
            with pytest.raises(HTTPException) as exc:
                await reveal_key(LoginRequest(email="alice@example.com", password="wrong-password"))
            assert exc.value.status_code == 401
            assert exc.value.detail == "Invalid email or password."

        with pytest.raises(HTTPException) as exc:
            await reveal_key(LoginRequest(email="alice@example.com", password="wrong-password"))

    assert exc.value.status_code == 429
    assert exc.value.detail == "Invalid email or password."


@pytest.mark.asyncio
async def test_rotate_key_blocks_unverified_user():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "email": "alice@example.com",
            "name": "Alice",
            "password_hash": _hash_password("SuperSecret123"),
            "is_verified": False,
        }
    )

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await rotate_key(LoginRequest(email="alice@example.com", password="SuperSecret123"))

    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail


@pytest.mark.asyncio
async def test_verify_email_activates_account():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "email": "alice@example.com",
            "signup_intent_type": None,
            "signup_intent_value": None,
        }
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        response = await verify_email(VerifyEmailRequest(token="verify-token"))

    assert response["email"] == "alice@example.com"
    assert response["next_path"] == "/login"
    assert "verified" in response["message"].lower()
    conn.execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("intent_type", "intent_value", "expected_path"),
    [
        ("plan", "alerts-pro", "/login?upgrade=alerts-pro"),
        ("plan", "data-business", "/login?upgrade=data-business"),
        ("provider_tier", "enhanced", "/login?provider_tier=enhanced"),
        ("provider_tier", "sponsored", "/login?provider_tier=sponsored"),
        ("plan", "https://evil.example/steal", "/login"),
        ("redirect", "//evil.example", "/login"),
    ],
)
async def test_verify_email_returns_only_allowlisted_server_backed_continuation(
    intent_type,
    intent_value,
    expected_path,
):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "email": "buyer@example.com",
            "signup_intent_type": intent_type,
            "signup_intent_value": intent_value,
        }
    )
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        response = await verify_email(VerifyEmailRequest(token="cross-device-token"))

    assert response["next_path"] == expected_path


def test_purchase_intent_continuation_never_accepts_raw_paths():
    assert purchase_intent_continuation("plan", "/admin") == "/login"
    assert purchase_intent_continuation("provider_tier", "//evil.example") == "/login"


@pytest.mark.asyncio
async def test_forgot_password_generates_high_entropy_reset_token():
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value={"id": 1})
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection), \
         patch("api.routers.auth._send_reset_email", AsyncMock()) as send_email:
        response = await forgot_password(ForgotPasswordRequest(email="alice@example.com"))

    assert "reset" in response["message"].lower()
    insert_call = conn.execute.await_args.args
    token = insert_call[1]
    assert "INSERT INTO password_reset_tokens" in insert_call[0]
    assert len(token) >= 43
    assert not token.isdigit()
    assert set(token) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert RESET_TOKEN_BYTES == 32
    send_email.assert_awaited_once_with("alice@example.com", token)


@pytest.mark.asyncio
async def test_reset_password_accepts_valid_token_and_marks_used():
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetchrow = AsyncMock(
        return_value={
            "id": 9,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            "used": False,
            "attempts": 0,
        }
    )
    conn.execute = AsyncMock()
    conn.transaction = lambda: _noop_transaction()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        response = await reset_password(
            ResetPasswordRequest(
                email="alice@example.com",
                token="strong-reset-token",
                new_password="NewSecret123",
            )
        )

    assert "reset" in response["message"].lower()
    queries = [call.args[0] for call in conn.execute.await_args_list]
    assert any("UPDATE users SET password_hash" in query for query in queries)
    assert any("UPDATE user_sessions" in query for query in queries)
    assert any("UPDATE password_reset_tokens SET used = true" in query for query in queries)


@pytest.mark.asyncio
async def test_reset_password_rejects_expired_or_invalid_token():
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection():
        yield conn

    with patch("api.routers.auth.get_connection", mock_get_connection):
        with pytest.raises(HTTPException) as exc:
            await reset_password(
                ResetPasswordRequest(
                    email="alice@example.com",
                    token="invalid-reset-token",
                    new_password="NewSecret123",
                )
            )

    assert exc.value.status_code == 400
    assert "Invalid or expired reset token" in exc.value.detail
    query = conn.execute.await_args.args[0]
    assert "UPDATE password_reset_tokens SET attempts = attempts + 1" in query
