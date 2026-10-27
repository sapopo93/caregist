-- Immutable CQC evidence editions. Import in one transaction; never replace
-- records underneath a paid order. No cascade may erase its pinned evidence.
CREATE TABLE territory_brief_source_editions (
  id BIGSERIAL PRIMARY KEY,
  import_transaction BIGINT NOT NULL DEFAULT txid_current(),
  source_retrieved_at TIMESTAMPTZ NOT NULL,
  source_as_of DATE NOT NULL,
  locations_sha256 CHAR(64) NOT NULL CHECK (locations_sha256 ~ '^[0-9a-f]{64}$'),
  providers_sha256 CHAR(64) NOT NULL CHECK (providers_sha256 ~ '^[0-9a-f]{64}$'),
  location_count INTEGER NOT NULL CHECK (location_count > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (locations_sha256, providers_sha256)
);
CREATE TABLE territory_brief_source_locations (
  edition_id BIGINT NOT NULL REFERENCES territory_brief_source_editions(id) ON DELETE RESTRICT,
  location_id TEXT NOT NULL,
  local_authority TEXT NOT NULL,
  region TEXT NOT NULL,
  provider_name TEXT NOT NULL,
  payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
  -- The CareGist rating rule's result at import time (ratings file first, a
  -- newer CQC page check wins, API only for the file's gaps), frozen with the
  -- edition so a payment retry rebuilds the same Brief. applies = false means
  -- the file and page checks say nothing, so the payload's API rating stands;
  -- applies = true with a NULL rating means CQC's page shows none (withheld).
  rule_rating_applies BOOLEAN NOT NULL DEFAULT FALSE,
  rule_rating TEXT,
  rule_rating_date DATE,
  PRIMARY KEY (edition_id, location_id)
);
CREATE INDEX territory_brief_source_la ON territory_brief_source_locations(edition_id, lower(local_authority));
CREATE INDEX territory_brief_source_region ON territory_brief_source_locations(edition_id, lower(region));
ALTER TABLE territory_brief_orders ADD COLUMN source_edition_id BIGINT
  REFERENCES territory_brief_source_editions(id) ON DELETE RESTRICT;

CREATE FUNCTION territory_brief_source_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'Territory Brief source editions are immutable; import a new edition';
END;
$$;
CREATE TRIGGER territory_brief_editions_immutable BEFORE UPDATE OR DELETE
  ON territory_brief_source_editions FOR EACH ROW EXECUTE FUNCTION territory_brief_source_immutable();
CREATE TRIGGER territory_brief_locations_immutable BEFORE UPDATE OR DELETE
  ON territory_brief_source_locations FOR EACH ROW EXECUTE FUNCTION territory_brief_source_immutable();

-- Only the transaction that creates an edition may append its evidence.
CREATE FUNCTION territory_brief_source_insert_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM territory_brief_source_editions
                 WHERE id = NEW.edition_id AND import_transaction = txid_current()) THEN
    RAISE EXCEPTION 'Territory Brief source editions are sealed after import';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER territory_brief_locations_insert_guard BEFORE INSERT
  ON territory_brief_source_locations FOR EACH ROW EXECUTE FUNCTION territory_brief_source_insert_guard();
CREATE TRIGGER territory_brief_locations_no_truncate BEFORE TRUNCATE
  ON territory_brief_source_locations FOR EACH STATEMENT EXECUTE FUNCTION territory_brief_source_immutable();
CREATE TRIGGER territory_brief_editions_no_truncate BEFORE TRUNCATE
  ON territory_brief_source_editions FOR EACH STATEMENT EXECUTE FUNCTION territory_brief_source_immutable();
