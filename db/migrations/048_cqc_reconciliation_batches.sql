-- Immutable, resumable CQC reconciliation control state.

CREATE TABLE IF NOT EXISTS cqc_reconciliation_batches (
  id UUID PRIMARY KEY,
  pipeline_run_id BIGINT NOT NULL UNIQUE REFERENCES pipeline_runs(id),
  status TEXT NOT NULL CHECK (status IN ('prepared', 'running', 'failed', 'completed')),
  source_uri TEXT NOT NULL,
  source_published_at DATE NOT NULL,
  source_retrieved_at TIMESTAMPTZ NOT NULL,
  source_checksum_sha256 CHAR(64) NOT NULL CHECK (source_checksum_sha256 ~ '^[0-9a-f]{64}$'),
  manifest_checksum_sha256 CHAR(64) NOT NULL CHECK (manifest_checksum_sha256 ~ '^[0-9a-f]{64}$'),
  manifest JSONB NOT NULL,
  source_count INT NOT NULL CHECK (source_count > 0),
  current_count INT NOT NULL CHECK (current_count >= 0),
  intersection_count INT NOT NULL CHECK (intersection_count >= 0),
  addition_count INT NOT NULL CHECK (addition_count >= 0),
  reactivation_count INT NOT NULL CHECK (reactivation_count >= 0),
  deactivation_count INT NOT NULL CHECK (deactivation_count >= 0),
  deactivation_ids_sha256 CHAR(64) NOT NULL CHECK (deactivation_ids_sha256 ~ '^[0-9a-f]{64}$'),
  shard_count INT NOT NULL CHECK (shard_count > 0),
  records_inserted INT NOT NULL DEFAULT 0,
  records_updated INT NOT NULL DEFAULT 0,
  records_unchanged INT NOT NULL DEFAULT 0,
  records_deactivated INT NOT NULL DEFAULT 0,
  ledger_events_inserted INT NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  CHECK (intersection_count + addition_count + reactivation_count = source_count),
  CHECK (manifest->>'batchId' = id::text),
  CHECK (manifest->>'manifestChecksumSha256' = manifest_checksum_sha256::text)
);

CREATE TABLE IF NOT EXISTS cqc_reconciliation_shards (
  batch_id UUID NOT NULL REFERENCES cqc_reconciliation_batches(id) ON DELETE RESTRICT,
  shard_index INT NOT NULL CHECK (shard_index >= 0),
  status TEXT NOT NULL CHECK (status IN ('running', 'failed', 'completed')),
  manifest_checksum_sha256 CHAR(64) NOT NULL CHECK (manifest_checksum_sha256 ~ '^[0-9a-f]{64}$'),
  expected_count INT NOT NULL CHECK (expected_count >= 0),
  next_offset INT NOT NULL DEFAULT 0 CHECK (next_offset >= 0),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  error_message TEXT,
  PRIMARY KEY (batch_id, shard_index),
  CHECK (next_offset <= expected_count)
);

