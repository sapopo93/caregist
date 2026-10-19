"""SQL for the free Territory Brief preview.

Scope filters are built from a fixed column whitelist (``SCOPE_COLUMNS``); the
territory name and service aliases are always bound parameters. Every query
excludes locations held in ``reconciliation_quarantined_locations`` (migration
067); the router refuses to answer when that table is absent.

Parameters shared by the scope queries:
  $1 territory name, $2 lower-cased service aliases (text[] or NULL)
and, for window queries, $3 window start, $4 window end.
"""

SCOPE_COLUMNS = {"region": "region", "local_authority": "local_authority"}

# Public preview keys -> canonical service slugs in frontend/data/service-taxonomy.json.
# Aliases (for example "Domiciliary care service" and the legacy "Homecare Agencies")
# are resolved through api.service_taxonomy, never hard-coded here.
SERVICE_SLUGS = {
    "homecare": "home-care",
    "residential": "residential-care-homes",
    "nursing": "nursing-care-homes",
    "supported_living": "supported-living",
}

QUARANTINE_TABLE_PRESENT = "SELECT to_regclass('public.reconciliation_quarantined_locations') IS NOT NULL"


def _not_quarantined(alias: str) -> str:
    return (
        "NOT EXISTS (SELECT 1 FROM reconciliation_quarantined_locations q "
        f"WHERE q.location_id = {alias}.id AND q.resolved_at IS NULL)"
    )


def _scope_where(column: str, alias: str = "cp") -> str:
    return (
        f"UPPER({alias}.status) = 'ACTIVE' "
        f"AND lower({alias}.{column}) = lower($1) "
        f"AND ($2::text[] IS NULL OR EXISTS ("
        f"SELECT 1 FROM unnest(string_to_array(coalesce({alias}.service_types, ''), '|')) AS s(service_type) "
        f"WHERE lower(btrim(s.service_type)) = ANY($2::text[]))) "
        f"AND {_not_quarantined(alias)}"
    )


TERRITORIES = f"""
SELECT 'region' AS kind, cp.region AS name, COUNT(DISTINCT cp.provider_id)::int AS organisations
FROM care_providers cp
WHERE UPPER(cp.status) = 'ACTIVE' AND cp.region IS NOT NULL AND cp.region <> ''
  AND {_not_quarantined('cp')}
GROUP BY cp.region
UNION ALL
SELECT 'local_authority' AS kind, cp.local_authority AS name, COUNT(DISTINCT cp.provider_id)::int AS organisations
FROM care_providers cp
WHERE UPPER(cp.status) = 'ACTIVE' AND cp.local_authority IS NOT NULL AND cp.local_authority <> ''
  AND {_not_quarantined('cp')}
GROUP BY cp.local_authority
ORDER BY kind DESC, name
"""


def scope_counts(column: str) -> str:
    return f"""
SELECT COUNT(DISTINCT cp.provider_id)::int AS organisations,
       COUNT(*)::int AS locations,
       MIN(cp.{column}) AS canonical_name
FROM care_providers cp
WHERE {_scope_where(column)}
"""


# The window ends at the newest recorded registration date. This is event
# recency only; source freshness is reported separately from get_cqc_freshness.
LATEST_REGISTRATION = f"""
SELECT MAX(cp.registration_date)
FROM care_providers cp
WHERE UPPER(cp.status) = 'ACTIVE' AND cp.registration_date <= CURRENT_DATE
  AND {_not_quarantined('cp')}
"""


def signal_counts(column: str) -> str:
    """Uncapped aggregate counts. Rating events without a source date cannot be
    placed in the window, so they are counted separately, never as zero."""
    return f"""
WITH scope AS (
  SELECT cp.id, cp.provider_id, cp.registration_date FROM care_providers cp
  WHERE {_scope_where(column)}
), regs AS (
  SELECT id, provider_id FROM scope WHERE registration_date BETWEEN $3 AND $4
), ratings AS (
  SELECT e.effective_date, s.provider_id
  FROM trusted_event_ledger e JOIN scope s ON s.id = e.location_id
  WHERE e.event_type = 'rating_changed'
)
SELECT
  (SELECT COUNT(*) FROM regs)::int AS new_registrations,
  (SELECT COUNT(*) FROM ratings WHERE effective_date BETWEEN $3 AND $4)::int AS rating_changes_dated,
  (SELECT COUNT(*) FROM ratings WHERE effective_date IS NULL)::int AS rating_changes_undated,
  (SELECT COUNT(DISTINCT provider_id) FROM (
     SELECT provider_id FROM regs
     UNION SELECT provider_id FROM ratings WHERE effective_date BETWEEN $3 AND $4
   ) moved)::int AS organisations_with_signals
"""


EXAMPLE_LIMIT = 20


def new_registration_examples(column: str) -> str:
    return f"""
SELECT 'new_registration' AS event_type, cp.registration_date AS event_date,
       NULL::text AS old_value, NULL::text AS new_value,
       cp.id AS location_id, cp.provider_id, cp.name, cp.town, cp.service_types
FROM care_providers cp
WHERE {_scope_where(column)} AND cp.registration_date BETWEEN $3 AND $4
ORDER BY cp.registration_date DESC, cp.id
LIMIT {EXAMPLE_LIMIT}
"""


def rating_change_examples(column: str) -> str:
    """Only dated events can be examples; undated ones are reported as unavailable."""
    return f"""
SELECT 'rating_changed' AS event_type, e.effective_date AS event_date,
       e.old_value #>> '{{}}' AS old_value, e.new_value #>> '{{}}' AS new_value,
       cp.id AS location_id, cp.provider_id, cp.name, cp.town, cp.service_types
FROM trusted_event_ledger e
JOIN care_providers cp ON cp.id = e.location_id
WHERE e.event_type = 'rating_changed'
  AND e.effective_date BETWEEN $3 AND $4
  AND {_scope_where(column)}
ORDER BY e.effective_date DESC, cp.id
LIMIT {EXAMPLE_LIMIT}
"""
