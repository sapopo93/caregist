# CareGist Radar checkout audit — 2026-08-14

> **Release addendum — 2026-08-14 06:00 UTC:** The original audit below records
> the pre-release state. The owner subsequently directed that both paid products
> be opened immediately. The following production changes supersede the original
> “do not enable” conclusion; the unchanged historical audit remains below for
> traceability.

## Production release addendum

- Deployed release: `201a0c0e9376d9337cc872eab1876ae5a64e5dbb`
- Vercel deployment: `dpl_8fZUaDPzk9WLUL9sKsqSD5tBss7D` (`READY`, aliased to
  `https://www.caregist.co.uk`)
- Live database: migrations 055 and 056 applied; migration history and
  `users_signup_purchase_intent_valid` were verified in the production database.
- Checkout switches: billing and Radar checkout enabled. The operational-readiness
  requirement is explicitly overridden by configuration following the owner's
  instruction; terms acceptance and all Stripe configuration checks remain fail-closed.
- Business Terms: version 2.0, SHA-256
  `55e95bcec0b5f58cecb819406c8d415145d78b6fec475e29b3fc907942f5f810`.
- Stripe webhook `we_1TLKZI4mijLHzRRkzoD75vqv`: corrected to
  `https://www.caregist.co.uk/api/v1/billing/webhook`, status enabled, with exactly
  the seven application-handled checkout, subscription, expiry, and refund events.
- Stripe customer emails: successful-payment receipts and refund emails enabled
  and verified after a settings-page reload. Replies route to
  `support@caregist.co.uk`.
- CareGist customer emails: successful fulfillment now queues an idempotent
  “Your CareGist Radar access is ready” message; subscription termination queues
  an idempotent “Your CareGist Radar subscription has ended” message.

### Live non-charging buyer verification

Two fresh, verified accounts delivering to `henry.mlalazi@gmail.com` exercised the
production buyer journey. Verification emails arrived with SPF, DKIM, and DMARC
passing. No card details were submitted and no charge or subscription was created.

| Step | Regional | National |
|---|---:|---:|
| Public CTA enabled | PASS | PASS |
| Signup intent persisted | PASS | PASS |
| Verification email delivered | PASS | PASS |
| Verified login returns to selected plan | PASS | PASS |
| Business Terms acceptance required | PASS | PASS |
| Live Stripe Checkout created | PASS | PASS |
| Hosted amount | £299/month | £799/month |
| Live Price | `price_1U2Ruk4mijLHzRRk8zoP3Sk3` | `price_1U2Rv74mijLHzRRk89djyvzJ` |
| Success/cancel URLs | PASS | PASS |
| Successful charge | NOT RUN | NOT RUN |
| Webhook entitlement + access email | TESTED IN CODE; NOT LIVE-CHARGED | TESTED IN CODE; NOT LIVE-CHARGED |

The Regional and National sessions are live-mode, open, and unpaid. They will
expire automatically. The pending-operation lock correctly prevented the first
buyer from opening a concurrent second billing change.

### Current release conclusion

Customers can select either paid product and reach the correct live Stripe payment
screen. The prior button, schema, webhook-routing, event-coverage, and receipt-email
blockers are fixed. A real paid purchase and its resulting live entitlement/email
cannot be truthfully marked end-to-end PASS until a valid payment method completes
one live session. Automated coverage proves the webhook state transition,
idempotency, entitlement update, success polling, access-ready email, cancellation,
revocation, and termination email; it does not replace that final live commercial
transaction.

## Executive conclusion

**Radar checkout is not safe to enable yet.** The £299/month Regional and £799/month National Stripe Products and Prices are correct in both test and live mode, and the core code has strong signature, ownership, payment-state, and event-deduplication controls. However, the deployed integration cannot currently complete an end-to-end purchase:

