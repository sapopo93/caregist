"""SQL queries for enquiries (lead-gen)."""

INSERT_ENQUIRY = """
INSERT INTO enquiries
  (provider_id, enquirer_name, enquirer_email, enquirer_phone,
   relationship, care_type, urgency, message)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id, provider_id, status, enquirer_name, created_at
"""

UPDATE_PROVIDER_ENQUIRY_COUNT = """
UPDATE care_providers
SET enquiry_count = (SELECT COUNT(*) FROM enquiries WHERE provider_id = $1)
WHERE id = $1
"""

LIST_ENQUIRIES = """
SELECT e.id, e.provider_id, e.status, e.enquirer_name, e.enquirer_email,
       e.enquirer_phone, e.relationship, e.care_type, e.urgency, e.message,
       e.created_at, e.read_at,
       cp.name AS provider_name, cp.slug AS provider_slug
FROM enquiries e
JOIN care_providers cp ON cp.id = e.provider_id
WHERE ($1::text IS NULL OR e.provider_id = $1)
  AND ($2::text IS NULL OR e.status = $2)
ORDER BY e.created_at DESC
LIMIT $3 OFFSET $4
"""

COUNT_ENQUIRIES = """
SELECT COUNT(*) AS total FROM enquiries
WHERE ($1::text IS NULL OR provider_id = $1)
  AND ($2::text IS NULL OR status = $2)
"""

UPDATE_ENQUIRY_STATUS = """
UPDATE enquiries
SET status = $2,
    read_at = CASE WHEN $2 IN ('read', 'responded', 'converted') AND read_at IS NULL
              THEN NOW() ELSE read_at END
WHERE id = $1
RETURNING id, status
"""
