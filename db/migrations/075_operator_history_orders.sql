-- Operator History (stage 2): paid orders and their immutable delivered files.
-- Additive only. Nothing here changes or removes an existing column, row or
-- constraint, and the Stripe-facing tables are untouched.
--
-- operator_history_orders   One row per purchase attempt. It pins the record that
--                           was built at checkout (the record JSON, its
--                           content_sha256, the CQC edition rows and their
--                           SHA-256 values) and the price. Those columns can
--                           never be updated. A refund changes `state` only.
-- operator_history_artefacts  The delivered CSV and PDF bytes with their SHA-256.
--                           Append-only: no update, no delete.
--
-- Owner scope is the buying account (users.id), as for every other paid
-- checkout that needs a signed-in browser session. No download token exists, so
-- no raw or hashed token is stored.

CREATE TABLE IF NOT EXISTS operator_history_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  customer_email TEXT NOT NULL,
  provider_id VARCHAR(20) NOT NULL CHECK (provider_id ~ '^1-[0-9]{3,15}$'),
  legal_name TEXT NOT NULL CHECK (legal_name = BTRIM(legal_name) AND legal_name <> ''),

  state TEXT NOT NULL DEFAULT 'pending_payment'
    CHECK (state IN ('pending_payment', 'paid', 'delivered', 'refunded', 'failed', 'expired')),

  -- Price, fixed on the server when the order is created.
  price_pence INTEGER NOT NULL CHECK (price_pence > 0),
  currency CHAR(3) NOT NULL CHECK (currency = 'gbp'),
  stripe_price_id TEXT NOT NULL CHECK (stripe_price_id LIKE 'price_%'),

  -- The pinned build. `record` is the exact record built at checkout.
  record_schema_version INTEGER NOT NULL CHECK (record_schema_version >= 1),
  record JSONB NOT NULL,
  content_sha256 CHAR(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  edition_id BIGINT NOT NULL,
  edition_ids BIGINT[] NOT NULL CHECK (cardinality(edition_ids) >= 1),
  edition_providers_sha256 CHAR(64) NOT NULL CHECK (edition_providers_sha256 ~ '^[0-9a-f]{64}$'),
  edition_locations_sha256 CHAR(64) NOT NULL CHECK (edition_locations_sha256 ~ '^[0-9a-f]{64}$'),

  -- Terms the buyer accepted. The acceptance reference is the Checkout Session id
  -- on the shared b2b_contract_acceptances row.
  terms_version TEXT NOT NULL CHECK (terms_version = BTRIM(terms_version) AND terms_version <> ''),
  terms_sha256 CHAR(64) NOT NULL CHECK (terms_sha256 ~ '^[0-9a-f]{64}$'),
  contract_acceptance_id BIGINT REFERENCES b2b_contract_acceptances(id) ON DELETE RESTRICT,

  stripe_checkout_session_id TEXT UNIQUE,
  stripe_checkout_url TEXT,
  checkout_expires_at TIMESTAMPTZ NOT NULL,
  stripe_payment_intent_id TEXT UNIQUE,
  amount_total INTEGER CHECK (amount_total IS NULL OR amount_total >= 0),

  delivery_attempts INTEGER NOT NULL DEFAULT 0 CHECK (delivery_attempts >= 0),
  last_error TEXT,
  csv_sha256 CHAR(64) CHECK (csv_sha256 IS NULL OR csv_sha256 ~ '^[0-9a-f]{64}$'),
  pdf_sha256 CHAR(64) CHECK (pdf_sha256 IS NULL OR pdf_sha256 ~ '^[0-9a-f]{64}$'),

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  paid_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ,

  CHECK (customer_email = LOWER(BTRIM(customer_email))),
  CHECK (state NOT IN ('paid', 'delivered', 'failed') OR (stripe_payment_intent_id IS NOT NULL AND paid_at IS NOT NULL)),
  CHECK (state <> 'delivered' OR (csv_sha256 IS NOT NULL AND pdf_sha256 IS NOT NULL AND delivered_at IS NOT NULL))
);

-- One payable checkout per account and operator at a time: a double submit finds
-- the pending order instead of creating a second one. A later, deliberate
-- purchase starts after this one is paid, expired or failed.
CREATE UNIQUE INDEX IF NOT EXISTS operator_history_orders_one_pending
  ON operator_history_orders (user_id, provider_id) WHERE state = 'pending_payment';

CREATE INDEX IF NOT EXISTS operator_history_orders_user_created
  ON operator_history_orders (user_id, created_at DESC);

-- Orders that were paid and not yet delivered, for the retry command.
CREATE INDEX IF NOT EXISTS operator_history_orders_undelivered
  ON operator_history_orders (updated_at) WHERE state IN ('paid', 'failed');

CREATE TABLE IF NOT EXISTS operator_history_artefacts (
  id BIGSERIAL PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES operator_history_orders(id) ON DELETE RESTRICT,
  format TEXT NOT NULL CHECK (format IN ('csv', 'pdf')),
  filename TEXT NOT NULL CHECK (filename = BTRIM(filename) AND filename <> ''),
  content_type TEXT NOT NULL,
  content BYTEA NOT NULL,
  byte_size INTEGER NOT NULL,
  artefact_sha256 CHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (order_id, format),
  CHECK (byte_size = octet_length(content)),
  CHECK (artefact_sha256 = encode(sha256(content), 'hex'))
);

