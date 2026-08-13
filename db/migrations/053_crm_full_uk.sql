-- Lean UK CRM expansion: compliant email campaigns, call recording metadata,
-- provider-neutral call intelligence, and reporting evidence.
-- All features remain fail-closed behind application configuration.

ALTER TABLE crm_contacts
  ADD COLUMN market_code CHAR(2) NOT NULL DEFAULT 'GB'
    CHECK (market_code = 'GB'),
  ADD COLUMN subscriber_type TEXT NOT NULL DEFAULT 'unknown'
    CHECK (subscriber_type IN ('corporate', 'sole_trader', 'partnership', 'individual', 'unknown')),
  ADD COLUMN email_marketing_basis TEXT NOT NULL DEFAULT 'none'
    CHECK (email_marketing_basis IN ('corporate_subscriber', 'consent', 'soft_opt_in', 'none')),
  ADD COLUMN email_marketing_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN email_marketing_recorded_at TIMESTAMPTZ,
  ADD COLUMN phone_screening_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (phone_screening_status IN ('unknown', 'clear', 'tps', 'ctps', 'consent_override')),
  ADD COLUMN phone_screening_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN phone_screened_at TIMESTAMPTZ;

ALTER TABLE crm_call_sessions
  ADD COLUMN dispositioned_at TIMESTAMPTZ,
  ADD COLUMN recording_notice_version VARCHAR(80);

ALTER TABLE crm_suppressions DROP CONSTRAINT crm_suppressions_reason_check;
ALTER TABLE crm_suppressions ADD CONSTRAINT crm_suppressions_reason_check CHECK (
  reason IN (
    'contact_objection', 'tps', 'ctps', 'invalid', 'legal', 'manual',
    'unsubscribe', 'bounce', 'complaint', 'provider_suppressed'
  )
);

ALTER TABLE crm_activities DROP CONSTRAINT crm_activities_activity_type_check;
ALTER TABLE crm_activities ADD CONSTRAINT crm_activities_activity_type_check CHECK (
  activity_type IN (
    'contact_created', 'note', 'task_created', 'task_completed', 'call',
    'deal_created', 'deal_stage_changed', 'suppressed',
    'email_campaign_queued', 'email_unsubscribed', 'recording_available',
    'email_bounced', 'email_complained', 'phone_screened',
    'ai_evaluation_completed'
  )
);

CREATE TABLE crm_phone_screening_imports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  imported_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  source TEXT NOT NULL CHECK (source IN ('tps_ctps_licence', 'approved_provider')),
  source_reference VARCHAR(500) NOT NULL,
  file_name VARCHAR(255) NOT NULL,
  file_sha256 CHAR(64) NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
  row_count INTEGER NOT NULL CHECK (row_count >= 0),
  matched_count INTEGER NOT NULL CHECK (matched_count >= 0),
  clear_count INTEGER NOT NULL CHECK (clear_count >= 0),
  suppressed_count INTEGER NOT NULL CHECK (suppressed_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crm_phone_screening_imports_org
  ON crm_phone_screening_imports (organization_id, created_at DESC);

CREATE TABLE crm_phone_screening_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  import_id UUID NOT NULL REFERENCES crm_phone_screening_imports(id) ON DELETE CASCADE,
  phone_hmac CHAR(64) NOT NULL CHECK (phone_hmac ~ '^[0-9a-f]{64}$'),
  status TEXT NOT NULL CHECK (status IN ('clear', 'tps', 'ctps')),
  source TEXT NOT NULL CHECK (source IN ('tps_ctps_licence', 'approved_provider')),
  source_reference VARCHAR(500) NOT NULL,
  screened_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (organization_id, phone_hmac)
);
CREATE INDEX idx_crm_phone_screening_cache_import
  ON crm_phone_screening_cache (organization_id, import_id);

CREATE TABLE crm_phone_screening_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE RESTRICT,
  screened_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  import_id UUID REFERENCES crm_phone_screening_imports(id) ON DELETE SET NULL,
  phone_e164 VARCHAR(20) NOT NULL CHECK (phone_e164 ~ '^\+[1-9][0-9]{7,14}$'),
  status TEXT NOT NULL CHECK (status IN ('clear', 'tps', 'ctps', 'consent_override')),
  source TEXT NOT NULL CHECK (source IN ('tps_ctps_licence', 'approved_provider', 'specific_consent')),
  source_reference VARCHAR(500) NOT NULL,
  screened_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crm_phone_screening_contact
  ON crm_phone_screening_events (organization_id, contact_id, screened_at DESC);

