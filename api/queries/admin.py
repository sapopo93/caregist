"""SQL queries for admin dashboard."""

DASHBOARD_STATS = """
SELECT
  (SELECT COUNT(*) FROM care_providers WHERE UPPER(status) = 'ACTIVE') AS total_providers,
  (SELECT COUNT(*) FROM care_providers WHERE is_claimed = true) AS claimed_providers,
  (SELECT COUNT(*) FROM provider_claims WHERE status = 'pending') AS pending_claims,
  (SELECT COUNT(*) FROM reviews WHERE status = 'pending') AS pending_reviews,
  (SELECT COUNT(*) FROM enquiries WHERE status = 'new') AS new_enquiries,
  (SELECT COUNT(*) FROM reviews WHERE status = 'approved') AS total_reviews,
  (SELECT COUNT(*) FROM enquiries) AS total_enquiries
"""

TOP_ENQUIRED_PROVIDERS = """
SELECT cp.name, cp.slug, cp.enquiry_count, cp.is_claimed, cp.overall_rating
FROM care_providers cp
WHERE cp.enquiry_count > 0
ORDER BY cp.enquiry_count DESC
LIMIT $1
"""

PROVIDER_TYPE_DISTRIBUTION = """
SELECT COALESCE(NULLIF(TRIM(type), ''), 'Unknown') AS label, COUNT(*)::int AS count
FROM care_providers
WHERE UPPER(status) = 'ACTIVE'
GROUP BY label
ORDER BY count DESC
LIMIT $1
"""

SERVICE_TYPE_DISTRIBUTION = """
SELECT COALESCE(NULLIF(TRIM(st), ''), 'Unknown') AS label, COUNT(*)::int AS count
FROM care_providers
CROSS JOIN LATERAL unnest(string_to_array(COALESCE(service_types, ''), '|')) AS st
WHERE UPPER(status) = 'ACTIVE'
GROUP BY label
ORDER BY count DESC
LIMIT $1
"""

SERVICE_TYPE_GROWTH = """
WITH service_events AS (
  SELECT
    COALESCE(NULLIF(TRIM(st), ''), 'Unknown') AS label,
    tel.effective_date
  FROM trusted_event_ledger tel
  JOIN care_providers cp ON cp.id = tel.entity_id
  CROSS JOIN LATERAL unnest(string_to_array(COALESCE(cp.service_types, ''), '|')) AS st
  WHERE tel.event_type = 'new_registration'
    AND tel.effective_date >= CURRENT_DATE - INTERVAL '180 days'
),
counts AS (
  SELECT
    label,
    COUNT(*) FILTER (WHERE effective_date >= CURRENT_DATE - INTERVAL '90 days')::int AS recent_count,
    COUNT(*) FILTER (
      WHERE effective_date < CURRENT_DATE - INTERVAL '90 days'
        AND effective_date >= CURRENT_DATE - INTERVAL '180 days'
    )::int AS previous_count
  FROM service_events
  GROUP BY label
)
SELECT
  label,
  recent_count,
  previous_count,
  (recent_count - previous_count)::int AS growth_count,
  CASE
    WHEN previous_count = 0 AND recent_count > 0 THEN 100.0
    WHEN previous_count = 0 THEN 0.0
    ELSE ROUND(((recent_count - previous_count)::numeric / previous_count::numeric) * 100, 1)
  END::float AS growth_rate
FROM counts
WHERE recent_count > 0 OR previous_count > 0
ORDER BY growth_count DESC, recent_count DESC, label ASC
LIMIT $1
"""
