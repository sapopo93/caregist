-- Outbound webhook subscriptions for Business+ tier users
-- Delivery is performed by api/utils/webhook_delivery.py
-- Initial supported event: provider.rating_changed
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id                SERIAL PRIMARY KEY,
    user_id           INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url               TEXT NOT NULL,
    secret            TEXT NOT NULL,        -- HMAC-SHA256 signing secret (plain, generated once, shown once)
    events            TEXT[] NOT NULL DEFAULT '{provider.rating_changed}',
    active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    last_delivery_at  TIMESTAMPTZ,
    delivery_failures INT NOT NULL DEFAULT 0,
    UNIQUE(user_id, url)
);

CREATE INDEX IF NOT EXISTS idx_ws_user   ON webhook_subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_ws_active ON webhook_subscriptions (active) WHERE active = TRUE;
