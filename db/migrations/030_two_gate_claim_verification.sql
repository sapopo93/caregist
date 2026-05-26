-- Migration 030: add review_reason and pending_review status support to provider_claims
-- Supports two-gate claim verification: auto-approved vs pending_review.

-- Add review_reason column to store why a claim was auto-approved or queued.
ALTER TABLE provider_claims
  ADD COLUMN IF NOT EXISTS review_reason TEXT,
  ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;

-- Allow 'pending_review' and 'approved' as valid status values.
-- (The existing CHECK constraint, if any, would need updating — this migration
--  adds it only if the column lacks a check constraint already.)
-- No CHECK constraint was defined in init.sql, so no alteration needed.

-- Add fast_track column if missing (was added in growth features but guard here).
ALTER TABLE provider_claims
  ADD COLUMN IF NOT EXISTS fast_track BOOLEAN NOT NULL DEFAULT false;

-- Index to speed up admin moderation queue queries on status.
CREATE INDEX IF NOT EXISTS idx_provider_claims_status
  ON provider_claims (status);

-- Index for claimant email lookups (my-providers endpoint).
CREATE INDEX IF NOT EXISTS idx_provider_claims_email
  ON provider_claims (claimant_email);
