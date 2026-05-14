"""Unit tests for AES-GCM webhook signing-secret encryption (api/utils/crypto.py)."""

from __future__ import annotations

import base64
import os

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_KEY_B64 = base64.b64encode(b"A" * 32).decode()  # 32 bytes, valid base64


@pytest.fixture(autouse=False)
def valid_key(monkeypatch):
    """Set a valid WEBHOOK_SECRET_KEY for tests that need it."""
    monkeypatch.setenv("WEBHOOK_SECRET_KEY", _TEST_KEY_B64)


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_round_trip(valid_key):
    from api.utils.crypto import decrypt_webhook_secret, encrypt_webhook_secret

    plaintext = "abc123"
    blob = encrypt_webhook_secret(plaintext)
    assert isinstance(blob, bytes)
    recovered = decrypt_webhook_secret(blob)
    assert recovered == plaintext


def test_round_trip_unicode(valid_key):
    from api.utils.crypto import decrypt_webhook_secret, encrypt_webhook_secret

    plaintext = "secret-with-unicode-éàü"
    assert decrypt_webhook_secret(encrypt_webhook_secret(plaintext)) == plaintext


# ---------------------------------------------------------------------------
# Nonce uniqueness — same plaintext must produce different ciphertexts
# ---------------------------------------------------------------------------


def test_nonce_uniqueness(valid_key):
    from api.utils.crypto import encrypt_webhook_secret

    blob1 = encrypt_webhook_secret("same_plaintext")
    blob2 = encrypt_webhook_secret("same_plaintext")
    assert blob1 != blob2, "Two encryptions of the same plaintext should differ (fresh nonces)"


# ---------------------------------------------------------------------------
# Missing key
# ---------------------------------------------------------------------------


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET_KEY", raising=False)
    # Reload module to clear any cached state
    import importlib
    import api.utils.crypto as crypto_mod
    importlib.reload(crypto_mod)

    with pytest.raises(RuntimeError, match="WEBHOOK_SECRET_KEY is not set"):
        crypto_mod.encrypt_webhook_secret("test")


def test_missing_key_decrypt_raises(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET_KEY", raising=False)
    import importlib
    import api.utils.crypto as crypto_mod
    importlib.reload(crypto_mod)

    with pytest.raises(RuntimeError, match="WEBHOOK_SECRET_KEY is not set"):
        crypto_mod.decrypt_webhook_secret(b"\x00" * 40)


# ---------------------------------------------------------------------------
# Wrong-length key
# ---------------------------------------------------------------------------


def test_wrong_length_key_raises(monkeypatch):
    # 16-byte key base64-encoded — valid base64 but wrong decoded length
    short_key = base64.b64encode(b"B" * 16).decode()
    monkeypatch.setenv("WEBHOOK_SECRET_KEY", short_key)
    import importlib
    import api.utils.crypto as crypto_mod
    importlib.reload(crypto_mod)

    with pytest.raises(RuntimeError, match="32 bytes"):
        crypto_mod.encrypt_webhook_secret("test")


def test_invalid_base64_key_raises(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET_KEY", "not-valid-base64!!!")
    import importlib
    import api.utils.crypto as crypto_mod
    importlib.reload(crypto_mod)

    with pytest.raises(RuntimeError, match="valid base64"):
        crypto_mod.encrypt_webhook_secret("test")


# ---------------------------------------------------------------------------
# Tampered ciphertext — auth tag failure
# ---------------------------------------------------------------------------


def test_tampered_ciphertext_raises(valid_key):
    from cryptography.exceptions import InvalidTag

    from api.utils.crypto import decrypt_webhook_secret, encrypt_webhook_secret

    blob = bytearray(encrypt_webhook_secret("original"))
    # Flip a bit in the ciphertext portion (after the 12-byte nonce)
    blob[15] ^= 0xFF
    with pytest.raises(InvalidTag):
        decrypt_webhook_secret(bytes(blob))


def test_too_short_blob_raises(valid_key):
    from api.utils.crypto import decrypt_webhook_secret

    with pytest.raises(ValueError, match="too short"):
        decrypt_webhook_secret(b"\x00" * 10)
