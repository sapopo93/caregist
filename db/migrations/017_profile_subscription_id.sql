-- Track the Stripe subscription ID for provider profile (listing) subscriptions.
-- Used to locate the provider on cancellation webhooks and downgrade profile_tier.
ALTER TABLE care_providers
    ADD COLUMN IF NOT EXISTS profile_subscription_id TEXT DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_profile_subscription_id
    ON care_providers (profile_subscription_id)
    WHERE profile_subscription_id IS NOT NULL;
