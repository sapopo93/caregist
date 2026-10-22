ALTER TABLE care_providers DROP COLUMN IF EXISTS file_rating_source_sha256;
ALTER TABLE care_providers DROP COLUMN IF EXISTS file_rating_source;
ALTER TABLE care_providers DROP COLUMN IF EXISTS file_overall_rating_date;
ALTER TABLE care_providers DROP COLUMN IF EXISTS file_overall_rating;
