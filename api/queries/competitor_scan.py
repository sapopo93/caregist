"""SQL for the P4 competitor scan (api/services/competitor_scan.py).

Read-only. The rating columns are the resolver's inputs
(api/services/rating_resolver.evidence_from_provider_row); the served
API-first display is never selected here.
"""

#: Rating evidence columns shared by report queries.
RATING_EVIDENCE_COLUMNS = """
       overall_rating, last_published_rating_date,
       file_overall_rating, file_overall_rating_date, file_rating_source, file_rating_source_sha256
"""

ORIGIN_FROM_POSTCODE_CACHE = """
SELECT latitude, longitude FROM postcode_cache
WHERE REPLACE(UPPER(postcode), ' ', '') = REPLACE(UPPER($1), ' ', '')
"""

#: Fallback origin: the centroid of directory locations sharing the postcode.
ORIGIN_FROM_DIRECTORY = """
SELECT AVG(latitude)::float AS latitude, AVG(longitude)::float AS longitude, COUNT(*) AS n
FROM care_providers
WHERE REPLACE(UPPER(postcode), ' ', '') = REPLACE(UPPER($1), ' ', '')
  AND latitude IS NOT NULL AND longitude IS NOT NULL
"""

#: $1 longitude, $2 latitude, $3 radius km, $4 service_types ILIKE pattern.
COMPETITORS_WITHIN_RADIUS = f"""
SELECT id, provider_id, name, postcode, local_authority, service_types, number_of_beds,
       registration_date, {RATING_EVIDENCE_COLUMNS},
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) / 1000.0 AS distance_km
FROM care_providers
WHERE geom IS NOT NULL
  AND UPPER(status) = 'ACTIVE'
  AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, $3 * 1000)
  AND COALESCE(service_types, '') ILIKE $4
ORDER BY distance_km ASC, id ASC
"""
