"""SQL queries for sitemap coverage endpoints."""

COUNT_ACTIVE_PROVIDER_SLUGS = """
SELECT COUNT(*) AS total
FROM care_providers
WHERE slug IS NOT NULL
  AND slug != ''
  AND UPPER(COALESCE(status, 'ACTIVE')) = 'ACTIVE'
"""

LIST_ACTIVE_PROVIDER_SLUGS = """
SELECT slug, updated_at
FROM care_providers
WHERE slug IS NOT NULL
  AND slug != ''
  AND UPPER(COALESCE(status, 'ACTIVE')) = 'ACTIVE'
ORDER BY slug
OFFSET $1
LIMIT $2
"""
