# CareGist — Codebase Audit Against VA Sales Claims and Market Readiness

You are a principal engineer auditing the CareGist codebase. Your job is to
verify that every claim made to customers and every feature described in the VA
sales training is actually implemented, correctly gated, and production-safe.

You are NOT writing new features. You are reading, searching, and reporting.
Do not modify any file unless you discover a critical security defect so severe
that leaving it unpatched before the report is completed would be negligent —
in which case, fix it, state what you changed and why, and continue.

At the end of every section, write a verdict line:
  PASS — claim is supported and implementation looks correct.
  WARN — claim is partially supported or has a condition attached.
  FAIL — claim is not supported, mis-implemented, or contradicts the codebase.
  MISSING — the feature or file does not exist at all.

Produce a structured audit report. Be specific: file name, line number or
function name, exact quote from the code where relevant.

---

## SECTION 1 — TIER AND PRICING ACCURACY

The VA training document makes the following pricing claims. Verify each
against `api/config.py` (the `TIERS` dict and any related constants).

1.1  Free tier exists with: 2 req/s rate limit, 20 calls/day, 10 feed rows,
     view-only (no export), 1 user.
     Check: does the free tier in `TIERS` match these constraints exactly?

1.2  Alerts Pro tier exists at £49/month with: 5 req/s, 200 calls/day,
     no feed (monitoring/alerts only), no export, 1 user.
     Check: is this tier present in `TIERS`? Is it named `alerts-pro`?
     Is there a Stripe price ID env var (`STRIPE_PRICE_ALERTS_PRO`) wired up
     in `api/config.py` and `api/routers/billing.py`?

1.3  Starter tier: £99/month, 10 req/s, 500 calls/day, 25 feed rows,
     CSV/XLSX export, 1 user.
     Verify field values in `TIERS`.

1.4  Pro tier: £199/month, 25 req/s, 2,000 calls/day, 50 feed rows,
     20 saved filters, 3 users.
     Verify. Also check whether seat add-ons (`STRIPE_PRICE_PRO_SEAT`,
     £15/seat/month) are referenced in billing router.

1.5  Business tier: £499/month, 60 req/s, 10,000 calls/day, 100 feed rows,
     100 saved filters, webhooks enabled, 10 users.
     Verify. Check that `webhooks` feature is gated to Business+ only.

1.6  Enterprise tier: 200 req/s, 50,000 calls/day, 250 feed rows,
     500 saved filters, webhooks, 10 users.
     Verify.

1.7  Provider listing tiers exist with these prices:
     - Claimed: free
     - Enhanced/Pro: £99/month/location (`STRIPE_PRICE_PROFILE_ENHANCED`)
     - Sponsored: £149/month/location (`STRIPE_PRICE_PROFILE_SPONSORED`)
     Check that these Stripe price env vars are referenced in billing or
     provider-profile router. Check `care_providers.profile_tier` is a
     recognised column in `db/init.sql` or migrations.

1.8  Plan names: the VA uses "Starter", "Pro", "Business", "Alerts Pro".
     Confirm these are the actual tier key names in the codebase, not aliases.
     If the UI or API returns different names, flag it — the VA and the
     product must use the same vocabulary.

---

## SECTION 2 — FEATURE GATE ACCURACY

The VA makes specific claims about which features are available on which
plans. Verify each gate in the actual auth middleware and route handlers.

2.1  New Provider Lead Feed requires Starter or above.
     Find where the feed endpoint (`GET /api/v1/feed/new-registrations`)
     checks the caller's tier. Confirm it rejects Free and Alerts-Pro.

2.2  Feed exports (CSV, XLSX) require Starter or above.
     Find the export endpoint. Confirm tier check. Confirm the export
     actually produces a real CSV/XLSX — not a stub or TODO.

2.3  Saved filters: Starter gets 3, Pro gets 20, Business gets 100.
     Find where saved filter count is enforced. If it is not enforced,
     state FAIL and the location where it should be.

2.4  Webhooks are Business+ only.
     Find the gate on `POST /api/v1/webhooks`. Confirm Starter and Pro
     cannot register webhook subscriptions.

