"""SQL queries for provider endpoints."""

SEARCH_QUERY = """
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, overall_rating, service_types, specialisms, number_of_beds,
       quality_score, quality_tier, latitude, longitude, phone
FROM care_providers
WHERE ($1::text IS NULL OR to_tsvector('english',
    coalesce(name,'') || ' ' || coalesce(town,'') || ' ' ||
    coalesce(county,'') || ' ' || coalesce(postcode,'') || ' ' ||
    coalesce(service_types,'') || ' ' || coalesce(specialisms,''))
    @@ plainto_tsquery('english', $1))
  AND ($2::text IS NULL OR region = $2)
  AND ($3::text IS NULL OR overall_rating = $3)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR service_types ILIKE '%' || $5 || '%')
  AND ($6::text IS NULL OR postcode ILIKE $6 || '%')
ORDER BY ts_rank(
    to_tsvector('english',
        coalesce(name,'') || ' ' || coalesce(town,'') || ' ' ||
        coalesce(county,'') || ' ' || coalesce(postcode,'') || ' ' ||
        coalesce(service_types,'') || ' ' || coalesce(specialisms,'')),
    plainto_tsquery('english', coalesce($1, ''))
) DESC, quality_score DESC, name ASC
LIMIT $7 OFFSET $8
"""

SEARCH_COUNT = """
SELECT COUNT(*) as total
FROM care_providers
WHERE ($1::text IS NULL OR to_tsvector('english',
    coalesce(name,'') || ' ' || coalesce(town,'') || ' ' ||
    coalesce(county,'') || ' ' || coalesce(postcode,'') || ' ' ||
    coalesce(service_types,'') || ' ' || coalesce(specialisms,''))
    @@ plainto_tsquery('english', $1))
  AND ($2::text IS NULL OR region = $2)
  AND ($3::text IS NULL OR overall_rating = $3)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR service_types ILIKE '%' || $5 || '%')
  AND ($6::text IS NULL OR postcode ILIKE $6 || '%')
"""

DETAIL_BY_SLUG = """
SELECT * FROM care_providers WHERE slug = $1
"""

NEARBY_QUERY = """
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, overall_rating, service_types, specialisms, number_of_beds,
       quality_score, quality_tier, latitude, longitude, phone,
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) / 1000.0 AS distance_km
FROM care_providers
WHERE geom IS NOT NULL
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1000)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR overall_rating = $5)
ORDER BY distance_km ASC
LIMIT $6 OFFSET $7
"""

NEARBY_COUNT = """
SELECT COUNT(*) as total
FROM care_providers
WHERE geom IS NOT NULL
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1000)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR overall_rating = $5)
"""

REGIONS_QUERY = """
SELECT region, COUNT(*) as provider_count
FROM care_providers
WHERE region IS NOT NULL AND region != ''
GROUP BY region
ORDER BY provider_count DESC
"""

SERVICE_TYPES_QUERY = """
SELECT unnest(string_to_array(service_types, '|')) as service_type, COUNT(*) as provider_count
FROM care_providers
WHERE service_types IS NOT NULL AND service_types != ''
GROUP BY service_type
ORDER BY provider_count DESC
"""