1. The production business, legal, price, and operational-readiness gates are closed.
2. Stripe test mode has no webhook endpoint, so a test payment cannot update CareGist entitlements.
3. The live webhook points to `https://api.caregist.co.uk/api/v1/billing/webhook`; that hostname resolves but timed out on every HTTPS probe. The current backend is reachable at `https://www.caregist.co.uk/api/v1/billing/webhook`.
4. Three code defects would have broken or misreported first-time paid activation. They are fixed in commit `fdfd0c9` on branch `codex/radar-checkout-audit-20260814`, but are not deployed.

No production checkout gate was changed. No live Checkout Session, charge, subscription, webhook endpoint, or Stripe configuration was created or modified.

## Scope and evidence

- Repository: `/Users/user/CareGist`
- Audited production deployment: Vercel deployment `dpl_3vx9k73GBxw7Kybnu851KLbA5M6a`, created 2026-08-13 16:55 BST
- Production health release: `69c1ea0470d7ad3934b5b31d476297cadbf48436`
- Live health observation: 2026-08-14 05:21:20 UTC
- Stripe evidence: authenticated Stripe CLI, read-only list/retrieve calls in test and live mode
- Configuration evidence: Vercel environment metadata and deployed endpoint behaviour; encrypted secret values were not exposed

## A. Exact gate mechanisms and current state

### 1. Human/business checkout gates

The public pricing page computes checkout availability in `frontend/app/pricing/page.tsx:27-30`:

```text
BILLING_CHECKOUT_ENABLED == "true"
AND RADAR_CHECKOUT_ENABLED == "true"
AND B2B_TERMS_VERSION is non-empty
```

`frontend/components/PricingCTA.tsx:137-145` renders the disabled “Paid checkout unavailable” state when that condition is not met.

The backend independently fails closed in `api/routers/billing.py:619-650` before resolving a Price or calling Stripe. Both settings default to `False` in `api/config.py:396` and `api/config.py:405`. Production startup also rejects `RADAR_CHECKOUT_ENABLED=true` unless generic billing is enabled and both Radar Price IDs and the approved terms version/hash are configured (`api/config.py:624-639`).

Effective production state:

| Setting | Current state | Required to pass |
|---|---:|---|
| `BILLING_CHECKOUT_ENABLED` | Empty/effectively false | Exact string `true` |
| `RADAR_CHECKOUT_ENABLED` | Absent/default false | Exact string `true` |
| `STRIPE_PRICE_RADAR_REGIONAL` | Absent | Approved live Price ID |
| `STRIPE_PRICE_RADAR_NATIONAL` | Absent | Approved live Price ID |
| `B2B_TERMS_VERSION` | Absent | Non-empty solicitor-approved version |
| `B2B_TERMS_SHA256` | Absent | SHA-256 of the approved terms |
| Approved catalogue manifest | `checkout_enabled: false` at `deploy/stripe-price-manifest.json:5` | Human-reviewed manifest/config release |

The manifest records the intended IDs, but it is not itself the runtime feature flag.

### 2. Per-buyer legal evidence gate

Even after the global switches are enabled, each buyer must:

1. Check the business-use/authority box in `frontend/components/PricingCTA.tsx:148-160`.
2. Submit the exact deployed `B2B_TERMS_VERSION` (`PricingCTA.handleUpgrade`, lines 65-87).
3. Pass `_verify_contract_acceptance()` in `api/routers/billing.py:352-360`, which rejects missing/stale versions and anything other than literal `true` business authority.
4. Have immutable acceptance evidence written by `_persist_contract_acceptance()` (`api/routers/billing.py:373-396`) before being redirected to Stripe. The database trigger in `db/migrations/044_b2b_contract_acceptance.sql:30-40` prevents later update or deletion.
5. On webhook fulfillment, have the Checkout metadata match that immutable row, including user, version, terms hash, and authority (`api/routers/billing.py:1540-1572`).

This gate is intentionally closed in production because the approved terms version and hash are absent. It was not altered.

### 3. Seven-day source/readiness gate

`create_checkout()` calls `_require_radar_commerce_ready()` at `api/routers/billing.py:515-524`. It loads the live database snapshot from `get_pipeline_health()` and requires `commercialReadiness.checkoutReady=true`.

The exact thresholds are defined in `api/services/pipeline_health.py:18-24` and combined at lines 425-441:

