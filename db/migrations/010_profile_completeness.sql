ALTER TABLE care_providers
    ADD COLUMN IF NOT EXISTS profile_completeness INT NOT NULL DEFAULT 0;

UPDATE care_providers
SET profile_completeness = LEAST(
    100,
    (CASE WHEN profile_description IS NOT NULL AND length(trim(profile_description)) >= 40 THEN 30 ELSE 0 END) +
    (CASE WHEN COALESCE(jsonb_array_length(profile_photos), 0) > 0 THEN 20 ELSE 0 END) +
    (CASE WHEN virtual_tour_url IS NOT NULL AND trim(virtual_tour_url) != '' THEN 10 ELSE 0 END) +
    (CASE WHEN inspection_response IS NOT NULL AND trim(inspection_response) != '' THEN 15 ELSE 0 END) +
    (CASE WHEN is_claimed = true THEN 10 ELSE 0 END) +
    (CASE WHEN profile_tier IS NOT NULL THEN 15 ELSE 0 END)
);

CREATE INDEX IF NOT EXISTS idx_care_providers_profile_completeness
    ON care_providers (profile_completeness DESC);
