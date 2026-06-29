-- Rebuild care_groups so public benchmarking contains only named groups.
--
-- Migration 005 created the materialized view before group_name was backfilled
-- in production. Refreshing that definition could surface unnamed provider_id
-- aggregates, which are not useful as public care-group benchmark rows.

DO $$
DECLARE
  matview_exists BOOLEAN;
  matview_owner TEXT;
BEGIN
  SELECT EXISTS (
    SELECT 1
    FROM pg_matviews
    WHERE schemaname = 'public' AND matviewname = 'care_groups'
  )
  INTO matview_exists;

  IF matview_exists THEN
    SELECT matviewowner
    FROM pg_matviews
    WHERE schemaname = 'public' AND matviewname = 'care_groups'
    INTO matview_owner;

    IF matview_owner <> current_user THEN
      RAISE NOTICE 'Skipping care_groups materialized view DDL because owner is % and current_user is %',
        matview_owner, current_user;
      RETURN;
    END IF;
  END IF;

  DROP MATERIALIZED VIEW IF EXISTS care_groups;

  CREATE MATERIALIZED VIEW care_groups AS
  SELECT
    provider_id,
    MAX(group_name) as group_name,
    LOWER(REPLACE(REPLACE(REPLACE(MAX(group_name), ' ', '-'), '''', ''), '.', '')) as slug,
    COUNT(*) as location_count,
    COUNT(*) FILTER (WHERE overall_rating = 'Outstanding') as outstanding_count,
    COUNT(*) FILTER (WHERE overall_rating = 'Good') as good_count,
    COUNT(*) FILTER (WHERE overall_rating = 'Requires Improvement') as ri_count,
    COUNT(*) FILTER (WHERE overall_rating = 'Inadequate') as inadequate_count,
    COUNT(*) FILTER (WHERE overall_rating = 'Not Yet Inspected' OR overall_rating IS NULL) as not_inspected_count,
    ROUND(AVG(quality_score)::numeric, 1) as avg_quality_score,
    ROUND(
      (COUNT(*) FILTER (WHERE overall_rating IN ('Outstanding', 'Good'))::numeric /
       NULLIF(COUNT(*) FILTER (WHERE overall_rating IS NOT NULL AND overall_rating != 'Not Yet Inspected'), 0)) * 100, 1
    ) as pct_good_or_outstanding,
    SUM(number_of_beds) FILTER (WHERE number_of_beds > 0) as total_beds,
    array_agg(DISTINCT region) FILTER (WHERE region IS NOT NULL AND region != '') as regions,
    array_agg(DISTINCT type) FILTER (WHERE type IS NOT NULL) as provider_types,
    MAX(last_inspection_date) as latest_inspection
  FROM care_providers
  WHERE provider_id IS NOT NULL
    AND provider_id != ''
    AND group_name IS NOT NULL
    AND BTRIM(group_name) != ''
  GROUP BY provider_id
  HAVING COUNT(*) >= 2;

  CREATE UNIQUE INDEX IF NOT EXISTS idx_care_groups_provider_id ON care_groups (provider_id);
  CREATE INDEX IF NOT EXISTS idx_care_groups_slug ON care_groups (slug);
  CREATE INDEX IF NOT EXISTS idx_care_groups_locations ON care_groups (location_count DESC);
END $$;
