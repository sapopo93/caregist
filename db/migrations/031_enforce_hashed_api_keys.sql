-- Enforce hashed-only API key storage.
--
-- Migration 026 converted existing plaintext keys to SHA-256 hashes and nulled
-- the legacy key column. This migration makes that invariant permanent.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

UPDATE api_keys
SET
  key_hash = encode(digest(key, 'sha256'), 'hex'),
  key_prefix = COALESCE(key_prefix, LEFT(key, 10))
WHERE key IS NOT NULL AND key_hash IS NULL;

UPDATE api_keys
SET key = NULL
WHERE key_hash IS NOT NULL;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM api_keys WHERE key_hash IS NULL) THEN
    RAISE EXCEPTION 'Cannot enforce hashed API keys while api_keys.key_hash contains NULL rows';
  END IF;
END $$;

ALTER TABLE api_keys
  ALTER COLUMN key_hash SET NOT NULL;

ALTER TABLE api_keys
  ADD CONSTRAINT api_keys_plaintext_key_absent CHECK (key IS NULL);
