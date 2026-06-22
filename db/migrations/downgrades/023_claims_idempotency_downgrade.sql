-- Downgrade: 023_claims_idempotency
-- PARTIALLY REVERSIBLE with data caveat
-- The unique index and nullable column can be dropped safely.
-- The data mutation (auto-rejected duplicate claims) is NOT reversible without a snapshot restore;
-- those rows will remain in status='rejected' with the migration note.

-- Step 1: Drop unique index on pending_emails idempotency_key
DROP INDEX IF EXISTS idx_pending_emails_idempotency;

-- Step 2: Drop column (nullable, no data loss beyond the column itself)
ALTER TABLE pending_emails DROP COLUMN IF EXISTS idempotency_key;

-- Step 3: Drop partial unique index on provider_claims pending status
DROP INDEX IF EXISTS idx_provider_claims_one_pending;

-- NOTE: Rows that were auto-rejected by this migration remain rejected.
-- To restore them you must restore from a pre-migration snapshot.
-- See workflows/restore-from-snapshot.md (Bedrock PR #3).