ALTER TABLE pending_emails
  ADD COLUMN provider_message_id VARCHAR(255);
CREATE UNIQUE INDEX uq_pending_emails_provider_message
  ON pending_emails (provider_message_id)
  WHERE provider_message_id IS NOT NULL;

CREATE TABLE crm_email_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  approved_by_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
  name VARCHAR(160) NOT NULL,
  subject VARCHAR(500) NOT NULL,
  html_body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'queued', 'sending', 'completed', 'cancelled')),
  recipient_count INTEGER NOT NULL DEFAULT 0 CHECK (recipient_count >= 0),
  scheduled_at TIMESTAMPTZ,
  launched_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crm_email_campaigns_org_created
  ON crm_email_campaigns (organization_id, created_at DESC);

CREATE TABLE crm_email_deliveries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  campaign_id UUID NOT NULL REFERENCES crm_email_campaigns(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE RESTRICT,
  queued_email_id INTEGER REFERENCES pending_emails(id) ON DELETE SET NULL,
  recipient_email VARCHAR(320) NOT NULL,
  unsubscribe_token_hash CHAR(64) NOT NULL UNIQUE
    CHECK (unsubscribe_token_hash ~ '^[0-9a-f]{64}$'),
  queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  delivered_at TIMESTAMPTZ,
  failed_at TIMESTAMPTZ,
  bounced_at TIMESTAMPTZ,
  complained_at TIMESTAMPTZ,
  last_event_type VARCHAR(80),
  last_event_at TIMESTAMPTZ,
  unsubscribed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (campaign_id, contact_id)
);
CREATE INDEX idx_crm_email_deliveries_campaign
  ON crm_email_deliveries (organization_id, campaign_id, created_at DESC);

CREATE TABLE crm_email_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  delivery_id UUID NOT NULL REFERENCES crm_email_deliveries(id) ON DELETE CASCADE,
  provider_event_id VARCHAR(255) NOT NULL UNIQUE,
  event_type VARCHAR(80) NOT NULL,
  occurred_at TIMESTAMPTZ,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crm_email_events_delivery
  ON crm_email_events (organization_id, delivery_id, received_at DESC);

CREATE TABLE crm_recordings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  call_session_id UUID NOT NULL UNIQUE REFERENCES crm_call_sessions(id) ON DELETE RESTRICT,
  twilio_recording_sid VARCHAR(40) NOT NULL UNIQUE,
  storage_provider TEXT NOT NULL DEFAULT 's3_compatible'
    CHECK (storage_provider = 's3_compatible'),
  object_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'uploading', 'ready', 'deleting', 'error', 'deleted')),
  content_type VARCHAR(100),
  byte_size BIGINT CHECK (byte_size IS NULL OR byte_size >= 0),
  sha256 CHAR(64) CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'),
  duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
  source_deleted_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL,
  deleted_at TIMESTAMPTZ,
  error_code VARCHAR(80),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  processing_started_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK ((status IN ('queued', 'uploading', 'error')) OR object_key IS NOT NULL)
);
CREATE INDEX idx_crm_recordings_expiry
  ON crm_recordings (status, expires_at);
CREATE INDEX idx_crm_recordings_org_created
  ON crm_recordings (organization_id, created_at DESC);

CREATE TABLE crm_call_intelligence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  call_session_id UUID NOT NULL UNIQUE REFERENCES crm_call_sessions(id) ON DELETE RESTRICT,
  recording_id UUID NOT NULL UNIQUE REFERENCES crm_recordings(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'purged')),
  transcript TEXT,
  summary TEXT,
  evaluation JSONB,
  transcription_provider VARCHAR(80),
  transcription_model VARCHAR(160),
  evaluation_provider VARCHAR(80),
  evaluation_model VARCHAR(160),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  error_code VARCHAR(80),
  processing_started_at TIMESTAMPTZ,
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_crm_call_intelligence_queue
  ON crm_call_intelligence (status, created_at);
