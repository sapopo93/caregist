from __future__ import annotations

from unittest.mock import patch
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from api.config import Settings
from api.routers import crm
from api.services.crm_calling import (
    allowed_test_numbers,
    hash_call_authorization,
    hash_screening_number,
    map_twilio_status,
    normalize_e164,
    twilio_webhook_url,
    validate_twilio_call_sid,
    validate_twilio_request,
)


def test_e164_boundary_accepts_normalized_number_only():
    assert normalize_e164(" +447700900000 ") == "+447700900000"
    assert normalize_e164(None) is None

    for invalid in ("07700900000", "+44 7700-900000", "+0123456789", "+44"):
        with pytest.raises(HTTPException) as exc:
            normalize_e164(invalid)
        assert exc.value.status_code == 422


def test_test_number_allowlist_is_fail_closed():
    assert allowed_test_numbers("+447700900000, +442071234567") == {
        "+447700900000", "+442071234567"
    }
    assert allowed_test_numbers("") == frozenset()
    with pytest.raises(RuntimeError, match="E.164"):
        allowed_test_numbers("07700900000")


def test_call_authorization_hash_is_deterministic_without_storing_secret():
    digest = hash_call_authorization("one-time-secret")
    assert digest == hash_call_authorization("one-time-secret")
    assert digest != hash_call_authorization("different-secret")
    assert len(digest) == 64
    assert "one-time-secret" not in digest


def test_screening_number_hash_is_keyed_and_deterministic():
    number = "+442071234567"
    first = hash_screening_number(number, "a" * 32)
    assert first == hash_screening_number(number, "a" * 32)
    assert first != hash_screening_number(number, "b" * 32)
    assert number not in first
    with pytest.raises(RuntimeError, match="hash key"):
        hash_screening_number(number, "short")


@pytest.mark.parametrize(
    ("twilio_status", "crm_status"),
    [
        ("queued", "initiated"),
        ("ringing", "ringing"),
        ("in-progress", "in_progress"),
        ("completed", "completed"),
        ("busy", "busy"),
        ("no-answer", "no_answer"),
        ("failed", "failed"),
        ("canceled", "canceled"),
    ],
)
def test_twilio_statuses_map_to_constrained_crm_states(twilio_status, crm_status):
    assert map_twilio_status(twilio_status) == crm_status


def test_open_call_can_be_closed_so_the_operator_can_log_an_outcome():
    assert crm.close_status_for_disposition("completed") is None
    assert crm.close_status_for_disposition("authorized") == "failed"
    assert crm.close_status_for_disposition("initiated") == "failed"
    with pytest.raises(HTTPException) as exc:
        crm.close_status_for_disposition("unknown")
    assert exc.value.status_code == 409


def test_unknown_twilio_status_is_rejected():
    with pytest.raises(HTTPException) as exc:
        map_twilio_status("mystery")
    assert exc.value.status_code == 422


def test_webhook_url_uses_configured_public_origin():
    assert twilio_webhook_url(
        "https://www.caregist.co.uk/",
        "/api/v1/crm/twilio/voice",
    ) == "https://www.caregist.co.uk/api/v1/crm/twilio/voice"


def test_twilio_call_sid_is_strict():
    sid = "CA" + "a" * 32
    assert validate_twilio_call_sid(sid) == sid
    for invalid in ("", "CA123", "RE" + "a" * 32, "CA" + "z" * 32):
        with pytest.raises(HTTPException) as caught:
            validate_twilio_call_sid(invalid)
        assert caught.value.status_code == 422


def test_invalid_twilio_signature_is_rejected():
    class RejectingValidator:
        def __init__(self, _token):
            pass

        def validate(self, _url, _form, _signature):
            return False

    with patch("twilio.request_validator.RequestValidator", RejectingValidator):
        with pytest.raises(HTTPException) as exc:
            validate_twilio_request(
                auth_token="secret",
                signature="invalid",
                url="https://www.caregist.co.uk/api/v1/crm/twilio/voice",
                form={"CallSid": "CA123"},
            )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_twilio_body_size_is_rejected_before_form_parsing():
    request = Mock()
    request.headers = {"content-length": str(crm.MAX_TWILIO_WEBHOOK_BYTES + 1)}
    request.body = AsyncMock()
    request.form = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await crm._twilio_form(request)

    assert exc.value.status_code == 413
    request.body.assert_not_awaited()
    request.form.assert_not_awaited()


