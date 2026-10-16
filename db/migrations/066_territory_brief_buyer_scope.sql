-- Private, versioned buyer scope for the Territory Opportunity Brief.
--
-- Additive only. territory_brief_orders (migration 060) is not altered, so every
-- existing order, its Stripe metadata and its fulfilment path are unchanged. An
-- order that carries buyer rules has one row here per scope version; an order
-- without rules has none and behaves exactly as before.
--
-- Stripe receives only scope_versions.id as an opaque reference. The objective
-- text and the exclusion identifiers never leave this database.
--
-- Exclusions hold CQC identifiers only (provider "1-..." / location "1-..."),
-- never names. They are deleted after the agreed correction period; the scope
-- row, its hash and the counts stay, so the order can still evidence what rules
-- applied without keeping the list.

CREATE TABLE IF NOT EXISTS territory_brief_scope_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES territory_brief_orders(id) ON DELETE RESTRICT,
  version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
  supersedes_version INTEGER,
  rule_version INTEGER NOT NULL DEFAULT 1 CHECK (rule_version >= 1),
  buyer_objective TEXT CHECK (
    buyer_objective IS NULL
    OR (buyer_objective = BTRIM(buyer_objective) AND char_length(buyer_objective) BETWEEN 10 AND 300)
  ),
  provider_exclusion_count INTEGER NOT NULL DEFAULT 0 CHECK (provider_exclusion_count BETWEEN 0 AND 500),
  location_exclusion_count INTEGER NOT NULL DEFAULT 0 CHECK (location_exclusion_count BETWEEN 0 AND 500),
  -- sha256 over the canonical rule JSON, so the frozen rules can be evidenced
  -- after the exclusion rows are purged.
  scope_sha256 CHAR(64) NOT NULL CHECK (scope_sha256 ~ '^[0-9a-f]{64}$'),
  exclusions_purge_after TIMESTAMPTZ,
  exclusions_purged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (order_id, version),
  CHECK (supersedes_version IS NULL OR supersedes_version < version)
);

CREATE INDEX IF NOT EXISTS territory_brief_scope_versions_purge
  ON territory_brief_scope_versions (exclusions_purge_after)
  WHERE exclusions_purge_after IS NOT NULL AND exclusions_purged_at IS NULL;

CREATE TABLE IF NOT EXISTS territory_brief_scope_exclusions (
  scope_version_id UUID NOT NULL REFERENCES territory_brief_scope_versions(id) ON DELETE CASCADE,
  id_kind TEXT NOT NULL CHECK (id_kind IN ('provider', 'location')),
  cqc_id TEXT NOT NULL CHECK (cqc_id ~ '^1-[0-9]{5,12}$'),
  PRIMARY KEY (scope_version_id, id_kind, cqc_id)
);

COMMENT ON TABLE territory_brief_scope_exclusions IS
  'Buyer exclusion identifiers for one scope version. Private to the order. Deleted after the correction period; never logged, never sent to Stripe, never shown in output.';

-- A scope version is frozen. Only the retention columns may change after insert,
-- and an amendment is a new row with a higher version, not an edit.
CREATE OR REPLACE FUNCTION prevent_territory_brief_scope_mutation()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'territory_brief_scope_versions rows are retained as evidence';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.order_id IS DISTINCT FROM OLD.order_id
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.supersedes_version IS DISTINCT FROM OLD.supersedes_version
     OR NEW.rule_version IS DISTINCT FROM OLD.rule_version
     OR NEW.buyer_objective IS DISTINCT FROM OLD.buyer_objective
     OR NEW.provider_exclusion_count IS DISTINCT FROM OLD.provider_exclusion_count
     OR NEW.location_exclusion_count IS DISTINCT FROM OLD.location_exclusion_count
     OR NEW.scope_sha256 IS DISTINCT FROM OLD.scope_sha256
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'territory_brief_scope_versions is frozen once written; add a new version instead';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS territory_brief_scope_versions_frozen ON territory_brief_scope_versions;
CREATE TRIGGER territory_brief_scope_versions_frozen
BEFORE UPDATE OR DELETE ON territory_brief_scope_versions
FOR EACH ROW EXECUTE FUNCTION prevent_territory_brief_scope_mutation();
