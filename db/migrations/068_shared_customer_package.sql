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

ALTER TABLE territory_brief_download_tokens
  DROP CONSTRAINT territory_brief_download_tokens_artifact_kind_check;

ALTER TABLE territory_brief_download_tokens
  ADD CONSTRAINT territory_brief_download_tokens_artifact_kind_check
    CHECK (artifact_kind IN ('pdf', 'csv', 'zip'));

