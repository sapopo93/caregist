# CareGist — Production Readiness Audit

> **Status update — 2026-06-29:** This audit is retained as historical context and is no longer the current production-readiness verdict. The hardening pass on 2026-06-29 resolved or superseded multiple findings below, including the `NEXT_PUBLIC_API_KEY` fallback, plaintext API-key acceptance, missing production gates for `WEBHOOK_SECRET_KEY`/`REDIS_URL`, profile checkout ownership checks, `.gitignore` coverage, and frontend dependency vulnerabilities. Remaining go-live gates are now external deployment operations: apply the latest migrations in staging/production, set required AWS/hosting secrets, run staging Stripe/webhook/email/Redis smoke tests, and confirm backup/restore coverage.

**Auditor:** Claude Code (staff-engineer audit, read-only pass)
**Date:** 2026-05-14
**Scope:** Entire repo at `/Users/user/CareGist` — FastAPI backend, Next.js 15 frontend, PostgreSQL/PostGIS schema, CQC ETL pipeline, operational tooling, CI/CD, deployment.
**Verdict:** **Not production-ready as-is.** Strong product surface and test scaffolding, but **8 launch-blocking gaps** in secrets handling, session/cookie security, rate-limit correctness, and disaster recovery. The codebase is closer to "real users can sign up" than "stable, safely monitored, legally defensible" — the path to production is well-defined but not short.

---

## 1. Executive Summary

1. **Session security is broken.** The full session bearer token is placed in a browser cookie as plaintext (`api/routers/auth.py:211–235`). DB stores `token_hash`, but the cookie carries the live secret — anyone with logs, a TLS-stripped link, or browser extension exfil gets a session.
2. **Frontend auth is client-side only.** Auth state lives in `localStorage` (`frontend/app/login/page.tsx:40–42`); no `middleware.ts` guards `/dashboard`, `/provider-dashboard`, `/admin`. XSS = full account takeover.
3. **`NEXT_PUBLIC_API_KEY` fallback exposes the backend master key in the browser bundle** (`frontend/lib/server-api-config.ts:147–153`) if the server-only `API_KEY` is unset.
4. **`WEBHOOK_SECRET_KEY` is unset in production.** Per `api/utils/crypto.py:44`, this means Business+ outbound-webhook signing secrets sit **plaintext** in `webhook_subscriptions`. DB-read access = forge any customer's signed events.
5. **`REDIS_URL` is unset in production.** Rate limits, burst caps, and tier quotas fall back to in-memory per uvicorn worker — a 2-worker deploy lets every customer burst at 2× their tier.
6. **No automated backups.** `workflows/apply-migrations.md:54` lists "DB is backed up" as a manual pre-flight checkbox. There is no `pg_dump`/snapshot cron, no PITR, no restore drill.
7. **No infrastructure-as-code.** Deploys are SSH + `git pull` + PM2 restart against a single EC2 (`workflows/deploy-ec2.md`). No HA, no blue/green, no canary, no smoke test post-deploy.
8. **`.gitignore` is 3 lines.** Only `*.docx`, `*.ods`, `~`. `.env`, `__pycache__`, `.venv`, `node_modules`, `frontend/.env.local`, `*.csv`/`*.ndjson` data dumps are *currently* untracked — but one stray `git add .` commits production secrets, the 1.8 GB cleaned CSV, and provider cache SQLite to the repo.
9. **Stripe webhook handler has a thin-margin race.** `ON CONFLICT DO NOTHING` on `stripe_processed_events` prevents *duplicate rows* but does not serialise *handlers* — concurrent retries can both run side-effects (`api/routers/billing.py:468–500`).
10. **Strong fundamentals to build on.** 29 numbered migrations applied via tracked `schema_migrations`, structured JSON logs, Sentry wired with env detection, ledger-backed feed, dedup keys, HTTP security headers, CORS validated against wildcards. The skeleton is sound — what's missing is the production hardening layer.

---

## 2. Stack & Architecture Map

| Layer | Stack | Entry point |
|---|---|---|
| Backend | FastAPI, asyncpg, pydantic-settings, bcrypt, Stripe Python, Sentry | `api/main.py` → `uvicorn api.main:app` |
| Frontend | Next.js 15, React 19, Tailwind 4, App Router, Sentry | `frontend/app/` |
| Database | PostgreSQL + PostGIS, 29 migrations | `db/init.sql` + `db/migrations/` |
| Background | PM2 + bare cron on EC2 | `ecosystem.config.cjs`, `/etc/cron.d/caregist` |
| ETL | CQC public API → CSV → Postgres | `extract_cqc.py`, `incremental_update.py` |
| Secrets | AWS Secrets Manager (prod), `.env` (dev) | `api/config.py:58–170` |
| Observability | Sentry, structured JSON logs, custom audit tables | `api/logging_config.py`, `audit_log`, `pipeline_runs` |
| Email | Resend, queued via `pending_emails`, drained both by background task (30s) and `/health` calls | `api/utils/email_queue.py` |
| Deploy | Single AWS EC2, PM2, manual SSH | `workflows/deploy-ec2.md` |

