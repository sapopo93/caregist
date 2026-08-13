from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from api.services.crm_ai import CallEvaluation, parse_evaluation_json
from api.services.crm_campaigns import is_email_marketing_eligible, render_campaign_html
from api.services.crm_email_events import resend_event_occurred_at, verify_resend_webhook
from api.services.crm_recordings import (
    delete_twilio_source,
    twilio_recording_url,
    validate_twilio_recording_sid,
    validate_twilio_recording_url,
)
from api.services.tenant_context import normalize_scope_config


def test_uk_email_eligibility_fails_closed():
    assert is_email_marketing_eligible(
        market_code="GB", subscriber_type="corporate",
        marketing_basis="corporate_subscriber", email="buyer@example.com",
    )
    assert not is_email_marketing_eligible(
        market_code="GB", subscriber_type="sole_trader",
        marketing_basis="corporate_subscriber", email="owner@example.com",
    )
    assert not is_email_marketing_eligible(
        market_code="GB", subscriber_type="corporate",
        marketing_basis="none", email="buyer@example.com",
    )
    assert not is_email_marketing_eligible(
        market_code="ZA", subscriber_type="corporate",
        marketing_basis="consent", email="buyer@example.com",
    )


def test_campaign_renderer_escapes_content_and_adds_unsubscribe(monkeypatch):
    from api.services import crm_campaigns

    monkeypatch.setattr(crm_campaigns.settings, "app_url", "https://www.caregist.co.uk")
    monkeypatch.setattr(crm_campaigns.settings, "crm_email_sender_postal_address", "CareGist, UK")
    html = render_campaign_html("Hello <script>alert(1)</script>", "safe-token")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "safe-token" in html
    assert "Unsubscribe" in html
    assert "CareGist, UK" in html


def test_recording_url_allows_twilio_https_only():
    assert validate_twilio_recording_url(
        "https://api.twilio.com/2010-04-01/Accounts/AC123/Recordings/RE123"
    ).endswith("RE123.mp3")
    assert validate_twilio_recording_url(
        "https://api.twilio.com/2010-04-01/Accounts/AC123/Recordings/RE123.mp3"
    ).endswith("RE123.mp3")
    for value in (
        "http://api.twilio.com/recording",
        "https://twilio.com.evil.example/recording",
        "https://user:pass@api.twilio.com/recording",
    ):
        with pytest.raises(ValueError):
            validate_twilio_recording_url(value)


def test_recording_sid_is_strict_and_url_is_account_bound(monkeypatch):
    from api.services import crm_recordings

    sid = "RE" + "a" * 32
    assert validate_twilio_recording_sid(sid) == sid
    monkeypatch.setattr(crm_recordings.settings, "twilio_account_sid", "AC" + "b" * 32)
    assert twilio_recording_url(sid) == (
        "https://api.twilio.com/2010-04-01/Accounts/"
        + "AC" + "b" * 32 + f"/Recordings/{sid}.mp3?RequestedChannels=2"
    )
    for invalid in ("", "RE123", "CA" + "a" * 32, "RE" + "z" * 32):
        with pytest.raises(ValueError):
            validate_twilio_recording_sid(invalid)


@pytest.mark.asyncio
async def test_twilio_source_delete_treats_already_absent_as_success(monkeypatch):
    import twilio.rest

    class AlreadyAbsent(Exception):
        status = 404

    class Recording:
        def delete(self):
            raise AlreadyAbsent()

    class Client:
        def __init__(self, *_args):
            pass

        def recordings(self, _sid):
            return Recording()

    monkeypatch.setattr(twilio.rest, "Client", Client)
    assert await delete_twilio_source("RE" + "a" * 32)


def test_ai_evaluation_is_schema_bound():
    evaluation = parse_evaluation_json(
        '{"summary":"A follow-up was agreed.","suggested_disposition":"callback_requested",'
        '"overall_qa_score":82,"customer_sentiment":"neutral","outcome":"Follow-up",'
        '"strengths":["Clear opening"],"coaching_actions":["Ask one more question"],'
        '"compliance_flags":[]}'
    )
    assert isinstance(evaluation, CallEvaluation)
    assert evaluation.overall_qa_score == 82
    with pytest.raises((ValidationError, ValueError)):
        parse_evaluation_json(
            '{"summary":"x","suggested_disposition":"connected","overall_qa_score":101,'
            '"customer_sentiment":"neutral","outcome":"x",'
            '"strengths":[],"coaching_actions":[],"compliance_flags":[]}'
        )
    with pytest.raises((ValidationError, ValueError)):
        CallEvaluation(
            summary="Follow-up agreed.",
            suggested_disposition="callback_requested",
            overall_qa_score=80,
            customer_sentiment="neutral",
            outcome="Follow-up",
            strengths=["x" * 501],
            coaching_actions=[],
            compliance_flags=[],
        )


