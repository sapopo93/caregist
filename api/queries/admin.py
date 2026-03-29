"""SQL queries for admin dashboard."""

DASHBOARD_STATS = """
SELECT
  (SELECT COUNT(*) FROM care_providers WHERE status = 'Active') AS total_providers,
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
