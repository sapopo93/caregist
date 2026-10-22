"""Tests documenting how a subscriber verifies CareGist webhook signatures.

This file serves two purposes:
  1. Executable tests proving the verification logic is correct.
  2. Embedded reference implementations in Python and Node.js that
     subscribers can copy directly (also published in docs/webhook-subscribers.md).

Signature scheme:
  Header:  X-CareGist-Signature: sha256=<hex-digest>
  Header:  X-CareGist-Event:     <event-name>
  Signing: HMAC-SHA256(key=shared_secret, msg=raw_request_body_bytes)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import pytest


# ---------------------------------------------------------------------------
# Reference Python verification (also in docs/webhook-subscribers.md)
# ---------------------------------------------------------------------------

PYTHON_VERIFICATION_SNIPPET = '''
import hashlib, hmac

def verify_caregist_signature(
    shared_secret: str,
    raw_body: bytes,
    signature_header: str,  # value of X-CareGist-Signature
) -> bool:
    """Return True if the webhook signature is authentic."""
    expected = hmac.new(
        shared_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected}"
    # Use compare_digest to prevent timing attacks
    return hmac.compare_digest(expected_header, signature_header)
'''

# ---------------------------------------------------------------------------
# Reference Node.js verification (for docs only — not executed by pytest)
# ---------------------------------------------------------------------------

NODEJS_VERIFICATION_SNIPPET = """
// Node.js / TypeScript
const crypto = require('crypto');

function verifyCareGistSignature(sharedSecret, rawBody, signatureHeader) {
  // rawBody must be the raw Buffer / Uint8Array from the request, not parsed JSON
  const expected = 'sha256=' + crypto
    .createHmac('sha256', sharedSecret)
    .update(rawBody)
    .digest('hex');
  // Use timingSafeEqual to prevent timing attacks
  const a = Buffer.from(expected);
  const b = Buffer.from(signatureHeader);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}
"""


# ---------------------------------------------------------------------------
# Helper: Python verifier extracted from snippet (keeps snippet testable)
# ---------------------------------------------------------------------------

def verify_caregist_signature(
    shared_secret: str,
    raw_body: bytes,
    signature_header: str,
) -> bool:
    expected = hmac.new(
        shared_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    expected_header = f"sha256={expected}"
    return hmac.compare_digest(expected_header, signature_header)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSubscriberSignatureVerification:
    """Exhaustive positive and negative tests for the subscriber verification path."""

    def _make_signed_body(self, secret: str, payload: dict) -> tuple[bytes, str]:
        """Return (raw_body, X-CareGist-Signature header value)."""
        body = json.dumps(payload, default=str).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return body, f"sha256={sig}"

    def test_valid_signature_verifies(self):
        secret = "super-secret-key"
        payload = {"event": "provider.rating_changed", "provider_id": "LOC123"}
        body, header = self._make_signed_body(secret, payload)
        assert verify_caregist_signature(secret, body, header) is True

    def test_tampered_body_fails(self):
        secret = "super-secret-key"
        payload = {"event": "provider.rating_changed", "provider_id": "LOC123"}
        body, header = self._make_signed_body(secret, payload)
        tampered_body = body.replace(b"LOC123", b"LOC999")
        assert verify_caregist_signature(secret, tampered_body, header) is False

    def test_wrong_secret_fails(self):
        correct_secret = "correct-secret"
        wrong_secret = "wrong-secret"
        payload = {"event": "test.event"}
        body, header = self._make_signed_body(correct_secret, payload)
        assert verify_caregist_signature(wrong_secret, body, header) is False

    def test_missing_sha256_prefix_fails(self):
        secret = "some-secret"
        payload = {"event": "test.event"}
        body, _ = self._make_signed_body(secret, payload)
        # Header without "sha256=" prefix
        raw_hex = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert verify_caregist_signature(secret, body, raw_hex) is False

    def test_empty_body_signed_correctly(self):
        secret = "empty-body-secret"
        raw_body = b""
        sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        header = f"sha256={sig}"
        assert verify_caregist_signature(secret, raw_body, header) is True

    def test_unicode_payload_bytes(self):
        """Payload with non-ASCII characters must use the exact byte representation."""
        secret = "unicode-secret"
        # Simulate what json.dumps produces — UTF-8 bytes
        payload_json = '{"name": "Ché Care Home", "event": "provider.rating_changed"}'
        raw_body = payload_json.encode("utf-8")
        sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        header = f"sha256={sig}"
        assert verify_caregist_signature(secret, raw_body, header) is True

    def test_different_events_different_signatures(self):
        secret = "shared-secret"
        body1, header1 = self._make_signed_body(secret, {"event": "event.a"})
        body2, header2 = self._make_signed_body(secret, {"event": "event.b"})
        # Verify each against its own header
        assert verify_caregist_signature(secret, body1, header1) is True
        assert verify_caregist_signature(secret, body2, header2) is True
        # Cross-verify must fail
        assert verify_caregist_signature(secret, body1, header2) is False

    def test_reference_snippet_is_valid_python(self):
        """The embedded Python snippet compiles and is syntactically valid."""
        compiled = compile(PYTHON_VERIFICATION_SNIPPET, "<snippet>", "exec")
        assert compiled is not None

    def test_nodejs_snippet_is_nonempty(self):
        """The Node.js snippet is present (content sanity check only)."""
        assert "timingSafeEqual" in NODEJS_VERIFICATION_SNIPPET
        assert "sha256" in NODEJS_VERIFICATION_SNIPPET
        assert "createHmac" in NODEJS_VERIFICATION_SNIPPET