CREATE INDEX idx_crm_call_intelligence_org
  ON crm_call_intelligence (organization_id, created_at DESC);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'crm_phone_screening_imports', 'crm_phone_screening_cache', 'crm_phone_screening_events',
    'crm_email_campaigns', 'crm_email_deliveries', 'crm_email_events',
    'crm_recordings', 'crm_call_intelligence'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (caregist_is_organization_member(organization_id)) WITH CHECK (caregist_is_organization_member(organization_id))',
      table_name || '_tenant_policy', table_name
    );
  END LOOP;
END
$$;

CREATE POLICY crm_recordings_twilio_policy ON crm_recordings
  USING (current_setting('caregist.worker', TRUE) = 'twilio')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_phone_screening_cache_twilio_policy ON crm_phone_screening_cache
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_intelligence_worker_policy ON crm_call_intelligence
  USING (current_setting('caregist.worker', TRUE) IN ('crm_ai', 'crm_retention'))
  WITH CHECK (current_setting('caregist.worker', TRUE) IN ('crm_ai', 'crm_retention'));
CREATE POLICY crm_intelligence_twilio_policy ON crm_call_intelligence
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_recordings_worker_policy ON crm_recordings
  USING (current_setting('caregist.worker', TRUE) IN ('crm_ai', 'crm_retention', 'crm_recording_ingest'))
  WITH CHECK (current_setting('caregist.worker', TRUE) IN ('crm_ai', 'crm_retention', 'crm_recording_ingest'));
CREATE POLICY crm_call_sessions_ai_policy ON crm_call_sessions
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_ai');
CREATE POLICY crm_activities_ai_policy ON crm_activities
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) IN ('crm_ai', 'crm_recording_ingest'));
CREATE POLICY crm_call_sessions_recording_ingest_policy ON crm_call_sessions
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_recording_ingest');
CREATE POLICY crm_intelligence_recording_ingest_policy ON crm_call_intelligence
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_recording_ingest');
CREATE POLICY crm_call_sessions_retention_policy ON crm_call_sessions
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_retention');
CREATE POLICY crm_email_deliveries_unsubscribe_select_policy ON crm_email_deliveries
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_unsubscribe');
CREATE POLICY crm_email_deliveries_unsubscribe_update_policy ON crm_email_deliveries
  FOR UPDATE USING (current_setting('caregist.worker', TRUE) = 'crm_unsubscribe')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_unsubscribe');
CREATE POLICY crm_contacts_unsubscribe_policy ON crm_contacts
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_unsubscribe');
CREATE POLICY crm_suppressions_unsubscribe_policy ON crm_suppressions
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_unsubscribe');
CREATE POLICY crm_activities_unsubscribe_policy ON crm_activities
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_unsubscribe');
CREATE POLICY crm_email_events_webhook_policy ON crm_email_events
  USING (current_setting('caregist.worker', TRUE) = 'crm_email_webhook')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_email_webhook');
CREATE POLICY crm_email_deliveries_webhook_select_policy ON crm_email_deliveries
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_email_webhook');
CREATE POLICY crm_email_deliveries_webhook_update_policy ON crm_email_deliveries
  FOR UPDATE USING (current_setting('caregist.worker', TRUE) = 'crm_email_webhook')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_email_webhook');
CREATE POLICY crm_contacts_email_webhook_policy ON crm_contacts
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_email_webhook');
CREATE POLICY crm_suppressions_email_webhook_policy ON crm_suppressions
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_email_webhook');
CREATE POLICY crm_activities_email_webhook_policy ON crm_activities
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_email_webhook');
CREATE POLICY crm_email_campaigns_maintenance_policy ON crm_email_campaigns
  FOR UPDATE USING (current_setting('caregist.worker', TRUE) = 'crm_campaigns')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'crm_campaigns');
CREATE POLICY crm_email_deliveries_maintenance_policy ON crm_email_deliveries
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'crm_campaigns');

COMMENT ON TABLE crm_recordings IS
  'Private recording metadata only. Audio is stored in encrypted S3-compatible object storage and deleted after 30 days.';
COMMENT ON TABLE crm_call_intelligence IS
  'AI output is advisory and requires human review; it must not be used for solely automated employment decisions.';
COMMENT ON COLUMN crm_contacts.email_marketing_evidence IS
  'Minimal evidence supporting the recorded PECR marketing basis; unknown contacts are ineligible for campaigns.';
