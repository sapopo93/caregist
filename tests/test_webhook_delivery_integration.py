"""Integration tests: happy-path webhook delivery + subscriber-side HMAC verification.

Covers the full pipeline:
  1. A webhook_subscription row exists (simulated via mock DB).
  2. deliver_to_subscriptions() fetches it, decrypts the stored secret via
     maybe_decrypt (Forge PR #5 AES-GCM path), and calls deliver_webhook().
  3. A mock subscriber endpoint receives the POST.
  4. The subscriber independently verifies the HMAC-SHA256 signature.
  5. Delivery metadata (attempts, status) is asserted.

These tests do NOT touch production code; they exercise the public API of
api/utils/webhook_delivery.py and api/utils/crypto.py only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from api.utils.webhook_delivery import (
    _sign_payload,
    deliver_webhook,
    deliver_to_subscriptions,
    _FAILURE_DISABLE_THRESHOLD,
)
from api.utils.crypto import encrypt_webhook_secret, maybe_decrypt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_aes_key() -> str:
    """Return a valid base64-encoded 32-byte key for AES-256-GCM."""
    return base64.b64encode(os.urandom(32)).decode()


def _subscriber_verify(shared_secret: str, payload_body: bytes, signature_header: str) -> bool:
    """Reference subscriber verification function (mirrors docs/webhook-subscribers.md)."""
    expected_sig = hmac.new(
        shared_secret.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected_sig}"
    return hmac.compare_digest(expected_header, signature_header)


# ---------------------------------------------------------------------------
# Unit: _sign_payload
# ---------------------------------------------------------------------------

def test_sign_payload_produces_sha256_hex():
    secret = "my-secret"
    payload_json = '{"event": "provider.rating_changed", "data": {}}'
    sig = _sign_payload(secret, payload_json)
    expected = hmac.new(secret.encode(), payload_json.encode(), hashlib.sha256).hexdigest()
    assert sig == expected
    assert len(sig) == 64  # 256 bits as hex


def test_sign_payload_differs_with_different_secret():
    payload_json = '{"event": "test"}'
    sig1 = _sign_payload("secret-a", payload_json)
    sig2 = _sign_payload("secret-b", payload_json)
    assert sig1 != sig2


# ---------------------------------------------------------------------------
# Integration: deliver_webhook — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deliver_webhook_happy_path_first_attempt():
    """Subscriber returns 200 on first attempt; delivery succeeds."""
    secret = "integration-test-secret"
    payload = {"event": "provider.rating_changed", "provider_id": "LOC123", "rating": "Good"}
    payload_json = json.dumps(payload, default=str)
    expected_sig = f"sha256={_sign_payload(secret, payload_json)}"

    received_headers: dict = {}
    received_body: bytes = b""

    with respx.mock(assert_all_called=True):
        def capture_request(request: httpx.Request) -> httpx.Response:
            nonlocal received_headers, received_body
            received_headers = dict(request.headers)
            received_body = request.content
            return httpx.Response(200)

        respx.post("https://subscriber.example.com/hooks").mock(side_effect=capture_request)

        result = await deliver_webhook(
            url="https://subscriber.example.com/hooks",
            secret=secret,
            payload=payload,
            return_metadata=True,
        )

    success, attempts, status_code, error = result

    # Delivery assertions
    assert success is True
    assert attempts == 1
    assert status_code == 200
    assert error is None

    # Header assertions
    assert received_headers["x-caregist-signature"] == expected_sig
    assert received_headers["x-caregist-event"] == "provider.rating_changed"
    assert received_headers["content-type"] == "application/json"
    assert received_headers["user-agent"] == "CareGist-Webhooks/1.0"

    # Subscriber-side HMAC verification
    assert _subscriber_verify(secret, received_body, received_headers["x-caregist-signature"])


@pytest.mark.asyncio
async def test_deliver_webhook_signature_fails_with_wrong_secret():
    """Subscriber with a wrong secret cannot validate the signature."""
    correct_secret = "correct-secret"
    wrong_secret = "wrong-secret"
    payload = {"event": "provider.rating_changed"}
    payload_json = json.dumps(payload, default=str)
    received_headers: dict = {}
    received_body: bytes = b""

    with respx.mock():
        def capture(request: httpx.Request) -> httpx.Response:
            nonlocal received_headers, received_body
            received_headers = dict(request.headers)
            received_body = request.content
            return httpx.Response(200)

        respx.post("https://subscriber.example.com/hooks").mock(side_effect=capture)
        await deliver_webhook("https://subscriber.example.com/hooks", correct_secret, payload)

    # Subscriber using the wrong secret must not validate
    assert not _subscriber_verify(wrong_secret, received_body, received_headers["x-caregist-signature"])


# ---------------------------------------------------------------------------
# Integration: deliver_to_subscriptions — uses encrypted-at-rest secret (Forge PR #5)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deliver_to_subscriptions_decrypts_aes_gcm_secret():
    """
    Verifies Forge PR #5 coordination: the secret stored in the DB is AES-GCM
    encrypted (enc: prefix). deliver_to_subscriptions decrypts it via
    maybe_decrypt before signing. The subscriber receives a correctly-signed payload.
    """
    aes_key = _make_aes_key()
    plaintext_secret = "my-subscriber-signing-secret"
    encrypted_secret = encrypt_webhook_secret(plaintext_secret, aes_key)

    assert encrypted_secret.startswith("enc:")

    payload = {"event": "provider.rating_changed", "provider_id": "LOC999"}
    payload_json = json.dumps(
        {"event": "provider.rating_changed", **payload},
        default=str,
    )

    received_headers: dict = {}
    received_body: bytes = b""

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {"id": 1, "url": "https://sub.example.com/hook", "secret": encrypted_secret}
    ])
    mock_conn.execute = AsyncMock()

    with respx.mock():
        def capture(request: httpx.Request) -> httpx.Response:
            nonlocal received_headers, received_body
            received_headers = dict(request.headers)
            received_body = request.content
            return httpx.Response(200)

        respx.post("https://sub.example.com/hook").mock(side_effect=capture)

        with patch("api.utils.webhook_delivery.settings") as mock_settings:
            mock_settings.webhook_secret_key = aes_key
            await deliver_to_subscriptions(
                conn=mock_conn,
                user_id=42,
                event="provider.rating_changed",
                payload={"provider_id": "LOC999"},
            )

    # After delivery the conn.execute should update last_delivery_at
    assert mock_conn.execute.called

    # Subscriber verification: decrypt the secret the same way, sign, compare
    decrypted_secret = maybe_decrypt(encrypted_secret, aes_key)
    assert decrypted_secret == plaintext_secret
    assert _subscriber_verify(decrypted_secret, received_body, received_headers["x-caregist-signature"])


@pytest.mark.asyncio
async def test_deliver_to_subscriptions_no_active_subscriptions_is_noop():
    """If no subscriptions match, nothing is delivered."""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])

    with respx.mock(assert_all_called=False):
        with patch("api.utils.webhook_delivery.settings") as mock_settings:
            mock_settings.webhook_secret_key = ""
            await deliver_to_subscriptions(
                conn=mock_conn,
                user_id=1,
                event="provider.rating_changed",
                payload={},
            )

    mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_to_subscriptions_legacy_plaintext_secret():
    """Legacy subscriptions (no enc: prefix) still work via maybe_decrypt passthrough."""
    plaintext_secret = "legacy-plaintext-secret"
    received_headers: dict = {}
    received_body: bytes = b""

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[
        {"id": 5, "url": "https://legacy.example.com/hook", "secret": plaintext_secret}
    ])
    mock_conn.execute = AsyncMock()

    with respx.mock():
        def capture(request: httpx.Request) -> httpx.Response:
            nonlocal received_headers, received_body
            received_headers = dict(request.headers)
            received_body = request.content
            return httpx.Response(200)

        respx.post("https://legacy.example.com/hook").mock(side_effect=capture)

        with patch("api.utils.webhook_delivery.settings") as mock_settings:
            mock_settings.webhook_secret_key = ""
            await deliver_to_subscriptions(
                conn=mock_conn,
                user_id=7,
                event="provider.rating_changed",
                payload={"note": "legacy"},
            )

    assert _subscriber_verify(plaintext_secret, received_body, received_headers["x-caregist-signature"])
