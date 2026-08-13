# CareGist lean UK CRM production completion report

Date: 2026-08-13
Build status: complete
Go-live status: approved for a single-destination, call-only production pilot

## Scope and safety state

The CRM is additive and disabled by default. Calling, recording, email campaigns and AI each have independent feature flags; UK SMS is a fatal startup error if enabled. The Twilio account is funded, an existing business line is verified as the outbound caller ID, and production credentials are stored outside the repository. Recording, AI, email campaigns, SMS and unrestricted calling remain out of scope for the initial pilot.

The implemented path includes organisation-scoped contacts and companies, notes, typed tasks, deals and pipeline automation; TPS/CTPS screening at import and dial; one-use browser call authorisation; signed/account-bound Twilio callbacks; mandatory four-choice dispositions; callbacks and immediate suppression; manager campaigns/reports/review; dual-channel encrypted recording intake; local faster-whisper transcription; fail-closed redaction; and advisory DeepSeek V4 Flash evaluation.

## Cost model

Pricing snapshot: 2026-08-13. Currency conversion and VAT are excluded because the account's billing currency, tax treatment and destination mix are external facts. Recheck at activation.

Assumptions per completed call:

- 5 minutes average duration;
- destination mix 50% UK local at $0.0158/min and 50% UK mobile at $0.0305/min;
- one browser/app call leg at $0.0040/min in addition to the outbound PSTN leg;
- Twilio recording at $0.0025/min and temporary Twilio storage at $0.0005/min/month; private CareGist storage is provider-specific and not included;
- one local CPU transcription, so no transcription API fee;
- DeepSeek V4 Flash: 1,500 cache-miss input tokens and 300 output tokens at $0.14/M and $0.28/M respectively;
- one UK local number at $3.50/month shared by three seats.

| Calls/month | Voice (PSTN + browser) | Recording + 1 month Twilio storage | DeepSeek | Shared number | Estimated total |
|---:|---:|---:|---:|---:|---:|
| 100 | $13.58 | $1.50 | $0.03 | $3.50 | $18.61 |
| 1,000 | $135.75 | $15.00 | $0.29 | $3.50 | $154.54 |
| 10,000 | $1,357.50 | $150.00 | $2.94 | $3.50 | $1,513.94 |

Add the dedicated worker host/CPU and private encrypted storage quote before approval. Those costs are infrastructure-dependent and cannot be responsibly invented from source code.

At 1,000 calls/month this is about $51.51 per seat/month before VAT, worker compute and private storage. Therefore the £30/seat target is **not yet accepted or evidenced** at that volume; it depends on actual minutes/destination mix, GBP/USD and the worker/storage quote. At 100 calls/month the metered provider portion is about $6.20 per seat before those additions. Configure usage alerts before the pilot and recalculate from the first week's actual call mix.

The DeepSeek implementation records every provider response attempt, pessimistically charges the UTF-8 byte-ceiling maximum when usage is absent, reserves all three retry attempts under an advisory transaction lock, releases a hold only when its usage ledger write is durable, and stops claims at the configurable monthly cap. Unresolved current-month charge holds fail closed; prior-month holds do not permanently exhaust later budgets.

## Executable evidence

- Final backend: 652 tests passed under a non-superuser/non-`BYPASSRLS` PostgreSQL owner, including the opt-in real Whisper model; Ruff passed.
- Final frontend: 136 tests, standalone TypeScript and Next.js production build passed.
- Real local faster-whisper `small.en` integration: synthetic stereo speech preserved deterministic `Agent` and `Contact` labels; empty, malformed and mono inputs failed closed.
- Redaction/provider-spy tests: lowercase, all-caps and CRM-known names, phones, email, NI number, postcode, cancer treatment and chemotherapy content were removed before the HTTP boundary; empty and oversized transcripts failed closed.
- Real PostgreSQL: migration 054 down→up, forced-RLS owner behavior, tenant and worker visibility, composite cross-tenant FK rejection, advisory lock contention, exact access expiry, retention purge and audit evidence passed.
- Authenticated Playwright exercised unresolved-disposition reload recovery, the four primary choices, a real disposition submission, task creation, reports and a zero-violation axe scan.
- Independent backend/security, frontend/E2E and AI/release reviews were run with file-and-line evidence. Their blockers were routed back, remediated and independently re-reviewed.

## Thirty-day deletion invariant

Database access and playback stop exactly at `expires_at`. The retention worker atomically purges transcript, summary, evaluation and external identifiers, then independently deletes CareGist and Twilio objects and records audit evidence. Readiness fails while any expired object is not confirmed deleted. Production additionally requires an independently configured 30-day bucket lifecycle rule and an alert on any deletion lag; provider deletion cannot be made physically instantaneous by application code.

## Rollout and rollback

1. Verify a database backup and restore rehearsal.
2. Apply migrations 052, 053 and 054 in order.
3. Deploy API, web and the dedicated CRM AI worker with all CRM flags false.
4. Verify liveness/readiness, worker heartbeat, retention backlog and existing CareGist smoke paths.
5. Enable only `CRM_ENABLED` in an isolated preview and verify tenant/role workflows.
6. Configure licensed TPS/CTPS evidence and HMAC key.
7. With action-time approval, configure Twilio in pilot mode and only allowlisted CareGist test numbers.
8. Enable recording only after privacy wording, encrypted bucket, lifecycle and alerts are approved.
9. Exercise DeepSeek only with a synthetic redacted transcript and a memory-only key; persist a secret only after separate approval.
10. Enable campaigns only for internal test inboxes after legal-basis and postal-address review.

Operational rollback uses feature flags in reverse order: AI, recording, campaigns, calling, then CRM workspace. Do not run destructive down migrations as an incident rollback. Preserve CRM evidence and restore application code while migrations remain additive.

## External blockers before go-live

- DeepSeek API credential and balance for one memory-only synthetic request, followed by separate approval for persistent secret storage.
- Twilio funded/provisioned account, API credentials, UK number, approved recording notice and one supervised allowlisted test call.
- Licensed TPS/CTPS data source and current screening evidence.
- Approved private object-storage provider, encryption configuration, 30-day lifecycle rule and delivered alerts.
- Privacy/legal acceptance of the recording notice, retention, external redacted-text processing and email campaign basis.
- Explicit production deployment and activation confirmation.

## Production activation checklist

- [x] Final full backend, frontend, build, browser and secret/config checks are green.
- [x] Independent P0/P1 findings are closed; P2 findings are fixed or explicitly accepted.
- [ ] Backup/restore and operational feature-flag rollback have evidence.
- [ ] Worker deployment is running and heartbeat is under 120 seconds.
- [ ] DeepSeek cap and 80% alert are configured.
- [ ] Twilio usage alerts and allowlist are configured.
- [ ] Storage lifecycle/deletion alerts are delivered and recovery-tested.
- [ ] Licensed screening feed and legal/privacy approvals are recorded.
- [ ] Supervised synthetic DeepSeek and Twilio smokes pass.
- [ ] Action-time production confirmation is recorded.
