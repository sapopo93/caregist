-- Migration 033: marketing_consent_at column on users
-- UK GDPR Art 7 requires granular, freely-given, unbundled consent for marketing.
-- This column records the timestamp at which the user explicitly opted in.
-- NULL = no consent given (default). Never backfill to true.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS marketing_consent_at TIMESTAMPTZ;

COMMENT ON COLUMN users.marketing_consent_at IS
  'Timestamp (UTC) when the user actively opted in to marketing communications. '
  'NULL means no consent was given. Must not be set without explicit user action. '
  'UK GDPR Art 7 — freely given, specific, informed, unambiguous.';
