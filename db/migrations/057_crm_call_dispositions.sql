-- Expand the CRM call disposition catalogue with operator-facing outcomes.
-- Call dropped, call me some other time and number disconnected are additive;
-- existing rows remain valid because the re-created constraint is a superset.

ALTER TABLE crm_call_sessions
  DROP CONSTRAINT IF EXISTS crm_call_sessions_disposition_check;

ALTER TABLE crm_call_sessions
  ADD CONSTRAINT crm_call_sessions_disposition_check CHECK (
    disposition IS NULL OR disposition IN (
      'connected', 'no_answer', 'busy', 'voicemail', 'wrong_number',
      'callback_requested', 'gatekeeper', 'qualified', 'not_interested',
      'do_not_call', 'meeting_booked', 'sale_completed',
      'call_dropped', 'call_me_later', 'number_disconnected'
    )
  );
