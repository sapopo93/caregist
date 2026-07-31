from __future__ import annotations

import pytest

from api.services.trustroute import TrustRouteConfig, _payload_object, drain_trustroute_outbox


@pytest.mark.asyncio
async def test_disabled_trustroute_sync_is_a_noop() -> None:
    result = await drain_trustroute_outbox(TrustRouteConfig(False, "", "", ""))
    assert result == {"enabled": False, "claimed": 0, "succeeded": 0, "failed": 0}


def test_enabled_trustroute_sync_requires_https_and_credentials() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        TrustRouteConfig(True, "http://example.com", "org", "key").validate()
    with pytest.raises(ValueError, match="required"):
        TrustRouteConfig(True, "https://trustroute.example", "", "").validate()


def test_local_http_is_allowed_for_integration_tests() -> None:
    TrustRouteConfig(True, "http://127.0.0.1:8000", "org", "key", 1).validate()


def test_jsonb_payload_is_normalized_from_asyncpg_text() -> None:
    assert _payload_object('{"synthetic":true}') == {"synthetic": True}
    assert _payload_object({"synthetic": True}) == {"synthetic": True}
    with pytest.raises(ValueError, match="JSON object"):
        _payload_object('["not-an-object"]')
