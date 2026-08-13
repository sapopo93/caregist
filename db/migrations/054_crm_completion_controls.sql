-- Complete the additive UK CRM company, disposition and AI safety controls.

CREATE TABLE crm_companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  website VARCHAR(500),
  phone_e164 VARCHAR(20),
  address TEXT,
  notes TEXT,
  owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (BTRIM(name) <> ''),
  CHECK (phone_e164 IS NULL OR phone_e164 ~ '^\+[1-9][0-9]{7,14}$')
);
CREATE UNIQUE INDEX uq_crm_companies_org_name
  ON crm_companies (organization_id, LOWER(name));
CREATE INDEX idx_crm_companies_org_updated
  ON crm_companies (organization_id, updated_at DESC);

ALTER TABLE crm_companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY crm_companies_tenant_policy ON crm_companies
  USING (caregist_is_organization_member(organization_id))
  WITH CHECK (caregist_is_organization_member(organization_id));

ALTER TABLE crm_contacts ADD COLUMN company_id UUID REFERENCES crm_companies(id) ON DELETE SET NULL;

-- Preserve company associations already captured as names without changing the
-- existing contact display fallback.
INSERT INTO crm_companies (organization_id, name, created_by_user_id)
SELECT organization_id, BTRIM(company_name), MIN(created_by_user_id)
FROM crm_contacts
WHERE company_name IS NOT NULL AND BTRIM(company_name) <> ''
GROUP BY organization_id, BTRIM(company_name)
ON CONFLICT (organization_id, LOWER(name)) DO NOTHING;

UPDATE crm_contacts contact
SET company_id = company.id
FROM crm_companies company
WHERE company.organization_id = contact.organization_id
  AND LOWER(company.name) = LOWER(BTRIM(contact.company_name))
  AND contact.company_id IS NULL;

CREATE INDEX idx_crm_contacts_company ON crm_contacts (organization_id, company_id);

-- Repeated tenant identifiers are part of the integrity boundary, not merely
-- query helpers. Composite keys prevent any future worker or route defect from
-- linking a child row to another organisation's parent.
ALTER TABLE crm_contacts ADD CONSTRAINT uq_crm_contacts_org_id UNIQUE (organization_id, id);
ALTER TABLE crm_companies ADD CONSTRAINT uq_crm_companies_org_id UNIQUE (organization_id, id);
ALTER TABLE crm_phone_screening_imports ADD CONSTRAINT uq_crm_screening_imports_org_id UNIQUE (organization_id, id);
ALTER TABLE crm_email_campaigns ADD CONSTRAINT uq_crm_email_campaigns_org_id UNIQUE (organization_id, id);
ALTER TABLE crm_email_deliveries ADD CONSTRAINT uq_crm_email_deliveries_org_id UNIQUE (organization_id, id);
ALTER TABLE crm_recordings ADD CONSTRAINT uq_crm_recordings_org_id UNIQUE (organization_id, id);
ALTER TABLE crm_call_sessions ADD CONSTRAINT uq_crm_call_sessions_org_id UNIQUE (organization_id, id);

ALTER TABLE crm_contacts ADD CONSTRAINT fk_crm_contacts_company_tenant
  FOREIGN KEY (organization_id, company_id) REFERENCES crm_companies (organization_id, id);
ALTER TABLE crm_deals ADD CONSTRAINT fk_crm_deals_contact_tenant
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id);
ALTER TABLE crm_tasks ADD CONSTRAINT fk_crm_tasks_contact_tenant
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id);
ALTER TABLE crm_call_sessions ADD CONSTRAINT fk_crm_calls_contact_tenant
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id);
ALTER TABLE crm_activities ADD CONSTRAINT fk_crm_activities_contact_tenant
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id);
ALTER TABLE crm_phone_screening_cache ADD CONSTRAINT fk_crm_screening_cache_import_tenant
  FOREIGN KEY (organization_id, import_id)
  REFERENCES crm_phone_screening_imports (organization_id, id);
ALTER TABLE crm_phone_screening_events ADD CONSTRAINT fk_crm_screening_events_contact_tenant
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id);
ALTER TABLE crm_email_deliveries ADD CONSTRAINT fk_crm_deliveries_campaign_tenant
  FOREIGN KEY (organization_id, campaign_id) REFERENCES crm_email_campaigns (organization_id, id);
ALTER TABLE crm_email_deliveries ADD CONSTRAINT fk_crm_deliveries_contact_tenant
  FOREIGN KEY (organization_id, contact_id) REFERENCES crm_contacts (organization_id, id);
ALTER TABLE crm_email_events ADD CONSTRAINT fk_crm_email_events_delivery_tenant
  FOREIGN KEY (organization_id, delivery_id) REFERENCES crm_email_deliveries (organization_id, id);
ALTER TABLE crm_recordings ADD CONSTRAINT fk_crm_recordings_call_tenant
  FOREIGN KEY (organization_id, call_session_id) REFERENCES crm_call_sessions (organization_id, id);
ALTER TABLE crm_call_intelligence ADD CONSTRAINT fk_crm_intelligence_call_tenant
  FOREIGN KEY (organization_id, call_session_id) REFERENCES crm_call_sessions (organization_id, id);
