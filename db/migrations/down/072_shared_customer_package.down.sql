DELETE FROM territory_brief_download_tokens WHERE artifact_kind = 'zip';

ALTER TABLE territory_brief_download_tokens
  DROP CONSTRAINT territory_brief_download_tokens_artifact_kind_check;

ALTER TABLE territory_brief_download_tokens
  ADD CONSTRAINT territory_brief_download_tokens_artifact_kind_check
    CHECK (artifact_kind IN ('pdf', 'csv'));

ALTER TABLE territory_brief_orders
  DROP CONSTRAINT IF EXISTS territory_brief_orders_package_version_check,
  DROP CONSTRAINT IF EXISTS territory_brief_orders_selection_sha256_check,
  DROP CONSTRAINT IF EXISTS territory_brief_orders_package_sha256_check,
  DROP COLUMN IF EXISTS package_version,
  DROP COLUMN IF EXISTS package_manifest,
  DROP COLUMN IF EXISTS selection_sha256,
  DROP COLUMN IF EXISTS selection_snapshot,
  DROP COLUMN IF EXISTS package_sha256,
  DROP COLUMN IF EXISTS blob_zip_pathname;