2.5  Team seat enforcement: auth middleware must reject API key creation
     if `active_keys >= max_users`.
     Find this check in `api/middleware/auth.py` or `api/routers/auth.py`.
     Confirm it is enforced on every key-creation path, not just one.

2.6  Field filtering: `filter_fields()` in `api/config.py`.
     Confirm that restricted fields return `None` (not omitted) for
     lower-tier callers so the API schema shape stays consistent.
     Sample at least three fields and confirm the behaviour.

2.7  Rate limiting: per-key in-memory rate limiting is in
     `api/middleware/rate_limit.py`. Per-IP rate limiting is in
     `api/middleware/ip_rate_limit.py`.
     Confirm both are registered as middleware in `api/main.py`.
     Confirm per-key limits use values from `TIERS`, not hardcoded numbers.

2.8  Monitor/rating-change alerts.
     The VA may reference the Alerts Pro tier as being for "monitoring
     rating changes". Confirm `tools/send_monitor_alerts.py` exists and
     is functional (reads from `rating_changes` table, sends via email
     queue). Confirm it is gated to the correct tier (Pro+ per CLAUDE.md).
     Note any discrepancy between the tier the VA was trained on and the
     tier gate in code.

---

## SECTION 3 — NEW PROVIDER LEAD FEED INTEGRITY

3.1  `trusted_event_ledger` is the source of truth for new registrations.
     Confirm the feed service (`api/services/new_registration_feed.py`)
     reads from this table and not directly from `care_providers`.
     Confirm dedup logic uses `dedupe_key` with format
     `new_registration:{location_id}:{registration_date}`.

3.2  `tools/run_new_registration_feed_cycle.py` exists and:
     - syncs from `care_providers` to `trusted_event_ledger`
     - triggers webhook delivery
     - queues digest emails
     Confirm all three actions are present. Note any that are missing
     or commented out.

3.3  Feed digest subscriptions.
     Confirm `PUT /api/v1/feed/new-registrations/digest` exists and is
     gated to Starter+. Confirm the weekly digest is actually queued
     (entries written to `pending_emails` or a digest delivery table).

3.4  Webhook delivery.
     Confirm `api/utils/webhook_delivery.py` signs payloads with
     HMAC-SHA256. Check what secret it uses and confirm it comes from
     the `webhook_subscriptions` table (per-subscription secret), not a
     global env var. Confirm retry logic exists.

---

## SECTION 4 — PROVIDER VISIBILITY LISTING

4.1  Claiming flow.
     Confirm that a "claim this listing" mechanism exists — either an
     endpoint in `api/routers/claims.py` or `api/routers/provider_profile.py`.
     What does the VA need to tell providers to do? Does the endpoint
     actually set `care_providers.is_claimed = true`?

4.2  Profile tier enforcement.
     Confirm `care_providers.profile_tier` column exists (in `db/init.sql`
     or a migration). Confirm the provider profile router enforces that
     only the owning claimed provider can edit their own profile fields.

4.3  Sponsored placement.
     The VA says Sponsored providers get "stronger placement in search
     results". Find where the provider search endpoint
     (`GET /api/v1/providers`) applies sponsored boosting. If it does not
     exist, state FAIL.

4.4  Photo and description fields.
     Confirm `profile_photos`, `profile_description`, `virtual_tour_url`
     columns exist and are returned in API responses for providers with
     the correct `profile_tier`.

---

## SECTION 5 — DATA INTEGRITY AND COVERAGE CLAIMS

5.1  England-only coverage.
     The VA is instructed to tell customers CareGist covers England only.
     Confirm there is no data for Scotland/Wales/NI providers in the schema
     or ETL pipeline. Check `extract_cqc.py` — does it pull from the CQC
     public API (which is England-only by definition)? Is there any
     geographic filter applied, or is it implicitly England-only because
     CQC is England-only?

5.2  Provider count.
     CLAUDE.md states 55,818+ providers. Check whether this figure is
     hardcoded anywhere (e.g. a homepage stat, a config constant, a
     marketing copy file). If hardcoded, flag it — this number needs to
     be live from the database, not a static string.

