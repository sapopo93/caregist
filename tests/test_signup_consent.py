"""Tests for unbundled marketing consent — UK GDPR Art 7 compliance.

Verifies:
1. ToS and marketing consent are SEPARATE form fields (not bundled).
2. Marketing consent checkbox is default OFF (unchecked).
3. marketing_consent_at is set correctly on opt-in and remains NULL on opt-out.
4. Marketing emails are skipped when consent is missing.
5. Transactional emails (password reset, verification) bypass the marketing gate.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_register_request(**kwargs):
    """Build a RegisterRequest dict with sensible defaults."""
    defaults = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "securepassword123",
        "marketing_consent": False,
    }
    defaults.update(kwargs)
    return defaults


class FakeConn:
    """Minimal asyncpg connection mock."""

    def __init__(self):
        self._data = {}
        self.executed = []

    async def fetchrow(self, query, *args):
        return self._data.get("fetchrow")

    async def fetchval(self, query, *args):
        return self._data.get("fetchval", 0)

    async def execute(self, query, *args):
        self.executed.append((query, args))

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# 1. Separate checkboxes — RegisterRequest model
# ---------------------------------------------------------------------------

class TestRegisterRequestSeparateFields:
    """marketing_consent must be a distinct field from any ToS acceptance field."""

    def test_marketing_consent_field_exists(self):
        """RegisterRequest must expose a marketing_consent field."""
        from api.routers.auth import RegisterRequest
        fields = RegisterRequest.model_fields
        assert "marketing_consent" in fields, (
            "RegisterRequest must have a separate marketing_consent field. "
            "GDPR bundling — combining ToS + marketing into one checkbox — is illegal."
        )

    def test_tos_acceptance_not_bundled_with_marketing(self):
        """There must not be a single field that covers both ToS AND marketing consent."""
        from api.routers.auth import RegisterRequest
        fields = RegisterRequest.model_fields
        # Any field that bundles ToS + marketing in its name/description is a violation
        bundled_names = [
            name for name in fields
            if "terms" in name.lower() and "marketing" in name.lower()
        ]
        assert not bundled_names, (
            f"Found bundled ToS+marketing field(s): {bundled_names}. "
            "These MUST be separate fields under UK GDPR Art 7."
        )

    def test_marketing_consent_is_independent_bool(self):
        """marketing_consent must be a boolean, independently settable."""
        from api.routers.auth import RegisterRequest
        req_with = RegisterRequest(
            email="a@b.com", name="A", password="password123", marketing_consent=True
        )
        req_without = RegisterRequest(
            email="a@b.com", name="A", password="password123", marketing_consent=False
        )
        assert req_with.marketing_consent is True
        assert req_without.marketing_consent is False


# ---------------------------------------------------------------------------
# 2. Default OFF
# ---------------------------------------------------------------------------

class TestMarketingConsentDefaultOff:
    """marketing_consent must default to False — no pre-ticking allowed."""

    def test_default_is_false(self):
        from api.routers.auth import RegisterRequest
        req = RegisterRequest(email="a@b.com", name="A", password="password123")
        assert req.marketing_consent is False, (
            "marketing_consent must default to False. "
            "Pre-ticked opt-in boxes are invalid under UK GDPR Art 7."
        )

    def test_omitted_field_gives_false(self):
        from api.routers.auth import RegisterRequest
        # Simulate a payload that does not include marketing_consent
        req = RegisterRequest.model_validate({"email": "a@b.com", "name": "A", "password": "password123"})
        assert req.marketing_consent is False


# ---------------------------------------------------------------------------
# 3. marketing_consent_at timestamp
# ---------------------------------------------------------------------------

class TestMarketingConsentAt:
    """marketing_consent_at must be set on opt-in, NULL on opt-out."""

    @pytest.mark.asyncio
    async def test_consent_at_set_when_opted_in(self):
        """When marketing_consent=True, marketing_consent_at is a recent timestamp."""
        from api.routers.auth import register, RegisterRequest

        req = RegisterRequest(
            email="optin@example.com",
            name="Opt In",
            password="password123",
            marketing_consent=True,
        )

        inserted_marketing_consent_at = None

        class _Conn(FakeConn):
            async def fetchrow(self, query, *args):
                if "SELECT id FROM users WHERE email" in query:
                    return None  # email not taken
                if "INSERT INTO users" in query:
                    # Capture the marketing_consent_at argument (5th positional param)
                    nonlocal inserted_marketing_consent_at
                    # args = (email, name, password_hash, verification_token, marketing_consent_at)
                    inserted_marketing_consent_at = args[4]
                    return {"id": 1, "email": req.email, "name": req.name}
                return None

            async def execute(self, query, *args):
                self.executed.append((query, args))

        fake_conn = _Conn()

        with (
            patch("api.routers.auth.get_connection") as mock_get_conn,
            patch("api.routers.auth.get_subscription_entitlements", return_value={
                "included_users": 1, "extra_seats": 0, "max_users": 1, "seat_price_gbp": 0,
            }),
            patch("api.routers.auth.write_audit_log", new_callable=AsyncMock),
            patch("api.routers.auth._send_verification_email", new_callable=AsyncMock),
            patch("api.routers.auth.hash_api_key", return_value="hashed"),
            patch("api.routers.auth.api_key_prefix", return_value="cg_xxxx"),
            patch("api.routers.auth.get_tier_config", return_value={"rate": 100}),
            patch("api.routers.auth.check_ip_rate_limit", return_value=None),
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=fake_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=False)

            await register(req, _ip=None)

        assert inserted_marketing_consent_at is not None, (
            "marketing_consent_at must be set (non-NULL) when marketing_consent=True"
        )
        assert isinstance(inserted_marketing_consent_at, datetime), (
            "marketing_consent_at must be a datetime"
        )
        # Should be recent (within last 5 seconds)
        age = (datetime.now(timezone.utc) - inserted_marketing_consent_at).total_seconds()
        assert 0 <= age < 5

    @pytest.mark.asyncio
    async def test_consent_at_null_when_not_opted_in(self):
        """When marketing_consent=False (default), marketing_consent_at is NULL."""
        from api.routers.auth import register, RegisterRequest

        req = RegisterRequest(
            email="optout@example.com",
            name="Opt Out",
            password="password123",
            marketing_consent=False,
        )

        inserted_marketing_consent_at = "NOT_CAPTURED"

        class _Conn(FakeConn):
            async def fetchrow(self, query, *args):
                if "SELECT id FROM users WHERE email" in query:
                    return None
                if "INSERT INTO users" in query:
                    nonlocal inserted_marketing_consent_at
                    inserted_marketing_consent_at = args[4]
                    return {"id": 2, "email": req.email, "name": req.name}
                return None

            async def execute(self, query, *args):
                self.executed.append((query, args))

        fake_conn = _Conn()

        with (
            patch("api.routers.auth.get_connection") as mock_get_conn,
            patch("api.routers.auth.get_subscription_entitlements", return_value={
                "included_users": 1, "extra_seats": 0, "max_users": 1, "seat_price_gbp": 0,
            }),
            patch("api.routers.auth.write_audit_log", new_callable=AsyncMock),
            patch("api.routers.auth._send_verification_email", new_callable=AsyncMock),
            patch("api.routers.auth.hash_api_key", return_value="hashed"),
            patch("api.routers.auth.api_key_prefix", return_value="cg_xxxx"),
            patch("api.routers.auth.get_tier_config", return_value={"rate": 100}),
            patch("api.routers.auth.check_ip_rate_limit", return_value=None),
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=fake_conn)
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=False)

            await register(req, _ip=None)

        assert inserted_marketing_consent_at is None, (
            "marketing_consent_at must be NULL when marketing_consent=False"
        )


# ---------------------------------------------------------------------------
# 4. Marketing email gate
# ---------------------------------------------------------------------------

class TestMarketingEmailGate:
    """send_marketing_email must skip silently when consent is missing."""

    @pytest.mark.asyncio
    async def test_marketing_email_skipped_without_consent(self):
        """No email is sent when marketing_consent_at IS NULL."""
        from api.routers.auth import send_marketing_email

        class _Conn(FakeConn):
            async def fetchrow(self, query, *args):
                # Simulate user with no marketing consent
                return {"marketing_consent_at": None, "deleted_at": None}

        with (
            patch("api.routers.auth.get_connection") as mock_get_conn,
            patch("api.routers.auth._send_resend_email", new_callable=AsyncMock) as mock_send,
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=_Conn())
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await send_marketing_email(
                user_id=1,
                email="user@example.com",
                subject="Big product update!",
                html="<p>Check out what's new</p>",
            )

        assert result is False, "send_marketing_email must return False when consent is missing"
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_marketing_email_sent_with_consent(self):
        """Email IS sent when marketing_consent_at is set and user is not deleted."""
        from api.routers.auth import send_marketing_email

        class _Conn(FakeConn):
            async def fetchrow(self, query, *args):
                return {
                    "marketing_consent_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "deleted_at": None,
                }

        with (
            patch("api.routers.auth.get_connection") as mock_get_conn,
            patch("api.routers.auth._send_resend_email", new_callable=AsyncMock) as mock_send,
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=_Conn())
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await send_marketing_email(
                user_id=1,
                email="user@example.com",
                subject="Big product update!",
                html="<p>Check out what's new</p>",
            )

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_marketing_email_skipped_for_deleted_user(self):
        """No email is sent when the user is soft-deleted (deleted_at IS NOT NULL)."""
        from api.routers.auth import send_marketing_email

        class _Conn(FakeConn):
            async def fetchrow(self, query, *args):
                return {
                    "marketing_consent_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "deleted_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
                }

        with (
            patch("api.routers.auth.get_connection") as mock_get_conn,
            patch("api.routers.auth._send_resend_email", new_callable=AsyncMock) as mock_send,
        ):
            mock_get_conn.return_value.__aenter__ = AsyncMock(return_value=_Conn())
            mock_get_conn.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await send_marketing_email(
                user_id=1,
                email="user@example.com",
                subject="Big product update!",
                html="<p>Check out what's new</p>",
            )

        assert result is False
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Transactional emails bypass gate
# ---------------------------------------------------------------------------

class TestTransactionalEmailsBypassGate:
    """Password reset and verification emails must work regardless of marketing consent."""

    @pytest.mark.asyncio
    async def test_password_reset_bypasses_gate(self):
        """_send_reset_email must call _send_resend_email directly, not send_marketing_email."""
        from api.routers import auth as auth_module

        with patch.object(auth_module, "_send_resend_email", new_callable=AsyncMock) as mock_send:
            # Patch settings
            auth_module.settings.resend_api_key = "re_test"
            auth_module.settings.enquiry_from_email = "noreply@caregist.co.uk"
            auth_module.settings.app_url = "https://caregist.co.uk"

            await auth_module._send_reset_email("user@example.com", "tok123")

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "password reset" in call_kwargs["subject"].lower()

    @pytest.mark.asyncio
    async def test_verification_email_bypasses_gate(self):
        """_send_verification_email must call _send_resend_email directly."""
        from api.routers import auth as auth_module

        with patch.object(auth_module, "_send_resend_email", new_callable=AsyncMock) as mock_send:
            auth_module.settings.resend_api_key = "re_test"
            auth_module.settings.enquiry_from_email = "noreply@caregist.co.uk"
            auth_module.settings.app_url = "https://caregist.co.uk"

            await auth_module._send_verification_email("user@example.com", "Alice", "tok456")

        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        assert "verify" in call_kwargs["subject"].lower()

    @pytest.mark.asyncio
    async def test_transactional_emails_do_not_call_marketing_gate(self):
        """Transactional helpers must NOT consult send_marketing_email."""
        from api.routers import auth as auth_module

        with (
            patch.object(auth_module, "_send_resend_email", new_callable=AsyncMock),
            patch.object(auth_module, "send_marketing_email", new_callable=AsyncMock) as mock_gate,
        ):
            auth_module.settings.resend_api_key = "re_test"
            auth_module.settings.app_url = "https://caregist.co.uk"

            await auth_module._send_reset_email("a@b.com", "tok")
            await auth_module._send_verification_email("a@b.com", "Alice", "tok")

        mock_gate.assert_not_called()
