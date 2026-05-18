-- Migration 032: bcrypt-only enforcement for API keys.
-- Adds key_format column so the back-fill script (032_hash_legacy_api_keys.py)
-- can track which rows have been migrated. After migration 032 runs, the
-- plaintext acceptance path in api/middleware/auth.py no longer exists.
--
-- Idempotent: safe to re-run.

ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS key_format TEXT NOT NULL DEFAULT 'bcrypt'
        CHECK (key_format IN ('plaintext', 'bcrypt'));

-- Mark rows that still carry a non-NULL key column as plaintext so the
-- back-fill script can locate them precisely.
UPDATE api_keys
SET key_format = 'plaintext'
WHERE key IS NOT NULL
  AND key_format = 'bcrypt';

-- Pre-merge count-check SQL — run before merging this branch:
--   SELECT count(*) FILTER (WHERE key_format = 'plaintext') FROM api_keys;
-- If 0, merge freely. If > 0, run db/migrations/032_hash_legacy_api_keys.py first.
