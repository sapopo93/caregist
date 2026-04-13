-- Stripe webhook event deduplication table.
-- Prevents double-processing of replayed or retried webhook events.
-- Entries older than 24 hours are cleaned up on each webhook call.
CREATE TABLE IF NOT EXISTS stripe_processed_events (
    event_id     TEXT        PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_events_processed_at
    ON stripe_processed_events (processed_at);
