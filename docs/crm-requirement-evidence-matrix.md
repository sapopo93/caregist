# CareGist UK CRM requirement-to-evidence matrix

Status values are `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`. A `PASS` requires executable evidence; source inspection alone is not sufficient.

| Layer | Requirement / invariant | Evidence required | Current status |
|---|---|---|---|
| 1 | Additive CRM isolation; all feature flags default off | Config tests, route/build inspection, existing-workflow regression suite | PASS — baseline config and regression tests |
| 1 | Tenant isolation and role permissions | Fresh-database RLS tests; cross-tenant and operator/manager denial tests | PASS — forced-owner RLS, worker visibility and composite tenant-FK tests |
| 1 | UK SMS cannot start enabled | Startup validation test | PASS — `Settings.validate_production` test coverage |
| 1 | Exactly 30-day recording, transcript and AI retention | Startup invariant plus controlled-timestamp database deletion tests | PASS — exact access cutoff, purge selection/content clearing/audit tested |
| 1 | Secrets excluded from browser, logs, and repository | bundle/source checks and secret scan | PASS — bundle contracts and high-confidence repository scan |
| 1 | Migration ordering and reversible local rehearsal | Full fresh migration chain; down-migration inspection/rehearsal | PASS — 52→54 fresh chain and 054 down→up executed |
| 2 | Contacts, companies, notes, tasks, pipeline and deals | API, database and browser workflow tests | PASS — API contracts plus authenticated Playwright workflow |
| 2 | TPS/CTPS screening at import and immediately before dial | Positive, stale, suppression and cross-tenant tests | PASS — helper/contracts, stale monotonicity and dial-boundary locking |
| 2 | One-use call authorization and signed/account-bound callbacks | Duplicate, stale, invalid-signature, wrong-account and out-of-order tests | PASS — 27 calling/security tests plus body bounds |
| 2 | Four primary dispositions with relevant second level only | Browser/E2E evidence | PASS — four primary controls, conditional secondary controls |
| 2 | No next call before disposition | API concurrency/lock test and browser workflow | PASS — per-agent advisory lock and recoverable pinned UI state |
| 2 | Operator-selected callback date and time | API validation and browser workflow | PASS — future datetime validation and inline controls |
| 2 | Immediate DNC/wrong-number suppression and audit | Transactional API tests | PASS — suppression and audit contracts |
| 2 | Qualified/meeting/sale/lost pipeline automation | API/database tests | PASS — lifecycle/deal automation tests and UI |
| 2 | Email legal basis, unsubscribe, bounce and complaint suppression | Positive/negative/idempotency tests | PASS — campaign/event contracts and complete reporting |
| 2 | Manager, agent, call-review and disposition reporting | Permission tests and browser workflow | PASS — role gates, reports and canonical AI review fields |
| 3 | Signed bounded recording intake to private encrypted storage | Callback, malformed, oversize, integrity and storage tests | PASS — signed/account-bound intake, content bounds, AES256/private storage contracts |
| 3 | Twilio dual-channel recording and deterministic speaker labels | Synthetic stereo audio transcription test | PASS — real synthetic stereo model test |
| 3 | Local faster-whisper `small.en`, CPU `int8`, outside web requests | Worker integration test and health check | PASS — dedicated killable worker process and heartbeat readiness |
| 3 | Mandatory names/contact/identifier/sensitive redaction | Synthetic transcript tests and fail-closed provider-spy test | PASS — regex/known-entity plus mandatory dual-pass local NER |
| 3 | DeepSeek V4 Flash, non-thinking, strict required JSON | Contract tests including empty/truncated/invalid retry | PASS — strict Pydantic schema and bounded retries |
| 3 | Advisory-only AI | API/UI tests; no automatic compliance or employment mutation | PASS — persistence/UI advisory only; no state mutation path |
| 3 | Token/cost capture, pseudonymous `user_id`, monthly cap | Database and concurrency tests | PASS — per-attempt ledger, worst-case reservation and spend metrics |
| 3 | Exactly 30-day audio/transcript/report deletion with audit | Controlled-timestamp integration test | PASS — real PostgreSQL purge and audit test |
| 4 | Backend lint and full tests | Commands and results in completion report | PASS — 652 passed with the real model and fresh PostgreSQL; Ruff green |
| 4 | Frontend tests, standalone typecheck, production build | Commands and results in completion report | PASS — 136 tests, typecheck and production build |
| 4 | Browser E2E, concurrency, retries, provider outages and permissions | Automated browser and integration evidence | PASS — authenticated Playwright, DB lock, retry/outage contracts |
| 4 | Dependency/config/secret scanning | Audit commands and reviewed results | PASS — npm audit, config validation and secret scan |
| 4 | Cost estimates for 100, 1,000 and 10,000 calls | Reproducible assumptions and calculation | PASS — completion report, official pricing snapshot 2026-08-13 |
| 4 | Live synthetic redacted DeepSeek request | Model, usage, cost, latency, schema and retry evidence | BLOCKED — memory-only key not yet provided |
| 4 | Live allowlisted Twilio smoke | Signed local contracts plus supervised production smoke | BLOCKED — provisioning/credentials/number may be external |
| 5 | Rollout, rollback, monitoring, alerts and provider outage runbooks | Document and configuration review | PASS — feature-flag rollback, heartbeat/spend/retention signals and alert catalog |
| 5 | Storage lifecycle, worker health, operator and manager guides | Document and executable health evidence | BLOCKED — code/runbook complete; production lifecycle and delivered alert evidence are external |
| 5 | No unresolved P0/P1; P2 fixed or accepted | Three independent file-and-line reviews plus reconciliation | PASS — backend/security, frontend/E2E and AI/release findings reconciled and rerun |

