-- Concurrency-safe self-service plan/seat changes for existing subscriptions.
-- See api/routers/billing.py: existing subscriptions were fail-closed to
-- "contact support" until this optimistic-lock version + append-only ledger
-- existed.

ALTER TABLE subscriptions
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS subscription_mutations (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  stripe_subscription_id TEXT NOT NULL,
  from_tier TEXT NOT NULL,
  from_extra_seats INT NOT NULL,
  to_tier TEXT NOT NULL,
  to_extra_seats INT NOT NULL,
  stripe_idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscription_mutations_user
  ON subscription_mutations (user_id, requested_at DESC);

COMMENT ON TABLE subscription_mutations IS
  'Append-only evidence of plan/seat changes on existing subscriptions. Application code must never update or delete rows.';

CREATE OR REPLACE FUNCTION prevent_subscription_mutation_ledger_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'subscription_mutations is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_subscription_mutations_immutable ON subscription_mutations;
CREATE TRIGGER trg_subscription_mutations_immutable
BEFORE UPDATE OR DELETE ON subscription_mutations
FOR EACH ROW EXECUTE FUNCTION prevent_subscription_mutation_ledger_mutation();
