-- Immutable full-dataset artefacts, paid orders, consent evidence, and revocable downloads.

CREATE TABLE IF NOT EXISTS full_dataset_artifacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  blob_pathname TEXT NOT NULL UNIQUE,
  record_count INTEGER NOT NULL CHECK (record_count > 0),
  sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  source_watermark TIMESTAMPTZ NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ogl_attribution TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  CHECK (blob_pathname = BTRIM(blob_pathname) AND blob_pathname <> ''),
  CHECK (ogl_attribution = BTRIM(ogl_attribution) AND ogl_attribution <> '')
);

CREATE UNIQUE INDEX IF NOT EXISTS full_dataset_one_active_artifact
  ON full_dataset_artifacts (is_active) WHERE is_active;

CREATE TABLE IF NOT EXISTS full_dataset_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_id UUID NOT NULL REFERENCES full_dataset_artifacts(id) ON DELETE RESTRICT,
  stripe_checkout_session_id TEXT UNIQUE,
  stripe_payment_intent_id TEXT UNIQUE,
  customer_email TEXT NOT NULL,
  stripe_price_id TEXT NOT NULL,
  amount_total INTEGER,
  currency CHAR(3),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'paid', 'refunded', 'expired')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  paid_at TIMESTAMPTZ,
  fulfilled_at TIMESTAMPTZ,
  CHECK (customer_email = LOWER(BTRIM(customer_email))),
  CHECK (stripe_price_id LIKE 'price_%'),
  CHECK (amount_total IS NULL OR amount_total >= 0),
  CHECK (currency IS NULL OR currency ~ '^[a-z]{3}$')
);

CREATE INDEX IF NOT EXISTS full_dataset_orders_email_created
  ON full_dataset_orders (customer_email, created_at DESC);

CREATE TABLE IF NOT EXISTS digital_content_consents (
  id BIGSERIAL PRIMARY KEY,
  order_id UUID NOT NULL UNIQUE REFERENCES full_dataset_orders(id) ON DELETE RESTRICT,
  stripe_checkout_session_id TEXT NOT NULL UNIQUE,
  terms_version TEXT NOT NULL,
  terms_sha256 CHAR(64) NOT NULL CHECK (terms_sha256 ~ '^[0-9a-f]{64}$'),
  consent_text_sha256 CHAR(64) NOT NULL CHECK (consent_text_sha256 ~ '^[0-9a-f]{64}$'),
  immediate_supply_consented BOOLEAN NOT NULL CHECK (immediate_supply_consented),
  cancellation_right_acknowledged BOOLEAN NOT NULL CHECK (cancellation_right_acknowledged),
  accepted_at TIMESTAMPTZ NOT NULL,
  evidence_source TEXT NOT NULL CHECK (evidence_source = 'stripe_checkout_terms_checkbox'),
  CHECK (terms_version = BTRIM(terms_version) AND terms_version <> '')
);

COMMENT ON TABLE digital_content_consents IS
  'Append-only evidence of express immediate-supply consent and cancellation-right acknowledgement.';

CREATE OR REPLACE FUNCTION prevent_digital_content_consent_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'digital_content_consents is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS digital_content_consents_immutable ON digital_content_consents;
CREATE TRIGGER digital_content_consents_immutable
BEFORE UPDATE OR DELETE ON digital_content_consents
FOR EACH ROW EXECUTE FUNCTION prevent_digital_content_consent_mutation();

CREATE TABLE IF NOT EXISTS dataset_download_tokens (
  token_hash CHAR(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  order_id UUID NOT NULL REFERENCES full_dataset_orders(id) ON DELETE RESTRICT,
  expires_at TIMESTAMPTZ NOT NULL,
  max_downloads INTEGER NOT NULL DEFAULT 5 CHECK (max_downloads BETWEEN 1 AND 20),
  download_count INTEGER NOT NULL DEFAULT 0 CHECK (download_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_downloaded_at TIMESTAMPTZ,
  CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS dataset_download_tokens_order
  ON dataset_download_tokens (order_id, expires_at DESC);