- Required canonical tables, columns, and unique source-snapshot identity.
- Source freshness within 8 days.
- Latest signal poll completed within 75 minutes.
- Source record count reconciled to active CareGist rows.
- At least 336 polls during the last 7 days (48/day).
- At least 99% of those polls completed.
- At least one measured event and p95 `observed_at - source_published_at` no more than 45 minutes.
- Delivery outbox exists, with zero stuck items (older than 15 minutes) and zero dead letters.

Production state at 2026-08-14 05:21:20 UTC:

| Readiness check | Result | Evidence |
|---|---:|---|
| Overall `checkoutReady` | **FAIL** | `false` |
| CQC source watermark | **FAIL** | 12 Aug source; latest authoritative attempt incomplete; no retrieved/reconciled timestamp or checksum |
| Source counts reconciled | **FAIL** | source count unavailable vs 57,779 active rows |
| Seven-day shadow coverage | **FAIL** | 64 total polls, 16 completed, 25%; requires 336 and 99% |
| Source-to-ledger latency | **FAIL** | 219 samples; p95 6,956,491.8 minutes; target 45 minutes |
| Delivery outbox | PASS | 0 pending, 0 stuck, 0 dead letter |

The extreme latency value needs observation, not a gate bypass. The query measures events observed in the last seven days (`api/services/pipeline_health.py:233-243`), while the poller can populate `source_published_at` from an historical CQC report publication date (`tools/poll_cqc_signals.py:195-206,430-437`). Bootstrap/backfill events can therefore inflate the seven-day sample. Those observations age out after seven days; if p95 remains anomalous after a clean seven-day shadow window, the source-time semantics should be corrected under a separate evidence-backed change. This audit did not weaken the threshold.

## B. Full checkout flow

### New buyer and plan selection

1. `PricingPage()` maps the approved catalogue into cards (`frontend/app/pricing/page.tsx:26-125`).
2. `PricingCTA` maps Regional/National to the two saleable billing tiers (`frontend/components/PricingCTA.tsx:21-28`).
3. An unauthenticated buyer follows `/signup?plan=radar-regional|radar-national` (`PricingCTA`, lines 213-223).
4. `SignupForm.handleSubmit()` posts the allowlisted plan to `/api/v1/auth/register` (`frontend/app/signup/page.tsx:44-83`).
5. `RegisterRequest` permits only Free and the two Radar plans (`api/routers/auth.py:174-180`). `register()` creates the user, Free subscription, API key, and structured purchase intent (`api/routers/auth.py:243-290`).
6. `verify_email()` returns a server-owned continuation to `/login?upgrade=<radar-plan>` (`api/routers/auth.py:758-798`), then login returns the buyer to the highlighted pricing card (`frontend/app/login/page.tsx:53-57`).

### Checkout creation

7. `PricingCTA.handleUpgrade()` submits the plan, authenticated email, terms version, and authority to `POST /api/v1/billing/checkout` (`frontend/components/PricingCTA.tsx:65-102`).
8. The Vercel service rewrite routes `/api/v1/*` to FastAPI (`vercel.json:75-81`).
9. `create_checkout()` (`api/routers/billing.py:619-945`) verifies, in order:
   - both global checkout flags;
   - current legal acceptance;
   - browser-session ownership and verified email;
   - an allowlisted saleable tier and zero extra seats;
   - live operational readiness;
   - authenticated user/email ownership;
   - whether this is a safe existing-subscription change or a new subscription.
10. `_base_price_for_tier()` uses server configuration only (`api/routers/billing.py:425-427`); client-supplied Price/amount/cadence fields are forbidden by the request model.
11. `_reserve_billing_operation()` serializes concurrent checkout attempts per account and produces the stable Stripe idempotency key (`api/routers/billing.py:108-174`).
12. A Stripe Customer is created idempotently when needed (`create_checkout`, lines 853-863).
13. `stripe.checkout.Session.create()` creates a subscription Checkout with the approved Price, first-party success/cancel URLs, immutable metadata, a 30-minute expiry, and no hard-coded `payment_method_types` (`create_checkout`, lines 883-912).
14. `_persist_contract_acceptance()` and `_record_operation_object()` must succeed locally; otherwise the newly created Stripe Session is expired (`create_checkout`, lines 913-942).
15. The browser performs a full navigation to Stripe (`PricingCTA`, lines 100-102).