COMMENT ON TABLE operator_history_artefacts IS
  'Delivered Operator History files. Append-only: a delivered file is never updated or deleted.';

CREATE OR REPLACE FUNCTION operator_history_artefacts_append_only()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'operator_history_artefacts is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS operator_history_artefacts_immutable ON operator_history_artefacts;
CREATE TRIGGER operator_history_artefacts_immutable
BEFORE UPDATE OR DELETE ON operator_history_artefacts
FOR EACH ROW EXECUTE FUNCTION operator_history_artefacts_append_only();

-- The order guard. Pinned columns never change. Write-once columns can be set
-- once and never changed. `state` moves only along the allowed transitions, so a
-- delivered record's content cannot be rewritten and a refund changes state only.
CREATE OR REPLACE FUNCTION operator_history_orders_guard()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'operator_history_orders rows are never deleted';
  END IF;

  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.user_id IS DISTINCT FROM OLD.user_id
     OR NEW.customer_email IS DISTINCT FROM OLD.customer_email
     OR NEW.provider_id IS DISTINCT FROM OLD.provider_id
     OR NEW.legal_name IS DISTINCT FROM OLD.legal_name
     OR NEW.price_pence IS DISTINCT FROM OLD.price_pence
     OR NEW.currency IS DISTINCT FROM OLD.currency
     OR NEW.stripe_price_id IS DISTINCT FROM OLD.stripe_price_id
     OR NEW.record_schema_version IS DISTINCT FROM OLD.record_schema_version
     OR NEW.content_sha256 IS DISTINCT FROM OLD.content_sha256
     OR NEW.edition_id IS DISTINCT FROM OLD.edition_id
     OR NEW.edition_ids IS DISTINCT FROM OLD.edition_ids
     OR NEW.edition_providers_sha256 IS DISTINCT FROM OLD.edition_providers_sha256
     OR NEW.edition_locations_sha256 IS DISTINCT FROM OLD.edition_locations_sha256
     OR NEW.terms_version IS DISTINCT FROM OLD.terms_version
     OR NEW.terms_sha256 IS DISTINCT FROM OLD.terms_sha256
     OR NEW.checkout_expires_at IS DISTINCT FROM OLD.checkout_expires_at
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
     OR NEW.record IS DISTINCT FROM OLD.record THEN
    RAISE EXCEPTION 'operator_history_orders: the pinned record, edition and price never change';
  END IF;

  IF (OLD.stripe_checkout_session_id IS NOT NULL AND NEW.stripe_checkout_session_id IS DISTINCT FROM OLD.stripe_checkout_session_id)
     OR (OLD.stripe_checkout_url IS NOT NULL AND NEW.stripe_checkout_url IS DISTINCT FROM OLD.stripe_checkout_url)
     OR (OLD.contract_acceptance_id IS NOT NULL AND NEW.contract_acceptance_id IS DISTINCT FROM OLD.contract_acceptance_id)
     OR (OLD.stripe_payment_intent_id IS NOT NULL AND NEW.stripe_payment_intent_id IS DISTINCT FROM OLD.stripe_payment_intent_id)
     OR (OLD.amount_total IS NOT NULL AND NEW.amount_total IS DISTINCT FROM OLD.amount_total)
     OR (OLD.paid_at IS NOT NULL AND NEW.paid_at IS DISTINCT FROM OLD.paid_at)
     OR (OLD.csv_sha256 IS NOT NULL AND NEW.csv_sha256 IS DISTINCT FROM OLD.csv_sha256)
     OR (OLD.pdf_sha256 IS NOT NULL AND NEW.pdf_sha256 IS DISTINCT FROM OLD.pdf_sha256)
     OR (OLD.delivered_at IS NOT NULL AND NEW.delivered_at IS DISTINCT FROM OLD.delivered_at)
     OR (OLD.refunded_at IS NOT NULL AND NEW.refunded_at IS DISTINCT FROM OLD.refunded_at) THEN
    RAISE EXCEPTION 'operator_history_orders: payment, delivery and refund evidence is write-once';
  END IF;

  IF NEW.state IS DISTINCT FROM OLD.state AND NOT (
       (OLD.state = 'pending_payment' AND NEW.state IN ('paid', 'expired', 'refunded'))
    OR (OLD.state = 'expired' AND NEW.state IN ('paid', 'refunded'))
    OR (OLD.state = 'paid' AND NEW.state IN ('delivered', 'failed', 'refunded'))
    OR (OLD.state = 'failed' AND NEW.state IN ('paid', 'delivered', 'refunded'))
    OR (OLD.state = 'delivered' AND NEW.state = 'refunded')
  ) THEN
    RAISE EXCEPTION 'operator_history_orders: state cannot move from % to %', OLD.state, NEW.state;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS operator_history_orders_guard_trg ON operator_history_orders;
CREATE TRIGGER operator_history_orders_guard_trg
BEFORE UPDATE OR DELETE ON operator_history_orders
FOR EACH ROW EXECUTE FUNCTION operator_history_orders_guard();

COMMENT ON TABLE operator_history_orders IS
  'Operator History purchases. The pinned record and edition never change; a refund changes state only.';
