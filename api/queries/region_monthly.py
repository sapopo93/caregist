"""SQL for Region Monthly (flag-gated; see docs/region-monthly-v1.md).

Scope rules shared by every metric:

* a location is in scope when its region matches and, for a service filter, at
  least one of its pipe-separated ``service_types`` is an alias of the canonical
  service slug. A location with two service types in different slugs is therefore
  in scope for each of those slugs, and once in the all-services scope;
* locations held in ``reconciliation_quarantined_locations`` (unresolved) are
  left out, the same rule the Territory Brief preview uses;
* every status is kept (ACTIVE and INACTIVE) because a registration or closure
  is about a location that may no longer be active.

Parameters:
  $1 region (canonical name), $2 lower-cased service aliases (text[] or NULL),
  $3 first day of the month, $4 first day of the next month (both dates),
  $5 last inspection date the rating history can speak for (date),
  $6 start and $7 end of the month as UK-time instants (timestamptz),
  $8 earliest instant status changes were observed (timestamptz).
"""

QUARANTINE_TABLE_PRESENT = "SELECT to_regclass('public.reconciliation_quarantined_locations') IS NOT NULL"
BUILDS_TABLE_PRESENT = "SELECT to_regclass('public.region_monthly_builds') IS NOT NULL"

# Ledger status values arrive as JSON strings ("ACTIVE"); ``#>> '{}'`` reads a
# JSON scalar as text. Only ACTIVE <-> INACTIVE moves are counted.
MONTH_COUNTS = """
WITH scope AS (
  SELECT cp.id, cp.registration_date
  FROM care_providers cp
  WHERE lower(btrim(cp.region)) = lower($1)
    AND ($2::text[] IS NULL OR EXISTS (
      SELECT 1
      FROM unnest(string_to_array(coalesce(cp.service_types, ''), '|')) AS s(service_type)
      WHERE lower(btrim(s.service_type)) = ANY($2::text[])
    ))
    AND NOT EXISTS (
      SELECT 1 FROM reconciliation_quarantined_locations q
      WHERE q.location_id = cp.id AND q.resolved_at IS NULL
    )
),
regs AS (
  SELECT COUNT(*)::int AS n
  FROM scope
  WHERE registration_date >= $3::date AND registration_date < $4::date
),
rated AS (
  SELECT NULLIF(lower(regexp_replace(btrim(coalesce(h.overall_rating, '')), '\\s+', ' ', 'g')), '') AS norm
  FROM provider_rating_history h
  JOIN scope s ON s.id = h.provider_id
  WHERE h.inspection_date >= $3::date
    AND h.inspection_date < $4::date
    AND h.inspection_date <= $5::date
),
ratings AS (
  SELECT
    COUNT(*) FILTER (WHERE norm = 'outstanding')::int AS outstanding,
    COUNT(*) FILTER (WHERE norm = 'good')::int AS good,
    COUNT(*) FILTER (WHERE norm = 'requires improvement')::int AS requires_improvement,
    COUNT(*) FILTER (WHERE norm = 'inadequate')::int AS inadequate,
    COUNT(*) FILTER (
      WHERE norm IS NULL
         OR norm NOT IN ('outstanding', 'good', 'requires improvement', 'inadequate')
    )::int AS no_published_rating_value,
    COUNT(*)::int AS total
  FROM rated
),
status_moves AS (
  SELECT
    COUNT(*) FILTER (
      WHERE upper(e.old_value #>> '{}') = 'ACTIVE' AND upper(e.new_value #>> '{}') = 'INACTIVE'
    )::int AS closures_observed,
    COUNT(*) FILTER (
      WHERE upper(e.old_value #>> '{}') = 'INACTIVE' AND upper(e.new_value #>> '{}') = 'ACTIVE'
    )::int AS reinstatements_observed
  FROM trusted_event_ledger e
  JOIN scope s ON s.id = e.location_id
  WHERE e.event_type = 'status_changed'
    AND e.observed_at >= $6::timestamptz
    AND e.observed_at < $7::timestamptz
    AND e.observed_at >= $8::timestamptz
)
SELECT regs.n AS new_registrations,
       ratings.outstanding, ratings.good, ratings.requires_improvement,
       ratings.inadequate, ratings.no_published_rating_value, ratings.total AS ratings_total,
       status_moves.closures_observed, status_moves.reinstatements_observed
FROM regs, ratings, status_moves
"""

# Months already built for a region and service, for the coverage preview.
BUILT_MONTHS = """
SELECT DISTINCT period_month
FROM region_monthly_builds
WHERE region = $1 AND service_slug IS NOT DISTINCT FROM $2::text
ORDER BY period_month
"""

LATEST_BUILD = """
SELECT build_version, content_sha256
FROM region_monthly_builds
WHERE period_month = $1 AND region = $2 AND service_slug IS NOT DISTINCT FROM $3::text
ORDER BY build_version DESC
LIMIT 1
"""

INSERT_BUILD = """
INSERT INTO region_monthly_builds (
  period_month, region, service_slug, build_version, supersedes_build_version,
  correction_reason, schema_version, built_from_data_cutoff,
  metrics, coverage, limits, content_sha256
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb, $11::jsonb, $12)
"""