### Webhook, persistence, and entitlement

16. Stripe posts to `POST /api/v1/billing/webhook`, mounted by `api.main` through `billing.router`.
17. `stripe_webhook()` (`api/routers/billing.py:1324-1412`) requires the configured secret and verifies `Stripe-Signature` before parsing the event.
18. The event ID is inserted into `stripe_processed_events` inside the same transaction as fulfillment. Duplicate or concurrent deliveries do no work; handler failure rolls back the event ID so Stripe can retry (`stripe_webhook`, lines 1354-1410; schema at `db/migrations/016_stripe_event_deduplication.sql`).
19. `checkout.session.completed` and `checkout.session.async_payment_succeeded` route to `_handle_checkout_completed()` (`api/routers/billing.py:1540-1653`).
20. The handler re-verifies immutable legal evidence, valid payment state, authoritative Stripe Subscription/customer, exact base Price/tier, and seat quantity.
21. `_persist_subscription_state()` (`api/routers/billing.py:430-512`) writes the subscription and retiered API-key entitlements atomically. Commit `fdfd0c9` now retires the registration-created Free row before the first paid insert.
22. `GET /api/v1/billing/subscription` (`api/routers/billing.py:1103-1137`) returns server-authoritative entitlements for the authenticated user.
23. The dashboard updates browser display state from that endpoint; Radar API access remains enforced server-side by authenticated tier/entitlement checks.

### Success, cancellation, and failed payment

- Stripe success redirects to `/dashboard?session_id={CHECKOUT_SESSION_ID}`. Commit `fdfd0c9` adds `GET /api/v1/billing/checkout-session/{session_id}` (`api/routers/billing.py:1141-1211`) and bounded polling in `frontend/app/dashboard/page.tsx:105-133`. It confirms success only when the Session belongs to the current user, Stripe reports valid completed payment, and the matching local subscription is entitled. It never grants access itself.
- Checkout cancellation returns to `/pricing` without a charge (`create_checkout`, line 891). There is no dedicated cancellation banner, but no entitlement mutation occurs.
- Account cancellation uses `POST /api/v1/billing/subscription/cancel` (`api/routers/billing.py:1222-1297`) or Stripe Billing Portal (`api/routers/billing.py:1300-1321`). It preserves access until period end, which matches “cancel at period end.”
- `customer.subscription.deleted` invokes `_handle_subscription_deleted()` (`api/routers/billing.py:1751-1785`) and writes Free tier/canceled status, revoking paid API-key entitlements.
- Declined Checkout payments cannot pass the `paid|no_payment_required` check. `customer.subscription.updated` invokes `_handle_subscription_updated()` (`api/routers/billing.py:1656-1748`); any state outside `active|trialing`, including `past_due` or `unpaid`, is persisted with effective Free entitlements.

## C. Stripe wiring verification

### Products and Prices

Read-only Stripe retrieval matched `deploy/stripe-price-manifest.json` exactly:

| Mode | Plan | Product | Price | Amount/recurrence | Result |
|---|---|---|---|---|---:|
| Test | Regional | `prod_V2WsV3wis15Jwl` | `price_1U2Rol4mijLHzRRk9aku2utp` | GBP 29,900/month | PASS |
| Test | National | `prod_V2WtFqQyMHHTeL` | `price_1U2RpS4mijLHzRRkyKjdbowD` | GBP 79,900/month | PASS |
| Live | Regional | `prod_V2WyLyVAIOkj3v` | `price_1U2Ruk4mijLHzRRk8zoP3Sk3` | GBP 29,900/month | PASS |
| Live | National | `prod_V2WzvW9HP6GNqn` | `price_1U2Rv74mijLHzRRk89djyvzJ` | GBP 79,900/month | PASS |

