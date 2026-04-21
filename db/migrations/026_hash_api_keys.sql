-- Store API keys as one-way SHA-256 hashes.
-- Existing plaintext keys are converted in-place so presented keys continue to authenticate.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_hash CHAR(64);
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS key_prefix VARCHAR(16);
ALTER TABLE api_keys ALTER COLUMN key DROP NOT NULL;

UPDATE api_keys
SET
  key_hash = encode(digest(key, 'sha256'), 'hex'),
  key_prefix = LEFT(key, 10)
WHERE key IS NOT NULL AND key_hash IS NULL;

UPDATE api_rate_usage_daily
SET api_key = encode(digest(api_key, 'sha256'), 'hex')
WHERE length(api_key) <> 64 AND api_key NOT LIKE 'guest:%';

UPDATE api_keys
SET key = NULL
WHERE key_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON api_keys (key_prefix);
