"""AES-GCM encryption helpers for webhook secrets at rest."""

from __future__ import annotations

import base64
import logging
import os
import secrets

logger = logging.getLogger("caregist.crypto")

_NONCE_SIZE = 12


def _get_key() -> bytes:
    """Decode and validate WEBHOOK_SECRET_KEY from the environment.

    Raises RuntimeError if the variable is missing, not valid base64, or not
    exactly 32 bytes.  Every encrypt/decrypt call goes through this function so
    there is no code path that silently falls back to plaintext.
    """
    key_b64 = os.environ.get("WEBHOOK_SECRET_KEY")
    if not key_b64:
        raise RuntimeError(
            "WEBHOOK_SECRET_KEY is not set. "
            "Generate with `openssl rand -base64 32` and set in /etc/caregist/env. "
            "Caregist no longer supports plaintext webhook signing secrets."
        )
    try:
        key = base64.b64decode(key_b64, validate=True)
    except Exception as e:
        raise RuntimeError("WEBHOOK_SECRET_KEY must be valid base64.") from e
    if len(key) != 32:
        raise RuntimeError(
            f"WEBHOOK_SECRET_KEY must decode to exactly 32 bytes; got {len(key)}. "
            "Use `openssl rand -base64 32`."
        )
    return key


def encrypt_webhook_secret(plaintext: str) -> bytes:
    """AES-GCM encrypt a webhook signing secret.

    Returns raw bytes in the format: nonce (12 bytes) || ciphertext+tag.
    The caller is responsible for storing the returned bytes in a BYTEA column
    (signing_secret_encrypted).
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    cipher = AESGCM(_get_key())
    nonce = secrets.token_bytes(_NONCE_SIZE)
    ciphertext_and_tag = cipher.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return nonce + ciphertext_and_tag


def decrypt_webhook_secret(blob: bytes) -> str:
    """Decrypt an AES-GCM encrypted webhook signing secret.

    Expects raw bytes previously produced by encrypt_webhook_secret.
    Raises ValueError on obviously-malformed blobs; the underlying AESGCM raises
    cryptography.exceptions.InvalidTag on tampered ciphertext.
    """
    if len(blob) < _NONCE_SIZE + 16:
        raise ValueError("Encrypted blob too short to contain nonce + tag.")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    cipher = AESGCM(_get_key())
    nonce, ciphertext_and_tag = blob[:_NONCE_SIZE], blob[_NONCE_SIZE:]
    plaintext = cipher.decrypt(nonce, ciphertext_and_tag, associated_data=None)
    return plaintext.decode("utf-8")
