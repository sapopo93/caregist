-- Prevent duplicate pending claims for the same provider.
-- Only one claim per provider may be in 'pending' status at a time.
-- Existing multi-pending rows are collapsed before the index is created.
-- The newest pending claim remains pending; older duplicate pending claims are
-- rejected so this migration is safe to run against production data that already
-- contains duplicates.
WITH ranked_pending AS (
  SELECT
    id,
    ROW_NUMBER() OVER (PARTITION BY provider_id ORDER BY created_at DESC, id DESC) AS rn
  FROM provider_claims
  WHERE status = 'pending'
)
UPDATE provider_claims pc
SET
  status = 'rejected',
  reviewed_at = COALESCE(pc.reviewed_at, NOW()),
  admin_notes = CONCAT_WS(
    E'\n',
    NULLIF(pc.admin_notes, ''),
    'Auto-rejected by migration 023: duplicate pending claim superseded by the newest pending claim.'
  )
FROM ranked_pending rp
WHERE pc.id = rp.id
  AND rp.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_provider_claims_one_pending
  ON provider_claims (provider_id)
  WHERE status = 'pending';

-- Idempotency key for pending_emails to prevent duplicate drip emails
-- on retried claim submissions or concurrent requests.
ALTER TABLE pending_emails
  ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_pending_emails_idempotency
  ON pending_emails (idempotency_key)
  WHERE idempotency_key IS NOT NULL;