def test_resend_webhook_fails_closed_without_secret(monkeypatch):
    from api.services import crm_email_events

    monkeypatch.setattr(crm_email_events.settings, "resend_webhook_secret", "")
    with pytest.raises(RuntimeError, match="not configured"):
        verify_resend_webhook(b"{}", {})


def test_resend_event_time_is_provider_evidence():
    occurred_at = resend_event_occurred_at({"created_at": "2026-08-13T05:00:00.000Z"})
    assert occurred_at.isoformat() == "2026-08-13T05:00:00+00:00"
    for invalid in (None, "2026-08-13T05:00:00", "not-a-time"):
        with pytest.raises(ValueError):
            resend_event_occurred_at({"created_at": invalid})


def test_tenant_scope_config_handles_asyncpg_json_codec_variants():
    assert normalize_scope_config({"region": "London"}) == {"region": "London"}
    assert normalize_scope_config('{"region":"London"}') == {"region": "London"}
    assert normalize_scope_config(None) == {}
    with pytest.raises(ValueError, match="JSON object"):
        normalize_scope_config('["London"]')


def test_full_uk_migration_keeps_audio_private_and_screening_hashed():
    migration = (
        Path(__file__).parents[1] / "db/migrations/053_crm_full_uk.sql"
    ).read_text(encoding="utf-8").lower()
    assert "crm_phone_screening_cache" in migration
    assert "phone_hmac" in migration
    assert "enable row level security" in migration
    assert "crm_recordings" in migration
    assert "bytea" not in migration
    assert "interval '30 days'" not in migration  # retention is application policy, not an unnoticed DB default
    assert "purged" in migration
    assert "crm_recording_ingest" in migration


def test_recording_callback_only_queues_private_ingestion():
    source = (
        Path(__file__).parents[1] / "api/routers/crm_extended.py"
    ).read_text(encoding="utf-8")
    endpoint = source.split("async def recording_complete", 1)[1].split(
        "@router.get(\"/recordings/", 1
    )[0]
    assert "download_twilio_recording" not in endpoint
    assert '"queued": True' in endpoint


def test_retention_reclaims_interrupted_deletions_and_separates_providers():
    source = (
        Path(__file__).parents[1] / "api/services/crm_retention.py"
    ).read_text(encoding="utf-8")
    assert "status = 'deleting'" in source
    assert "updated_at < NOW() - INTERVAL '15 minutes'" in source
    assert source.index("delete_recording_object") < source.index(
        "delete_twilio_source", source.index("async def purge_expired_recordings")
    )
    assert '"sources_deleted": sources_deleted' in source


def test_crm_operator_routes_use_unmetered_strict_browser_sessions():
    root = Path(__file__).parents[1]
    for route_file in (root / "api/routers/crm.py", root / "api/routers/crm_extended.py"):
        source = route_file.read_text(encoding="utf-8")
        assert "Depends(validate_api_key)" not in source
        assert "Depends(validate_session_identity)" in source


def test_call_permission_is_checked_at_authorization_and_dial_boundaries():
    source = (Path(__file__).parents[1] / "api/routers/crm.py").read_text(encoding="utf-8")
    assert source.count("await _enforce_call_permission(") == 2
    migration = (
        Path(__file__).parents[1] / "db/migrations/053_crm_full_uk.sql"
    ).read_text(encoding="utf-8")
    assert "crm_phone_screening_cache_twilio_policy" in migration
    assert 'call["status"] not in TERMINAL_CALL_STATUSES' in source
    assert "sequence > call[\"last_sequence_number\"]" in source


def test_crm_audit_json_keeps_uuid_parameters_typed_as_uuid():
    root = Path(__file__).parents[1]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            root / "api/routers/crm.py",
            root / "api/routers/crm_extended.py",
            root / "api/services/crm_ai.py",
        )
    )
    uuid_keys = "task|call_session|screening_event|deal|campaign|delivery|recording"
    assert not re.search(rf"'(?:{uuid_keys})_id'\s*,\s*\$\d+::text", source)
    assert "due_at.isoformat()" not in source
