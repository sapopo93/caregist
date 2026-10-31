-- Add the immutable shared customer package to Territory Brief fulfilment.
-- Existing PDF/CSV entitlements remain valid; new fulfilments also receive the
-- order/customer/payment-bound ZIP and its selection/manifest evidence.

ALTER TABLE territory_brief_orders
  ADD COLUMN IF NOT EXISTS blob_zip_pathname TEXT,
  ADD COLUMN IF NOT EXISTS package_sha256 CHAR(64),
  ADD COLUMN IF NOT EXISTS selection_snapshot JSONB,
  ADD COLUMN IF NOT EXISTS selection_sha256 CHAR(64),
  ADD COLUMN IF NOT EXISTS package_manifest JSONB,
  ADD COLUMN IF NOT EXISTS package_version TEXT;

ALTER TABLE territory_brief_orders
  ADD CONSTRAINT territory_brief_orders_package_sha256_check
    CHECK (package_sha256 IS NULL OR package_sha256 ~ '^[0-9a-f]{64}$'),
  ADD CONSTRAINT territory_brief_orders_selection_sha256_check
    CHECK (selection_sha256 IS NULL OR selection_sha256 ~ '^[0-9a-f]{64}$'),
  ADD CONSTRAINT territory_brief_orders_package_version_check
    CHECK (package_version IS NULL OR (package_version = BTRIM(package_version) AND package_version <> ''));

-- Production's token table predates migration 060's design and has no
-- artifact_kind column at all (both 30 Oct 2026 applies failed on it). Migration
-- 073 rebuilds that table, so here only touch the CHECK where the column exists.
-- Elsewhere, drop whichever CHECK constrains artifact_kind (its name is not
-- guaranteed) and add one under a known name.
DO $$
DECLARE
  existing RECORD;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'territory_brief_download_tokens'
      AND column_name = 'artifact_kind'
  ) THEN
    RETURN;
  END IF;
  FOR existing IN
    SELECT conname FROM pg_constraint
    WHERE conrelid = 'territory_brief_download_tokens'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%artifact_kind%'
  LOOP
    EXECUTE format('ALTER TABLE territory_brief_download_tokens DROP CONSTRAINT %I', existing.conname);
  END LOOP;
  ALTER TABLE territory_brief_download_tokens
    ADD CONSTRAINT territory_brief_download_tokens_artifact_kind_check
      CHECK (artifact_kind IN ('pdf', 'csv', 'zip'));
END $$;
