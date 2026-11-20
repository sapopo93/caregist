"""SQL for Region Monthly orders and entitlements (stage 2; flag-gated).

See docs/region-monthly-v1.md. Builds are read-only here: this module never
writes ``region_monthly_builds``.
"""

# The latest build of each requested month, for the order status view.
# $1 region, $2 service slug (NULL for all services), $3 months (date[]).
LATEST_BUILDS_FOR_MONTHS = """
SELECT DISTINCT ON (period_month)
       period_month, build_version, content_sha256, built_at
FROM region_monthly_builds
WHERE region = $1
  AND service_slug IS NOT DISTINCT FROM $2::text
  AND period_month = ANY($3::date[])
ORDER BY period_month, build_version DESC
"""

# The latest build of one month, in full, for a download.
# $1 region, $2 service slug (NULL for all services), $3 month.
LATEST_BUILD_FULL = """
SELECT period_month, region, service_slug, build_version, schema_version, built_at,
       built_from_data_cutoff, metrics, coverage, limits, content_sha256
FROM region_monthly_builds
WHERE region = $1
  AND service_slug IS NOT DISTINCT FROM $2::text
  AND period_month = $3::date
ORDER BY build_version DESC
LIMIT 1
"""

# Months this account already holds (paid, not refunded) in a region and service.
# $1 user, $2 region, $3 service slug, $4 months (date[]).
HELD_OVERLAP = """
SELECT o.id, o.months
FROM region_monthly_orders o
WHERE o.user_id = $1
  AND o.region = $2
  AND o.service_slug IS NOT DISTINCT FROM $3::text
  AND o.state = 'paid'
  AND o.months && $4::date[]
ORDER BY o.created_at, o.id
"""

ENTITLED_MONTHS = """
SELECT period_month FROM region_monthly_entitlements WHERE order_id = $1 ORDER BY period_month
"""

INSERT_ENTITLEMENTS = """
INSERT INTO region_monthly_entitlements (order_id, period_month)
SELECT o.id, u.period_month
FROM region_monthly_orders o, unnest(o.months) AS u(period_month)
WHERE o.id = $1 AND o.state = 'paid'
ON CONFLICT (order_id, period_month) DO NOTHING
RETURNING period_month
"""
