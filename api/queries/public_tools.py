"""SQL queries for public tool endpoints."""

NEARBY_PUBLIC_QUERY = """
SELECT id, name, slug, type, town, postcode, overall_rating,
       quality_tier, service_types, last_inspection_date,
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) / 1609.34 AS distance_miles
FROM care_providers
WHERE geom IS NOT NULL
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1609.34)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR overall_rating = $5)
  AND ($6::text IS NULL OR service_types ILIKE '%' || $6 || '%')
ORDER BY distance_miles ASC
LIMIT $7
"""

NEARBY_PUBLIC_COUNT = """
SELECT COUNT(*) as total
FROM care_providers
WHERE geom IS NOT NULL
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1609.34)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR overall_rating = $5)
  AND ($6::text IS NULL OR service_types ILIKE '%' || $6 || '%')
"""

GET_CACHED_POSTCODE = """
SELECT latitude, longitude FROM postcode_cache WHERE postcode = $1
"""

INSERT_POSTCODE_CACHE = """
INSERT INTO postcode_cache (postcode, latitude, longitude)
VALUES ($1, $2, $3)
ON CONFLICT (postcode) DO NOTHING
"""
