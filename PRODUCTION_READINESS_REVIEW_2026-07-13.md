# CareGist production-readiness review — 13 July 2026

## Current state summary

CareGist has strong application-level foundations: revocable browser sessions, hashed API keys, transactional Stripe event deduplication, production secret validation, Redis-aware API rate limiting, structured request-correlated logs, protected metrics, database migration governance, a broad Python test suite, and a buildable Next.js application. The current repository nevertheless describes two competing release architectures: a FastAPI account/billing platform and a Next.js-only directory MVP. The latter links to a Stripe Payment Link but contains no matching paid-entitlement fulfilment path, exposes unauthenticated lead/export routes without distributed abuse controls, and relies on a 53 MB in-process CSV fallback. The application is suitable for staging, but it is not safe to launch to 10,000 paying customers until the blocking items below have evidence.

## Assumptions and correctness criteria

- The current working tree is the release candidate; existing uncommitted changes were preserved.
- Public directory data is not clinical data, but user, lead, claim, review, billing, analytics, and monitoring records are personal or commercially sensitive data.
- Paying customers must receive deterministic entitlements after successful payment, and cancellation/downgrade must revoke them.
- No single process, instance, database connection pool, cron host, or unpackaged local file may be the only recovery path.
- Authentication, authorization, billing, migrations, exports, and webhook handling must fail closed.
- A release requires reproducible CI, a successful migration replay, dependency audits, load evidence, backup/restore evidence, and production smoke tests.

## Production-readiness score

| Area | Rating | Rationale |
|---|---|---|
| Security | NEEDS WORK | Core FastAPI auth is materially hardened; public Next.js lead/export abuse controls, capability-token transport, and production proxy configuration still need deployment evidence. |
| Data integrity | NEEDS WORK | Numbered migrations and Stripe transactions are sound, but migrations 036/037 were not replayed locally and deployed schema state is unknown. |
| Resilience | BLOCKING | The 53 MB per-instance fallback, stateless write degradation, unproven database capacity, and absent HA evidence are not credible for 10,000 customers. |
| Observability | NEEDS WORK | FastAPI has request IDs, Sentry and Prometheus; Next.js lead/export modes rely mainly on console output and a point health route. |
| Operations | BLOCKING | No repository evidence proves PITR, restore drills, HA, infrastructure-as-code, or a deterministic promotion/rollback procedure for the chosen architecture. |
| Billing | BLOCKING | The documented Next.js-only MVP uses an unrelated Payment Link and has no code path that provisions paid access from its completion. |
| UX/accessibility | NEEDS WORK | Error boundaries and degraded search exist, but token URLs, hard export limits, incomplete redirect restoration, and no automated accessibility/browser suite remain. |
| Test coverage | NEEDS WORK | 326 Python tests and 59 frontend tests pass locally; 10 database integration tests were skipped and no load, browser E2E, failover, restore, or live Stripe tests were run. |

## Blocking issues

