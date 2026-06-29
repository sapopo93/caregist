-- F-23: store password-reset tokens as hashes, not plaintext.
--
-- A DB read previously revealed live reset tokens. We add a token_hash column
-- (SHA-256 hex) that the application writes/compares against, and stop relying
-- on the plaintext token column. Any existing plaintext tokens are migrated to
-- their hash so in-flight resets keep working; the legacy column is nulled.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE password_reset_tokens
    ADD COLUMN IF NOT EXISTS token_hash CHAR(64);

UPDATE password_reset_tokens
SET token_hash = encode(digest(token, 'sha256'), 'hex')
WHERE token_hash IS NULL AND token IS NOT NULL;

ALTER TABLE password_reset_tokens
    ALTER COLUMN token DROP NOT NULL;

UPDATE password_reset_tokens
SET token = NULL
WHERE token_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token_hash
    ON password_reset_tokens (token_hash);