CREATE TABLE IF NOT EXISTS cqc_reconciliation_records (
  batch_id UUID NOT NULL REFERENCES cqc_reconciliation_batches(id) ON DELETE RESTRICT,
  location_id VARCHAR(20) NOT NULL,
  shard_index INT NOT NULL CHECK (shard_index >= 0),
  record JSONB NOT NULL,
  record_sha256 CHAR(64) NOT NULL CHECK (record_sha256 ~ '^[0-9a-f]{64}$'),
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (batch_id, location_id),
  FOREIGN KEY (batch_id, shard_index)
    REFERENCES cqc_reconciliation_shards(batch_id, shard_index) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_cqc_reconciliation_records_shard
  ON cqc_reconciliation_records (batch_id, shard_index, location_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cqc_one_active_batch
  ON cqc_reconciliation_batches ((1))
  WHERE status IN ('prepared', 'running');

CREATE INDEX IF NOT EXISTS idx_cqc_batches_status_created
  ON cqc_reconciliation_batches (status, created_at DESC);

CREATE OR REPLACE FUNCTION enforce_cqc_reconciliation_batch_plan_immutability()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IN ('completed', 'failed') AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'completed or failed CQC reconciliation batch is terminal';
  END IF;
  IF NEW.pipeline_run_id IS DISTINCT FROM OLD.pipeline_run_id
     OR NEW.source_uri IS DISTINCT FROM OLD.source_uri
     OR NEW.source_published_at IS DISTINCT FROM OLD.source_published_at
     OR NEW.source_retrieved_at IS DISTINCT FROM OLD.source_retrieved_at
     OR NEW.source_checksum_sha256 IS DISTINCT FROM OLD.source_checksum_sha256
     OR NEW.manifest_checksum_sha256 IS DISTINCT FROM OLD.manifest_checksum_sha256
     OR NEW.manifest IS DISTINCT FROM OLD.manifest
     OR NEW.source_count IS DISTINCT FROM OLD.source_count
     OR NEW.current_count IS DISTINCT FROM OLD.current_count
     OR NEW.intersection_count IS DISTINCT FROM OLD.intersection_count
     OR NEW.addition_count IS DISTINCT FROM OLD.addition_count
     OR NEW.reactivation_count IS DISTINCT FROM OLD.reactivation_count
     OR NEW.deactivation_count IS DISTINCT FROM OLD.deactivation_count
     OR NEW.deactivation_ids_sha256 IS DISTINCT FROM OLD.deactivation_ids_sha256
     OR NEW.shard_count IS DISTINCT FROM OLD.shard_count THEN
    RAISE EXCEPTION 'CQC reconciliation batch plan and manifest are immutable';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cqc_reconciliation_batch_plan_immutability
  ON cqc_reconciliation_batches;
CREATE TRIGGER trg_cqc_reconciliation_batch_plan_immutability
BEFORE UPDATE ON cqc_reconciliation_batches
FOR EACH ROW EXECUTE FUNCTION enforce_cqc_reconciliation_batch_plan_immutability();

CREATE OR REPLACE FUNCTION enforce_cqc_reconciliation_shard_index()
RETURNS TRIGGER AS $$
DECLARE
  configured_shards INT;
BEGIN
  SELECT shard_count INTO configured_shards
  FROM cqc_reconciliation_batches
  WHERE id = NEW.batch_id;

  IF configured_shards IS NULL OR NEW.shard_index >= configured_shards THEN
    RAISE EXCEPTION 'shard index % is outside batch shard count %',
      NEW.shard_index, configured_shards;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cqc_reconciliation_shard_index ON cqc_reconciliation_shards;
CREATE TRIGGER trg_cqc_reconciliation_shard_index
BEFORE INSERT OR UPDATE OF batch_id, shard_index ON cqc_reconciliation_shards
FOR EACH ROW EXECUTE FUNCTION enforce_cqc_reconciliation_shard_index();

CREATE OR REPLACE FUNCTION enforce_cqc_reconciliation_shard_control()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF NEW.batch_id IS DISTINCT FROM OLD.batch_id
       OR NEW.shard_index IS DISTINCT FROM OLD.shard_index
       OR NEW.manifest_checksum_sha256 IS DISTINCT FROM OLD.manifest_checksum_sha256
       OR NEW.expected_count IS DISTINCT FROM OLD.expected_count THEN
      RAISE EXCEPTION 'CQC reconciliation shard identity and plan are immutable';
    END IF;
    IF NEW.next_offset < OLD.next_offset THEN
      RAISE EXCEPTION 'CQC reconciliation shard checkpoint cannot regress';
    END IF;
    IF OLD.status = 'completed' AND (
         NEW.status IS DISTINCT FROM 'completed'
         OR NEW.next_offset IS DISTINCT FROM OLD.next_offset
         OR NEW.completed_at IS DISTINCT FROM OLD.completed_at
       ) THEN
      RAISE EXCEPTION 'completed CQC reconciliation shard is terminal';
    END IF;
  END IF;
  IF NEW.status = 'completed' AND NEW.next_offset <> NEW.expected_count THEN
    RAISE EXCEPTION 'completed CQC reconciliation shard requires full checkpoint coverage';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cqc_reconciliation_shard_control
  ON cqc_reconciliation_shards;
CREATE TRIGGER trg_cqc_reconciliation_shard_control
BEFORE INSERT OR UPDATE ON cqc_reconciliation_shards
FOR EACH ROW EXECUTE FUNCTION enforce_cqc_reconciliation_shard_control();

CREATE OR REPLACE FUNCTION enforce_cqc_reconciliation_record_immutability()
RETURNS TRIGGER AS $$
DECLARE
  shard_status TEXT;
  batch_status TEXT;
  expected_hash TEXT;
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE') THEN
    RAISE EXCEPTION 'CQC reconciliation records are immutable';
  END IF;

  SELECT s.status, b.status INTO shard_status, batch_status
  FROM cqc_reconciliation_shards s
  JOIN cqc_reconciliation_batches b ON b.id = s.batch_id
  WHERE s.batch_id = NEW.batch_id AND s.shard_index = NEW.shard_index;

  IF shard_status IS DISTINCT FROM 'running'
     OR batch_status NOT IN ('prepared', 'running') THEN
    RAISE EXCEPTION 'cannot stage into a non-running shard or inactive batch';
  END IF;
  IF NEW.record->>'id' IS DISTINCT FROM NEW.location_id THEN
    RAISE EXCEPTION 'staged payload identity does not match location_id';
  END IF;
  expected_hash := encode(digest(convert_to(NEW.record::text, 'UTF8'), 'sha256'), 'hex');
  IF NEW.record_sha256 IS DISTINCT FROM expected_hash THEN
    RAISE EXCEPTION 'staged payload hash does not match canonical JSONB';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cqc_reconciliation_record_immutability
  ON cqc_reconciliation_records;
CREATE TRIGGER trg_cqc_reconciliation_record_immutability
BEFORE INSERT OR UPDATE OR DELETE ON cqc_reconciliation_records
FOR EACH ROW EXECUTE FUNCTION enforce_cqc_reconciliation_record_immutability();