1. **[Architecture/Billing] Choose one production topology and prove payment fulfilment.** `README.md` says the Python API is not required for the MVP, while `frontend/app/layout.tsx` sends users to `STRIPE_PAYMENT_LINK_URL`; no Next.js handler maps that payment to an account, export entitlement, subscription lifecycle, or cancellation. Either use the FastAPI Checkout/webhook flow end-to-end or implement and test Payment Link fulfilment before accepting money.
2. **[Security/Availability] Add distributed edge rate limits and bot controls to public Next.js routes.** `/api/leads/request`, `/api/export`, search, sitemaps, and health have no application-level distributed quota. Stateless tokens let an unverified email obtain exports, so automated scraping can create database/email load and egress cost. Configure Vercel Firewall/Redis-backed limits, CAPTCHA or equivalent risk checks on lead capture, per-token export quotas, and 429 telemetry.
3. **[Resilience] Remove the full CSV fallback from the request hot path.** Each fresh instance can read and parse a 53 MB CSV into a much larger object graph. Under a database incident, traffic amplifies memory, cold-start, and stale-data pressure. Move fallback reads to a pre-indexed external store or static read service; load test degraded mode before retaining it as a production feature.
4. **[Data/Operations] Replay and apply every migration against the exact production engine.** Local integration tests skipped because no test database was supplied. Run the PostGIS CI service, verify migrations through 037, record schema hashes, and test forward recovery before deployment.
5. **[Operations] Prove backup, PITR, restore, HA, and rollback.** Documentation contains gates but the repository cannot establish that they are configured. Define RPO/RTO, enable automated backups/PITR, restore into an isolated environment, capture timings, and document application rollback when schema rollback is unsafe.
6. **[Capacity] Establish a database and application capacity envelope.** The FastAPI pool permits 20 connections per instance and Next.js permits 5 after this review. At horizontal scale these can still exceed PostgreSQL limits. Use a pooled connection endpoint/PgBouncer, set global budgets, and load test search, export, login, checkout, webhook bursts, and degraded fallback at expected peak concurrency.
7. **[Data/UX] Do not report successful lead capture when no durable channel exists.** If PostgreSQL is down, the route issues a stateless export token. If Resend is also unavailable or unconfigured, the lead is not stored or delivered, but the user sees success. Add a durable queue/store independent of the primary database, or fail the submission clearly.
8. **[Release evidence] Run production-equivalent external smoke tests.** Verify live hosting secrets, Redis TLS/auth, Stripe webhook signatures and retries, Resend SPF/DKIM/delivery, Sentry ingestion, Prometheus scraping, alert routing, database-required smoke tests, and cancellation/downgrade behaviour before traffic cutover.

## Needs work

1. **[Security] Capability tokens appear in query strings.** They can persist in browser history and same-origin access logs/referrers. Exchange lead submission for an HttpOnly, short-lived cookie or POST download authorization; hash database-backed tokens and support key rotation/revocation.
2. **[Data lifecycle] Define retention and deletion for new `leads` and `export_access_tokens`.** Existing pruning covers other tables but not migration 037. Add documented retention, expiry deletion, erasure handling, and access auditing.
3. **[Observability] Instrument Next.js server routes.** Add request IDs, structured redacted logs, Sentry capture, latency/error counters, database/fallback mode counters, export row/byte metrics, and alerts for fallback activation or lead-delivery loss.
4. **[Billing] Add reconciliation and entitlement invariants.** Schedule Stripe reconciliation, alert on webhook lag/failure, and continuously assert that Stripe status, subscriptions, API-key tiers, seats, and profile tiers agree.
5. **[Database] Normalize multi-valued searchable fields.** Pipe-separated `service_types` and `specialisms` require repeated `unnest/string_to_array` work and weaken indexing. Plan normalized join tables or generated/indexed representations before query volume grows.
6. **[Performance] Replace `COUNT(*) OVER()` and unrestricted offset pagination for deep searches.** Capture query plans and introduce cached facets/keyset pagination where evidence shows pressure.
7. **[Security] Remove legacy webhook plaintext compatibility after re-encryption.** Production now requires an encryption key, but decrypt logic still accepts legacy plaintext. Inventory, re-encrypt, verify, then reject plaintext.
8. **[Compliance] Complete UK GDPR/PECR operational evidence.** Confirm lawful bases, consent behaviour, processor DPAs, international transfers, DPIA need, data-subject export/erasure procedure, ICO registration, and review/claim moderation. Obtain legal review rather than relying on code review.
9. **[UX] Restore intended destinations after login.** Middleware supplies `redirect`, but the login page ignores it. Validate an internal-only redirect and return customers to the requested protected page.
10. **[Testing] Add browser and accessibility coverage.** Exercise signup/login/session expiry, checkout/cancel, claims, lead/export, keyboard navigation, mobile layouts, 404/500 states, and degraded database mode with Playwright plus automated accessibility checks.
11. **[Maintainability] Unify dependency manifests and remove test-runner warnings.** Production and development Python manifests can drift; generate both from one locked source. Configure the TypeScript test module format so every run does not reparse files as ESM.
12. **[Repository hygiene] Split release source from large audit/media/data artifacts.** The current working tree contains many screenshots, snapshots, documents, datasets, and tool state files. Keep operational evidence in an artifact store and enforce repository size/secret scanning in CI.

