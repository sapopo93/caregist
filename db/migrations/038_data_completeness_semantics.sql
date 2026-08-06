-- Rename the directory field-completeness metric so it cannot be mistaken for
-- a care-quality score. Rebuild the dependent group view with explicit names.

DROP MATERIALIZED VIEW IF EXISTS care_groups;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'care_providers'
      AND column_name = 'quality_score'
  ) THEN
    ALTER TABLE care_providers RENAME COLUMN quality_score TO data_completeness_score;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'care_providers'
      AND column_name = 'quality_tier'
  ) THEN
    ALTER TABLE care_providers RENAME COLUMN quality_tier TO data_completeness_tier;
  END IF;
END $$;

DROP INDEX IF EXISTS idx_quality_tier;
CREATE INDEX IF NOT EXISTS idx_data_completeness_tier
  ON care_providers (data_completeness_tier);

-- Remove the legacy, misleading sentence from generated summaries. The score
-- remains available as a separately labelled directory-completeness field.
UPDATE care_providers
SET inspection_summary = regexp_replace(
  inspection_summary,
  '\\s*CareGist quality score: [0-9]+/100\\.',
  '',
  'gi'
)
WHERE inspection_summary ~* 'CareGist quality score:';

CREATE MATERIALIZED VIEW care_groups AS
SELECT
  provider_id,
  MAX(group_name) AS group_name,
  LOWER(REPLACE(REPLACE(REPLACE(MAX(group_name), ' ', '-'), '''', ''), '.', '')) AS slug,
  COUNT(*) AS location_count,
  COUNT(*) FILTER (WHERE overall_rating = 'Outstanding') AS outstanding_count,
  COUNT(*) FILTER (WHERE overall_rating = 'Good') AS good_count,
  COUNT(*) FILTER (WHERE overall_rating = 'Requires Improvement') AS ri_count,
  COUNT(*) FILTER (WHERE overall_rating = 'Inadequate') AS inadequate_count,
  COUNT(*) FILTER (
    WHERE overall_rating = 'Not Yet Inspected' OR overall_rating IS NULL
  ) AS not_inspected_count,
  ROUND(AVG(data_completeness_score)::numeric, 1) AS avg_data_completeness_score,
  ROUND(
    (COUNT(*) FILTER (WHERE overall_rating IN ('Outstanding', 'Good'))::numeric /
     NULLIF(COUNT(*) FILTER (
       WHERE overall_rating IS NOT NULL
         AND overall_rating != 'Not Yet Inspected'
     ), 0)) * 100,
    1
  ) AS pct_good_or_outstanding,
  SUM(number_of_beds) FILTER (WHERE number_of_beds > 0) AS total_beds,
  array_agg(DISTINCT region) FILTER (WHERE region IS NOT NULL AND region != '') AS regions,
  array_agg(DISTINCT type) FILTER (WHERE type IS NOT NULL) AS provider_types,
  MAX(last_inspection_date) AS latest_inspection
FROM care_providers
WHERE provider_id IS NOT NULL
  AND provider_id != ''
  AND group_name IS NOT NULL
  AND BTRIM(group_name) != ''
GROUP BY provider_id
HAVING COUNT(*) >= 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_care_groups_provider_id
  ON care_groups (provider_id);
CREATE INDEX IF NOT EXISTS idx_care_groups_slug ON care_groups (slug);
CREATE INDEX IF NOT EXISTS idx_care_groups_locations
  ON care_groups (location_count DESC);