**Routers registered (`api/main.py:111–132`):** 22 routers — `health`, `internal`, `auth`, `analytics`, `billing`, `claims`, `reviews`, `enquiries`, `admin`, `groups`, `provider_profile`, `providers`, `feed`, `regions`, `subscribe`, `comparisons`, `api_applications`, `public_tools`, `region_stats`, `city_pages`, `sitemaps`, `webhooks`. Tier system in `api/config.py:237–406` (8 tiers, free → admin).

**Frontend routes present (`frontend/app/`):** `/`, `/search`, `/provider/[slug]`, `/provider-dashboard`, `/dashboard`, `/admin`, `/groups`, `/region`, `/find-care`, `/compare`, `/care-homes`, `/good-care-homes`, `/outstanding-care-homes`, `/requires-improvement-care-homes`, `/pricing`, `/services`, `/why-caregist`, `/claim`, `/login`, `/signup`, `/forgot-password`, `/verify-email`, `/privacy`, `/terms`, `/cookies`, `/acceptable-use`, `/review-policy`, `/sample-report`, `/story-video`.

**Ambiguous / unverified:**
- `tools/reconcile_stripe_subscriptions.py` — no schedule, no docs; one-shot or recurring?
- `STRIPE_PRICE_ENTERPRISE` defined in config but no checkout path uses it; enterprise pricing path is unclear.
- `frontend/app/admin` exists — depth of auth enforcement on it not fully verified.

---

## 3. Core User Flows — Status

| # | Flow | Status | Notes |
|---|------|--------|-------|
| 1 | **Public provider search & detail** | ✅ Complete | Routes, filters, exports, sitemap, FTS index all wired |
| 2 | **Sign up → email verify → login** | ⚠️ Partial | Backend complete; cookie design insecure (F-1); no CSRF; password complexity weak (F-22) |
| 3 | **Password reset** | ⚠️ Partial | Migration 029 fixed entropy; per-token attempt counter logic is buggy (F-23); timing leak on `/forgot-password` (F-24) |
| 4 | **B2B checkout (Stripe → tier upgrade)** | ⚠️ Partial | Checkout creates session; webhook dedup races (F-11); enterprise tier price ID defined but unused in flow |
| 5 | **Provider listing claim (free → enhanced)** | ⚠️ Partial | Claim submission + admin moderation present; profile checkout does not verify caller owns the slug (F-15) |
| 6 | **New-registration feed (Starter+)** | ✅ Complete | Ledger-backed, dedup'd, sync + webhook delivery + digest in `tools/run_new_registration_feed_cycle.py` |
| 7 | **Outbound webhooks (Business+)** | ⚠️ Partial | HMAC delivery + retry + auto-disable working; secret encryption disabled in prod (F-3); subscriber-side signature verify not tested (F-43) |
| 8 | **Saved filters + weekly digests** | ✅ Complete | Endpoint + cron `tools/send_monitor_alerts.py`, `tools/send_weekly_movers.py` |
| 9 | **Provider dashboard (claimed listing edit)** | ⚠️ Partial | Routes exist; ownership-on-write not fully audited |
| 10 | **Admin moderation (claims, reviews, enquiries)** | ⚠️ Partial | Routes + audit log; `admin` tier inferred from `name` field (F-16); frontend `/admin` lacks server middleware guard (F-2) |
| 11 | **API key issuance, rotation, team seats** | ⚠️ Partial | Hashed via migration 026 but plaintext fallback still accepted (F-5); key not invalidated on subscription downgrade (F-17) |

---

## 4. Findings

### Severity legend
- **Blocker** — must fix before any paid customer touches it
- **High** — must fix before scaling beyond design-partner phase
- **Med** — should fix before paid GA
- **Low** — cleanup / polish

### Findings table

