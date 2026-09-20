-- Reverses 062_provider_last_published_rating.sql exactly: both columns are
-- additive. overall_rating is untouched by the forward migration, so no data is
-- restored here.
ALTER TABLE care_providers DROP COLUMN IF EXISTS last_published_rating_date;
ALTER TABLE care_providers DROP COLUMN IF EXISTS last_published_rating;
