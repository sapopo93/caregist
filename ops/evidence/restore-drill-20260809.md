# Neon restore-drill evidence — 2026-08-09

- Drill date (UTC): 2026-08-09
- Operator: Codex production-remediation session
- Authorization: founder instruction to fix release blockers, push, test, and deploy; paid-release approval remains a separate gate
- Neon project ID (non-secret): `purple-voice-97710924`
- Source branch ID (non-secret): `br-nameless-glitter-abix2cgn`
- Pre-migration recovery branch ID (non-secret): `br-flat-art-ab8e7jhb`
- Temporary restored branch ID (non-secret): `br-young-paper-abfjvrf8`
- Requested restore timestamp (UTC): `2026-08-09T22:06:27.804Z`
- Restore branch created (UTC): `2026-08-09T22:06:52Z`
- Seven-day history-window evidence: Neon Console project overview showed Launch plan and `History retention: 7 days` on 2026-08-09
- Pre-drill deployed Git SHA: `a79f18f724c6c99a262c121c4220027cac6eb17e`
- Latest required production migration: `043_trustroute_outbox.sql`
- Recovery checkpoint fork duration: 4.27 seconds
- Restore-drill RPO: 24.196 seconds between requested restore point and branch creation
- Restore-drill RTO: under 60 seconds from submit to an available isolated branch; the console did not expose a more precise backend duration
- Invariant output: `ops/evidence/restore-drill-20260809-invariants.json`, SHA-256 `045cce46dd1b387c65cd2462d5bd12bdd4ea15e967b050ca204daf781dd72ec5`
- Isolated migration branch ID (non-secret): `br-silent-lake-abfr5f08`
- Isolated migration result: all seven pending repository migrations from `043_reconciliation_batches.sql` through `049_cqc_signal_intelligence.sql` applied; provider counts remained 56,743 total and 56,742 active; duplicate canonical CQC location IDs remained zero; the new ledger, tenancy, outbox, and RLS structures were present
- Source watermark/reconciliation result: not exercised by this database restore; collectors and paid checkout remain disabled pending shadow evidence
- Result: **PASS**
- Discrepancies found and resolved: the restore verifier queried nonexistent `care_providers.location_id`; it now checks the canonical `care_providers.id`. Migration 048 was not replay-safe against an already provisioned compatibility schema; its table, index, and trigger creation is now idempotent.
- Cleanup: the restore-drill and isolated-migration branches expire automatically after one day. The pre-migration recovery branch has no expiry and must remain until production migration verification and explicit cleanup approval.

No connection strings, credentials, customer records, payment data, or other secrets were opened or stored.
