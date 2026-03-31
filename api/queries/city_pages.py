"""SQL queries for city/SEO page endpoints."""

PROVIDERS_BY_CITY = """
SELECT id, name, slug, type, overall_rating, quality_score, quality_tier,
       postcode, town, service_types, phone, is_claimed, last_inspection_date,
       address_line1
FROM care_providers
WHERE LOWER(REPLACE(town, ' ', '-')) = $1
  AND ($2::text IS NULL OR overall_rating = $2)
  AND ($3::text IS NULL OR type = $3)
ORDER BY quality_score DESC NULLS LAST
LIMIT $4 OFFSET $5
"""

COUNT_BY_CITY = """
SELECT COUNT(*) as total
FROM care_providers
WHERE LOWER(REPLACE(town, ' ', '-')) = $1
  AND ($2::text IS NULL OR overall_rating = $2)
  AND ($3::text IS NULL OR type = $3)
"""

RATING_DIST_BY_CITY = """
SELECT overall_rating, COUNT(*) as count
FROM care_providers
WHERE LOWER(REPLACE(town, ' ', '-')) = $1 AND overall_rating IS NOT NULL
GROUP BY overall_rating
"""

CITY_NAME_FROM_SLUG = """
SELECT town FROM care_providers
WHERE LOWER(REPLACE(town, ' ', '-')) = $1 AND town IS NOT NULL
LIMIT 1
"""

TOP_CITIES = """
SELECT town, LOWER(REPLACE(town, ' ', '-')) as slug, COUNT(*) as provider_count
FROM care_providers
WHERE town IS NOT NULL AND town != ''
GROUP BY town
ORDER BY provider_count DESC
LIMIT 500
"""
