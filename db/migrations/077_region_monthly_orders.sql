-- Region Monthly (stage 2): paid orders and per-month entitlements.
-- Additive only. Nothing here changes or removes an existing column, row or
-- constraint, and the stage 1 table region_monthly_builds is not touched.
--
-- region_monthly_orders        One row per purchase attempt: the buying account,
--                              the region and service, the purchase length, the
--                              exact ordered list of months, which of those months
--                              were future at purchase time and when each becomes
--                              available, the price and the terms the buyer accepted.
--                              Those columns can never be updated after the row is
--                              written. A refund changes `state` only.
-- region_monthly_entitlements  One row per purchased month, created once when the
--                              signed payment event pays the order. Append-only.
--                              Access to a month needs a row here AND an order in
--                              state 'paid', so a refund withdraws access without
--                              touching any entitlement row.
--
-- Owner scope is the buying account (users.id), as for Operator History orders.
-- Nothing is rendered at payment time: months are built on the 7th of the
-- following month by the build command, and delivery means the entitlement.

CREATE TABLE IF NOT EXISTS region_monthly_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  customer_email TEXT NOT NULL,

  region TEXT NOT NULL
    CHECK (region IN (
      'East', 'East Midlands', 'London', 'North East', 'North West',
      'South East', 'South West', 'West Midlands', 'Yorkshire & Humberside'
    )),
  -- NULL means all services.
  service_slug TEXT CHECK (service_slug IS NULL OR service_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  kind TEXT NOT NULL CHECK (kind IN ('single', 'six', 'twelve')),
  month_count INTEGER NOT NULL CHECK (month_count IN (1, 6, 12)),

  -- The exact ordered list of purchased months (first day of each month).
  months DATE[] NOT NULL,
  -- Which of those months were not built when the order was made, and the day each
  -- becomes available (the 7th of the following month), in the same order.
  future_months DATE[] NOT NULL DEFAULT '{}',
  future_available_from DATE[] NOT NULL DEFAULT '{}',
  future_months_accepted BOOLEAN NOT NULL DEFAULT FALSE,

  state TEXT NOT NULL DEFAULT 'pending_payment'
    CHECK (state IN ('pending_payment', 'paid', 'refunded', 'expired')),

  -- Price, fixed on the server when the order is created (api/services/region_monthly.py PURCHASE_KINDS).
  price_pence INTEGER NOT NULL CHECK (price_pence > 0),
  currency CHAR(3) NOT NULL CHECK (currency = 'gbp'),
  stripe_price_id TEXT NOT NULL CHECK (stripe_price_id LIKE 'price_%'),

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

  -- A failed attempt to create the entitlements after payment is recorded here.
  entitlement_attempts INTEGER NOT NULL DEFAULT 0 CHECK (entitlement_attempts >= 0),
  last_error TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  paid_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ,

  CHECK (customer_email = LOWER(BTRIM(customer_email))),
  CHECK (
    (kind = 'single' AND month_count = 1)
    OR (kind = 'six' AND month_count = 6)
    OR (kind = 'twelve' AND month_count = 12)
  ),
  CHECK (cardinality(months) = month_count),
  CHECK (cardinality(future_months) = cardinality(future_available_from)),
  CHECK (future_months <@ months),
  CHECK (cardinality(future_months) = 0 OR future_months_accepted),
  CHECK (state <> 'paid' OR (stripe_payment_intent_id IS NOT NULL AND paid_at IS NOT NULL))
);

-- One payable checkout per account, region and service at a time: a double submit
-- finds the pending order instead of creating a second one. A later, deliberate
-- purchase of the same scope starts after this one is paid, refunded or expired.
CREATE UNIQUE INDEX IF NOT EXISTS region_monthly_orders_one_pending
  ON region_monthly_orders (user_id, region, COALESCE(service_slug, ''))
  WHERE state = 'pending_payment';

