"""SQL queries for region/local authority stats."""

RATING_DIST_BY_LA = """
SELECT overall_rating, COUNT(*) as count
FROM care_providers
WHERE local_authority = $1 AND overall_rating IS NOT NULL
GROUP BY overall_rating
"""

TOP_PROVIDERS_BY_LA = """
SELECT name, slug, overall_rating, type, quality_score, last_inspection_date
FROM care_providers
WHERE local_authority = $1 AND UPPER(status) = 'ACTIVE'
ORDER BY quality_score DESC NULLS LAST
LIMIT 5
"""

TYPE_DIST_BY_LA = """
SELECT type, COUNT(*) as count
FROM care_providers
WHERE local_authority = $1 AND type IS NOT NULL
GROUP BY type
ORDER BY count DESC
"""

TOTAL_BY_LA = """
SELECT COUNT(*) as total FROM care_providers WHERE local_authority = $1
"""

ALL_LOCAL_AUTHORITIES = """
SELECT local_authority, COUNT(*) as provider_count
FROM care_providers
WHERE local_authority IS NOT NULL AND local_authority != ''
GROUP BY local_authority
ORDER BY provider_count DESC
"""

LA_NAME_FROM_SLUG = """
SELECT local_authority
FROM care_providers
WHERE LOWER(REPLACE(REPLACE(local_authority, ' ', '-'), '''', '')) = $1
  AND local_authority IS NOT NULL
LIMIT 1
"""