ALTER TABLE crm_call_intelligence ADD CONSTRAINT fk_crm_intelligence_recording_tenant
  FOREIGN KEY (organization_id, recording_id) REFERENCES crm_recordings (organization_id, id);

ALTER TABLE crm_call_sessions
  ADD COLUMN disposition_group TEXT,
  ADD COLUMN callback_due_at TIMESTAMPTZ;
ALTER TABLE crm_call_sessions ADD CONSTRAINT crm_call_sessions_disposition_group_check CHECK (
  disposition_group IS NULL OR disposition_group IN ('no_contact', 'connected', 'callback', 'do_not_call')
);
ALTER TABLE crm_call_sessions ADD CONSTRAINT crm_call_sessions_callback_due_check CHECK (
  (disposition = 'callback_requested' AND callback_due_at IS NOT NULL)
  OR (disposition IS DISTINCT FROM 'callback_requested' AND callback_due_at IS NULL)
);

ALTER TABLE crm_call_intelligence
  ADD COLUMN redaction_summary JSONB,
  ADD COLUMN external_user_id CHAR(64),
  ADD COLUMN external_request_id VARCHAR(255),
  ADD COLUMN input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  ADD COLUMN output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  ADD COLUMN cache_hit_input_tokens INTEGER CHECK (
    cache_hit_input_tokens IS NULL OR cache_hit_input_tokens >= 0
  ),
  ADD COLUMN reserved_cost_usd NUMERIC(12, 8) NOT NULL DEFAULT 0 CHECK (reserved_cost_usd >= 0),
  ADD COLUMN actual_cost_usd NUMERIC(12, 8) CHECK (actual_cost_usd IS NULL OR actual_cost_usd >= 0),
  ADD COLUMN evaluation_latency_ms INTEGER CHECK (
    evaluation_latency_ms IS NULL OR evaluation_latency_ms >= 0
  );
ALTER TABLE crm_call_intelligence ADD CONSTRAINT crm_call_intelligence_external_user_check CHECK (
  external_user_id IS NULL OR external_user_id ~ '^[0-9a-f]{64}$'
);
CREATE POLICY crm_contacts_ai_policy ON crm_contacts
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_ai');
CREATE INDEX idx_crm_call_intelligence_monthly_cost
  ON crm_call_intelligence (created_at, actual_cost_usd);

CREATE TABLE crm_ai_usage_attempts (
  id BIGSERIAL PRIMARY KEY,
  intelligence_id UUID NOT NULL REFERENCES crm_call_intelligence(id) ON DELETE CASCADE,
  request_id VARCHAR(255),
  input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
  output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
  cache_hit_input_tokens INTEGER NOT NULL CHECK (cache_hit_input_tokens >= 0),
  cost_usd NUMERIC(12, 8) NOT NULL CHECK (cost_usd >= 0),
  schema_valid BOOLEAN NOT NULL,
  incurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crm_ai_usage_attempts_month
  ON crm_ai_usage_attempts (incurred_at, cost_usd);
ALTER TABLE crm_ai_usage_attempts ENABLE ROW LEVEL SECURITY;
CREATE POLICY crm_ai_usage_worker_policy ON crm_ai_usage_attempts
  USING (current_setting('caregist.worker', TRUE) = 'crm_ai')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_ai');
CREATE POLICY crm_ai_usage_health_policy ON crm_ai_usage_attempts
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_health');
CREATE POLICY crm_recordings_health_policy ON crm_recordings
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_health');

CREATE TABLE crm_worker_heartbeats (
  worker_name VARCHAR(80) PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('starting', 'idle', 'processing', 'error')),
  last_seen_at TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE crm_activities DROP CONSTRAINT crm_activities_activity_type_check;
ALTER TABLE crm_activities ADD CONSTRAINT crm_activities_activity_type_check CHECK (
  activity_type IN (
    'contact_created', 'note', 'task_created', 'task_completed',
    'call', 'deal_created', 'deal_stage_changed', 'suppressed',
    'email_campaign_queued', 'email_unsubscribed', 'recording_available',
    'email_bounced', 'email_complained', 'phone_screened',
    'ai_evaluation_completed'
  )
);

COMMENT ON COLUMN crm_call_intelligence.redaction_summary IS
  'Counts and integrity hashes proving the fail-closed redaction boundary; never contains redacted values.';
COMMENT ON COLUMN crm_call_intelligence.external_user_id IS
  'HMAC pseudonym sent to the external AI provider; never a CareGist user or contact identifier.';
COMMENT ON COLUMN crm_call_intelligence.actual_cost_usd IS
  'Cost derived from provider-reported token usage and configured prices.';

-- The application commonly connects as the schema owner. PostgreSQL table
-- owners otherwise bypass enabled RLS, so CRM isolation must be forced after
-- the data-preserving migration statements above have completed.
DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'crm_contacts', 'crm_companies', 'crm_deals', 'crm_tasks',
    'crm_suppressions', 'crm_call_sessions', 'crm_call_events', 'crm_activities',
    'crm_phone_screening_imports', 'crm_phone_screening_cache',
    'crm_phone_screening_events', 'crm_email_campaigns', 'crm_email_deliveries',
    'crm_email_events', 'crm_recordings', 'crm_call_intelligence',
    'crm_ai_usage_attempts'
  ] LOOP
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
  END LOOP;
END
$$;
