"""SQL queries for provider claims."""

PROVIDER_ID_BY_SLUG = """
SELECT id, is_claimed FROM care_providers WHERE slug = $1
"""

INSERT_CLAIM = """
INSERT INTO provider_claims
  (provider_id, claimant_name, claimant_email, claimant_phone,
   claimant_role, organisation_name, proof_of_association)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING id, provider_id, status, claimant_name, claimant_email, created_at
"""

HAS_PENDING_CLAIM = """
SELECT id FROM provider_claims WHERE provider_id = $1 AND status = 'pending'
"""

LIST_CLAIMS = """
SELECT pc.id, pc.provider_id, pc.status, pc.claimant_name, pc.claimant_email,
       pc.claimant_phone, pc.claimant_role, pc.organisation_name,
       pc.proof_of_association, pc.admin_notes, pc.created_at, pc.reviewed_at,
       cp.name AS provider_name, cp.slug AS provider_slug
FROM provider_claims pc
JOIN care_providers cp ON cp.id = pc.provider_id
WHERE ($1::text IS NULL OR pc.status = $1)
ORDER BY pc.created_at DESC
LIMIT $2 OFFSET $3
"""

COUNT_CLAIMS = """
SELECT COUNT(*) AS total FROM provider_claims
WHERE ($1::text IS NULL OR status = $1)
"""

UPDATE_CLAIM_STATUS = """
UPDATE provider_claims
SET status = $2, reviewed_at = NOW(), reviewed_by = $3, admin_notes = $4
WHERE id = $1
RETURNING id, provider_id, status
"""

MARK_PROVIDER_CLAIMED = """
UPDATE care_providers SET is_claimed = true, claimed_at = NOW() WHERE id = $1
"""

MARK_PROVIDER_UNCLAIMED = """
UPDATE care_providers SET is_claimed = false, claimed_at = NULL WHERE id = $1
"""