All four Products are active, correctly named, and carry the expected `caregist_plan`, `catalog_version=2026-08`, and `sale_channel=self-serve-gated` metadata. Test/live IDs are distinct.

The production environment does **not** currently assign the live Radar Price IDs, so correct Stripe objects exist but are not wired into checkout.

### Key and API-version separation

- Code keeps secret key, signing secret, and Price IDs server-only (`api/config.py:23-42`).
- Test and live catalogue IDs are explicitly separate.
- The deployed webhook route proves a Stripe API key and signing secret are loaded: an unsigned request to the current `www` endpoint returned HTTP 400 “Invalid webhook signature,” not the 503 missing-configuration response.
- The secret values and deployed key prefix could not be read through Vercel because they are encrypted. Therefore the production key's live/test prefix is **not independently verified** by this audit.
- `requirements-api.txt:6` declares `stripe>=8.0.0` without an upper bound or lock; the audited local environment resolved 15.4.0. That is non-deterministic for a regulated deployment.
- The live webhook endpoint uses Stripe API version `2026-01-28.clover`, behind the current integration guidance version `2026-06-24.dahlia`. Upgrade should be rehearsed in test mode, not changed directly in production.

### Webhook endpoints and event coverage

Test mode: **no webhook endpoints configured**.

Live CareGist endpoint:

- ID: `we_1TLKZI4mijLHzRRkzoD75vqv`
- URL: `https://api.caregist.co.uk/api/v1/billing/webhook`
- Status: enabled in Stripe, but HTTPS probes timed out
- Subscribed: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `invoice.paid`, `invoice.payment_failed`, `invoice.payment_action_required`, `customer.subscription.paused`, `customer.subscription.deleted`

Code/event configuration mismatch:

- Code handles but live endpoint does not subscribe: `checkout.session.async_payment_succeeded`, `checkout.session.expired`, `charge.refunded`, `charge.refund.updated`.
- Live endpoint sends but code currently logs as unhandled: `customer.subscription.created`, invoice events, and `customer.subscription.paused`.
- Core card Checkout activation, subscription status change, and deletion event names overlap, but the unreachable URL makes that overlap moot.

The endpoint URL/event selection and signing secret must be corrected in Stripe under a controlled deployment change. This audit intentionally did not mutate the live endpoint.

### Idempotency and ownership

PASS in code and tests:

- Customer creation, Checkout creation, subscription changes, and cancellation use idempotency keys.
- `billing_operations` has a partial unique pending-owner index, preventing concurrent duplicate Checkout/change mutations.
- Webhook event IDs are transactionally deduplicated.
- Subscription persistence upserts on unique Stripe subscription ID.
- Checkout metadata is not trusted alone: the handler retrieves authoritative Stripe Subscription state and verifies customer, Price, tier, and quantity.
- Browser billing endpoints scope every read/write to authenticated `user_id`; return verification additionally matches the Stripe Customer.

The billing tables do not use PostgreSQL RLS. Isolation is enforced by the trusted backend and user/customer predicates rather than direct-client database policies. No cross-account billing query was found. This is acceptable only while clients cannot connect directly to Neon; introducing a direct data API or organization-owned billing would require RLS/organization-scoped entitlement design before launch.

## D. Test-mode end-to-end results

There is a Neon staging database resource, but there is no complete Stripe staging environment:

- The active Vercel project has no test Stripe secret/Price/webhook configuration for this branch.
- Stripe test mode contains the correct Products and Prices but zero webhook endpoints.
- No protected preview URL is wired to both the staging database and test Stripe.
- Local Docker/Postgres was not running. The integration suite correctly refuses production or remote database URLs.

Accordingly, an honest browser/card/webhook/database E2E could not be run. No step was silently skipped:

