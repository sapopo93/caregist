-- Slice 2: fully-instant delivery of the GBP 795 Territory Opportunity Brief.
--
-- Unlike the retired full-dataset product (one shared immutable artefact,
-- migration 048), every Territory Opportunity Brief is generated per order for
-- the buyer's chosen scope, so the generated PDF + CSV live on the order row.
-- Consent evidence and revocable download tokens mirror the 048 shapes but are
-- kept on their own tables: the Brief is sold under different published Business
-- Terms and its immediate-supply consent wording must be approved separately.

CREATE TABLE IF NOT EXISTS territory_brief_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_checkout_session_id TEXT UNIQUE,
  stripe_payment_intent_id TEXT UNIQUE,
  customer_email TEXT NOT NULL,
  stripe_price_id TEXT NOT NULL,
  amount_total INTEGER,
  currency CHAR(3),
  -- Buyer-chosen scope, captured at checkout and echoed in immutable Stripe
  -- metadata. Fulfilment re-validates scope_name against live source data.
  scope_kind TEXT NOT NULL CHECK (scope_kind IN ('local_authority', 'region')),
  scope_name TEXT NOT NULL CHECK (scope_name = BTRIM(scope_name) AND scope_name <> ''),
  scope_window_days INTEGER NOT NULL DEFAULT 90 CHECK (scope_window_days BETWEEN 7 AND 365),
  scope_shortlist_target INTEGER NOT NULL DEFAULT 30 CHECK (scope_shortlist_target BETWEEN 10 AND 50),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'paid', 'generating', 'fulfilled', 'failed', 'expired', 'refunded')),
  generation_attempts INTEGER NOT NULL DEFAULT 0 CHECK (generation_attempts >= 0),
  last_error TEXT,
  blob_pdf_pathname TEXT,
  blob_csv_pathname TEXT,
  artifact_sha256 CHAR(64) CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  paid_at TIMESTAMPTZ,
  fulfilled_at TIMESTAMPTZ,
  CHECK (customer_email = LOWER(BTRIM(customer_email))),
  CHECK (stripe_price_id LIKE 'price_%'),
  CHECK (amount_total IS NULL OR amount_total >= 0),
  CHECK (currency IS NULL OR currency ~ '^[a-z]{3}$')
);

CREATE INDEX IF NOT EXISTS territory_brief_orders_email_created
  ON territory_brief_orders (customer_email, created_at DESC);
CREATE INDEX IF NOT EXISTS territory_brief_orders_status
  ON territory_brief_orders (status) WHERE status IN ('paid', 'generating', 'failed');

CREATE TABLE IF NOT EXISTS territory_brief_consents (
  id BIGSERIAL PRIMARY KEY,
  order_id UUID NOT NULL UNIQUE REFERENCES territory_brief_orders(id) ON DELETE RESTRICT,
  stripe_checkout_session_id TEXT NOT NULL UNIQUE,
  terms_version TEXT NOT NULL CHECK (terms_version = BTRIM(terms_version) AND terms_version <> ''),
  terms_sha256 CHAR(64) NOT NULL CHECK (terms_sha256 ~ '^[0-9a-f]{64}$'),
  consent_text_sha256 CHAR(64) NOT NULL CHECK (consent_text_sha256 ~ '^[0-9a-f]{64}$'),
  immediate_supply_consented BOOLEAN NOT NULL CHECK (immediate_supply_consented),
  cancellation_right_acknowledged BOOLEAN NOT NULL CHECK (cancellation_right_acknowledged),
  accepted_at TIMESTAMPTZ NOT NULL,
  evidence_source TEXT NOT NULL CHECK (evidence_source = 'stripe_checkout_terms_checkbox')
);

COMMENT ON TABLE territory_brief_consents IS
  'Append-only evidence of express immediate-supply consent for the Territory Opportunity Brief.';

CREATE OR REPLACE FUNCTION prevent_territory_brief_consent_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'territory_brief_consents is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS territory_brief_consents_immutable ON territory_brief_consents;
CREATE TRIGGER territory_brief_consents_immutable
BEFORE UPDATE OR DELETE ON territory_brief_consents
FOR EACH ROW EXECUTE FUNCTION prevent_territory_brief_consent_mutation();

CREATE TABLE IF NOT EXISTS territory_brief_download_tokens (
  token_hash CHAR(64) PRIMARY KEY CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  order_id UUID NOT NULL REFERENCES territory_brief_orders(id) ON DELETE RESTRICT,
  artifact_kind TEXT NOT NULL CHECK (artifact_kind IN ('pdf', 'csv')),
  expires_at TIMESTAMPTZ NOT NULL,
  max_downloads INTEGER NOT NULL DEFAULT 5 CHECK (max_downloads BETWEEN 1 AND 20),
  download_count INTEGER NOT NULL DEFAULT 0 CHECK (download_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_downloaded_at TIMESTAMPTZ,
  CHECK (expires_at > created_at),
  UNIQUE (order_id, artifact_kind)
);

CREATE INDEX IF NOT EXISTS territory_brief_download_tokens_order
  ON territory_brief_download_tokens (order_id, expires_at DESC);
