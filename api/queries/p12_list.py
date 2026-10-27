"""SQL for the P12 list (api/services/p12_list.py). Read-only.

Base population: ACTIVE care homes with 11-49 registered places. The Well-led
rating itself is resolved outside SQL (care_providers.rating_well_led is not
populated for ACTIVE rows), so these queries fix the denominator the list is
reconciled against.
"""

P12_BASE_PREDICATE = """
UPPER(status) = 'ACTIVE'
  AND COALESCE(service_types, '') ILIKE '%care home service%'
  AND number_of_beds BETWEEN 11 AND 49
"""

#: $1 region.
P12_BASE_POPULATION = f"""
SELECT id, provider_id, name, postcode, local_authority, region, number_of_beds, registration_date,
       rating_well_led
FROM care_providers
WHERE {P12_BASE_PREDICATE}
  AND region = $1
ORDER BY local_authority, name, id
"""

P12_BASE_COUNTS_BY_REGION = f"""
SELECT region, COUNT(*) AS base_count,
       COUNT(*) FILTER (WHERE rating_well_led IN ('Requires improvement', 'Inadequate')) AS stored_well_led_below_good
FROM care_providers
WHERE {P12_BASE_PREDICATE}
GROUP BY region
ORDER BY region
"""
