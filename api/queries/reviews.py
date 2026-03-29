"""SQL queries for reviews."""

INSERT_REVIEW = """
INSERT INTO reviews
  (provider_id, rating, title, body, reviewer_name, reviewer_email,
   relationship, visit_date)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id, provider_id, status, rating, title, reviewer_name, created_at
"""

LIST_APPROVED_REVIEWS = """
SELECT id, rating, title, body, reviewer_name, relationship, visit_date, created_at
FROM reviews
WHERE provider_id = $1 AND status = 'approved'
ORDER BY created_at DESC
LIMIT $2 OFFSET $3
"""

COUNT_APPROVED_REVIEWS = """
SELECT COUNT(*) AS total FROM reviews
WHERE provider_id = $1 AND status = 'approved'
"""

REVIEW_SUMMARY = """
SELECT COUNT(*) AS count, ROUND(AVG(rating)::numeric, 1) AS avg_rating
FROM reviews
WHERE provider_id = $1 AND status = 'approved'
"""

LIST_REVIEWS_ADMIN = """
SELECT r.id, r.provider_id, r.status, r.rating, r.title, r.body,
       r.reviewer_name, r.reviewer_email, r.relationship, r.created_at,
       r.moderated_at, r.admin_notes,
       cp.name AS provider_name, cp.slug AS provider_slug
FROM reviews r
JOIN care_providers cp ON cp.id = r.provider_id
WHERE ($1::text IS NULL OR r.status = $1)
ORDER BY r.created_at DESC
LIMIT $2 OFFSET $3
"""

COUNT_REVIEWS_ADMIN = """
SELECT COUNT(*) AS total FROM reviews
WHERE ($1::text IS NULL OR status = $1)
"""

MODERATE_REVIEW = """
UPDATE reviews SET status = $2, moderated_at = NOW(), admin_notes = $3
WHERE id = $1
RETURNING id, provider_id, status
"""

UPDATE_PROVIDER_REVIEW_STATS = """
UPDATE care_providers SET
  review_count = sub.cnt,
  avg_review_rating = sub.avg_r
FROM (
  SELECT COUNT(*) AS cnt, ROUND(AVG(rating)::numeric, 1) AS avg_r
  FROM reviews WHERE provider_id = $1 AND status = 'approved'
) sub
WHERE id = $1
"""
