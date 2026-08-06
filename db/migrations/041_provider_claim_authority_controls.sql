-- Fail-closed provider identity, authority, and moderation controls.
-- No claim becomes active unless verified evidence exists and a separate
-- moderator records the final decision.

ALTER TABLE provider_claims
  ADD COLUMN IF NOT EXISTS claimant_user_id INT REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS identity_status TEXT NOT NULL DEFAULT 'unverified',
  ADD COLUMN IF NOT EXISTS authority_status TEXT NOT NULL DEFAULT 'unverified',
  ADD COLUMN IF NOT EXISTS identity_verified_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS identity_verified_by TEXT,
  ADD COLUMN IF NOT EXISTS authority_verified_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS authority_verified_by TEXT,
  ADD COLUMN IF NOT EXISTS verification_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS decision_reason_code TEXT,
  ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;

UPDATE provider_claims pc
SET claimant_user_id = u.id
FROM users u
WHERE pc.claimant_user_id IS NULL
  AND LOWER(pc.claimant_email) = LOWER(u.email);

ALTER TABLE provider_claims
  DROP CONSTRAINT IF EXISTS provider_claims_identity_status_check,
  ADD CONSTRAINT provider_claims_identity_status_check
    CHECK (identity_status IN ('unverified', 'verified', 'rejected', 'expired')),
  DROP CONSTRAINT IF EXISTS provider_claims_authority_status_check,
  ADD CONSTRAINT provider_claims_authority_status_check
    CHECK (authority_status IN ('unverified', 'verified', 'rejected', 'expired'));

CREATE TABLE IF NOT EXISTS provider_claim_verification_evidence (
  id BIGSERIAL PRIMARY KEY,
  claim_id INT NOT NULL REFERENCES provider_claims(id) ON DELETE CASCADE,
  evidence_class TEXT NOT NULL CHECK (evidence_class IN ('identity', 'authority')),
  evidence_type TEXT NOT NULL CHECK (evidence_type IN (
    'verified_account_email',
    'cqc_registered_contact',
    'companies_house_officer',
    'signed_organisation_authority',
    'regulated_domain_control'
  )),
  evidence_sha256 CHAR(64) NOT NULL,
  result TEXT NOT NULL CHECK (result IN ('verified', 'rejected')),
  checked_by TEXT NOT NULL,
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  reason_code TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (claim_id, evidence_class, evidence_sha256)
);

CREATE INDEX IF NOT EXISTS idx_claim_evidence_readiness
  ON provider_claim_verification_evidence (claim_id, evidence_class, result, expires_at DESC);

COMMENT ON COLUMN provider_claim_verification_evidence.evidence_sha256 IS
  'SHA-256 fingerprint only. Raw identity/authority documents must not be stored in this table.';
