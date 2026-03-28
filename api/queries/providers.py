"""SQL queries for provider endpoints."""

SEARCH_SELECT = """
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, overall_rating, service_types, specialisms, number_of_beds,
       quality_score, quality_tier, latitude, longitude, phone
FROM care_providers
"""

SEARCH_WHERE = """
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

# Whitelisted sort options to prevent SQL injection
SORT_OPTIONS = {
    "relevance": "quality_score DESC, name ASC",
    "name": "name ASC",
    "name_desc": "name DESC",
    "rating": "CASE overall_rating WHEN 'Outstanding' THEN 1 WHEN 'Good' THEN 2 WHEN 'Requires Improvement' THEN 3 WHEN 'Inadequate' THEN 4 ELSE 5 END ASC, name ASC",
    "beds": "number_of_beds DESC NULLS LAST, name ASC",
    "quality": "quality_score DESC, name ASC",
    "newest": "registration_date DESC NULLS LAST, name ASC",
}

DEFAULT_SORT = "relevance"


def build_search_query(sort: str) -> str:
    order = SORT_OPTIONS.get(sort, SORT_OPTIONS[DEFAULT_SORT])
    return f"{SEARCH_SELECT}\n{SEARCH_WHERE}\nORDER BY {order}\nLIMIT $7 OFFSET $8"


SEARCH_COUNT = f"SELECT COUNT(*) as total FROM care_providers\n{SEARCH_WHERE}"

SEARCH_EXPORT = f"{SEARCH_SELECT}\n{SEARCH_WHERE}\nORDER BY name ASC"

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

RATINGS_QUERY = """
SELECT overall_rating, COUNT(*) as provider_count
FROM care_providers
WHERE overall_rating IS NOT NULL AND overall_rating != ''
GROUP BY overall_rating
ORDER BY provider_count DESC
"""
