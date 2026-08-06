"""Round-trip signing/verification test for outbound webhooks (F-43)."""

from unittest.mock import patch

import pytest

from api.utils import webhook_delivery
from api.utils.webhook_delivery import deliver_webhook, verify_signature


class _Resp:
    status_code = 200


def test_verify_signature_accepts_valid_and_rejects_tampered():
    secret = "whsec_test_secret"
    body = '{"event":"provider.rating_changed","id":42}'
    sig = "sha256=" + webhook_delivery._sign_payload(secret, body)

    assert verify_signature(secret, body, sig) is True
    # Wrong secret, tampered body, wrong scheme, and missing header all fail.
    assert verify_signature("other", body, sig) is False
    assert verify_signature(secret, body + " ", sig) is False
    assert verify_signature(secret, body, "md5=deadbeef") is False
    assert verify_signature(secret, body, None) is False


@pytest.mark.asyncio
async def test_delivered_payload_passes_published_verifier():
    """What deliver_webhook sends must verify with the helper we hand customers."""
    secret = "whsec_roundtrip"
    payload = {"event": "provider.rating_changed", "provider_id": "1-123", "new_rating": "Good"}

    captured = {}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, content=None, headers=None):
            captured["body"] = content
            captured["headers"] = headers
            return _Resp()

    with patch.object(webhook_delivery, "assert_public_webhook_url"), \
         patch.object(webhook_delivery.httpx, "AsyncClient", _Client):
        ok = await deliver_webhook("https://sub.example.com/hook", secret, payload)

    assert ok is True
    # A subscriber using verify_signature on the raw body + header accepts it.
    assert verify_signature(
        secret, captured["body"], captured["headers"]["X-CareGist-Signature"]
    )


@pytest.mark.asyncio
async def test_deliver_webhook_blocks_private_destination_before_http():
    class _Client:
        def __init__(self, *a, **k):
            raise AssertionError("HTTP client must not be opened for blocked destinations")

    with patch.object(webhook_delivery.httpx, "AsyncClient", _Client):
        result = await deliver_webhook(
            "http://127.0.0.1/internal",
            "whsec_blocked",
            {"event": "provider.rating_changed"},
            return_metadata=True,
        )

    assert result[0] is False
    assert result[1] == 0
    assert "public" in result[3]