5.3  Data refresh cadence.
     The VA is instructed to say the feed is "updated regularly" without
     specifying a frequency. Check whether the feed cycle tool has any
     documented or enforced run schedule (e.g. a cron comment, a
     workflow file in `workflows/`). Report what the actual cadence is
     or whether it is undefined.

5.4  Contact data.
     The VA claims providers have "phone, website where available".
     Confirm `care_providers` has `phone` and `website` columns.
     Check `clean_cqc.py` for how phone numbers are normalised (UK format
     via `phonenumbers` library). Spot-check that these fields are
     included in feed response payload.

---

## SECTION 6 — SECURITY HARDENING

Work through each item below. For each, state the file and line where the
control is implemented, or FAIL/MISSING if it is absent.

6.1  Stripe webhook signature verification.
     Find the Stripe webhook endpoint in `api/routers/billing.py`.
     Confirm it verifies the `Stripe-Signature` header using
     `stripe.Webhook.construct_event` before processing any event.
     Confirm the raw request body is used (not the parsed JSON) for
     verification. A webhook handler that parses JSON before verifying
     the signature is vulnerable.

6.2  Stripe environment guard.
     CLAUDE.md states the API refuses to start with `sk_live_` if the
     DATABASE_URL is the localhost default. Find this guard in
     `api/main.py` or `api/config.py`. Confirm it raises an error at
     startup, not at runtime.

6.3  Internal endpoint token guard.
     `api/routers/internal.py` is gated by `SUPPORT_INTERNAL_TOKEN`.
     Confirm comparison uses `secrets.compare_digest` (timing-safe),
     not `==`.

6.4  CORS configuration.
     Find CORS setup in `api/main.py`. Confirm allowed origins are
     read from `CORS_ORIGINS` env var and are not `*` in production.
     Confirm credentials are not allowed from wildcard origins.

6.5  SQL injection.
     The codebase uses raw SQL via `asyncpg`. Inspect
     `api/queries/` — confirm all user-supplied values are passed as
     query parameters (`$1`, `$2` placeholders), never via f-strings
     or string concatenation. Flag any instance of f-string SQL
     construction as a critical finding.

6.6  API master key protection.
     `API_MASTER_KEY` has no default in config. Confirm it is
     `Required` (not optional with a default). Confirm the app will
     not start without it.

6.7  Password storage.
     Find where passwords are hashed in `api/routers/auth.py`.
     Confirm bcrypt or argon2 is used, not MD5/SHA1/SHA256 directly.

6.8  Password reset tokens.
     `password_reset_tokens` table exists. Confirm tokens are:
     - cryptographically random (not sequential IDs)
     - time-limited (expiry column exists and is checked)
     - single-use (deleted or invalidated after use)

6.9  Rate limiting on auth endpoints.
     Login and password-reset endpoints are targets for brute force.
     Confirm they are covered by the IP rate limiter
     (`api/middleware/ip_rate_limit.py`), not only by the per-key
     limiter (which requires a valid key).

6.10 Sentry DSN.
     Confirm Sentry is initialised in `api/main.py` only when
     `SENTRY_DSN` is set (not unconditionally). Confirm
     `traces_sample_rate` is set to a value below 1.0 in production
     to avoid performance overhead.

6.11 Outbound webhook secret storage.
     Confirm that per-subscription HMAC secrets in
     `webhook_subscriptions` are not returned in any API response
     (i.e. the secret is write-only — set on creation, never read
     back). Check the webhook listing endpoint if one exists.

6.12 Dedup window for Stripe events.
     `stripe_processed_events` table tracks processed event IDs with
     a 24-hour dedup window. Confirm the billing router checks this
     table before processing any Stripe event, and inserts the event ID
     after processing (not before, to avoid skipping events on failure).

---

## SECTION 7 — OPERATIONAL READINESS

7.1  Email queue drain.
     Confirm `process_email_queue()` in `api/utils/email_queue.py`
     is called on every health check request. Confirm it drains a
     bounded batch (not unbounded) to avoid health check timeouts.
     What is the batch size?

