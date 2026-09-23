-- Durable intake and lifecycle tracking for Territory Opportunity Brief scopes.
-- This records an enquiry only. It does not create an order or authorize checkout.

CREATE TABLE IF NOT EXISTS territory_scope_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  public_reference TEXT NOT NULL UNIQUE,
  submission_key TEXT NOT NULL UNIQUE CHECK (LENGTH(submission_key) = 64),
  requester_fingerprint TEXT NOT NULL CHECK (LENGTH(requester_fingerprint) = 64),
  contact_email TEXT NOT NULL,
  contact_name TEXT,
  company_name TEXT,
  region TEXT NOT NULL,
  buyer_type TEXT NOT NULL,
  service_type TEXT NOT NULL DEFAULT '',
  location_count INTEGER NOT NULL CHECK (location_count >= 0),
  provider_organisation_count INTEGER NOT NULL CHECK (provider_organisation_count >= 0),
  coverage_verdict TEXT NOT NULL CHECK (coverage_verdict IN ('ready', 'partial', 'insufficient')),
  coverage_sufficient BOOLEAN NOT NULL,
  checkout_eligible BOOLEAN NOT NULL DEFAULT FALSE CHECK (checkout_eligible = FALSE),
  status TEXT NOT NULL DEFAULT 'requested' CHECK (
    status IN ('requested', 'reviewing', 'accepted', 'declined', 'fulfilled', 'cancelled')
  ),
  reviewed_at TIMESTAMPTZ,
  fulfilled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (status <> 'fulfilled' OR fulfilled_at IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS territory_scope_requests_status_created
  ON territory_scope_requests (status, created_at);
CREATE INDEX IF NOT EXISTS territory_scope_requests_email_created
  ON territory_scope_requests (contact_email, created_at DESC);
CREATE INDEX IF NOT EXISTS territory_scope_requests_requester_created
  ON territory_scope_requests (requester_fingerprint, created_at DESC);

CREATE TABLE IF NOT EXISTS territory_scope_request_events (
  id BIGSERIAL PRIMARY KEY,
  request_id UUID NOT NULL REFERENCES territory_scope_requests(id) ON DELETE RESTRICT,
  event_type TEXT NOT NULL CHECK (
    event_type IN ('requested', 'reviewing', 'accepted', 'declined', 'fulfilled', 'cancelled')
  ),
  actor_type TEXT NOT NULL CHECK (actor_type IN ('customer', 'operator', 'system')),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS territory_scope_request_events_request_created
  ON territory_scope_request_events (request_id, created_at);

CREATE OR REPLACE FUNCTION prevent_territory_scope_request_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'territory_scope_request_events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS territory_scope_request_events_immutable
  ON territory_scope_request_events;
CREATE TRIGGER territory_scope_request_events_immutable
BEFORE UPDATE OR DELETE ON territory_scope_request_events
FOR EACH ROW EXECUTE FUNCTION prevent_territory_scope_request_event_mutation();

CREATE OR REPLACE FUNCTION enforce_territory_scope_request_transition()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = OLD.status THEN
    RETURN NEW;
  END IF;

  IF NOT (
    (OLD.status = 'requested' AND NEW.status IN ('reviewing', 'cancelled')) OR
    (OLD.status = 'reviewing' AND NEW.status IN ('accepted', 'declined', 'cancelled')) OR
    (OLD.status = 'accepted' AND NEW.status IN ('fulfilled', 'cancelled'))
  ) THEN
    RAISE EXCEPTION 'invalid territory scope request transition: % -> %', OLD.status, NEW.status;
  END IF;

  IF NEW.status IN ('accepted', 'declined') AND NEW.reviewed_at IS NULL THEN
    RAISE EXCEPTION 'reviewed_at is required for status %', NEW.status;
  END IF;
  IF NEW.status = 'fulfilled' AND NEW.fulfilled_at IS NULL THEN
    RAISE EXCEPTION 'fulfilled_at is required for fulfilled status';
  END IF;

  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS territory_scope_request_transition_guard
  ON territory_scope_requests;
CREATE TRIGGER territory_scope_request_transition_guard
BEFORE UPDATE OF status ON territory_scope_requests
FOR EACH ROW EXECUTE FUNCTION enforce_territory_scope_request_transition();
