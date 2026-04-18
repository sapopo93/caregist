-- Enforce provider slugs as required URL identifiers.
--
-- Runtime backfills are responsible for filling any legacy rows before this
-- migration runs. These guards fail loudly if production data regresses.

DO $$
DECLARE
  missing_slug_count INTEGER;
  duplicate_slug_count INTEGER;
BEGIN
  SELECT COUNT(*)
    INTO missing_slug_count
  FROM care_providers
  WHERE slug IS NULL OR btrim(slug) = '';

  IF missing_slug_count > 0 THEN
    RAISE EXCEPTION 'Cannot enforce care_providers.slug invariant: % rows have NULL or blank slugs', missing_slug_count;
  END IF;

  SELECT COUNT(*)
    INTO duplicate_slug_count
  FROM (
    SELECT slug
    FROM care_providers
    WHERE slug IS NOT NULL AND btrim(slug) <> ''
    GROUP BY slug
    HAVING COUNT(*) > 1
  ) duplicate_slugs;

  IF duplicate_slug_count > 0 THEN
    RAISE EXCEPTION 'Cannot enforce care_providers.slug invariant: % duplicate slug groups exist', duplicate_slug_count;
  END IF;
END
$$;

ALTER TABLE care_providers
  ADD CONSTRAINT care_providers_slug_not_blank
  CHECK (btrim(slug) <> '') NOT VALID;

ALTER TABLE care_providers
  VALIDATE CONSTRAINT care_providers_slug_not_blank;

ALTER TABLE care_providers
  ALTER COLUMN slug SET NOT NULL;