## Changes made in this review

- Removed legacy API-key cookies from browser-session authentication; only revocable session records are accepted.
- Required directory token secrets to contain at least 32 characters and added strict token structure, timestamp, type, and size validation.
- Added lead email/filter length limits before database or email use.
- Neutralized CSV formula injection and capped exports at 10,000 rows with an explicit narrow-filter response.
- Added a five-second Resend timeout and removed lead email/raw database error details from fallback logs and notifications.
- Limited Next.js database pools and connection acquisition time; unexpected SQL/schema defects now surface instead of silently activating fallback.
- Added correct 401/403/413/503 export failure semantics.
- Added missing production API dependencies for cryptography, Redis, and Prometheus; CI now audits the production manifest and builds the production image.
- Replaced wildcard forwarded-header trust with an explicit deployment setting and added a Docker context denylist for local secrets and large data.

## Go-live checklist

### Security

- [ ] Configure explicit `FORWARDED_ALLOW_IPS` and `TRUSTED_PROXY_CIDRS` for the actual ingress; block direct origin access.
- [ ] Add edge/distributed quotas and bot protection to lead, export, search, sitemap, and health routes.
- [ ] Replace URL capability tokens or formally accept and document their leakage/replay model.
- [ ] Run secret scanning across the full Git history and rotate any exposed credential.

### Data

- [ ] Replay migrations 001–037 on clean PostGIS and a production-like snapshot.
- [ ] Apply migrations with recorded hashes and verify invariants after deployment.
- [ ] Add retention/erasure jobs for leads and export tokens.
- [ ] Enable PITR and complete a timed restore drill.

### Resilience

- [ ] Load test normal and degraded modes at the agreed peak concurrency.
- [ ] Replace or isolate the 53 MB in-process fallback.
- [ ] Configure pooled database endpoints and enforce a global connection budget.
- [ ] Prove multi-instance API/frontend behaviour and remove single-host cron dependencies.

### Observability

- [ ] Add structured Next.js route telemetry and fallback/lead-loss alerts.
- [ ] Verify Sentry events, metrics scrape, dashboards, paging, and dead-man alerts in staging.
- [ ] Define SLOs for availability, p95 latency, checkout, export, webhook delivery, and data freshness.

### Operations

- [ ] Select and document the production topology and ownership boundaries.
- [ ] Make infrastructure reproducible with IaC or an equivalently reviewed declarative configuration.
- [ ] Run database-required deployment smoke tests and retain evidence.
- [ ] Document canary, rollback, incident response, key rotation, and disaster recovery.

### Billing

- [ ] Prove payment-to-entitlement fulfilment for the selected Stripe flow.
- [ ] Test webhook duplicates, out-of-order events, cancellation, payment failure, downgrade, and reconciliation.
- [ ] Verify paid feature authorization independently of UI visibility.

### Testing

- [ ] Require Python tests, frontend tests, typecheck, production build, image build, both dependency audits, lint, and migration replay in protected CI.
- [ ] Add Playwright accessibility and critical-flow E2E suites.
- [ ] Add load, failover, restore, and production-like external integration tests.

## Validation performed

- `pytest -q`: 326 passed, 10 skipped (database integration tests skipped without a configured test database).
- `npm test`: 59 passed.
- `npx tsc --noEmit`: passed when run after the production build; an earlier concurrent invocation raced with Next.js replacing `.next/types`.
- `npm run build`: passed; 33 static pages generated.
- `npm audit --omit=dev --audit-level=high`: zero vulnerabilities.
- Evidence-language and migration-governance checks: passed.
- Scoped `git diff --check` for review changes: passed. The whole-worktree check still reports pre-existing trailing spaces in `PRODUCTION_READY.md`.
- Production API image build: passed with a 990 kB context; the previously missing security/metrics dependencies installed successfully.
- Python `pip-audit`, Ruff, live services, migration replay, load, failover, and restore were not locally verified in this environment; CI and pre-launch evidence remain required.
