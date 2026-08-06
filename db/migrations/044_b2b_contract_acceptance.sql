-- Immutable B2B contract evidence and cancellation-at-period-end state.

ALTER TABLE subscriptions
  ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE subscriptions
  ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS b2b_contract_acceptances (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  stripe_checkout_session_id TEXT NOT NULL UNIQUE,
  terms_version TEXT NOT NULL,
  terms_sha256 CHAR(64) NOT NULL,
  business_use_confirmed BOOLEAN NOT NULL CHECK (business_use_confirmed),
  accepted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_address_hash CHAR(64),
  user_agent TEXT,
  CHECK (terms_version = BTRIM(terms_version) AND terms_version <> ''),
  CHECK (terms_sha256 ~ '^[0-9a-f]{64}$'),
  CHECK (ip_address_hash IS NULL OR ip_address_hash ~ '^[0-9a-f]{64}$'),
  CHECK (user_agent IS NULL OR LENGTH(user_agent) <= 512)
);

CREATE INDEX IF NOT EXISTS idx_b2b_contract_acceptances_user
  ON b2b_contract_acceptances (user_id, accepted_at DESC);

COMMENT ON TABLE b2b_contract_acceptances IS
  'Append-only evidence. Application code must never update or delete acceptance rows.';

CREATE OR REPLACE FUNCTION prevent_b2b_contract_acceptance_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'b2b_contract_acceptances is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_b2b_contract_acceptances_immutable ON b2b_contract_acceptances;
CREATE TRIGGER trg_b2b_contract_acceptances_immutable
BEFORE UPDATE OR DELETE ON b2b_contract_acceptances
FOR EACH ROW EXECUTE FUNCTION prevent_b2b_contract_acceptance_mutation();