7.2  Health endpoint.
     `GET /api/v1/health` must return 200 with minimal latency.
     Confirm it does not make blocking DB calls beyond the email drain.
     Confirm the email drain failure does not cause the health check
     to return a non-200 status (a failed email drain should log, not
     crash the health check).

7.3  Migration runner idempotency.
     `db/apply_migrations.py` tracks applied migrations in
     `schema_migrations`. Confirm it will not re-apply a migration
     that is already recorded, even if run multiple times. Confirm
     migrations run in numeric order.

7.4  Pending emails failure handling.
     In `api/utils/email_queue.py`, if the Resend API call fails,
     confirm the email is not permanently lost. Check whether failed
     sends increment an `attempts` counter and set a `send_after`
     backoff. Check whether there is a max-attempts limit after which
     emails are marked as permanently failed rather than retried
     forever.

7.5  Feed cycle error handling.
     In `tools/run_new_registration_feed_cycle.py`, if a webhook
     delivery fails, does the tool continue processing other webhooks,
     or does it abort the whole cycle? Confirm failed deliveries are
     logged and retried independently.

7.6  Geocoding cache.
     `postcode_cache` table caches geocoding from postcodes.io.
     Confirm `prepare_directory.py` reads from this cache before
     hitting the external API. Confirm stale or failed lookups are
     handled gracefully (not silently dropped).

7.7  ISR cache consistency.
     CLAUDE.md states the frontend uses `revalidate: 3600` (1-hour
     ISR cache). Confirm this is set in `lib/api.ts` or the relevant
     `fetch()` calls. Flag any provider or feed pages that use
     `revalidate: 0` (which would bypass caching) or have no
     `revalidate` set (which would cache forever until a rebuild).

7.8  Frontend API key exposure.
     CLAUDE.md explicitly warns: "Never set `NEXT_PUBLIC_API_KEY`".
     Search the entire `frontend/` directory for any reference to
     `NEXT_PUBLIC_API_KEY`. If found anywhere — env files, code,
     comments — this is a FAIL and a security finding.

---

## SECTION 8 — CONSISTENCY BETWEEN SALES CLAIMS AND CODE CONSTANTS

8.1  "Provider Intelligence Dossier" as a product.
     Search the entire codebase for any endpoint, service, or config
     that implements a "dossier" or "provider intelligence" product.
     If no such implementation exists, state MISSING and note that the
     VA is being trained to sell a product that has no backend.

8.2  Dossier pricing "from £2.50".
     Is this price defined anywhere in the codebase? If not, state
     MISSING. The VA cannot sell something with no billing implementation.

8.3  "Provider Intelligence Dossier included in bulk packs / higher plans."
     Check `api/config.py` `TIERS` dict for any dossier allowance field.
     If absent, state MISSING.

8.4  API documentation.
     `/docs` (FastAPI auto-docs) will be publicly accessible unless
     disabled. Determine whether `/docs` and `/redoc` are enabled in
     production. If they expose internal schema details (admin tiers,
     internal endpoints, etc.), this is a WARN — consider disabling
     them in production.

8.5  Admin tier exposure.
     The `admin` tier is listed in `TIERS` with unlimited access.
     Confirm it is not purchasable via Stripe (i.e. there is no
     `STRIPE_PRICE_ADMIN` and no Stripe checkout path that results in
     `tier = admin`). Admin keys must only be created by a server-side
     process with the master key.

---

## OUTPUT FORMAT

Produce your report under these headings, in this order:

### CRITICAL FINDINGS
Issues that could cause a data breach, financial loss, or allow unauthorised
access. Must be resolved before launch.

### HIGH FINDINGS
Features the VA is selling that are not implemented, or pricing/tier gates
that are wrong. Will result in customer complaints or refunds.

### MEDIUM FINDINGS
Partial implementations, missing error handling, operational gaps.
Should be resolved within one sprint of launch.

### LOW FINDINGS
Minor inconsistencies, documentation gaps, hardcoded values that should
be dynamic.

### PASSED CHECKS
A concise list of everything that checked out correctly.

### LAUNCH READINESS VERDICT
One paragraph. State whether the system is ready for the VA team to begin
selling, or what must be resolved first. Be direct.
