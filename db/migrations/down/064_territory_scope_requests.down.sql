DROP TRIGGER IF EXISTS territory_scope_request_events_immutable ON territory_scope_request_events;
DROP TRIGGER IF EXISTS territory_scope_request_transition_guard ON territory_scope_requests;
DROP FUNCTION IF EXISTS prevent_territory_scope_request_event_mutation();
DROP FUNCTION IF EXISTS enforce_territory_scope_request_transition();
DROP TABLE IF EXISTS territory_scope_request_events;
DROP TABLE IF EXISTS territory_scope_requests;
