-- Single source of truth for profile completeness scoring.
-- The function replaces the duplicated CASE expression that existed in both
-- migration 010 and the Python update logic.

CREATE OR REPLACE FUNCTION calculate_profile_completeness(
    p_description      TEXT,
    p_photos           JSONB,
    p_virtual_tour_url TEXT,
    p_inspection_resp  TEXT,
    p_is_claimed       BOOLEAN,
    p_profile_tier     TEXT
) RETURNS INT
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT LEAST(100,
        (CASE WHEN p_description IS NOT NULL AND length(trim(p_description)) >= 40 THEN 30 ELSE 0 END) +
        (CASE WHEN COALESCE(jsonb_array_length(p_photos), 0) > 0 THEN 20 ELSE 0 END) +
        (CASE WHEN p_virtual_tour_url IS NOT NULL AND trim(p_virtual_tour_url) != '' THEN 10 ELSE 0 END) +
        (CASE WHEN p_inspection_resp IS NOT NULL AND trim(p_inspection_resp) != '' THEN 15 ELSE 0 END) +
        (CASE WHEN p_is_claimed = true THEN 10 ELSE 0 END) +
        (CASE WHEN p_profile_tier IS NOT NULL THEN 15 ELSE 0 END)
    )
$$;

-- Backfill using the canonical function so existing rows reflect the correct score.
UPDATE care_providers
SET profile_completeness = calculate_profile_completeness(
    profile_description,
    profile_photos,
    virtual_tour_url,
    inspection_response,
    is_claimed,
    profile_tier
);
