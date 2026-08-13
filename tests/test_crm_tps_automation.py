"""TPSCheck automation boundary, filtering, and fail-closed tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import HTTPException

from api.config import Settings
from api.routers.crm_extended import _validated_tps_filters
from api.services.crm_tps_automation import (
    TpsCheckError,
    _candidate_query,
    _fetch_credits,
    _saved_result,
    _screen_phone,
    normalize_uk_provider_phone,
    parse_tpscheck_result,
    process_tps_automation,
)


def test_normalize_uk_provider_phone_handles_cqc_national_numbers():
    assert normalize_uk_provider_phone("020 8081 4220") == "+442080814220"
    assert normalize_uk_provider_phone("07748 822130") == "+447748822130"
    assert normalize_uk_provider_phone("+44 1202 023109") == "+441202023109"
    assert normalize_uk_provider_phone("not a number") is None
    assert normalize_uk_provider_phone("+1 202 555 0123") is None


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"e164": "+442080814220", "valid": True, "tps": False, "ctps": False}, "clear"),
        ({"e164": "+442080814220", "valid": True, "tps": True, "ctps": False}, "tps"),
        ({"e164": "+442080814220", "valid": True, "tps": False, "ctps": True}, "ctps"),
        ({"e164": "+442080814220", "valid": False, "tps": False, "ctps": False}, "invalid"),
    ],
)
def test_parse_tpscheck_result_maps_only_explicit_boolean_results(payload, expected):
    result = parse_tpscheck_result(payload, "+442080814220")
    assert result.status == expected
    assert len(result.response_sha256) == 64


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {"e164": "+442080814220", "valid": "yes", "tps": False, "ctps": False},
        {"e164": "+442080814220", "valid": True, "tps": False},
        {"e164": "+447748822130", "valid": True, "tps": False, "ctps": False},
    ],
)
def test_parse_tpscheck_result_rejects_ambiguous_or_mismatched_data(payload):
    with pytest.raises(TpsCheckError):
        parse_tpscheck_result(payload, "+442080814220")


def test_saved_result_verifies_hash_and_preserves_original_screening_time():
    payload = {"e164": "+442080814220", "valid": True, "tps": False, "ctps": False}
    parsed = parse_tpscheck_result(payload, "+442080814220")
    screened_at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
    restored = _saved_result(
        {
            "phone_e164": "+442080814220",
            "result_payload": payload,
            "result_sha256": parsed.response_sha256,
            "screened_at": screened_at,
        }
    )
    assert restored is not None
    assert restored.screened_at == screened_at

    with pytest.raises(TpsCheckError, match="integrity"):
        _saved_result(
            {
                "phone_e164": "+442080814220",
                "result_payload": payload,
                "result_sha256": "0" * 64,
                "screened_at": screened_at,
            }
        )


def test_candidate_query_applies_the_same_feed_filters_with_bound_parameters():
    query, args = _candidate_query(
        {
            "organization_id": "00000000-0000-0000-0000-000000000001",
            "registered_from": date(2026, 8, 1),
            "filter_config": {
                "region": "London",
                "service_type": "Homecare Agencies",
                "postcode_prefix": "SW1",
                "from_date": "2026-08-05",
                "to_date": "2026-08-12",
            },
        },
        50,
    )
    assert "NOT EXISTS" in query
    assert "cp.region = $3" in query
    assert "cp.service_types ILIKE $4" in query
    assert "replace(cp.postcode, ' ', '') ILIKE $5" in query
    assert "event.effective_date <= $6" in query
    assert "LIMIT $7" in query
    assert args == [
        "00000000-0000-0000-0000-000000000001",
        date(2026, 8, 5),
        "London",
        "%Homecare Agencies%",
        "SW1%",
        date(2026, 8, 12),
        50,
    ]


def test_tps_filter_validation_rejects_unknown_and_invalid_ranges():
    assert _validated_tps_filters({"region": " London ", "q": ""}) == {"region": "London"}
    with pytest.raises(HTTPException):
        _validated_tps_filters({"secret_sql": "anything"})
    with pytest.raises(HTTPException):
        _validated_tps_filters({"from_date": "2026-08-14", "to_date": "2026-08-13"})


@pytest.mark.asyncio
async def test_provider_http_contract_uses_v2_and_token_auth(monkeypatch):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/credits":
            return httpx.Response(
                200,
                json={
                    "requests_used": 1,
                    "requests_remaining": 9999,
                    "monthly_limit": 10000,
                    "plan": "Starter",
                    "reset_date": "2026-09-13T00:00:00Z",
                },
            )
        return httpx.Response(
            200,
            json={"e164": "+442080814220", "valid": True, "tps": False, "ctps": False},
        )

    monkeypatch.setattr("api.services.crm_tps_automation.settings.crm_tpscheck_api_key", "test-key")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.tpscheck.uk"
    ) as client:
        credits = await _fetch_credits(client)
        result, status = await _screen_phone(client, "+442080814220")

    assert credits["requests_remaining"] == 9999
    assert result.status == "clear" and status == 200
    assert [request.url.path for request in seen] == ["/credits", "/check"]
    assert seen[1].url.params["version"] == "2"
    assert all(request.headers["authorization"] == "Token test-key" for request in seen)


@pytest.mark.asyncio
async def test_automation_is_a_noop_behind_global_kill_switch(monkeypatch):
    monkeypatch.setattr("api.services.crm_tps_automation.settings.crm_tps_automation_enabled", False)
    assert await process_tps_automation() == {
        "skipped": True,
        "reason": "disabled",
        "seeded": 0,
        "processed": 0,
    }


def test_tps_automation_startup_is_fail_closed_without_secret_or_approved_origin():
    with pytest.raises(RuntimeError, match="CRM_TPSCHECK_API_KEY"):
        Settings(
            crm_enabled=True,
            crm_tps_automation_enabled=True,
            crm_screening_hash_key="h" * 32,
        ).validate_production()

    with pytest.raises(RuntimeError, match="approved TPSCheck HTTPS origin"):
        Settings(
            crm_enabled=True,
            crm_tps_automation_enabled=True,
            crm_screening_hash_key="h" * 32,
            crm_tpscheck_api_key="secret",
            crm_tpscheck_base_url="https://attacker.example/check",
        ).validate_production()

    Settings(
        crm_enabled=True,
        crm_tps_automation_enabled=True,
        crm_screening_hash_key="h" * 32,
        crm_tpscheck_api_key="secret",
        crm_tpscheck_base_url="https://api.tpscheck.uk",
    ).validate_production()