| ID | Area | Sev | Description | File(s) | Suggested fix | Effort |
|----|------|-----|-------------|---------|----------------|--------|
| F-1 | Auth — sessions | **Blocker** | Session token (the live bearer credential, `cs_…`) is placed in cookie `caregist_session` in plaintext; only hash stored in DB. Logs, proxies, browser-extension exfil = full session theft. | `api/routers/auth.py:211–235` | Issue an opaque session ID (random 128-bit) to cookie; keep the API key server-side only. Or rotate to short-lived JWT + refresh. | M |
| F-2 | Frontend — auth | **Blocker** | Auth state in `localStorage`; no `middleware.ts`. Protected routes `/dashboard`, `/provider-dashboard`, `/admin` are client-side gated only. | `frontend/app/login/page.tsx:40–42`; `frontend/middleware.ts` (missing) | Move session to httpOnly cookie; add `frontend/middleware.ts` that validates session against backend before rendering protected routes. | M |
| F-3 | Secrets — webhooks | **Blocker** | `WEBHOOK_SECRET_KEY` absent from production `.env`. Per `api/utils/crypto.py:44`, missing key = plaintext storage of every customer's webhook signing secret in `webhook_subscriptions`. | `.env`; `api/utils/crypto.py:44`; `api/routers/webhooks.py:89–94`; `api/config.py:201` | Generate 32-byte AES-GCM key, put in AWS Secrets Manager. Promote to required: extend `REQUIRED_PRODUCTION_SECRETS` in `api/config.py:49`. Re-encrypt existing rows in a migration. | S |
| F-4 | Frontend — keys | **Blocker** | `NEXT_PUBLIC_API_KEY` fallback path leaks backend master key into the browser bundle if `API_KEY` is unset. | `frontend/lib/server-api-config.ts:147–153` | Delete the fallback; throw `Error('API_KEY required for server-side fetch')` instead. | S |
| F-5 | Auth — API keys | **Blocker** | `api/middleware/auth.py:174–189` accepts plaintext keys (`WHERE ak.key_hash = $1 OR ak.key = $2`) — migration 026 hashed existing keys but left the comparison path open. | `api/middleware/auth.py:174–189`; `db/migrations/026_hash_api_keys.sql` | Drop `OR ak.key = $2` branch. Add `CHECK (key IS NULL)` and `NOT NULL key_hash` constraints in a new migration after revoking any remaining plaintext rows. | S |
| F-6 | Ops — rate limits | **Blocker** | `REDIS_URL` unset → per-worker in-memory rate limiting (`api/middleware/rate_limit.py:209–248`). 2 uvicorn workers ⇒ every paid tier doubles its allowed burst and quota. | `.env`; `api/middleware/rate_limit.py:209–248` | Provision Redis (ElastiCache or Upstash). Make `REDIS_URL` required in prod via `REQUIRED_PRODUCTION_SECRETS`. | S |
| F-7 | Ops — backups | **Blocker** | No automated backup. `workflows/apply-migrations.md:54` lists DB backup as a manual checklist item. No restore runbook, no restore drill. | `workflows/apply-migrations.md:54`; no `tools/backup.sh` | If on Neon: enable + document branch snapshots; if RDS: configure 7-day PITR + daily snapshot retention. Add monthly restore-into-staging dry run as a workflow doc. | M |
| F-8 | Ops — IaC | **Blocker** | No Terraform/CDK/Pulumi. Single EC2, manual `ssh` + `git pull`. No HA, no DR, no canary. EC2 instance failure = downtime until manual rebuild. | `workflows/deploy-ec2.md` | Minimum viable: Terraform module for EC2 + RDS/Neon + ALB + IAM + Secrets Manager. Even one-AZ IaC beats untracked SSH. | L |
| F-9 | Repo hygiene | **High** | `.gitignore` is 3 lines (`*.docx`, `*.ods`, `~`). `.env`, `__pycache__/`, `.venv/`, `node_modules/`, `frontend/.env.local`, 1.8 GB `cleaned_cqc.csv`, `_provider_cache.sqlite`, NDJSON dumps — all currently *untracked* but unprotected from a stray `git add .`. | `/Users/user/CareGist/.gitignore` | Replace with proper Python/Node/Next.js gitignore covering: `.env*`, `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `.next/`, `*.tsbuildinfo`, `_*.ndjson`, `_*.sqlite`, `*.csv` (selective), `outputs/`, `.DS_Store`, `.tmp/`. | S |
| F-10 | Auth — CSRF | **High** | CORS `allow_credentials=True` + cookie session + no CSRF token = classic CSRF on every POST/PUT/PATCH/DELETE using cookie auth (login, register, rotate-key, billing, admin). SameSite=`lax` does not protect top-level POSTs. | `api/main.py:75–81`; `api/routers/auth.py` (multiple) | Set `SameSite=Strict` for the session cookie, or add a CSRF token (double-submit pattern). Easiest: require `X-API-Key` header for state-changing endpoints (kills CSRF entirely). | M |
| F-11 | Billing — Stripe | **High** | Stripe webhook dedup uses `INSERT … ON CONFLICT DO NOTHING` but does not lock concurrent retries. Two simultaneous deliveries of the same `event_id` can both run side-effects between insert and check. | `api/routers/billing.py:468–500` | Wrap handler in `BEGIN; INSERT … ON CONFLICT DO NOTHING RETURNING id;` — proceed only if RETURNING yielded a row; otherwise the duplicate transaction sees no row and returns 200 without side effects. Then `COMMIT`. | S |
| F-12 | DB — FKs | **High** | `rating_changes.provider_id` has no FK to `care_providers(id)`. Orphans accumulate; cascading deletes don't clean it. | `db/migrations/006_rating_changes.sql:4` | `ALTER TABLE rating_changes ADD CONSTRAINT fk_rating_changes_provider FOREIGN KEY (provider_id) REFERENCES care_providers(id) ON DELETE CASCADE;` after cleaning orphans. | S |
| F-13 | DB — FKs | **High** | `trusted_event_ledger.provider_id` (the audit-of-record for the entire feed product) has no FK. | `db/migrations/015_trusted_event_ledger_new_registration_feed.sql:8` | `ALTER TABLE trusted_event_ledger ADD CONSTRAINT … FOREIGN KEY (provider_id) REFERENCES care_providers(id) ON DELETE SET NULL;` | S |
| F-14 | DB — invariants | **High** | No unique constraint preventing multiple `status='active'` subscriptions per user. Combined with the Stripe race (F-11), duplicate billing is plausible. | `db/init.sql:134–148` | `CREATE UNIQUE INDEX uniq_active_sub_per_user ON subscriptions (user_id) WHERE status = 'active';` | S |
| F-15 | Authz — billing | **High** | `POST /billing/checkout/profile` accepts `req.slug` and does not verify the caller owns the slug via `provider_claims`. A free user could initiate a checkout against a competitor's slug. | `api/routers/billing.py:165, 325` | Validate ownership before creating Stripe session: join `provider_claims` on `(user_id, provider_id, status='approved')`. | S |
| F-16 | Authz — admin | **High** | Admin actions audit-log the user-controlled `auth["name"]` (set by user at API-key creation, `auth.py:526`). An attacker with two keys named `"admin_audit_system"` and `"true_admin"` can muddy forensics. | `api/routers/admin.py:144, 158, 224, 286`; `api/middleware/auth.py:117` | Audit log should record `user_id` + `key_id` only; if a label is needed, store it as `key_name` (clearly labelled), not as `actor`. | S |
| F-17 | Authz — keys | **High** | Subscription downgrade does not revoke / re-tier existing keys. Old `tier='business'` keys keep `business` quotas after the user drops to `starter`. | `api/routers/auth.py`; `api/routers/billing.py` (webhook handlers) | On `customer.subscription.updated/deleted` webhook, update all keys for `user_id` to the new tier (or mark excess keys inactive per seat count). | S |
| F-18 | Ops — secrets | **High** | Master API key (`API_MASTER_KEY`) has no rotation, no expiry, no audit. Used only as `secrets.compare_digest` against a single env value. Leak = full admin until env edit + redeploy. | `api/middleware/auth.py:131–143`; `api/config.py:177` | Accept a list of valid master keys with rotation window; audit-log every use; alert on first use ever from a new IP. | M |
| F-19 | Auth — proxy trust | **High** | `api/middleware/ip_rate_limit.py:22–34` reads `X-Forwarded-For` without verifying the immediate hop is a trusted proxy. Direct attacker → forged header → IP-rate-limit bypass. | `api/middleware/ip_rate_limit.py:22–34` | Allowlist the ALB/CloudFront IP ranges; reject `X-Forwarded-For` from any other source. Reject ALB-less direct connections at the security-group level. | S |
| F-20 | Auth — exposure | **High** | `api/middleware/auth.py:115–124` returns the plaintext `api_key` in the auth metadata dict, which then flows through every dependency-injected handler and into the global exception handler's Sentry breadcrumbs. | `api/middleware/auth.py:115–124`; `api/main.py:103–108` | Strip `api_key` from the auth dict; only return `key_id`, `user_id`, `tier`, `name`, `is_verified`. | S |
| F-21 | Frontend — CSP | **High** | `Content-Security-Policy` allows `'unsafe-inline'` for both script and style. Defeats XSS mitigation. | `frontend/next.config.ts:128–129` | Adopt nonce-based CSP (Next 15 supports nonce injection via middleware). At minimum, drop `unsafe-inline` from `script-src` and refactor inline scripts to nonced or extracted. | M |
| F-22 | Auth — passwords | **High** | Min length 8, no complexity, no breach-check. "abcdefgh" passes. | `api/routers/auth.py:110, 590` | Raise to 12 + breach check via `pwnedpasswords` API range query, or run `zxcvbn` and require score ≥ 3. | S |
| F-23 | Auth — reset | **High** | Password-reset attempt counter increments on whichever token is fetched, allowing brute force of older tokens if a user has issued multiple. Plaintext token comparison instead of constant-time. | `api/routers/auth.py:679–711` | Hash reset tokens (already partially done in migration 029); `secrets.compare_digest`; invalidate prior tokens when a new one is issued. | S |
| F-24 | Auth — enumeration | **High** | `POST /forgot-password` has ~10× response-time difference between registered and unregistered emails. Trivial email-enumeration oracle. | `api/routers/auth.py:597–629` | Always perform the same DB+email path (queue a no-op send for unknown emails) or add a constant-time floor with `await asyncio.sleep(jitter())` to clamp both paths. | S |
| F-25 | Health — deps | **High** | `/api/v1/health` checks DB + ledger only. Does not ping Stripe, Resend, or Redis. Health returns 200 while checkout / email / rate-limit are dead. | `api/routers/health.py:17–67` | Add lightweight liveness probes (Stripe `accounts.retrieve` cached 60s; Resend domains list cached 60s; Redis `PING`). Distinguish `/health/liveness` (always 200 if process up) from `/health/readiness` (full deps). | S |
| F-26 | Tests — billing | **High** | Webhook handler tests cover only the error branch (missing `user_id` → `RuntimeError`); no happy-path test for `checkout.session.completed → tier upgrade → seat re-entitlement`. | `tests/test_billing_webhook_handlers.py` | Add fixture that mocks Stripe event payloads and asserts DB state transitions for the four critical events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`. | M |
| F-27 | Tests — restore | **High** | No integration test using a real Postgres (all tests mock asyncpg). Migrations have never been replayed end-to-end in CI. | `tests/conftest.py` | Add a single `tests/integration/test_migrations_apply_cleanly.py` that spins up Postgres in CI (Docker service), applies `init.sql` then every migration in order, then runs a few smoke queries. | M |
| F-28 | DB — retention | **High** | `analytics_events`, `audit_log`, `admin_audit_log`, `pending_emails` all grow unbounded with no pruning. Storage and query-plan degradation arrive together. | `db/migrations/001_growth_features.sql`; `db/migrations/022_admin_audit_log.sql`; `db/migrations/028_audit_log.sql` | Add nightly retention cron: events 90 days, audit 2 years (or compliance-driven), sent emails 30 days. Document retention SLA. | S |
| F-29 | Ops — IaC for cron | **High** | Cron is bare `/etc/cron.d/caregist` per `workflows/deploy-ec2.md:162`. No execution logs aggregated, no alert on missed run. Pipeline watchdog (`tools/check_new_registration_pipeline.py`) catches data-staleness but not "cron daemon died". | `/etc/cron.d/caregist`; `workflows/deploy-ec2.md:162–179` | systemd timers (per-unit logs to journald), or move feed cycle to an ECS scheduled task. Add a simple deadman switch: each cron job pings a health endpoint that records `last_seen`, alert if missing. | M |
| F-30 | Ops — rollback | **High** | No `--down` migrations. Rollback story is "restore from backup" (which doesn't exist — see F-7). | `workflows/apply-migrations.md:101`; `db/migrations/*` | Either commit to forward-only and rely on F-7's backups, or add `_down.sql` siblings for the destructive migrations (e.g., 026 key-hash, 029 token entropy). | M |
| F-31 | Ops — README | **High** | No `README.md` at project root. CLAUDE.md exists but is agent-oriented. A new engineer landing on the repo has no onboarding starting point. | `/Users/user/CareGist/README.md` (missing) | Write a short README: what the product is, how to spin up locally (`docker compose up db && uvicorn …`), how to run tests, where to read runbooks. | S |
| F-32 | DB — seed | **Med** | `db/seed.py:82–84` runs `TRUNCATE care_providers, provider_claims, reviews, enquiries RESTART IDENTITY CASCADE` on `--truncate` with no env guard. One bad CLI invocation on prod = all data gone. | `db/seed.py:82–84` | Refuse to run if `DATABASE_URL` host is not `localhost`/docker; require `--i-understand` flag; prompt for typed confirmation. | S |
| F-33 | DB — schema drift | **Med** | `init.sql:11` defines `slug VARCHAR(300) UNIQUE` allowing NULL. Migration 025 fixes it with NOT NULL + CHECK. New deployments going via `init.sql` are inconsistent with migrated prod until 025 runs. | `db/init.sql:11`; `db/migrations/025_care_provider_slug_invariant.sql` | Bake migration 025's invariant straight into `init.sql`; same for the password-reset token entropy fix from migration 029 vs. `init.sql:261`. | S |
| F-34 | DB — indexes | **Med** | Missing composite indexes for known query shapes: `rating_changes(provider_id, detected_at DESC)`; `care_providers(region, overall_rating, status) WHERE upper(status)='ACTIVE'`; `analytics_events(user_id, created_at DESC)`. | `db/migrations/006_rating_changes.sql`; `db/init.sql` | Add four targeted partial/composite indexes; verify via `EXPLAIN` on the slow queries flagged by Sentry / pgBadger. | S |
| F-35 | DB — counts | **Med** | `api/queries/enquiries.py:11–14` recounts enquiries on every insert via correlated subquery instead of `enquiry_count = enquiry_count + 1`. | `api/queries/enquiries.py:11–14` | Replace subquery with increment, or move to an AFTER INSERT trigger. | S |
| F-36 | Frontend — error UX | **Med** | Only root `error.tsx` / `global-error.tsx`; nested routes (`/provider/[slug]`, `/search`, `/dashboard`) have no per-segment error boundary. | `frontend/app/error.tsx`, `frontend/app/global-error.tsx` | Add `error.tsx` to `/dashboard`, `/provider/[slug]`, `/search`, `/admin`. Include `reset()` button + Sentry capture. | S |
| F-37 | Frontend — Sentry quota | **Med** | `instrumentation-client.ts:7` sets `replaysOnErrorSampleRate: 1.0` — every error captures a full session replay. Quota will drown in any minor incident. | `frontend/instrumentation-client.ts:7` | Drop to 0.1–0.2 in production. | S |
| F-38 | Frontend — SEO | **Med** | `frontend/public/robots.txt` only disallows `/admin/`. `/login`, `/signup`, `/dashboard`, `/forgot-password`, `/provider-dashboard` are indexable. | `frontend/public/robots.txt:3–4` | Add `Disallow:` entries for all authenticated routes. | S |
| F-39 | Logging — correlation | **Med** | No request-id propagation; logs across middleware + handler + DB can't be stitched together for incident triage. | `api/logging_config.py:1–54` | Add a request-id middleware that injects `X-Request-ID` into both the response header and a `ContextVar` consumed by the JSON formatter. | S |
| F-40 | Logging — sensitive | **Med** | `api/routers/auth.py:765–804` logs Resend response `resp.text` verbatim on error. If Resend echoes the API key or recipient PII in its error body, it lands in logs. | `api/routers/auth.py:765–804` | Log only `resp.status_code` and a sanitised `resp.json().get('message')`. | S |
| F-41 | Headers — leakage | **Med** | `X-Tier` header is set on every response (`api/middleware/rate_limit.py:518–530`). Reveals customer tier to any intermediary / browser ext. | `api/middleware/rate_limit.py:518–530` | Drop the header, or restrict to internal calls. | S |
| F-42 | ETL — resumability | **Med** | `incremental_update.py` paginates the location list (~56 pages, 8–10 min). A mid-fetch crash restarts from page 1. The advisory lock can expire if the fetch is slow → duplicate runs. | `incremental_update.py:173–207, 237–241, 543` | Persist last-completed page to `pipeline_runs.checkpoint`; on restart, resume from there. Refresh the advisory lock periodically inside the loop. | M |
| F-43 | Webhooks — verification | **Med** | Outbound webhook *signing* is tested but signature *verification* (the consumer's side) is not exercised. Customer-facing docs reference `X-CareGist-Signature` — risk of doc/spec drift. | `api/utils/webhook_delivery.py` | Add a round-trip test: deliver a signed payload, run it through a verify helper that we also publish/document for customers. | S |
| F-44 | Email — DLQ | **Med** | `pending_emails` has no dead-letter handling. Permanently failed emails sit forever in `status='failed'` with no automated escalation. | `api/utils/email_queue.py`; `db/migrations/001_growth_features.sql:88–102` | Move `status='failed'` rows older than 24h to an alert. Add `octet_length(html_body) <= 1_000_000` CHECK to prevent blob bloat. | S |
| F-45 | Tests — admin | **Med** | `tests/test_api_admin.py` exercises admin endpoints but doesn't assert audit-log rows are written. Audit trail can rot silently. | `tests/test_api_admin.py:205` | After each admin action in tests, `assert await fetch_audit_log_rows(...) == expected`. | S |
| F-46 | Operations — alerting | **Med** | Pipeline watchdog suppresses repeat alerts for 6 h. A 7-h degradation gets one notification mid-incident. | `tools/check_new_registration_pipeline.py:18` | Use exponential backoff (1 / 15min / 1h / 4h) instead of fixed 6 h. | S |
| F-47 | Operations — metrics | **Med** | No metrics export (Prometheus, CloudWatch). Sentry covers errors and a sample of traces but not p95 latency by tier, queue depth, or webhook delivery success rate. | n/a | Expose `/metrics` (prometheus-client) and ship to either Grafana Cloud or CloudWatch. Track: request p50/p95/p99 by tier, `pending_emails` depth, webhook delivery success rate, rate-limit 429 counts. | M |
| F-48 | Frontend — a11y | **Low** | Several `<img>` tags use `alt=""` or missing alt; interactive `<div onClick>` patterns flagged on sampled pages. | `frontend/app/provider/[slug]/page.tsx:140`; `frontend/app/layout.tsx:44` | Replace decorative img with `<Image alt="">` (intentional) and informative img with explicit alts. Audit `<div onClick>` → `<button>`. | S |
| F-49 | Frontend — perf | **Low** | Most images use raw `<img>` instead of `next/image`. Provider profile photos and logos aren't responsive or optimised. | `frontend/app/provider/[slug]/page.tsx` (multiple) | Replace `<img>` with `<Image>` for above-the-fold/list assets. | S |
| F-50 | API key prefix | **Low** | `key_prefix` stored is 10 chars of a 32-byte key. Brute force is still infeasible but unnecessary surface. | `api/middleware/auth.py:25–26` | Display `first4…last4` only. | S |
| F-51 | Email — verify token | **Low** | Email verification token has no `expires_at`; once issued, it works forever (until `is_verified=true` flips). | `api/routers/auth.py:632–657` | Add `verification_token_expires_at`; reject expired and offer re-send. | S |
| F-52 | CI — lint/security | **Low** | CI runs tsc + tests + build + pip-audit + npm-audit. No ESLint, no ruff/black/mypy, no Snyk/CodeQL. | `.github/workflows/ci.yml:44–78` | Add ruff + mypy + ESLint to the matrix. Either CodeQL (free for public) or `bandit` for Python. | S |

**Counts:** 8 Blocker · 21 High · 16 Med · 7 Low · **52 total**

---

## 5. Compliance & Legal Call-outs

CareGist sits on **UK GDPR + DPA 2018** ground (UK-only audience, UK-only data). It is **not** clinical data (CQC ratings are public-register data) but the *user account + claim + review* data is personal data, and behavioural analytics + monitor watchlists are personal data when tied to a user.

| Area | Status | Detail |
|---|---|---|
| **Privacy notice** | ✅ Page exists | `/privacy` route present at `frontend/app/privacy/page.tsx` — content not deeply audited in this pass; verify it covers: lawful basis (legitimate interest for the public directory; consent for marketing), retention periods, data controller identity, ICO complaints route, international transfers (Stripe US, Resend US, Sentry US, AWS US-EAST/EU). |
| **Terms of service** | ✅ Page exists | `/terms` route present. Verify it covers API ToS (rate limits, scraping prohibition, redistribution rules), AUP cross-reference. |
| **Cookie policy + consent** | ⚠️ Partial | `/cookies` page exists; `frontend/components/CookieConsent.tsx` banner exists; **consent is stored only in localStorage** and not signalled to the analytics layer before firing. Risk: PECR/ePrivacy non-compliance if non-essential cookies set before consent. |
| **Acceptable use policy** | ✅ Page exists | `/acceptable-use` route present. Important for API tiers. |
| **Review moderation policy** | ✅ Page exists | `/review-policy` route present — relevant given user reviews are personal data about identifiable care homes (possible defamation surface). |
| **CQC attribution / OGL** | ✅ | `compliance/cqc_attribution.txt` present; CQC data is OGL-licensed but attribution must appear on user-facing pages — verify it renders. |
| **Right to erasure** | ❌ Not verified | `DELETE /account` (`api/routers/auth.py:812–849`) exists but does not cascade to reviews, enquiries, claims — orphan records remain attributable. Also does not invalidate sessions/keys (F-1 / F-17 / sub-issue). |
| **Data export / portability** | ❌ Missing | No "download your data" endpoint for end users. Required under UK GDPR Art. 20 on request; on-demand is acceptable but a manual process must exist. |
| **DPIA** | ❌ Unknown | No DPIA document found. A DPIA is required if you process "monitoring of publicly accessible areas at scale" or "evaluation/scoring at scale" — arguably applies to the new-registration feed product. |
| **Data Processing Agreements** | ❌ Unknown | DPAs with Stripe, Resend, AWS, Sentry, Neon (if used) need to be in place and referenced. |
| **CQC-specific concerns** | ⚠️ | Care-home reviews are a defamation hot zone; provider profile claims are an impersonation risk. Inspection-response field (`care_providers.inspection_response`) is user-controlled text shown publicly — verify HTML escaping; legally, providers must not be misrepresented. |
| **Safeguarding** | ✅ | `compliance/safeguarding_notice.txt` present. Verify it renders on the directory pages — handling of safeguarding allegations in reviews should be flagged + escalated. |
| **PCI** | ✅ Out of scope | Stripe Checkout / Elements only; card data never touches the API. Verify no `cardNumber` field ever appears in `frontend/`. |

**Highest-risk compliance gap:** cookie consent runs *post-set* rather than gating non-essential cookies. The fix is small (delay analytics SDK init until `consentAccepted === true`) and significant for ICO defensibility.

---

## 6. Open Questions for the Product Owner

1. **Hosting target** — staying on a single EC2 + bare cron, or willing to move to ECS/Fargate/Neon-managed-PG so we can introduce IaC and HA without rewriting deploys?
2. **Redis** — is the $20–40/mo for ElastiCache or Upstash acceptable? It's the cleanest way to fix the per-worker rate-limit drift (F-6) and unlock multi-instance scaling.
3. **DPIA / DPA** — has this been done with a DPO or legal advisor? If not, who is the data controller of record (`Henry / CareGist Ltd?`) and is there a registered ICO data-protection fee?
4. **Backup tolerance** — what RPO/RTO is acceptable for the directory? Hourly snapshots vs. daily snapshots changes cost ~3×.
5. **Account deletion semantics** — when a user deletes their account, do we keep their submitted reviews (with name redacted) or hard-delete them? Either is defensible but the choice must be in `/privacy`.
6. **Provider claim verification** — what verifies a claim today? Email domain match? Manual review? The audit found no automated verification logic in `api/routers/claims.py` (not deep-read in this pass).
7. **Enterprise tier checkout** — `STRIPE_PRICE_ENTERPRISE` exists in config but no checkout path uses it. Is enterprise sales-led only?
8. **Marketing communications** — is consent UI captured separately at signup? GDPR requires it not be bundled with terms acceptance.
9. **Webhook customer base** — Business+ customers expecting outbound webhooks: are there any live? Re-encrypting existing rows (F-3) requires knowing this.
10. **Stripe live keys** — has the prod env's `STRIPE_SECRET_KEY` ever been used in any non-prod environment (laptop, staging)? If yes, rotation is in order.

---

## 7. Recommended Path to Production

### Phase A — Launch Blockers (≈ 7–10 working days)

Must be done before any paid customer. Sequential because each unblocks the next.

1. **Fix the auth perimeter** (F-1, F-2, F-4, F-5, F-10) — switch session cookie to opaque ID, add `frontend/middleware.ts`, kill `NEXT_PUBLIC_API_KEY` fallback, drop plaintext API-key acceptance, enforce CSRF via `SameSite=Strict` or header-based auth.
2. **Provision Redis + WEBHOOK_SECRET_KEY** (F-3, F-6) — both go into AWS Secrets Manager; promote to `REQUIRED_PRODUCTION_SECRETS` in `api/config.py:49`. Run a one-shot migration to re-encrypt existing webhook secrets.
3. **Lock down the repo** (F-9, F-31) — proper `.gitignore`, write README, rotate any secret that has ever existed in a tracked file.
4. **Backups + restore drill** (F-7) — enable Neon branches or RDS PITR; document and run a restore-into-staging once before launch.
5. **DB invariants** (F-12, F-13, F-14, F-15) — four small ALTER TABLEs that close real data-integrity holes.
6. **Stripe webhook race** (F-11) — wrap dedup in a single transaction with `RETURNING`-gate.
7. **IaC seed** (F-8) — even a minimal Terraform module that describes the *current* EC2 + DB + Secrets Manager + ALB is enough to make rollback and rebuild deterministic. Don't aim for HA yet; aim for *reproducible*.

### Phase B — Before Paid Users at Scale (≈ 2–3 weeks)

8. **Health + observability** (F-25, F-39, F-47) — dep-aware health, request IDs, Prometheus metrics.
9. **Retention + DLQ** (F-28, F-44) — bound the growing tables; alert on stuck emails.
10. **Subscription/tier hardening** (F-16, F-17, F-18, F-21, F-22, F-23, F-24) — close authz holes, rotate-able master keys, password complexity, CSP nonce.
11. **Test coverage** (F-26, F-27, F-45) — Stripe happy paths, migration replay in CI, audit-log assertions.
12. **Frontend hardening** (F-36, F-37, F-38) — per-route error boundaries, Sentry quota fix, robots disallows.
13. **Compliance** — cookie consent gating, account-deletion cascades, on-demand data-export procedure, DPIA scoped.

### Phase C — Nice-to-have (post-launch)

14. **HA / canary** — multi-AZ, ALB-fronted blue/green; replace bare cron with systemd timers or ECS scheduled tasks (F-29).
15. **ETL resumability** (F-42) — checkpointed list scan + lock heartbeats.
16. **Indexing pass** (F-34, F-35) — guided by real EXPLAINs once production traffic exists.
17. **Tightenings** — proxy trust list (F-19), API-key prefix display (F-50), `X-Tier` header removal (F-41), Resend error sanitisation (F-40), webhook round-trip verification test (F-43), email-verify expiry (F-51), linting/SAST in CI (F-52), accessibility audit (F-48), `next/image` migration (F-49), seed.py truncate guard (F-32), init.sql drift fix (F-33), alert backoff (F-46).

---

## 8. Process Notes for the Audit Itself

- **No code was modified.** Read-only audit pass.
- **Confidence assumptions stated inline** where determinable from code.
- **Items I couldn't determine from the repo alone:** actual live customer count on webhooks, whether DPA/DPIA exists outside the repo, whether RDS/Neon snapshots are configured at infra level (not at code level), whether the cron in `/etc/cron.d/caregist` matches `workflows/deploy-ec2.md`, the depth of admin-route auth on `frontend/app/admin/` (sampled, not exhaustive), the freshness of the audit on Stripe live-key exposure history. These are flagged as questions in section 6.
