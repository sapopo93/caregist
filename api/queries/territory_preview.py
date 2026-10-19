"""SQL for the free Territory Brief preview.

Scope filters are built from a fixed column whitelist (``SCOPE_COLUMNS``); the
territory name and service type are always bound parameters.
"""

SCOPE_COLUMNS = {"region": "region", "local_authority": "local_authority"}

# Only England care services the Brief is sold for. Values match the
# pipe-delimited CQC taxonomy stored in care_providers.service_types.
SERVICE_TYPES = {
    "homecare": "Homecare Agencies",
    "residential": "Residential Homes",
    "nursing": "Nursing Homes",
    "supported_living": "Supported Living",
}

TERRITORIES = """
SELECT 'region' AS kind, region AS name, COUNT(DISTINCT provider_id)::int AS organisations
FROM care_providers
WHERE UPPER(status) = 'ACTIVE' AND region IS NOT NULL AND region <> ''
GROUP BY region
UNION ALL
SELECT 'local_authority' AS kind, local_authority AS name, COUNT(DISTINCT provider_id)::int AS organisations
FROM care_providers
WHERE UPPER(status) = 'ACTIVE' AND local_authority IS NOT NULL AND local_authority <> ''
GROUP BY local_authority
ORDER BY kind DESC, name
"""


def _scope_where(column: str, alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return (
        f"UPPER({prefix}status) = 'ACTIVE' "
        f"AND lower({prefix}{column}) = lower($1) "
        f"AND ($2::text IS NULL OR position('|' || lower($2::text) || '|' "
        f"IN '|' || lower(coalesce({prefix}service_types, '')) || '|') > 0)"
    )


def scope_counts(column: str) -> str:
    return f"""
SELECT COUNT(DISTINCT provider_id)::int AS organisations,
       COUNT(*)::int AS locations,
       MAX(registration_date) AS latest_registration,
       MIN({column}) AS canonical_name
FROM care_providers
WHERE {_scope_where(column)}
"""


# Anchor the window to the newest source date rather than today, so a stale
# source never reads as "nothing happened this quarter".
SOURCE_AS_OF = """
SELECT GREATEST(
  (SELECT MAX(registration_date) FROM care_providers
    WHERE UPPER(status) = 'ACTIVE' AND registration_date <= CURRENT_DATE),
  (SELECT MAX(effective_date) FROM trusted_event_ledger
    WHERE event_type = 'rating_changed' AND effective_date <= CURRENT_DATE)
) AS as_of
"""


def new_registrations(column: str) -> str:
    return f"""
SELECT 'new_registration' AS event_type, registration_date AS event_date,
       NULL::text AS old_value, NULL::text AS new_value,
       id AS location_id, provider_id, name, town, service_types
FROM care_providers
WHERE {_scope_where(column)} AND registration_date BETWEEN $3 AND $4
ORDER BY registration_date DESC, id
LIMIT 500
"""


def rating_changes(column: str) -> str:
    return f"""
SELECT 'rating_changed' AS event_type, e.effective_date AS event_date,
       e.old_value #>> '{{}}' AS old_value, e.new_value #>> '{{}}' AS new_value,
       cp.id AS location_id, cp.provider_id, cp.name, cp.town, cp.service_types
FROM trusted_event_ledger e
JOIN care_providers cp ON cp.id = e.location_id
WHERE e.event_type = 'rating_changed'
  AND e.effective_date BETWEEN $3 AND $4
  AND {_scope_where(column, 'cp')}
ORDER BY e.effective_date DESC, cp.id
LIMIT 500
"""
