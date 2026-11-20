-- Region Monthly stage 1: an immutable, versioned store for monthly counts.
--
-- One row is one build of one UK calendar month for one England region and one
-- service type (service_slug NULL means all services). A month is built on the
-- 7th day of the following month (UK time). Rows are never updated or deleted:
-- a correction is a new row with the next build_version. The new row names the
-- version it replaces in supersedes_build_version, so the older row never needs
-- an UPDATE; "superseded" is read as "a row with a higher build_version exists".
--
-- Only the nine England regions are accepted. The empty region and "Wales" that
-- exist in care_providers are refused by the CHECK below.
--
-- Entitlements (who bought which months) are deliberately NOT stored here. That
-- is stage 2, with payments, and needs the owner's decisions on terms and tax
-- (docs/region-monthly-v1.md, open questions).

CREATE TABLE IF NOT EXISTS region_monthly_builds (
  id BIGSERIAL PRIMARY KEY,
  period_month DATE NOT NULL,
  region TEXT NOT NULL,
  service_slug TEXT,
  build_version INTEGER NOT NULL,
  supersedes_build_version INTEGER,
  correction_reason TEXT,
  schema_version INTEGER NOT NULL DEFAULT 1,
  built_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  built_from_data_cutoff TIMESTAMPTZ NOT NULL,
  metrics JSONB NOT NULL,
  coverage JSONB NOT NULL,
  limits JSONB NOT NULL,
  content_sha256 TEXT NOT NULL,
  CONSTRAINT region_monthly_builds_month_first_day
    CHECK (EXTRACT(DAY FROM period_month) = 1),
  CONSTRAINT region_monthly_builds_england_region
    CHECK (region IN (
      'East', 'East Midlands', 'London', 'North East', 'North West',
      'South East', 'South West', 'West Midlands', 'Yorkshire & Humberside'
    )),
  CONSTRAINT region_monthly_builds_service_slug_shape
    CHECK (service_slug IS NULL OR service_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  CONSTRAINT region_monthly_builds_version_chain
    CHECK (
      (build_version = 1
         AND supersedes_build_version IS NULL
         AND correction_reason IS NULL)
      OR
      (build_version > 1
         AND supersedes_build_version = build_version - 1
         AND correction_reason IS NOT NULL
         AND btrim(correction_reason) <> '')
    ),
  CONSTRAINT region_monthly_builds_sha256_shape
    CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  CONSTRAINT region_monthly_builds_json_shapes
    CHECK (
      jsonb_typeof(metrics) = 'object'
      AND jsonb_typeof(coverage) = 'object'
      AND jsonb_typeof(limits) = 'array'
    )
);

-- NULL service_slug (all services) must still be unique per version, and a plain
-- UNIQUE constraint treats NULLs as distinct, so the key uses COALESCE.
CREATE UNIQUE INDEX IF NOT EXISTS region_monthly_builds_key
  ON region_monthly_builds (period_month, region, COALESCE(service_slug, ''), build_version);

CREATE INDEX IF NOT EXISTS region_monthly_builds_lookup
  ON region_monthly_builds (region, COALESCE(service_slug, ''), period_month);

CREATE OR REPLACE FUNCTION region_monthly_builds_guard_insert()
RETURNS TRIGGER AS $fn$
BEGIN
  IF NEW.build_version > 1 AND NOT EXISTS (
    SELECT 1 FROM region_monthly_builds b
    WHERE b.period_month = NEW.period_month
      AND b.region = NEW.region
      AND b.service_slug IS NOT DISTINCT FROM NEW.service_slug
      AND b.build_version = NEW.build_version - 1
  ) THEN
    RAISE EXCEPTION 'region_monthly_builds: version % has no version % to supersede',
      NEW.build_version, NEW.build_version - 1;
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION region_monthly_builds_reject_change()
RETURNS TRIGGER AS $fn$
BEGIN
  RAISE EXCEPTION 'region_monthly_builds is immutable: add a new build_version instead of changing or removing a build';
END;
$fn$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS region_monthly_builds_guard_insert ON region_monthly_builds;
CREATE TRIGGER region_monthly_builds_guard_insert
  BEFORE INSERT ON region_monthly_builds
  FOR EACH ROW EXECUTE FUNCTION region_monthly_builds_guard_insert();

DROP TRIGGER IF EXISTS region_monthly_builds_immutable_row ON region_monthly_builds;
CREATE TRIGGER region_monthly_builds_immutable_row
  BEFORE UPDATE OR DELETE ON region_monthly_builds
  FOR EACH ROW EXECUTE FUNCTION region_monthly_builds_reject_change();

DROP TRIGGER IF EXISTS region_monthly_builds_immutable_truncate ON region_monthly_builds;
CREATE TRIGGER region_monthly_builds_immutable_truncate
  BEFORE TRUNCATE ON region_monthly_builds
  FOR EACH STATEMENT EXECUTE FUNCTION region_monthly_builds_reject_change();
