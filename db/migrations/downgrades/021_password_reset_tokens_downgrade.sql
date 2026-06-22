-- Downgrade: 021_password_reset_tokens
-- REVERSIBLE
-- Drops the password_reset_tokens table and its indexes.
-- Risk: live password-reset flows will break immediately; invalidates all in-flight tokens.

DROP INDEX IF EXISTS idx_password_reset_tokens_email;
DROP INDEX IF EXISTS idx_password_reset_tokens_token;
DROP TABLE IF EXISTS password_reset_tokens;
