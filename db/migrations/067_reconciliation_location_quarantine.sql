-- Persist operator-reviewed CQC detail failures so they do not block every
-- future authoritative directory reconciliation. Quarantined locations stay
-- ACTIVE and remain visible in each batch's deactivation_confirmation record.
CREATE TABLE IF NOT EXISTS reconciliation_quarantined_locations (
    location_id TEXT PRIMARY KEY,
    source_batch_id UUID REFERENCES reconciliation_batches(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    last_error TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS reconciliation_quarantine_unresolved_idx
    ON reconciliation_quarantined_locations (location_id)
    WHERE resolved_at IS NULL;

-- 2026-10-18 operator-reviewed quarantine. The read-only detail probe at
-- 2026-10-18T01:06:48Z returned HTTP 404 for each id; keep the records ACTIVE
-- until CQC explains or restores the detail endpoint. These rows are exceptions,
-- not evidence of deregistration and must never trigger deactivation.
INSERT INTO reconciliation_quarantined_locations
    (location_id, reason, last_error)
VALUES
    ('1-29238634315', 'operator_quarantine_pending_cqc_investigation', 'Read-only detail probe returned HTTP 404 at 2026-10-18T01:06:48Z'),
    ('1-29608453477', 'operator_quarantine_pending_cqc_investigation', 'Read-only detail probe returned HTTP 404 at 2026-10-18T01:06:48Z'),
    ('1-3618483402', 'operator_quarantine_pending_cqc_investigation', 'Read-only detail probe returned HTTP 404 at 2026-10-18T01:06:48Z')
ON CONFLICT (location_id) DO UPDATE SET
    reason = EXCLUDED.reason,
    last_error = EXCLUDED.last_error,
    updated_at = NOW();
