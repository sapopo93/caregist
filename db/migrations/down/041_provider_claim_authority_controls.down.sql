DROP TABLE IF EXISTS provider_claim_verification_evidence;
ALTER TABLE provider_claims
  DROP CONSTRAINT IF EXISTS provider_claims_identity_status_check,
  DROP CONSTRAINT IF EXISTS provider_claims_authority_status_check,
  DROP COLUMN IF EXISTS claimant_user_id,
  DROP COLUMN IF EXISTS identity_status,
  DROP COLUMN IF EXISTS authority_status,
  DROP COLUMN IF EXISTS identity_verified_at,
  DROP COLUMN IF EXISTS identity_verified_by,
  DROP COLUMN IF EXISTS authority_verified_at,
  DROP COLUMN IF EXISTS authority_verified_by,
  DROP COLUMN IF EXISTS verification_expires_at,
  DROP COLUMN IF EXISTS decision_reason_code,
  DROP COLUMN IF EXISTS suspended_at;
