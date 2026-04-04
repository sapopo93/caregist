-- Enhanced provider profiles — paid feature for claimed providers
-- Adds fields that providers can populate after claiming and subscribing

ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS profile_description TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS profile_photos JSONB DEFAULT '[]';
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS virtual_tour_url TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS inspection_response TEXT;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS profile_tier VARCHAR(20) DEFAULT NULL;
ALTER TABLE care_providers ADD COLUMN IF NOT EXISTS profile_updated_at TIMESTAMP WITH TIME ZONE;

-- Track which provider profile tier they're on (basic/standard/premium)
-- NULL = free/unclaimed, 'basic' = £30/mo, 'standard' = £50/mo, 'premium' = £80/mo
COMMENT ON COLUMN care_providers.profile_tier IS 'NULL=free, basic=£30/mo, standard=£50/mo, premium=£80/mo';

-- Index for finding enhanced profiles (for featured/boosted search results later)
CREATE INDEX IF NOT EXISTS idx_profile_tier ON care_providers (profile_tier) WHERE profile_tier IS NOT NULL;
