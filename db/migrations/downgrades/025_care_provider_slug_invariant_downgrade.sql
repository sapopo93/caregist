-- Downgrade: 025_care_provider_slug_invariant
-- REVERSIBLE
-- Drops the CHECK constraint added on care_providers.slug.
-- Risk: rows with empty/sentinel slugs may re-appear after rollback;
-- ensure slug backfill is re-run if re-applying this migration.

ALTER TABLE care_providers
  DROP CONSTRAINT IF EXISTS care_providers_slug_nonempty;
