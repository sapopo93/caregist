"""SQL queries for provider endpoints."""

import re

# UK postcode regex — matches full or partial postcodes
_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d?[A-Z]{0,2}$", re.IGNORECASE
)

# CQC location ID pattern — e.g. "1-123456789" or "1-2881562896"
_CQC_ID_RE = re.compile(r"^1-\d{5,12}$")

# Expanded tsvector — includes local_authority and address_line1
_TSVECTOR = """to_tsvector('english',
    coalesce(name,'') || ' ' ||
    coalesce(town,'') || ' ' ||
    coalesce(county,'') || ' ' ||
    coalesce(postcode,'') || ' ' ||
    coalesce(local_authority,'') || ' ' ||
    coalesce(address_line1,'') || ' ' ||
    coalesce(service_types,'') || ' ' ||
    coalesce(specialisms,''))"""

SEARCH_SELECT = """
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, local_authority, overall_rating, service_types, specialisms,
       number_of_beds, quality_score, quality_tier, latitude, longitude, phone,
       is_claimed, review_count, avg_review_rating
FROM care_providers
"""

# Ranked search select — adds ts_rank for relevance sorting
SEARCH_SELECT_RANKED = f"""
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, local_authority, overall_rating, service_types, specialisms,
       number_of_beds, quality_score, quality_tier, latitude, longitude, phone,
       is_claimed, review_count, avg_review_rating,
       ts_rank({_TSVECTOR}, plainto_tsquery('english', coalesce($1, ''))) AS rank
FROM care_providers
"""

# Main search WHERE clause — supports multi-value filters via comma separation
SEARCH_WHERE = f"""
WHERE UPPER(status) = 'ACTIVE'
  AND ($1::text IS NULL OR {_TSVECTOR} @@ plainto_tsquery('english', $1))
  AND ($2::text IS NULL OR region = ANY(string_to_array($2, ',')))
  AND ($3::text IS NULL OR overall_rating = ANY(string_to_array($3, ',')))
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR service_types ILIKE '%' || $5 || '%')
  AND ($6::text IS NULL OR postcode ILIKE $6 || '%')
"""

# Postcode-specific WHERE — used when query looks like a UK postcode
SEARCH_WHERE_POSTCODE = """
WHERE UPPER(status) = 'ACTIVE'
  AND postcode ILIKE $1 || '%'
  AND ($2::text IS NULL OR region = ANY(string_to_array($2, ',')))
  AND ($3::text IS NULL OR overall_rating = ANY(string_to_array($3, ',')))
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR service_types ILIKE '%' || $5 || '%')
  AND ($6::text IS NULL OR postcode ILIKE $6 || '%')
"""

# CQC ID direct lookup
CQC_ID_LOOKUP = """
SELECT * FROM care_providers WHERE (id = $1 OR provider_id = $1) AND UPPER(status) = 'ACTIVE'
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

# When a text query is present, relevance sort uses ts_rank
SORT_RELEVANCE_RANKED = "rank DESC, quality_score DESC, name ASC"

DEFAULT_SORT = "relevance"


def classify_query(q: str | None) -> str:
    """Classify a search query. Returns 'postcode', 'cqc_id', 'text', or 'none'."""
    if not q or not q.strip():
        return "none"
    q = q.strip()
    if _CQC_ID_RE.match(q):
        return "cqc_id"
    if _POSTCODE_RE.match(q):
        return "postcode"
    return "text"


def build_search_query(sort: str, has_text_query: bool = False, is_postcode: bool = False) -> str:
    """Build the search SQL. Uses ranked select + ts_rank when text query is present."""
    if is_postcode:
        select = SEARCH_SELECT
        where = SEARCH_WHERE_POSTCODE
        order = SORT_OPTIONS.get(sort, SORT_OPTIONS[DEFAULT_SORT])
    elif has_text_query and sort == "relevance":
        select = SEARCH_SELECT_RANKED
        where = SEARCH_WHERE
        order = SORT_RELEVANCE_RANKED
    else:
        select = SEARCH_SELECT
        where = SEARCH_WHERE
        order = SORT_OPTIONS.get(sort, SORT_OPTIONS[DEFAULT_SORT])
    return f"{select}\n{where}\nORDER BY {order}\nLIMIT $7 OFFSET $8"


def build_count_query(is_postcode: bool = False) -> str:
    where = SEARCH_WHERE_POSTCODE if is_postcode else SEARCH_WHERE
    return f"SELECT COUNT(*) as total FROM care_providers\n{where}"


SEARCH_COUNT = f"SELECT COUNT(*) as total FROM care_providers\n{SEARCH_WHERE}"

SEARCH_EXPORT = f"{SEARCH_SELECT}\n{SEARCH_WHERE}\nORDER BY name ASC"

# Faceted counts — returns rating/region/type breakdowns for current query
FACET_RATINGS = f"""
SELECT overall_rating, COUNT(*) as count
FROM care_providers
{SEARCH_WHERE}
  AND overall_rating IS NOT NULL