-- The months an account already holds, for the overlap refusal.
CREATE INDEX IF NOT EXISTS region_monthly_orders_paid_scope
  ON region_monthly_orders (user_id, region, COALESCE(service_slug, ''))
  WHERE state = 'paid';

CREATE INDEX IF NOT EXISTS region_monthly_orders_user_created
  ON region_monthly_orders (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS region_monthly_entitlements (
  id BIGSERIAL PRIMARY KEY,
  order_id UUID NOT NULL REFERENCES region_monthly_orders(id) ON DELETE RESTRICT,
  period_month DATE NOT NULL CHECK (EXTRACT(DAY FROM period_month) = 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT region_monthly_entitlements_one_per_month UNIQUE (order_id, period_month)
);

COMMENT ON TABLE region_monthly_entitlements IS
  'One row per purchased Region Monthly month. Append-only; a refund changes the order state, never these rows.';

CREATE OR REPLACE FUNCTION region_monthly_orders_reject_change()
RETURNS TRIGGER AS $fn$
BEGIN
  RAISE EXCEPTION '% is append-only: it is never updated, deleted or truncated', TG_TABLE_NAME;
END;
$fn$ LANGUAGE plpgsql;

-- An entitlement can exist only for a month of a paid order.
CREATE OR REPLACE FUNCTION region_monthly_entitlements_guard_insert()
RETURNS TRIGGER AS $fn$
DECLARE
  parent region_monthly_orders%ROWTYPE;
BEGIN
  SELECT * INTO parent FROM region_monthly_orders WHERE id = NEW.order_id;
  IF NOT FOUND OR parent.state <> 'paid' THEN
    RAISE EXCEPTION 'region_monthly_entitlements: an entitlement needs a paid order';
  END IF;
  IF NOT (NEW.period_month = ANY (parent.months)) THEN
    RAISE EXCEPTION 'region_monthly_entitlements: % is not a month of this order', NEW.period_month;
  END IF;
  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS region_monthly_entitlements_guard_insert ON region_monthly_entitlements;
CREATE TRIGGER region_monthly_entitlements_guard_insert
  BEFORE INSERT ON region_monthly_entitlements
  FOR EACH ROW EXECUTE FUNCTION region_monthly_entitlements_guard_insert();

DROP TRIGGER IF EXISTS region_monthly_entitlements_immutable_row ON region_monthly_entitlements;
CREATE TRIGGER region_monthly_entitlements_immutable_row
  BEFORE UPDATE OR DELETE ON region_monthly_entitlements
  FOR EACH ROW EXECUTE FUNCTION region_monthly_orders_reject_change();

DROP TRIGGER IF EXISTS region_monthly_entitlements_immutable_truncate ON region_monthly_entitlements;
CREATE TRIGGER region_monthly_entitlements_immutable_truncate
  BEFORE TRUNCATE ON region_monthly_entitlements
  FOR EACH STATEMENT EXECUTE FUNCTION region_monthly_orders_reject_change();

DROP TRIGGER IF EXISTS region_monthly_orders_immutable_truncate ON region_monthly_orders;
CREATE TRIGGER region_monthly_orders_immutable_truncate
  BEFORE TRUNCATE ON region_monthly_orders
  FOR EACH STATEMENT EXECUTE FUNCTION region_monthly_orders_reject_change();

-- The order guard.
--   INSERT  the months must be consecutive first-of-month dates that start the
--           run, and a new order is always pending payment.
--   UPDATE  the purchase (scope, months, price, terms) never changes. Payment
--           evidence is write-once. `state` moves only along the allowed
--           transitions, so a refund changes state and nothing else.
--   DELETE  never.
CREATE OR REPLACE FUNCTION region_monthly_orders_guard()
RETURNS TRIGGER AS $fn$
DECLARE
  i INTEGER;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'region_monthly_orders rows are never deleted';
  END IF;

  IF TG_OP = 'INSERT' THEN
    IF NEW.state <> 'pending_payment' THEN
      RAISE EXCEPTION 'region_monthly_orders: a new order starts as pending_payment';
    END IF;
    FOR i IN 1 .. cardinality(NEW.months) LOOP
      IF EXTRACT(DAY FROM NEW.months[i]) <> 1
         OR NEW.months[i] <> (NEW.months[1] + ((i - 1) * INTERVAL '1 month'))::date THEN
        RAISE EXCEPTION 'region_monthly_orders: months must be consecutive first days of a month';
      END IF;
    END LOOP;
    RETURN NEW;
  END IF;

  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.user_id IS DISTINCT FROM OLD.user_id
     OR NEW.customer_email IS DISTINCT FROM OLD.customer_email
     OR NEW.region IS DISTINCT FROM OLD.region
     OR NEW.service_slug IS DISTINCT FROM OLD.service_slug
     OR NEW.kind IS DISTINCT FROM OLD.kind
     OR NEW.month_count IS DISTINCT FROM OLD.month_count
     OR NEW.months IS DISTINCT FROM OLD.months
     OR NEW.future_months IS DISTINCT FROM OLD.future_months
     OR NEW.future_available_from IS DISTINCT FROM OLD.future_available_from
     OR NEW.future_months_accepted IS DISTINCT FROM OLD.future_months_accepted
     OR NEW.price_pence IS DISTINCT FROM OLD.price_pence
     OR NEW.currency IS DISTINCT FROM OLD.currency
     OR NEW.stripe_price_id IS DISTINCT FROM OLD.stripe_price_id
     OR NEW.terms_version IS DISTINCT FROM OLD.terms_version
     OR NEW.terms_sha256 IS DISTINCT FROM OLD.terms_sha256
     OR NEW.checkout_expires_at IS DISTINCT FROM OLD.checkout_expires_at
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'region_monthly_orders: the purchased months, price and terms never change';
  END IF;

  IF (OLD.stripe_checkout_session_id IS NOT NULL AND NEW.stripe_checkout_session_id IS DISTINCT FROM OLD.stripe_checkout_session_id)
     OR (OLD.stripe_checkout_url IS NOT NULL AND NEW.stripe_checkout_url IS DISTINCT FROM OLD.stripe_checkout_url)
     OR (OLD.contract_acceptance_id IS NOT NULL AND NEW.contract_acceptance_id IS DISTINCT FROM OLD.contract_acceptance_id)
     OR (OLD.stripe_payment_intent_id IS NOT NULL AND NEW.stripe_payment_intent_id IS DISTINCT FROM OLD.stripe_payment_intent_id)
     OR (OLD.amount_total IS NOT NULL AND NEW.amount_total IS DISTINCT FROM OLD.amount_total)
     OR (OLD.paid_at IS NOT NULL AND NEW.paid_at IS DISTINCT FROM OLD.paid_at)
     OR (OLD.refunded_at IS NOT NULL AND NEW.refunded_at IS DISTINCT FROM OLD.refunded_at) THEN
    RAISE EXCEPTION 'region_monthly_orders: payment and refund evidence is write-once';
  END IF;

  IF NEW.state IS DISTINCT FROM OLD.state AND NOT (
       (OLD.state = 'pending_payment' AND NEW.state IN ('paid', 'expired', 'refunded'))
    OR (OLD.state = 'expired' AND NEW.state IN ('paid', 'refunded'))
    OR (OLD.state = 'paid' AND NEW.state = 'refunded')
  ) THEN
    RAISE EXCEPTION 'region_monthly_orders: state cannot move from % to %', OLD.state, NEW.state;
  END IF;

  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS region_monthly_orders_guard_trg ON region_monthly_orders;
CREATE TRIGGER region_monthly_orders_guard_trg
  BEFORE INSERT OR UPDATE OR DELETE ON region_monthly_orders
  FOR EACH ROW EXECUTE FUNCTION region_monthly_orders_guard();

COMMENT ON TABLE region_monthly_orders IS
  'Region Monthly purchases. The purchased months, price and terms never change; a refund changes state only.';
