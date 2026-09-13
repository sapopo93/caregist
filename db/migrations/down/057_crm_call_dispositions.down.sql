-- Restore the original CRM call disposition catalogue.

ALTER TABLE crm_call_sessions
  DROP CONSTRAINT IF EXISTS crm_call_sessions_disposition_check;

ALTER TABLE crm_call_sessions
  ADD CONSTRAINT crm_call_sessions_disposition_check CHECK (
    disposition IS NULL OR disposition IN (
      'connected', 'no_answer', 'busy', 'voicemail', 'wrong_number',
      'callback_requested', 'gatekeeper', 'qualified', 'not_interested',
      'do_not_call', 'meeting_booked', 'sale_completed'
    )
  );
