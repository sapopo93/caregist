-- Durable CQC -> TPSCheck -> CRM automation. The global application flag and
-- per-organisation setting are both required before the worker can run.

ALTER TABLE crm_contacts DROP CONSTRAINT crm_contacts_phone_screening_status_check;
ALTER TABLE crm_contacts ADD CONSTRAINT crm_contacts_phone_screening_status_check CHECK (
  phone_screening_status IN ('unknown', 'clear', 'tps', 'ctps', 'invalid', 'consent_override')
);

ALTER TABLE crm_phone_screening_cache DROP CONSTRAINT crm_phone_screening_cache_status_check;
ALTER TABLE crm_phone_screening_cache ADD CONSTRAINT crm_phone_screening_cache_status_check CHECK (
  status IN ('clear', 'tps', 'ctps', 'invalid')
);

ALTER TABLE crm_phone_screening_events DROP CONSTRAINT crm_phone_screening_events_status_check;
ALTER TABLE crm_phone_screening_events ADD CONSTRAINT crm_phone_screening_events_status_check CHECK (
  status IN ('clear', 'tps', 'ctps', 'invalid', 'consent_override')
);

CREATE TABLE crm_tps_automation_settings (
  organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  assigned_user_id INTEGER NOT NULL,
  configured_by_user_id INTEGER NOT NULL,
  registered_from DATE NOT NULL,
  filter_config JSONB NOT NULL DEFAULT '{}'::jsonb,
  max_monthly_checks INTEGER NOT NULL DEFAULT 10000
    CHECK (max_monthly_checks BETWEEN 1 AND 10000),
  per_run_limit INTEGER NOT NULL DEFAULT 50
    CHECK (per_run_limit BETWEEN 1 AND 50),
  last_run_at TIMESTAMPTZ,
  last_success_at TIMESTAMPTZ,
  last_error VARCHAR(500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_crm_tps_settings_assignee_member
    FOREIGN KEY (organization_id, assigned_user_id)
    REFERENCES organization_members (organization_id, user_id),
  CONSTRAINT fk_crm_tps_settings_configurer_member
    FOREIGN KEY (organization_id, configured_by_user_id)
    REFERENCES organization_members (organization_id, user_id)
);

CREATE TABLE crm_tps_screening_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id VARCHAR(20) NOT NULL REFERENCES care_providers(id) ON DELETE CASCADE,
  contact_id UUID,
  phone_e164 VARCHAR(20) CHECK (
    phone_e164 IS NULL OR phone_e164 ~ '^\+[1-9][0-9]{7,14}$'
  ),
  status TEXT NOT NULL DEFAULT 'queued' CHECK (
    status IN ('queued', 'processing', 'retryable', 'completed', 'review_required')
  ),
  screening_status TEXT CHECK (
    screening_status IS NULL OR screening_status IN ('clear', 'tps', 'ctps', 'invalid')
  ),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  lease_token UUID,
  lease_expires_at TIMESTAMPTZ,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  screened_at TIMESTAMPTZ,
  provider_reference VARCHAR(500),
  result_sha256 CHAR(64) CHECK (
    result_sha256 IS NULL OR result_sha256 ~ '^[0-9a-f]{64}$'
  ),
  result_payload JSONB,
  last_http_status INTEGER CHECK (
    last_http_status IS NULL OR last_http_status BETWEEN 100 AND 599
  ),
  last_error VARCHAR(500),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, provider_id),
  UNIQUE (organization_id, id),
  CONSTRAINT fk_crm_tps_job_contact_tenant
    FOREIGN KEY (organization_id, contact_id)
    REFERENCES crm_contacts (organization_id, id)
);
CREATE INDEX idx_crm_tps_jobs_claim
  ON crm_tps_screening_jobs (status, next_attempt_at, created_at);
CREATE INDEX idx_crm_tps_jobs_org_screened
  ON crm_tps_screening_jobs (organization_id, screened_at DESC);

CREATE TABLE crm_tps_usage_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  job_id UUID NOT NULL,
  request_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  response_received_at TIMESTAMPTZ,
  outcome TEXT NOT NULL DEFAULT 'started' CHECK (
    outcome IN ('started', 'result', 'ambiguous')
  ),
  screening_status TEXT CHECK (
    screening_status IS NULL OR screening_status IN ('clear', 'tps', 'ctps', 'invalid')
  ),
  result_sha256 CHAR(64) CHECK (
    result_sha256 IS NULL OR result_sha256 ~ '^[0-9a-f]{64}$'
  ),
  http_status INTEGER CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_crm_tps_usage_job_tenant
    FOREIGN KEY (organization_id, job_id)
    REFERENCES crm_tps_screening_jobs (organization_id, id) ON DELETE CASCADE
);
CREATE INDEX idx_crm_tps_usage_org_checked
  ON crm_tps_usage_attempts (organization_id, request_started_at DESC);

ALTER TABLE crm_tps_automation_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_tps_automation_settings FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_tps_settings_tenant_policy ON crm_tps_automation_settings
  USING (caregist_is_organization_member(organization_id))
  WITH CHECK (caregist_is_organization_member(organization_id));
CREATE POLICY crm_tps_settings_worker_policy ON crm_tps_automation_settings
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_tps_settings_health_policy ON crm_tps_automation_settings
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_health');

ALTER TABLE crm_tps_screening_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_tps_screening_jobs FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_tps_jobs_tenant_policy ON crm_tps_screening_jobs
  USING (caregist_is_organization_member(organization_id))
  WITH CHECK (caregist_is_organization_member(organization_id));
CREATE POLICY crm_tps_jobs_worker_policy ON crm_tps_screening_jobs
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_tps_jobs_health_policy ON crm_tps_screening_jobs
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_health');

ALTER TABLE crm_tps_usage_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_tps_usage_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY crm_tps_usage_tenant_policy ON crm_tps_usage_attempts
  USING (caregist_is_organization_member(organization_id))
  WITH CHECK (caregist_is_organization_member(organization_id));
CREATE POLICY crm_tps_usage_worker_policy ON crm_tps_usage_attempts
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_tps_usage_health_policy ON crm_tps_usage_attempts
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_health');

CREATE POLICY crm_contacts_tps_worker_policy ON crm_contacts
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_companies_tps_worker_policy ON crm_companies
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_suppressions_tps_worker_policy ON crm_suppressions
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_screening_imports_tps_worker_policy ON crm_phone_screening_imports
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_screening_cache_tps_worker_policy ON crm_phone_screening_cache
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_screening_events_tps_worker_policy ON crm_phone_screening_events
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');
CREATE POLICY crm_activities_tps_worker_policy ON crm_activities
  USING (current_setting('caregist.worker', TRUE) = 'crm_tps')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_tps');

COMMENT ON TABLE crm_tps_screening_jobs IS
  'Durable idempotent CQC-to-TPSCheck work queue; unknown outcomes never become callable.';