GROUP BY overall_rating
ORDER BY count DESC
"""

FACET_REGIONS = f"""
SELECT region, COUNT(*) as count
FROM care_providers
{SEARCH_WHERE}
  AND region IS NOT NULL AND region != ''
GROUP BY region
ORDER BY count DESC
"""

FACET_TYPES = f"""
SELECT unnest(string_to_array(service_types, '|')) as service_type, COUNT(*) as count
FROM care_providers
{SEARCH_WHERE}
  AND service_types IS NOT NULL
GROUP BY service_type
ORDER BY count DESC
LIMIT 20
"""

DETAIL_BY_SLUG = """
SELECT * FROM care_providers
WHERE slug = $1 OR id = $1
ORDER BY CASE WHEN slug = $1 THEN 0 ELSE 1 END
LIMIT 1
"""

NEARBY_QUERY = """
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, overall_rating, service_types, specialisms, number_of_beds,
       quality_score, quality_tier, latitude, longitude, phone,
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) / 1000.0 AS distance_km
FROM care_providers
WHERE geom IS NOT NULL
  AND UPPER(status) = 'ACTIVE'
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
  AND UPPER(status) = 'ACTIVE'
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1000)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR overall_rating = $5)
"""

REGIONS_QUERY = """
SELECT region, COUNT(*) as provider_count
FROM care_providers
WHERE region IS NOT NULL AND region != '' AND UPPER(status) = 'ACTIVE'
GROUP BY region
ORDER BY provider_count DESC
"""

SERVICE_TYPES_QUERY = """
SELECT st AS service_type, COUNT(*) AS provider_count
FROM care_providers
CROSS JOIN LATERAL unnest(string_to_array(service_types, '|')) AS st
WHERE service_types IS NOT NULL AND service_types != '' AND UPPER(status) = 'ACTIVE'
GROUP BY st
ORDER BY provider_count DESC
"""

RATINGS_QUERY = """
SELECT overall_rating, COUNT(*) as provider_count
FROM care_providers
WHERE overall_rating IS NOT NULL AND overall_rating != '' AND UPPER(status) = 'ACTIVE'
GROUP BY overall_rating
ORDER BY provider_count DESC
"""

COMPARE_QUERY = """
SELECT * FROM care_providers
WHERE (slug = ANY($1::text[]) OR id = ANY($1::text[]))
  AND UPPER(status) = 'ACTIVE'
"""

# --- Monitor queries ---

INSERT_MONITOR = """
INSERT INTO provider_monitors (user_id, provider_id)
VALUES ($1, $2)
ON CONFLICT (user_id, provider_id) DO NOTHING
RETURNING id
"""

DELETE_MONITOR = """
DELETE FROM provider_monitors WHERE user_id = $1 AND provider_id = $2
"""

CHECK_MONITOR = """
SELECT id FROM provider_monitors WHERE user_id = $1 AND provider_id = $2
"""

COUNT_USER_MONITORS = """
SELECT COUNT(*) as total FROM provider_monitors WHERE user_id = $1
"""

PROVIDER_ID_FROM_SLUG = """
SELECT id FROM care_providers
WHERE slug = $1 OR id = $1
ORDER BY CASE WHEN slug = $1 THEN 0 ELSE 1 END
LIMIT 1
"""

# --- Rating history queries ---

RATING_HISTORY_QUERY = """
SELECT overall_rating, inspection_date, report_url, recorded_at
FROM provider_rating_history
WHERE provider_id = $1
ORDER BY inspection_date DESC
LIMIT 20
"""
