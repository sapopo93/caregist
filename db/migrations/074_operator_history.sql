-- Operator History (stage 1): additive support only. Nothing here changes or
-- removes an existing column, row or constraint.
--
-- 1. An owner-maintained list of operators whose identity is in dispute. A row
--    with resolved_at IS NULL makes the Operator History builder refuse that
--    Provider ID (code identity_disputed) until the row is resolved.
-- 2. An index on the CQC Provider ID carried inside each stored edition
--    location's payload, so a name held for a Provider ID can be found without
--    scanning a whole edition. The edition tables stay immutable.
-- 3. An index on care_providers.provider_id so one operator's locations are
--    found without scanning the register.

CREATE TABLE IF NOT EXISTS operator_identity_disputes (
  id BIGSERIAL PRIMARY KEY,
  provider_id VARCHAR(20) NOT NULL CHECK (provider_id = BTRIM(provider_id) AND provider_id <> ''),
  reason TEXT NOT NULL CHECK (reason = BTRIM(reason) AND char_length(reason) BETWEEN 1 AND 300),
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  CHECK (resolved_at IS NULL OR resolved_at >= recorded_at)
);

CREATE INDEX IF NOT EXISTS operator_identity_disputes_open
  ON operator_identity_disputes (provider_id) WHERE resolved_at IS NULL;

COMMENT ON TABLE operator_identity_disputes IS
  'Operators whose CQC Provider ID binding is disputed. An open row blocks Operator History for that Provider ID.';

CREATE INDEX IF NOT EXISTS territory_brief_source_provider
  ON territory_brief_source_locations ((payload->>'providerId'), edition_id);

CREATE INDEX IF NOT EXISTS idx_care_providers_provider_id
  ON care_providers (provider_id);
