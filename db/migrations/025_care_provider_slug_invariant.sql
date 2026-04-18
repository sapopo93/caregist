-- Keep provider profile URLs resolvable by preventing empty or sentinel slugs.
-- Apply after the production slug backfill has cleaned existing rows.

ALTER TABLE care_providers
  ADD CONSTRAINT care_providers_slug_nonempty
  CHECK (
    slug IS NOT NULL
    AND btrim(slug) <> ''
    AND lower(btrim(slug)) NOT IN ('null', 'undefined')
  ) NOT VALID;

ALTER TABLE care_providers
  VALIDATE CONSTRAINT care_providers_slug_nonempty;
