-- Migration 030: Add signing_secret_encrypted BYTEA column to webhook_subscriptions.
--
-- This migration is idempotent (safe to re-run).
--
-- Phase A (this migration):
--   1. Add signing_secret_encrypted BYTEA column if it does not already exist.
--   2. The column is intentionally nullable; NULL = not yet back-filled (new rows
--      written by the updated application code will populate it directly).
--
-- Encryption back-fill of existing rows is performed by the companion Python
-- script db/migrations/030_encrypt_webhook_signing_secrets.py which must be run
-- AFTER applying this SQL migration and BEFORE starting the new application version.
--
-- Phase B (future cleanup migration):
--   Once the new code has been running in production for >= 7 days, a separate
--   migration will DROP the legacy plaintext `secret` column.
--
-- Pre-merge count-check (run against prod before merging this PR):
--   SELECT count(*) AS total_subs,
--          count(secret) AS plaintext_secrets,
--          count(signing_secret_encrypted) AS encrypted_secrets
--   FROM webhook_subscriptions;
--
-- If total_subs = 0: safe to merge and deploy; back-fill script is a no-op.
-- If total_subs > 0 with plaintext_secrets > 0: run back-fill script before deploy.

ALTER TABLE webhook_subscriptions
    ADD COLUMN IF NOT EXISTS signing_secret_encrypted BYTEA;

COMMENT ON COLUMN webhook_subscriptions.signing_secret_encrypted IS
    'AES-256-GCM encrypted webhook signing secret. '
    'Format: 12-byte nonce || ciphertext || 16-byte auth tag. '
    'Key = WEBHOOK_SECRET_KEY env var (32 bytes, base64-encoded). '
    'NULL on pre-030 rows until back-fill script runs. '
    'Phase B migration will drop the plaintext secret column.';