@pytest.mark.asyncio
async def test_twilio_actual_body_size_cannot_exceed_declared_length():
    request = Mock()
    request.headers = {"content-length": "1"}
    request.body = AsyncMock(return_value=b"x" * (crm.MAX_TWILIO_WEBHOOK_BYTES + 1))
    request.form = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await crm._twilio_form(request)

    assert exc.value.status_code == 413
    request.body.assert_awaited_once()
    request.form.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("content_length", [None, "not-a-number", "0", "-1"])
async def test_twilio_body_size_fails_closed_when_length_is_invalid(content_length):
    request = Mock()
    request.headers = {} if content_length is None else {"content-length": content_length}
    request.body = AsyncMock()
    request.form = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await crm._twilio_form(request)

    assert exc.value.status_code == 413
    request.body.assert_not_awaited()
    request.form.assert_not_awaited()


def test_calling_gate_requires_all_independent_approvals(monkeypatch):
    monkeypatch.setattr(crm.settings, "crm_enabled", True)
    monkeypatch.setattr(crm.settings, "crm_calling_enabled", True)
    monkeypatch.setattr(crm.settings, "outbound_communications_enabled", False)
    with pytest.raises(HTTPException) as exc:
        crm._require_calling_enabled()
    assert exc.value.status_code == 503


def test_calling_gate_allows_recording_only_after_calling_credentials_exist(monkeypatch):
    monkeypatch.setattr(crm.settings, "crm_enabled", True)
    monkeypatch.setattr(crm.settings, "crm_calling_enabled", True)
    monkeypatch.setattr(crm.settings, "outbound_communications_enabled", True)
    monkeypatch.setattr(crm.settings, "crm_recording_enabled", True)
    monkeypatch.setattr(crm.settings, "crm_pilot_mode", True)
    monkeypatch.setattr(crm.settings, "crm_allowed_test_numbers", "+447700900000")
    for name, value in {
        "twilio_account_sid": "AC123",
        "twilio_api_key_sid": "SK123",
        "twilio_api_key_secret": "secret",
        "twilio_auth_token": "auth",
        "twilio_twiml_app_sid": "AP123",
        "twilio_phone_number": "+442071234567",
        "twilio_webhook_base_url": "https://www.caregist.co.uk",
    }.items():
        monkeypatch.setattr(crm.settings, name, value)
    crm._require_calling_enabled()


def test_production_config_rejects_recording_without_notice_and_private_storage():
    configured = Settings(
        database_url="postgresql://production.example/caregist",
        app_url="https://www.caregist.co.uk",
        cors_origins="https://www.caregist.co.uk",
        api_master_key="master",
        support_internal_token="support",
        webhook_secret_key="encryption",
        redis_url="rediss://redis.example:6380/0",
        crm_calling_enabled=True,
        crm_recording_enabled=True,
    )
    with pytest.raises(RuntimeError, match="approved notice and private storage"):
        configured.validate_production()


def test_production_calling_requires_dual_gate_and_credentials():
    configured = Settings(
        database_url="postgresql://production.example/caregist",
        app_url="https://www.caregist.co.uk",
        cors_origins="https://www.caregist.co.uk",
        api_master_key="master",
        support_internal_token="support",
        webhook_secret_key="encryption",
        redis_url="rediss://redis.example:6380/0",
        crm_enabled=True,
        crm_calling_enabled=True,
        outbound_communications_enabled=False,
    )
    with pytest.raises(RuntimeError, match="OUTBOUND_COMMUNICATIONS_ENABLED"):
        configured.validate_production()


def test_crm_migration_keeps_audio_out_of_postgres():
    migration = (
        __import__("pathlib").Path(__file__).parents[1]
        / "db/migrations/052_crm_calling_mvp.sql"
    ).read_text(encoding="utf-8")
    lowered = migration.lower()
    assert "enable row level security" in lowered
    assert "authorization_token_hash" in lowered
    assert "recording_url" not in lowered
    assert "audio" not in lowered.replace("audio is never stored in postgresql", "")
    assert "crm_suppressions" in lowered
    assert "crm_call_events" in lowered
