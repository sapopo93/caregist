"""SQL queries for provider endpoints."""

import re

from api.services.rating_states import PUBLISHED_RATING_VALUES

# UK postcode regex — matches full or partial postcodes
_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d?[A-Z]{0,2}$", re.IGNORECASE
)
_FULL_POSTCODE_RE = re.compile(
    r"^([A-Z]{1,2}\d[A-Z\d]?)(\d[A-Z]{2})$", re.IGNORECASE
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

# The only expression a public read may render as a location's current rating.
#
# ``overall_rating`` holds whatever the last payload published. It is a
# statement about *now* only when the row's recorded ``rating_state`` says the
# source published a rating ('rated'). An 'unknown' state (the source published
# rating text this build cannot read) or any non-rated state must not render:
# ingestion's write policy clears the column for exactly those states, so the
# two agree, and a legacy writer -- one that changes ``overall_rating`` without
# touching ``rating_state`` -- is the case this state guard cannot see. That is
# why the public serialiser (``api.config.filter_fields``) additionally applies
# the value classifier ingestion uses before a rating reaches a response.
#
# The guard fails closed: a NULL state renders nothing. Every projection, filter,
# sort key and facet below is built from these constants, so there is one
# definition of "the rating this row may publish".
SERVED_RATING = "CASE WHEN rating_state = 'rated' THEN overall_rating END"
SERVED_RATING_COLUMN = f"{SERVED_RATING} AS overall_rating"
SERVED_RATING_NORMALISED = f"LOWER(BTRIM({SERVED_RATING}))"
#: The published vocabulary, taken from the module the ingestion classifier and
#: migration 061 both use, so a rating filter can only ever match a rating this
#: build is willing to render.
SERVED_RATING_IS_PUBLISHED = "{} IN ({})".format(
    SERVED_RATING_NORMALISED,
    ", ".join(f"'{value}'" for value in sorted(PUBLISHED_RATING_VALUES)),
)

SEARCH_SELECT = f"""
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, local_authority, {SERVED_RATING_COLUMN}, service_types, specialisms,
       number_of_beds, data_completeness_score, data_completeness_tier, latitude, longitude, phone,
       is_claimed, profile_tier, review_count, avg_review_rating
FROM care_providers
"""

# Ranked search select — adds ts_rank for relevance sorting
SEARCH_SELECT_RANKED = f"""
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, local_authority, {SERVED_RATING_COLUMN}, service_types, specialisms,
       number_of_beds, data_completeness_score, data_completeness_tier, latitude, longitude, phone,
       is_claimed, profile_tier, review_count, avg_review_rating,
       ts_rank({_TSVECTOR}, plainto_tsquery('english', coalesce($1, ''))) AS rank
FROM care_providers
"""

# Main search WHERE clause — supports multi-value filters via comma separation
SEARCH_WHERE = f"""
WHERE UPPER(status) = 'ACTIVE'
  AND ($1::text IS NULL OR {_TSVECTOR} @@ plainto_tsquery('english', $1))
  AND ($2::text IS NULL OR region = ANY(string_to_array($2, ',')))
  AND ($3::text IS NULL OR ({SERVED_RATING_IS_PUBLISHED} AND {SERVED_RATING_NORMALISED} = ANY(
        SELECT LOWER(BTRIM(value))
        FROM unnest(string_to_array($3, ',')) AS rating_value(value)
      )))
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text[] IS NULL OR EXISTS (
        SELECT 1
        FROM unnest(string_to_array(COALESCE(service_types, ''), '|')) AS service_label
        WHERE LOWER(BTRIM(service_label)) = ANY($5)
      ))
  AND ($6::text IS NULL OR postcode ILIKE $6 || '%')
  AND ($7::text IS NULL OR local_authority = $7)
"""

# Postcode-specific WHERE — used when query looks like a UK postcode
SEARCH_WHERE_POSTCODE = f"""
WHERE UPPER(status) = 'ACTIVE'
  AND postcode ILIKE $1 || '%'
  AND ($2::text IS NULL OR region = ANY(string_to_array($2, ',')))
  AND ($3::text IS NULL OR ({SERVED_RATING_IS_PUBLISHED} AND {SERVED_RATING_NORMALISED} = ANY(
        SELECT LOWER(BTRIM(value))
        FROM unnest(string_to_array($3, ',')) AS rating_value(value)
      )))
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text[] IS NULL OR EXISTS (
        SELECT 1
        FROM unnest(string_to_array(COALESCE(service_types, ''), '|')) AS service_label
        WHERE LOWER(BTRIM(service_label)) = ANY($5)
      ))
  AND ($6::text IS NULL OR postcode ILIKE $6 || '%')
  AND ($7::text IS NULL OR local_authority = $7)
"""

# CQC ID direct lookup
CQC_ID_LOOKUP = """
SELECT * FROM care_providers WHERE (id = $1 OR provider_id = $1) AND UPPER(status) = 'ACTIVE'
"""

SPONSORED_SORT_PREFIX = "CASE WHEN profile_tier = 'sponsored' THEN 0 ELSE 1 END ASC"


def _promote_sponsored(order: str) -> str:
    return f"{SPONSORED_SORT_PREFIX}, {order}"


# Whitelisted sort options to prevent SQL injection
SORT_OPTIONS = {
    "relevance": _promote_sponsored("name ASC"),
    "name": _promote_sponsored("name ASC"),
    "name_desc": _promote_sponsored("name DESC"),
    "rating": _promote_sponsored(f"CASE {SERVED_RATING_NORMALISED} WHEN 'outstanding' THEN 1 WHEN 'good' THEN 2 WHEN 'requires improvement' THEN 3 WHEN 'inadequate' THEN 4 ELSE 5 END ASC, name ASC"),
    "beds": _promote_sponsored("number_of_beds DESC NULLS LAST, name ASC"),
    "quality": _promote_sponsored(f"CASE {SERVED_RATING_NORMALISED} WHEN 'outstanding' THEN 1 WHEN 'good' THEN 2 WHEN 'requires improvement' THEN 3 WHEN 'inadequate' THEN 4 ELSE 5 END ASC, name ASC"),
    "newest": _promote_sponsored("registration_date DESC NULLS LAST, name ASC"),
}

# When a text query is present, relevance sort uses ts_rank
SORT_RELEVANCE_RANKED = _promote_sponsored("rank DESC, name ASC")

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


def postcode_search_prefix(q: str) -> str:
    """Return the outward code for full postcodes, preserving outward-only input."""
    compact = re.sub(r"\s+", "", q).upper()
    full_postcode = _FULL_POSTCODE_RE.fullmatch(compact)
    return full_postcode.group(1) if full_postcode else compact


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
    return f"{select}\n{where}\nORDER BY {order}\nLIMIT $8 OFFSET $9"


def build_count_query(is_postcode: bool = False) -> str:
    where = SEARCH_WHERE_POSTCODE if is_postcode else SEARCH_WHERE
    return f"SELECT COUNT(*) as total FROM care_providers\n{where}"


SEARCH_COUNT = f"SELECT COUNT(*) as total FROM care_providers\n{SEARCH_WHERE}"

SEARCH_EXPORT = f"{SEARCH_SELECT}\n{SEARCH_WHERE}\nORDER BY name ASC"

# Faceted counts — returns rating/region/type breakdowns for current query.
# The rating facet counts only ratings a row may publish (see SERVED_RATING), so
# a bucket cannot advertise a rating no row is allowed to render.
FACET_RATINGS = f"""
SELECT {SERVED_RATING_COLUMN}, COUNT(*) as count
FROM care_providers
{SEARCH_WHERE}
  AND {SERVED_RATING_IS_PUBLISHED}
GROUP BY {SERVED_RATING}
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

NEARBY_QUERY = f"""
SELECT id, provider_id, name, slug, type, status, town, county, postcode,
       region, {SERVED_RATING_COLUMN}, service_types, specialisms, number_of_beds,
       data_completeness_score, data_completeness_tier, latitude, longitude, phone,
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) / 1000.0 AS distance_km
FROM care_providers
WHERE geom IS NOT NULL
  AND UPPER(status) = 'ACTIVE'
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1000)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR {SERVED_RATING_NORMALISED} = LOWER(BTRIM($5)))
ORDER BY distance_km ASC
LIMIT $6 OFFSET $7
"""

NEARBY_COUNT = f"""
SELECT COUNT(*) as total
FROM care_providers
WHERE geom IS NOT NULL
  AND UPPER(status) = 'ACTIVE'
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1000)
  AND ($4::text IS NULL OR type = $4)
  AND ($5::text IS NULL OR {SERVED_RATING_NORMALISED} = LOWER(BTRIM($5)))
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

RATINGS_QUERY = f"""
SELECT {SERVED_RATING_COLUMN}, COUNT(*) as provider_count
FROM care_providers
WHERE {SERVED_RATING_IS_PUBLISHED} AND UPPER(status) = 'ACTIVE'
GROUP BY {SERVED_RATING}
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
