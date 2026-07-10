#!/usr/bin/env python3
"""Back-fill script for migration 030: AES-GCM encrypt webhook signing secrets.

Run AFTER applying 030_encrypt_webhook_signing_secrets.sql and BEFORE starting
the new application version in production.

Usage:
    WEBHOOK_SECRET_KEY=<base64-key> DATABASE_URL=<dsn> python db/migrations/030_encrypt_webhook_signing_secrets.py

Idempotent: rows that already have signing_secret_encrypted populated are skipped.
Re-running the script is a no-op once all rows are encrypted.

The legacy plaintext `secret` column is LEFT INTACT.  A Phase B cleanup migration
will drop it after >= 7 days of verified production uptime on the new code.
"""

from __future__ import annotations

import base64
import os
import secrets
import sys


def _get_key() -> bytes:
    key_b64 = os.environ.get("WEBHOOK_SECRET_KEY")
    if not key_b64:
        print(
            "ERROR: WEBHOOK_SECRET_KEY is not set.\n"
            "Generate with: openssl rand -base64 32\n"
            "Then re-run: WEBHOOK_SECRET_KEY=<value> python db/migrations/030_encrypt_webhook_signing_secrets.py",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        key = base64.b64decode(key_b64, validate=True)
    except Exception as exc:
        print(f"ERROR: WEBHOOK_SECRET_KEY is not valid base64: {exc}", file=sys.stderr)
        sys.exit(1)
    if len(key) != 32:
        print(
            f"ERROR: WEBHOOK_SECRET_KEY must decode to exactly 32 bytes; got {len(key)}.\n"
            "Use: openssl rand -base64 32",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _encrypt(plaintext: str, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    cipher = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext_and_tag = cipher.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return nonce + ciphertext_and_tag


def main() -> None:
    import psycopg2

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    key = _get_key()

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            # Verify migration 030 SQL has been applied
            cur.execute(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.columns"
                "  WHERE table_name = 'webhook_subscriptions'"
                "    AND column_name = 'signing_secret_encrypted'"
                ");"
            )
            col_exists = cur.fetchone()[0]
            if not col_exists:
                print(
                    "ERROR: signing_secret_encrypted column does not exist.\n"
                    "Apply the SQL migration first:\n"
                    "  psql $DATABASE_URL -f db/migrations/030_encrypt_webhook_signing_secrets.sql",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Rows that need back-filling
            cur.execute(
                "SELECT id, secret FROM webhook_subscriptions "
                "WHERE secret IS NOT NULL "
                "  AND (signing_secret_encrypted IS NULL "
                "       OR length(signing_secret_encrypted) = 0);"
            )
            rows_to_encrypt = cur.fetchall()

            # Rows already encrypted
            cur.execute(
                "SELECT count(*) FROM webhook_subscriptions "
                "WHERE signing_secret_encrypted IS NOT NULL "
                "  AND length(signing_secret_encrypted) > 0;"
            )
            already_encrypted = cur.fetchone()[0]

            # Rows with no plaintext secret (should not exist, but count them)
            cur.execute(
                "SELECT count(*) FROM webhook_subscriptions "
                "WHERE secret IS NULL;"
            )
            no_plaintext = cur.fetchone()[0]

        re_encrypted = 0
        with conn.cursor() as cur:
            for row_id, plaintext_secret in rows_to_encrypt:
                encrypted_blob = _encrypt(plaintext_secret, key)
                cur.execute(
                    "UPDATE webhook_subscriptions "
                    "SET signing_secret_encrypted = %s "
                    "WHERE id = %s;",
                    (psycopg2.Binary(encrypted_blob), row_id),
                )
                re_encrypted += 1

        conn.commit()

    finally:
        conn.close()

    print(
        f"Re-encrypted {re_encrypted} webhook signing secret(s). "
        f"{already_encrypted} row(s) already encrypted. "
        f"{no_plaintext} row(s) had no plaintext."
    )


if __name__ == "__main__":
    main()
