"""Migration 032 back-fill: bcrypt-hash any remaining plaintext API key rows.

Run this script once before deploying the bcrypt-only middleware change.
It is idempotent: rows already marked 'bcrypt' are skipped.

Usage:
    python db/migrations/032_hash_legacy_api_keys.py

Environment:
    DATABASE_URL — asyncpg-compatible connection string (required).
"""

from __future__ import annotations

import asyncio
import logging
import os

try:
    import bcrypt as _bcrypt  # type: ignore
except ImportError:
    raise SystemExit("bcrypt package is required: pip install bcrypt")

import asyncpg  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("migration-032")

DATABASE_URL = os.environ["DATABASE_URL"]


async def run() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT id, key
            FROM api_keys
            WHERE key_format = 'plaintext'
              AND key IS NOT NULL
            ORDER BY id
            """
        )
        if not rows:
            log.info("No plaintext rows found — nothing to migrate.")
            return

        log.info("Found %d plaintext row(s) to back-fill.", len(rows))

        for row in rows:
            key_id: int = row["id"]
            plaintext_key: str = row["key"]
            key_prefix: str = plaintext_key[:8]

            new_hash: str = _bcrypt.hashpw(
                plaintext_key.encode(), _bcrypt.gensalt(rounds=12)
            ).decode()

            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE api_keys
                    SET key_hash = $1,
                        key      = NULL,
                        key_format = 'bcrypt'
                    WHERE id = $2
                      AND key_format = 'plaintext'
                    """,
                    new_hash,
                    key_id,
                )
                await conn.execute(
                    """
                    INSERT INTO admin_audit_log (action, actor, metadata, created_at)
                    VALUES (
                        'api_key.bcrypt_backfill',
                        'migration-032',
                        jsonb_build_object(
                            'api_key_id', $1,
                            'key_prefix',  $2
                        ),
                        NOW()
                    )
                    """,
                    key_id,
                    key_prefix,
                )
                log.info("Migrated api_key id=%d (prefix=%s).", key_id, key_prefix)

        log.info("Back-fill complete. All plaintext rows are now bcrypt-hashed.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
