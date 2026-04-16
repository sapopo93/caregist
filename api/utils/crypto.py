"""AES-GCM encryption helpers for webhook secrets at rest."""

from __future__ import annotations

import base64
import logging
import os

logger = logging.getLogger("caregist.crypto")

_ENC_PREFIX = "enc:"


def _get_key(raw_key: str) -> bytes:
    """Decode the base64 key from settings. Must be 32 bytes."""
    key_bytes = base64.b64decode(raw_key)
    if len(key_bytes) != 32:
        raise ValueError(f"WEBHOOK_SECRET_KEY must decode to 32 bytes; got {len(key_bytes)}")
    return key_bytes


def encrypt_webhook_secret(plaintext: str, raw_key: str) -> str:
    """Encrypt a webhook signing secret with AES-256-GCM.

    Returns a string of the form ``enc:<base64(nonce + ciphertext + tag)>``
    that can be stored safely in the database.
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_key(raw_key)
    nonce = os.urandom(12)  # 96-bit nonce, standard for GCM
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode(), None)
    encoded = base64.b64encode(nonce + ciphertext_with_tag).decode()
    return f"{_ENC_PREFIX}{encoded}"


def decrypt_webhook_secret(stored: str, raw_key: str) -> str:
    """Decrypt a webhook signing secret previously produced by ``encrypt_webhook_secret``.

    If *stored* does not start with the ``enc:`` prefix it is returned as-is
    (plaintext legacy mode — allows gradual migration).
    """
    if not stored.startswith(_ENC_PREFIX):
        return stored  # legacy plaintext

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_key(raw_key)
    raw = base64.b64decode(stored[len(_ENC_PREFIX):])
    nonce, ciphertext_with_tag = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext_with_tag, None).decode()


def maybe_decrypt(stored: str, raw_key: str) -> str:
    """Decrypt if a key is configured, else return as-is."""
    if raw_key:
        return decrypt_webhook_secret(stored, raw_key)
    return stored
