-- Transactional outbox for de-identified TrustRoute business signals.

CREATE TABLE IF NOT EXISTS trustroute_outbox (
  outbox_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL CHECK (event_type = 'b2b.signal'),
  occurred_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','succeeded','dead')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  claim_token UUID,
  lease_until TIMESTAMPTZ,
  last_error_code TEXT,
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((status = 'processing') = (claim_token IS NOT NULL AND lease_until IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_trustroute_outbox_pending
  ON trustroute_outbox (next_attempt_at, created_at)
  WHERE status IN ('pending','processing');

CREATE OR REPLACE FUNCTION enqueue_trustroute_business_signal()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO trustroute_outbox (source_event_id,event_type,occurred_at,payload)
  VALUES (
    'caregist:' || NEW.id::text,
    'b2b.signal',
    NEW.observed_at,
    jsonb_strip_nulls(jsonb_build_object(
      'ledger_id', NEW.id::text,
      'entity_type', NEW.entity_type,
      'entity_id', NEW.entity_id,
      'provider_id', NEW.provider_id,
      'location_id', NEW.location_id,
      'signal_type', NEW.event_type,
      'effective_date', NEW.effective_date,
      'source', NEW.source,
      'confidence_score', NEW.confidence_score,
      'region', NEW.metadata->>'region',
      'local_authority', NEW.metadata->>'local_authority',
      'service_types', NEW.metadata->'service_types'
    ))
  )
  ON CONFLICT (source_event_id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trusted_event_ledger_trustroute_outbox ON trusted_event_ledger;
CREATE TRIGGER trusted_event_ledger_trustroute_outbox
AFTER INSERT ON trusted_event_ledger
FOR EACH ROW EXECUTE FUNCTION enqueue_trustroute_business_signal();
