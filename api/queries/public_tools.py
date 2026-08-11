"""SQL queries for public tool endpoints."""

NEARBY_PUBLIC_QUERY = """
SELECT id, name, slug, type, town, postcode, overall_rating,
       data_completeness_tier, service_types, last_inspection_date,
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

CHANGE_FREQUENCY_DAILY = """
WITH bounds AS (
  SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date - ($1::int - 1) AS start_date,
         (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date AS end_date
), days AS (
  SELECT generate_series(start_date, end_date, INTERVAL '1 day')::date AS day
  FROM bounds
), event_days AS (
  SELECT (observed_at AT TIME ZONE 'UTC')::date AS day,
         COUNT(*)::int AS events,
         COUNT(*) FILTER (WHERE event_type = 'new_registration')::int AS new_registrations,
         COUNT(*) FILTER (WHERE event_type = 'rating_changed')::int AS rating_changes,
         COUNT(*) FILTER (WHERE event_type = 'status_changed')::int AS status_changes,
         COUNT(*) FILTER (WHERE event_type = 'ownership_changed')::int AS ownership_changes,
         COUNT(*) FILTER (WHERE event_type = 'group_movement')::int AS group_movements
  FROM trusted_event_ledger, bounds
  WHERE observed_at >= start_date
    AND observed_at < end_date + INTERVAL '1 day'
    AND event_type IN (
      'new_registration', 'rating_changed', 'status_changed',
      'ownership_changed', 'group_movement'
    )
  GROUP BY (observed_at AT TIME ZONE 'UTC')::date
)
SELECT days.day,
       COALESCE(event_days.events, 0)::int AS events,
       COALESCE(event_days.new_registrations, 0)::int AS new_registrations,
       COALESCE(event_days.rating_changes, 0)::int AS rating_changes,
       COALESCE(event_days.status_changes, 0)::int AS status_changes,
       COALESCE(event_days.ownership_changes, 0)::int AS ownership_changes,
       COALESCE(event_days.group_movements, 0)::int AS group_movements
FROM days
LEFT JOIN event_days USING (day)
ORDER BY days.day
"""

CHANGE_FREQUENCY_COLLECTION_COVERAGE = """
WITH bounds AS (
  SELECT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date - ($1::int - 1) AS start_date,
         (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date AS end_date
)
SELECT (started_at AT TIME ZONE 'UTC')::date AS day,
       run_type,
       status,
       COUNT(*)::int AS runs,
       MAX(COALESCE(completed_at, started_at)) AS latest_run_at
FROM pipeline_runs, bounds
WHERE started_at >= start_date
  AND started_at < end_date + INTERVAL '1 day'
  AND run_type IN ('signal_poll', 'incremental', 'reconciliation')
GROUP BY (started_at AT TIME ZONE 'UTC')::date, run_type, status
ORDER BY (started_at AT TIME ZONE 'UTC')::date, run_type, status
"""