## Baseline commands (2026-08-13)

- `CAREGIST_TEST_DATABASE_URL=… CAREGIST_RUN_WHISPER_INTEGRATION=1 .venv/bin/python -m pytest -q` — PASS, 652 tests under a non-superuser/non-`BYPASSRLS` owner.
- `.venv/bin/ruff check api/ tools/ db/ tests/` — PASS.
- `npm --prefix frontend test` — PASS, 136 tests.
- `npm --prefix frontend run build` — PASS, including Next.js TypeScript phase.
- `frontend/./node_modules/.bin/tsc --noEmit` — PASS.
- Authenticated Playwright operator workflow — PASS with synthetic local database, disposition recovery and zero axe violations.
- Model-backed local dual-channel transcription — PASS.
- Fresh PostgreSQL security/migration/retention suite — PASS, 11 tests.

## Decision log

1. Preserve the additive CRM architecture and existing user-owned worktree changes.
2. Run transcription in a separate long-lived local worker using faster-whisper `small.en` on CPU `int8`; do not load model binaries in Vercel or invoke transcription from a request/cron handler.
3. Retrieve Twilio recordings as two channels and label the outbound browser leg as `Agent` and the inbound PSTN leg as `Contact`; reject mono input instead of guessing speaker identity.
4. Permit external AI only after deterministic redaction and a post-redaction leak scan succeed. Any uncertainty fails the job before the HTTP client is called.

## Initial risk register

| Risk | Mitigation | Owner |
|---|---|---|
| Existing unstaged CRM work is user-owned | Minimal patches only; no staging, discard, commit or broad rewrite | Primary agent |
| Local model dependency is too large for serverless | Separate worker requirements and process; web runtime only queues work | Primary agent |
| Redaction misses unknown personal data | Known CRM-entity redaction, conservative patterns, residual scan and fail-closed tests | Primary agent |
| AI cost races across workers | Database-backed reservation under a transaction lock and configurable monthly cap | Primary agent |
| Provider credentials/provisioning unavailable | Complete local contract tests and list exact supervised live smoke separately | User/external provider |
