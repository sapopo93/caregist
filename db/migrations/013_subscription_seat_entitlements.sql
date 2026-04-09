-- Persist plan seat entitlements so billing and account surfaces can stay authoritative.
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS included_users INT NOT NULL DEFAULT 1;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS extra_seats INT NOT NULL DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS max_users INT NOT NULL DEFAULT 1;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS seat_price_gbp INT NOT NULL DEFAULT 0;
