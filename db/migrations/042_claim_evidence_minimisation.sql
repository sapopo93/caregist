-- Remove legacy raw claim proof and suspend approvals that pre-date the
-- identity/authority evidence ledger. This is intentionally irreversible:
-- deleted personal evidence must not be reconstructed by rollback.

UPDATE provider_claims
SET proof_of_association = '[legacy evidence removed; reverification required]'
WHERE proof_of_association IS NOT NULL
  AND proof_of_association NOT LIKE 'sha256:%'
  AND proof_of_association <> '[retention-anonymised]';

UPDATE provider_claims pc
SET status = 'suspended',
    suspended_at = COALESCE(pc.suspended_at, NOW()),
    decision_reason_code = 'reverification_required',
    identity_status = CASE WHEN pc.identity_status = 'verified' THEN 'expired' ELSE pc.identity_status END,
    authority_status = CASE WHEN pc.authority_status = 'verified' THEN 'expired' ELSE pc.authority_status END
WHERE pc.status = 'approved'
  AND NOT (
    pc.identity_status = 'verified'
    AND pc.authority_status = 'verified'
    AND pc.verification_expires_at > NOW()
    AND EXISTS (
      SELECT 1
      FROM provider_claim_verification_evidence e
      WHERE e.claim_id = pc.id
        AND e.evidence_class = 'identity'
        AND e.result = 'verified'
        AND e.expires_at > NOW()
    )
    AND EXISTS (
      SELECT 1
      FROM provider_claim_verification_evidence e
      WHERE e.claim_id = pc.id
        AND e.evidence_class = 'authority'
        AND e.result = 'verified'
        AND e.expires_at > NOW()
    )
  );

UPDATE care_providers cp
SET is_claimed = FALSE,
    claimed_at = NULL
WHERE cp.is_claimed = TRUE
  AND NOT EXISTS (
    SELECT 1
    FROM provider_claims pc
    WHERE pc.provider_id = cp.id
      AND pc.status = 'approved'
      AND pc.identity_status = 'verified'
      AND pc.authority_status = 'verified'
      AND pc.verification_expires_at > NOW()
  );

COMMENT ON COLUMN provider_claims.proof_of_association IS
  'SHA-256 fingerprint only for new claims. Legacy raw proof is removed by migration 042.';
