-- Persist Stripe mutations so retries reuse one operation key while later
-- plan cycles and checkout attempts receive a fresh key.

CREATE TABLE IF NOT EXISTS billing_operations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_type VARCHAR(20) NOT NULL CHECK (owner_type IN ('account', 'provider')),
  owner_id VARCHAR(100) NOT NULL,
  operation_type VARCHAR(40) NOT NULL CHECK (
    operation_type IN ('checkout', 'subscription_change', 'profile_checkout', 'profile_change')
  ),
  request_fingerprint VARCHAR(64) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending', 'succeeded', 'failed', 'expired')
  ),
  stripe_object_id VARCHAR(255),
  stripe_object_url TEXT,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_operations_pending_owner
  ON billing_operations (owner_type, owner_id, operation_type)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_billing_operations_expiry
  ON billing_operations (status, expires_at);
