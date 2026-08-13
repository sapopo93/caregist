-- Additive, tenant-isolated CRM and outbound calling foundation.
-- Calling remains fail-closed at the application layer until its Human Gate is enabled.

CREATE TABLE IF NOT EXISTS crm_contacts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  provider_id VARCHAR(20) REFERENCES care_providers(id) ON DELETE SET NULL,
  owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  first_name VARCHAR(120) NOT NULL DEFAULT '',
  last_name VARCHAR(120) NOT NULL DEFAULT '',
  job_title VARCHAR(160),
  company_name VARCHAR(255),
  email VARCHAR(320),
  phone_e164 VARCHAR(20),
  lifecycle_stage TEXT NOT NULL DEFAULT 'new' CHECK (
    lifecycle_stage IN (
      'new', 'assigned', 'attempting_contact', 'connected', 'qualified',
      'demo_booked', 'proposal_sent', 'negotiation', 'won', 'lost', 'suppressed'
    )
  ),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (email IS NOT NULL OR phone_e164 IS NOT NULL OR provider_id IS NOT NULL),
  CHECK (phone_e164 IS NULL OR phone_e164 ~ '^\+[1-9][0-9]{7,14}$')
);
CREATE INDEX IF NOT EXISTS idx_crm_contacts_org_updated
  ON crm_contacts (organization_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_crm_contacts_owner_stage
  ON crm_contacts (organization_id, owner_user_id, lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_crm_contacts_provider
  ON crm_contacts (organization_id, provider_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_contacts_org_phone
  ON crm_contacts (organization_id, phone_e164)
  WHERE phone_e164 IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_contacts_org_email
  ON crm_contacts (organization_id, LOWER(email))
  WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS crm_deals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
  owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  title VARCHAR(255) NOT NULL,
  stage TEXT NOT NULL DEFAULT 'new' CHECK (
    stage IN (
      'new', 'assigned', 'attempting_contact', 'connected', 'qualified',
      'demo_booked', 'proposal_sent', 'negotiation', 'won', 'lost', 'suppressed'
    )
  ),
  value_pence BIGINT NOT NULL DEFAULT 0 CHECK (value_pence >= 0),
  loss_reason VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  closed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_crm_deals_org_stage
  ON crm_deals (organization_id, stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_crm_deals_contact
  ON crm_deals (contact_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS crm_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
  assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  task_type TEXT NOT NULL CHECK (task_type IN ('call', 'email', 'follow_up', 'meeting', 'general')),
  title VARCHAR(255) NOT NULL,
  notes TEXT,
  due_at TIMESTAMPTZ NOT NULL,
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'completed', 'cancelled')),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crm_tasks_agent_queue
  ON crm_tasks (organization_id, assigned_user_id, status, due_at);
CREATE INDEX IF NOT EXISTS idx_crm_tasks_contact
  ON crm_tasks (contact_id, created_at DESC);

CREATE TABLE IF NOT EXISTS crm_suppressions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  phone_e164 VARCHAR(20),
  email VARCHAR(320),
  channel TEXT NOT NULL CHECK (channel IN ('call', 'email', 'all')),
  reason TEXT NOT NULL CHECK (reason IN ('contact_objection', 'tps', 'ctps', 'invalid', 'legal', 'manual')),
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (phone_e164 IS NOT NULL OR email IS NOT NULL),
  CHECK (phone_e164 IS NULL OR phone_e164 ~ '^\+[1-9][0-9]{7,14}$')
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_suppressions_phone_channel
  ON crm_suppressions (organization_id, phone_e164, channel)
  WHERE phone_e164 IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_suppressions_email_channel
  ON crm_suppressions (organization_id, LOWER(email), channel)
  WHERE email IS NOT NULL;

CREATE TABLE IF NOT EXISTS crm_call_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE RESTRICT,
  agent_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  authorization_token_hash CHAR(64) NOT NULL UNIQUE CHECK (authorization_token_hash ~ '^[0-9a-f]{64}$'),
  authorization_expires_at TIMESTAMPTZ NOT NULL,
  authorization_consumed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'authorized' CHECK (
    status IN ('authorized', 'initiated', 'ringing', 'in_progress', 'completed', 'busy', 'no_answer', 'failed', 'canceled')
  ),
  twilio_parent_call_sid VARCHAR(40),
  twilio_child_call_sid VARCHAR(40),
  last_sequence_number INTEGER NOT NULL DEFAULT -1,
  duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
  disposition TEXT CHECK (
    disposition IS NULL OR disposition IN (
      'connected', 'no_answer', 'busy', 'voicemail', 'wrong_number',
      'callback_requested', 'gatekeeper', 'qualified', 'not_interested',
      'do_not_call', 'meeting_booked', 'sale_completed'
    )
  ),
  notes TEXT,
  started_at TIMESTAMPTZ,
  answered_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crm_calls_org_created
  ON crm_call_sessions (organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crm_calls_contact
  ON crm_call_sessions (contact_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_crm_calls_twilio_child
  ON crm_call_sessions (twilio_child_call_sid)
  WHERE twilio_child_call_sid IS NOT NULL;

CREATE TABLE IF NOT EXISTS crm_call_events (
  id BIGSERIAL PRIMARY KEY,
  call_session_id UUID NOT NULL REFERENCES crm_call_sessions(id) ON DELETE CASCADE,
  twilio_call_sid VARCHAR(40) NOT NULL,
  sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
  event_status TEXT NOT NULL,
  duration_seconds INTEGER,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (twilio_call_sid, sequence_number)
);
CREATE INDEX IF NOT EXISTS idx_crm_call_events_session
  ON crm_call_events (call_session_id, sequence_number);

CREATE TABLE IF NOT EXISTS crm_activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES crm_contacts(id) ON DELETE CASCADE,
  actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  activity_type TEXT NOT NULL CHECK (
    activity_type IN ('contact_created', 'note', 'task_created', 'task_completed', 'call', 'deal_created', 'deal_stage_changed', 'suppressed')
  ),
  body TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crm_activities_timeline
  ON crm_activities (organization_id, contact_id, created_at DESC);

DO $$
DECLARE
  table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'crm_contacts', 'crm_deals', 'crm_tasks', 'crm_suppressions',
    'crm_call_sessions', 'crm_activities'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format(
      'CREATE POLICY %I ON %I USING (caregist_is_organization_member(organization_id)) WITH CHECK (caregist_is_organization_member(organization_id))',
      table_name || '_tenant_policy', table_name
    );
  END LOOP;
END
$$;

ALTER TABLE crm_call_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY crm_call_events_tenant_policy ON crm_call_events
  USING (
    EXISTS (
      SELECT 1 FROM crm_call_sessions calls
      WHERE calls.id = call_session_id
        AND caregist_is_organization_member(calls.organization_id)
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM crm_call_sessions calls
      WHERE calls.id = call_session_id
        AND caregist_is_organization_member(calls.organization_id)
    )
  );

-- Twilio webhooks have no CareGist user session. A narrowly scoped transaction
-- worker identity permits only the records needed to consume an authorization
-- and reconcile status callbacks. Ordinary CRM traffic still uses membership RLS.
CREATE POLICY crm_contacts_twilio_read_policy ON crm_contacts
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_suppressions_twilio_read_policy ON crm_suppressions
  FOR SELECT USING (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_call_sessions_twilio_policy ON crm_call_sessions
  USING (current_setting('caregist.worker', TRUE) = 'twilio')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_call_events_twilio_policy ON crm_call_events
  USING (current_setting('caregist.worker', TRUE) = 'twilio')
  WITH CHECK (current_setting('caregist.worker', TRUE) = 'twilio');
CREATE POLICY crm_activities_twilio_policy ON crm_activities
  FOR INSERT WITH CHECK (current_setting('caregist.worker', TRUE) = 'twilio');

COMMENT ON TABLE crm_call_sessions IS
  'Outbound call authorizations and lifecycle metadata. Audio is never stored in PostgreSQL.';
COMMENT ON COLUMN crm_suppressions.evidence IS
  'Minimal evidence for contact objections or TPS/CTPS screening; suppression always overrides outreach.';