| E2E step | Result | Evidence/blocker |
|---|---:|---|
| Select Regional/National plan | PASS (code/tests) | Allowlisted paths and pricing contracts |
| Create app Checkout Session in test mode | BLOCKED | No Stripe-enabled staging app/config |
| Complete with Stripe test card | BLOCKED | No app-created test Session |
| Test webhook fires | FAIL (configuration) | Test mode has zero webhook endpoints |
| Subscription record written | BLOCKED E2E | No webhook path; real-DB test environment unavailable |
| User gains Radar access | BLOCKED E2E | Depends on prior steps |
| Declined/failed payment stays unentitled | PASS (unit semantics), BLOCKED E2E | Handler tests pass; no staging Stripe path |
| Duplicate webhook changes state once | PASS (unit semantics), BLOCKED E2E | Transaction/dedup tests pass; no staging webhook |
| Cancellation revokes at period end | PASS (unit semantics), BLOCKED E2E | Delete/update handlers tested; no staged subscription |

Automated validation completed:

- `666 passed, 22 skipped` for the full Python suite. Skips are environment-gated real database/local transcription tests.
- `140 passed` for frontend tests.
- Next.js production build and TypeScript passed.
- Ruff passed for affected Python files.
- Migration governance and `git diff --check` passed.

## E. Bugs found and fixed

All fixes are in commit `fdfd0c9` (`fix(billing): make Radar checkout fulfillment retry-safe`).

1. **Radar signup database constraint mismatch — fixed.** API and UI allowed the Radar plans, but migration 045 and `init.sql` allowed only retired plan values. A real Radar registration could fail at the user insert. Migration 056 and fresh schema now allow the two current plans while retaining historical values; invalid plans still fail closed.
2. **First paid subscription collided with active Free row — fixed.** Registration creates an active Free row and the database permits only one active subscription per user. Webhook fulfillment inserted the paid row without retiring Free, so first activation could fail forever on the unique index. `_persist_subscription_state()` now supersedes older entitled rows in the same transaction before upsert.
3. **Success redirect/webhook race and false conversion — fixed.** The dashboard fetched subscription state once and tracked conversion merely from an untrusted `session_id` query parameter. It now polls a read-only authenticated status endpoint and confirms only when Stripe and local entitlement agree; delayed fulfillment remains visibly pending and never grants browser-side access.

## F. Unverified or externally blocked items

- Actual Vercel production Stripe key prefix and exact signing-secret match: secrets are encrypted and were not exposed.
- Real webhook delivery attempts: no safe staging destination exists, and no live event was triggered.
- Real database migration/transition execution: 22 integration tests were skipped because no isolated local Postgres was available. Unit coverage passed, but the new migration and Free-to-paid transition must run against an isolated Postgres before deployment.
- Stripe-hosted decline, SCA/action-required, async payment, refund, portal cancellation, and period-end deletion flows: require the staged test webhook path.
- Current live endpoint repair: changing Stripe endpoint URL/events/secret is production configuration, outside the branch-only remediation authority in this audit.
- Latency anomaly: likely influenced by historical report dates during bootstrap; it must be re-measured after a complete clean seven-day window before changing logic.

## G. Enablement recommendation

**Do not enable production checkout now.** After commit `fdfd0c9`, the code is materially safer but the integration is still unproven and the live webhook is unreachable.

Required sequence before a human enablement decision:

1. Deploy this branch to a protected preview connected to an isolated staging database; apply migration 056 and run all real-Postgres integration tests.
2. Configure Stripe test keys and the approved test Price IDs only in preview/staging.
3. Create a test webhook endpoint for that protected preview, with a matching signing secret and the complete code-handled event set.
4. Execute and record the full matrix: both plans, successful card, decline, SCA/action-required, async method if enabled, webhook retry, duplicate delivery, failed renewal, portal cancellation, period-end deletion, and entitlement revocation.
5. Point the live Stripe endpoint to the current production backend (`www.caregist.co.uk` or a verified stable API hostname), align its event subscriptions, and verify a signed non-commercial test event before any paid gate opens.
6. Wire the approved live Radar Product/Price IDs and approved B2B terms while leaving both checkout flags false.
7. Wait for `commercialReadiness.checkoutReady=true` over a clean seven-day window and investigate the latency sample if it remains above 45 minutes.
8. Only then obtain the explicit human legal/business approval to set both checkout flags true.

Until every step is evidenced, the existing disabled pricing state is the correct production behaviour.
