-- Provider profile analytics records canonical slugs, not only short CQC IDs.
-- TrackRequest permits slugs up to 300 characters, so VARCHAR(20) silently drops
-- ordinary profile-view events. TEXT keeps the analytics write non-lossy.
ALTER TABLE analytics_events
  ALTER COLUMN provider_id TYPE TEXT;
