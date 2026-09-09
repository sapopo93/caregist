-- Provider-intelligence CRM extension. Additive and fail-closed.
-- Agents may insert proposals and evidence, but cannot update canonical CRM truth.

CREATE TYPE crm_evidence_state AS ENUM (
  'verified',
  'strong_source_backed_observation',
  'inferred',
  'conflicting',
  'weak_unverified',
  'requires_human_review'
);

ALTER TABLE crm_deals ADD CONSTRAINT uq_crm_deals_org_id UNIQUE (organization_id, id);

CREATE TABLE crm_referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  contact_id UUID,
  opportunity_id UUID,
  status TEXT NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'qualified', 'accepted', 'declined', 'placed', 'closed')),
  source TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, id),
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id),
  FOREIGN KEY (organization_id, opportunity_id) REFERENCES crm_deals (organization_id, id)
);

CREATE TABLE crm_placements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  referral_id UUID NOT NULL,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'confirmed', 'started', 'ended', 'cancelled')),
  start_date DATE,
  end_date DATE,
  value_pence BIGINT CHECK (value_pence IS NULL OR value_pence >= 0),
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, id),
  FOREIGN KEY (organization_id, referral_id) REFERENCES crm_referrals (organization_id, id),
  CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE TABLE crm_contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  opportunity_id UUID,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  title TEXT NOT NULL CHECK (BTRIM(title) <> ''),
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'signed', 'active', 'expired', 'terminated')),
  value_pence BIGINT CHECK (value_pence IS NULL OR value_pence >= 0),
  starts_on DATE,
  ends_on DATE,
  evidence_manifest JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  approved_by_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, id),
  FOREIGN KEY (organization_id, opportunity_id) REFERENCES crm_deals (organization_id, id),
  CHECK ((approved_at IS NULL) = (approved_by_user_id IS NULL)),
  CHECK (ends_on IS NULL OR starts_on IS NULL OR ends_on >= starts_on)
);

CREATE TABLE crm_commissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contract_id UUID NOT NULL,
  amount_pence BIGINT NOT NULL CHECK (amount_pence >= 0),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'earned', 'invoiced', 'paid', 'void')),
  earned_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, id),
  FOREIGN KEY (organization_id, contract_id) REFERENCES crm_contracts (organization_id, id)
);

CREATE TABLE crm_evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('provider', 'location', 'ownership_group', 'manager', 'contact', 'inspection', 'rating', 'referral', 'placement', 'opportunity', 'contract', 'commission', 'alert')),
  subject_id TEXT NOT NULL,
  field_name TEXT NOT NULL,
  observed_value JSONB NOT NULL,
  evidence_state crm_evidence_state NOT NULL,
  source_uri TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_sha256 CHAR(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
  observed_at TIMESTAMPTZ NOT NULL,
  retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by TEXT NOT NULL,
  independent_check JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, id),
  CHECK (evidence_state <> 'verified' OR independent_check IS NOT NULL)
);
CREATE UNIQUE INDEX uq_crm_evidence_observation
  ON crm_evidence (organization_id, subject_type, subject_id, field_name, source_sha256);

CREATE TABLE crm_enrichment_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('provider', 'company', 'contact', 'deal', 'task', 'referral', 'placement', 'contract', 'commission', 'alert')),
  target_id TEXT NOT NULL,
  proposed_changes JSONB NOT NULL CHECK (jsonb_typeof(proposed_changes) = 'object'),
  evidence_ids UUID[] NOT NULL DEFAULT '{}',
  evidence_state crm_evidence_state NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'accepted', 'rejected', 'superseded')),
  producer_model TEXT,
  reviewed_by_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
  reviewed_at TIMESTAMPTZ,
  review_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (evidence_state IN ('verified', 'strong_source_backed_observation', 'conflicting', 'requires_human_review')),
  CHECK ((reviewed_at IS NULL) = (reviewed_by_user_id IS NULL)),
  CHECK (status = 'pending_review' OR reviewed_at IS NOT NULL)
);
CREATE INDEX idx_crm_enrichment_review_queue
  ON crm_enrichment_proposals (organization_id, status, created_at);

CREATE TABLE crm_alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  evidence_id UUID,
  alert_type TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
  title TEXT NOT NULL,
  body TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  FOREIGN KEY (organization_id, evidence_id) REFERENCES crm_evidence (organization_id, id)
);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'crm_referrals', 'crm_placements', 'crm_contracts', 'crm_commissions',
    'crm_evidence', 'crm_enrichment_proposals', 'crm_alerts'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (caregist_is_organization_member(organization_id)) WITH CHECK (caregist_is_organization_member(organization_id))',
      table_name || '_tenant_policy', table_name
    );
  END LOOP;
END
$$;

-- The intelligence worker can append evidence and proposals only. It receives
-- no UPDATE policy on canonical CRM tables and no permission to accept proposals.
CREATE POLICY crm_evidence_intelligence_insert ON crm_evidence
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'provider_intelligence');
CREATE POLICY crm_proposals_intelligence_insert ON crm_enrichment_proposals
  FOR INSERT WITH CHECK (
    current_setting('caregist.worker', TRUE) = 'provider_intelligence'
    AND status = 'pending_review'
    AND reviewed_by_user_id IS NULL
    AND reviewed_at IS NULL
  );

COMMENT ON TABLE crm_enrichment_proposals IS
  'Agent suggestions only. Human review is required before canonical CRM records change.';
COMMENT ON COLUMN crm_enrichment_proposals.evidence_ids IS
  'Application validates that every ID belongs to this organization before insert.';
