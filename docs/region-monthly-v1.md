# Region Monthly (design note: stage 1 and stage 2)

Region Monthly is a monthly, versioned set of counts for one England region and one service type, for one UK calendar month. Customers will buy access to specific months: £49 for one month, £245 for six consecutive months and £445 for twelve consecutive months. Stage 1 built the month rules, the counting query, the immutable store, the purchase rules, the free coverage preview and the build command. Stage 2 (section "Stage 2: orders, entitlements and download" below) adds the paid checkout, the signed payment event, per-month entitlements, the account-scoped download and refund handling. Terms, tax and refund wording are not decided here.

Status: code only, behind `REGION_MONTHLY_ENABLED` (`region_monthly_enabled`, default false) and, for the paid path, `REGION_MONTHLY_CHECKOUT_ENABLED` (`region_monthly_checkout_enabled`, default false). `REGION_MONTHLY_ENABLED` off returns the same plain 404 as an unknown route and reads nothing. Both stay off until the wording and the numbers have had independent review. The build workflow cannot be scheduled (see "Schedule and backfill"). No real payment has been taken and no Stripe account was called while building stage 2.

Every figure is a count, a date or a quoted CQC value. There are no scores, predictions, rankings or trend claims. The archive is never described as complete.

## Month semantics

- A month is a UK calendar month. It starts at 00:00 `Europe/London` and ends at 00:00 on the first day of the next month. October 2026 is therefore 745 hours long (BST ended on 25 October) and March 2026 is 743 hours (BST began on 29 March). February 2028 has 29 days.
- A ledger event is placed in a month by converting `observed_at` to `Europe/London` first. `2026-10-31T23:30:00Z` is 23:30 GMT on 31 October, so it is in October. `2026-03-31T23:30:00Z` is 00:30 BST on 1 April, so it is in April.
- A month is built on the 7th day of the FOLLOWING month. It may be built from 00:00 `Europe/London` on that day (`is_buildable`). The 6th is refused. 00:00 on the 7th is allowed, in both GMT and BST. The rule is evaluated in UK time, not UTC.
- `period_month` is always the first day of the month.
- A month that cannot be built yet is a future month. Its availability date is the 7th of the following month.

## Scope: region and service

- Only the nine England regions are supported, spelled as `care_providers.region` holds them: East, East Midlands, London, North East, North West, South East, South West, West Midlands and Yorkshire & Humberside. Measured on production on 20 November 2026, the column also holds an empty string (17 rows) and "Wales" (3 rows). Both are excluded. A request for either is refused with `region_unsupported`, and a database CHECK stops a build for them being stored.
- A service is one of the canonical slugs in `frontend/data/service-taxonomy.json`, read by `api/service_taxonomy.py` (the same file and the same `resolve_service_filter()` the site search uses). No slug or alias is added by this feature. At the time of writing there are 31 slugs, for example `residential-care-homes`, `nursing-care-homes`, `home-care`, `supported-living`, `primary-medical-care` and `dental-services`. No service (empty) means all services.
- `care_providers.service_types` holds several service type names in one text value, separated by a pipe (`|`), for example `Domiciliary care service|Supported living service`. The task brief said comma-separated; the data and every existing query use the pipe, and so does this feature. A location is in scope for a slug when at least one of its service types, trimmed and lower-cased, is one of that slug's aliases.
- A location with service types in two slugs counts once under EACH slug. In the all-services scope it counts once. The regional figure is computed by its own query over distinct locations. Service figures are never added up to make a regional figure (limit 4 says so). Locations whose service types are empty, or outside the taxonomy, appear only in the all-services scope.
- Locations in `reconciliation_quarantined_locations` with `resolved_at IS NULL` are left out, the same rule the Territory Brief preview uses. If that table is missing, building and the coverage preview fail closed (`source_unavailable`).
- Every status is counted (ACTIVE and INACTIVE), because a registration or a closure is about a location that may no longer be active.

## Metrics and sources

| Metric | Source | Definition |
|---|---|---|
| New registrations | `care_providers.registration_date` | Locations whose registration date falls in the month. Exact for the locations CareGist holds, for any month. |
| Ratings published | `provider_rating_history` (`overall_rating`, `inspection_date`) joined on `provider_id` = `care_providers.id` | Rows whose `inspection_date` falls in the month, counted by value after trimming and lower-casing: Outstanding, Good, Requires improvement, Inadequate. Rows with no value, or a value that is not one of those four (for example "Not Yet Inspected"), are counted as `no_published_rating_value`. `total` is the sum. Rows with an inspection date after 11 August 2026 are never read. |
| Closures observed | `trusted_event_ledger`, `event_type = 'status_changed'`, `old_value` ACTIVE and `new_value` INACTIVE, by `observed_at` in UK time | Changes CareGist saw in the month, from 10 August 2026. |
| Reinstatements observed | the same rows with `old_value` INACTIVE and `new_value` ACTIVE | The same rule in the other direction. |

Never read: `ownership_changed` (a seeding artefact), `rating_changed`, `rating_status_changed` (different meaning from the rating history table; the two are never mixed), `group_movement`, `new_registration`.

Left out of version 1: active locations at month end. CareGist has no stored monthly snapshot of the active estate, so the figure cannot be stated for a past month and is not estimated.

A closure count counts status changes, not distinct locations. A location that closed and was reinstated in the same month counts once in each. The observation date is never presented as CQC's deregistration date.

### What the rating history can say

`provider_rating_history` is written when CareGist sees a published rating move to a different published rating (`incremental_update.py`, `_project_rating_change`), plus a seed of current ratings from migration 001. CareGist has recorded from 31 March 2026. So an inspection that confirmed the same rating is not recorded, and "ratings published" means rating records CareGist holds, not every inspection. The table's inspection dates end on 11 August 2026. Months after that date are marked "not available from the rating history table after 11 August 2026" and the metric is `null`, never zero. August 2026 is partial.

### First supported month

`EARLIEST_SUPPORTED_MONTH` is April 2026. Registrations alone could go back to April 2010, but the other metrics begin in 2026, and a product whose meaning changes from month to month would be harder to state honestly. April 2026 is the first month wholly after rating recording began (31 March 2026). This is an owner decision to confirm (open question 1). Months before it are refused (`month_before_earliest`).

## Coverage per month (per metric)

Each build stores a `coverage` object. Per metric the status is one of `available`, `partial`, `not_captured_before` and `not_available_after`, with a fixed text and the boundary date.

| Month | New registrations | Ratings published | Closures and reinstatements observed |
|---|---|---|---|
| April to July 2026 | available | available | not captured before 10 August 2026 (`null`) |
| August 2026 | available | partial: rating records up to 11 August 2026 only | partial: observed from 10 August 2026 only |
| September 2026 onwards | available | not available from the rating history table after 11 August 2026 (`null`) | available |

## Limits (verbatim templates)

Stored with every build, hashed, and returned by the preview. Changing a word is a new `schema_version`, because the text is part of the hash. A test checks that this note contains each template exactly.

1. These figures are counts and dates only. They are not scores, rankings or predictions.
2. They cover only the locations CareGist holds. CareGist holds locations that are on the CQC register and locations recorded as no longer active. It does not hold other locations CQC registered in the past.
3. Region and service type are the values CareGist holds on the build date. They are not the values on the date of the event.
4. A location with more than one service type is counted once under each of its service types. Do not add the service figures together to get a regional figure. The regional figure for all services counts each location once.
5. Ratings published counts the rating records CareGist holds. CareGist began recording ratings on 31 March 2026. After that date a rating is recorded when the published rating differs from the previous one, so an inspection that confirmed the same rating may not be counted. Rating records with an inspection date after 11 August 2026 are not available.
6. Closures observed and reinstatements observed begin on 10 August 2026. The date is the date CareGist saw the change. It is not the date CQC removed or restored the registration.
7. Locations that CareGist could not confirm against CQC data are left out.
8. A month is built on the 7th day of the following month. If a month is corrected, the correction is a new numbered version and the earlier version is kept.

Future-month notice, shown when a purchase includes unbuilt months: "A future month can be downloaded only after it has been built, on the 7th day of the following month."

A test fails if the limits, the metric definitions or the refusal messages contain "complete", "every", "all history", or scoring, ranking or prediction wording.

## The store: `region_monthly_builds`

Migration `076_region_monthly_builds.sql` (down script `db/migrations/down/076_region_monthly_builds.down.sql`). One row is one build of one month for one region and service.

- Columns: `period_month` (first of month), `region`, `service_slug` (NULL means all services), `build_version`, `supersedes_build_version`, `correction_reason`, `schema_version`, `built_at`, `built_from_data_cutoff`, `metrics` (JSONB), `coverage` (JSONB), `limits` (JSONB array), `content_sha256`.
- Unique on (`period_month`, `region`, `COALESCE(service_slug, '')`, `build_version`). The COALESCE is needed because a plain UNIQUE treats NULLs as distinct.
- Triggers reject UPDATE, DELETE and TRUNCATE. A correction is a new row with the next `build_version`, a `correction_reason` and `supersedes_build_version` set. The old row is never touched, so no UPDATE is ever needed: "superseded" means "a row with a higher version exists". An insert trigger refuses a version with no predecessor, and CHECK constraints refuse a region outside the nine, a non-first-of-month date, a malformed slug or hash, and a broken version chain.
- `content_sha256` is the SHA-256 of canonical JSON (sorted keys, compact separators) of: schema version, month, region, service, metrics, coverage and limits. It holds no generation time, no `built_at`, no version and no row id. The same data gives the same hash whatever order the rows were inserted in (tested).
- A rerun with identical content writes nothing. Changed content is stored only when the command is given `--correction-reason`.
- Entitlements and orders are not stored here. They are stored by migration 077 (stage 2, below).

Rollback: the down script drops the triggers, the two functions and the table. Under `db/migrations/README.md`, never run it on production as an ordinary rollback. A built month is a published record: turn the flag off, use a forward-fix migration, and take a verified Neon recovery point before any production migration. Migration number: Operator History keeps 074 and 075, so Region Monthly is 076.

## Purchase rules (`resolve_purchase`, no charge)

Prices live in one place, `PURCHASE_KINDS` in `api/services/region_monthly.py`: `single` 1 month 4900 pence, `six` 6 months 24500 pence, `twelve` 12 months 44500 pence (GBP, held as pence like the other products). Stage 2 reads prices from there and nowhere else. The wording about VAT ("no VAT added" on the Territory Brief) is not decided for this product.

A purchase is a kind, a first month, a region and a service. The months are consecutive from the first month. Each month is either built (a stored build exists) or future (not buildable yet; available on the 7th of the following month). A bundle may include future months only when the buyer accepts them explicitly (`accept_future_months`), and a future month can be downloaded only after it is built. Everything that can fail fails before any charge.

| Code | HTTP | Message template |
|---|---|---|
| `region_unsupported` | 422 | That region is not available. Region Monthly covers these regions of England: {regions}. |
| `service_unsupported` | 422 | That service type is not available. Use one of the service names listed by CareGist. |
| `kind_unsupported` | 422 | That purchase length is not available. Choose one month, six months or twelve months. |
| `months_malformed` | 422 | The months could not be read. Give months as YYYY-MM, for example 2026-10. |
| `months_not_consecutive` | 422 | The months must follow each other with no gaps, in date order. |
| `months_count_mismatch` | 422 | The number of months does not match the purchase length: {expected} expected. |
| `month_before_earliest` | 422 | {month} is before the first month available, {earliest}. |
| `month_not_built` | 409 | {month} has not been built yet, so it cannot be sold. Please try again later. |
| `future_months_not_accepted` | 409 | This purchase includes months that are not built yet: {months}. Confirm that you accept them to continue. |
| `future_months_too_far` | 422 | A purchase cannot include months after {latest}. That is {limit} months beyond the latest month that can be built. |
| `month_not_yet_buildable` | 409 | {month} can be built from {available}. |
| `range_invalid` | 422 | The first month must not be after the last month. |
| `source_unavailable` | 503 | Region Monthly is unavailable because a required data source is missing. |

`month_not_built` is the refusal for a past month that could be built but has no stored build: it is never sold until it exists. `month_not_yet_buildable` and `range_invalid` come from build planning (the command and `plan_backfill`), not from the purchase. A purchase may not reach more than 12 months beyond the latest month that can be built (`future_months_too_far`).

## Endpoint

`GET /api/v1/region-monthly/coverage?region=&service=&first_month=&kind=` with an optional `accept_future_months=true`. Public, no key, the same per-IP rate limit as the territory preview (`check_public_rate_limit`). `first_month` is `YYYY-MM`; `kind` is `single`, `six` or `twelve`; an empty `service` means all services. The route reads the months already built for the region and service, then returns the preview or a 4xx whose body is `{"detail": {"code": ..., "message": ...}}`. The preview holds the price in pence, each month with its status (`built` or `future`), the availability date of each future month, per-metric coverage, the metric definitions and the limits. It returns no counts: figures are for buyers, in a later stage.

## Schedule and backfill

- `tools/build_region_monthly.py` takes `--dry-run` or `--write` (exactly one), `--period-month YYYY-MM` (default: the latest month that can be built), `--from-month`, `--regions`, `--services` (slugs or `all-services`) and `--correction-reason`. It reads `DATABASE_URL`. A dry run counts inside a read-only transaction and writes nothing. Exit 3 means a built month's content differs from its stored build and nothing was stored.
- `.github/workflows/region-monthly-build.yml` is `workflow_dispatch` only. The schedule trigger (`30 6 7 * *`, the 7th at 06:30 UTC, after 00:00 UK time in both GMT and BST) is present but commented out, with a header saying it must not be enabled until the owner approves. A write needs `dry_run` false, a run from `refs/heads/main` and the repository variable `REGION_MONTHLY_BUILD_APPROVED` set to `true`. The variable is an addition to the brief; it keeps a main-branch dispatch from writing before the owner has said yes. Every `uses:` is pinned to a full commit SHA.
- Backfill: a build per month, region and service (all services plus 31 slugs, so 32 per region, 288 per month). April to October 2026 is 7 months, so 2,016 builds. `plan_backfill` refuses months before April 2026, months not yet buildable, and unsupported regions or services. Backfilled August and earlier months carry the partial or not-captured coverage above; they are not made to look whole. No backfill has been run.

## What the data cannot do (stated plainly)

- Ratings published is not every inspection: only rating moves are recorded (see above), and nothing after 11 August 2026 is available.
- Closures observed start on 10 August 2026. Nothing before it exists, and a location already inactive before then has no closure observation.
- A closure date is when CareGist saw the change, never CQC's deregistration date.
- Region and service are the values held on the build date, not on the date of the event.
- CareGist holds only the locations in its tables. Locations CQC registered and removed before CareGist held them are not there.
- A months-old build is not rewritten when later data arrives. A correction is a new version.

## Stage 2: orders, entitlements and download

Code: `api/routers/region_monthly_orders.py` (checkout, status, download), `api/services/region_monthly_orders.py` (orders, payment event, entitlements, refunds), `api/services/region_monthly_render.py` (CSV and PDF), `api/queries/region_monthly_orders.py`, `tools/retry_region_monthly_entitlements.py`, migration `077_region_monthly_orders.sql`. It follows Operator History stage 2 (`docs/operator-history-v1.md`) in design.

### Gates

| Gate | Off means |
|---|---|
| `REGION_MONTHLY_ENABLED` | Every stage 2 route answers the same plain 404 as an unknown route, before authentication, and nothing is read. |
| `BILLING_CHECKOUT_ENABLED` and `REGION_MONTHLY_CHECKOUT_ENABLED` | Checkout answers a plain 503 and makes no Stripe call. Status and download keep working, so turning checkout off never strands a customer who has paid. |
| `STRIPE_SECRET_KEY` and the three Prices `STRIPE_PRICE_REGION_MONTHLY_SINGLE`, `_SIX`, `_TWELVE` | A plain 503 if any is missing. |
| `B2B_TERMS_VERSION` and `B2B_TERMS_SHA256` | A plain 503 ("awaiting approved B2B terms"); a wrong version is 409; an unconfirmed business use is 422. |
| Source-freshness gate | A plain 503. It uses the same pipeline-health snapshot as Operator History and Radar (readiness checks passed, CQC source fresh, counts reconciled). It leaves out Operator History's check of the stored CQC edition, because that edition supplies provider names and Region Monthly does not read it, and adds a check that the stored builds table exists. |

`validate_production` refuses to start with checkout on unless `BILLING_CHECKOUT_ENABLED`, `REGION_MONTHLY_ENABLED`, the three Prices, `B2B_TERMS_VERSION` and `B2B_TERMS_SHA256` are set. The signed payment webhook keeps working whatever the checkout switch says.

### Endpoints and HTTP codes

`POST /api/v1/billing/region-monthly-checkout` needs a signed-in browser session with a verified email. An API key is refused (403). The body holds `region`, optional `service` (a canonical slug), `kind` (`single`, `six` or `twelve`), `first_month` (`YYYY-MM`), `accept_future_months` (default false), `email`, `terms_version` and `business_use_confirmed`. There is no price field and no other field (422). The price is never read from the client.

Order of checks, each before the next and all before any Stripe call: 404 (module off); 503 (checkout switches, key, Prices); terms (503, 409, 422); session and verified email (403, 401); email matches the account (403); 503 (source-freshness gate); the stage 1 purchase rules (`resolve_purchase`, the refusal table above, with `{"detail": {"code", "message"}}`); the months the account already holds (409 `months_already_held`); the pending order; the Stripe Price check (503); then the Checkout Session (502 if Stripe refuses, with "No payment has been taken").

`GET /api/v1/region-monthly/orders/{order_id}` returns the order state and each month: `available`, `will_be_available` (with the date), `not_built` (its day has passed and no build exists), `not_paid`, `refunded` or `being_set_up`. It never returns Stripe identifiers or the terms hash.

`GET /api/v1/region-monthly/orders/{order_id}/months/{YYYY-MM}/download?format=csv|pdf`:

| Code | Meaning |
|---|---|
| 200 | The file, with `X-Content-SHA256` (of the bytes), `X-Build-Version`, `X-Build-Content-SHA256` (of the stored build), `Cache-Control: private, no-store`. |
| 402 | The order is not paid (pending or expired). |
| 404 | An unknown order, another account's order, a malformed order id, a month that is not in the order or a malformed month. All have the same body, `{"detail": "Order not found."}`. |
| 409 | `month_not_available_yet` (a future month with no build; includes `available_from`), `month_not_built` (its day has passed and no build exists; includes `available_from`), or `access_being_set_up` (paid, entitlement not yet created). |
| 410 | The order was refunded. |
| 422 | A format other than `csv` or `pdf`. |
| 500 | The stored build no longer matches its `content_sha256`; nothing is served. |

### Order states

`pending_payment` (created at checkout) moves to `paid` (signed payment event), `expired` (checkout lifetime ended, replaced by a different purchase, or its session could not be recorded) or, if a full refund arrives before the payment event, `refunded`. `expired` can still move to `paid` if Stripe reports payment for its session later. `paid` moves to `refunded` on a full refund. Nothing else moves; the database enforces this. A new order is always created as `pending_payment`.

### Flow

1. Checkout resolves the purchase, takes an advisory lock for the account and scope (region and service), expires a pending order past its one-hour lifetime and refuses months the account already holds in a paid order. A repeated identical request returns the one pending order and its one session (`reused: true`). A different purchase in the same scope replaces it, after Stripe has expired the earlier session; if Stripe cannot, nothing changes and the buyer gets a plain 409 (`checkout_still_open`). A later deliberate purchase of the same scope, after the earlier one is paid, is a new order with its own idempotency key `caregist-region-monthly-<order id>`.
2. The Checkout Session is made with that idempotency key, so a lost response is recovered: the same request finds the same session. The order pins the region, service, kind, the exact ordered list of months, which months were future with their availability dates, the price, the Stripe Price id and the terms.
3. The Stripe Price is read before the session is made. It must be active, GBP, one-time, carry the lookup key `region_monthly_<kind>_gbp_oneoff_v1`, have a live product, and its amount must equal the central price.
4. The signed `checkout.session.completed` (or `async_payment_succeeded`) event is verified by the shared webhook and deduplicated in `stripe_processed_events`. `region_monthly_orders.handle_checkout_completed` reads the authoritative session from Stripe and checks its metadata (user, region, service, kind, months, price), amount, currency, line item, payment intent and the stored B2B acceptance against the pinned order. It marks the order paid and creates one entitlement per purchased month in the same transaction. Nothing is rendered at payment time: delivery means entitlement.
5. A download needs a paid order, the month's entitlement and a stored build at that moment. A month that was future at purchase is downloadable only after a build exists for it, even if its date has not been reached. The latest build version of the month is served and named in the file and the `X-Build-Version` header.

### Webhook wiring (`api/routers/billing.py`)

Four small edits, the same four as Operator History: the import gains `region_monthly_orders`; `_handle_checkout_completed` dispatches metadata type `region_monthly` to `region_monthly_orders.handle_checkout_completed`; the `except` in `stripe_webhook` also catches `region_monthly_orders.EntitlementError`, so its failure recorder runs after the transaction rolls back; `_handle_refund` calls `region_monthly_orders.mark_refunded` inside the full-refund branch.

### Tables and migration 077

`region_monthly_orders` holds the buying account (`user_id`), region, service (NULL means all), kind, month count, `months` (the exact list), `future_months` with `future_available_from`, whether future months were accepted, state, price, currency, Stripe Price id, the terms version and hash, the acceptance reference, Stripe session and payment ids, attempts and last error, and timestamps. `region_monthly_entitlements` has one row per order and month (unique). The guard trigger refuses any change to the purchased months, price, terms, scope or payment evidence, any delete, and any state move outside the list above, and checks that months are consecutive first days of a month. An entitlement can be inserted only for a month of a paid order, and cannot be updated, deleted or truncated. A refund changes `state` and `refunded_at` and nothing else. Only one pending order can exist per account, region and service (partial unique index).

Rollback: `db/migrations/down/077_region_monthly_orders.down.sql` drops the triggers, functions and the two tables and leaves `region_monthly_builds` alone. As with every migration it is for non-production verification only. A paid order is a financial record: on production, turn the flags off and use a forward-fix migration, and take a verified Neon recovery point before applying 077 (`db/migrations/README.md`). The migration is additive and idempotent.

### Refunds

A full refund (`charge.refunded` with the whole amount refunded) moves a paid order to `refunded`; downloads answer 410 and the order and its entitlement rows are not changed. A full refund that arrives before the payment event is remembered, so the later payment event marks the order refunded and grants nothing. A replayed payment event cannot revive a refunded order. A partial refund changes nothing: the order stays paid and downloadable. This is the documented default and is flagged for the owner (open question 10).

### Failure and recovery

- Payment event for an unknown or mismatching order, a wrong amount or currency, an unexpected line item, a missing or different B2B acceptance: the webhook answers 500 and rolls back. The order stays `pending_payment`, nothing is granted, and Stripe redelivers.
- Entitlement creation fails after payment: the transaction rolls back, then the failure recorder (fresh connection) restores the payment evidence, leaves the order `paid` with `last_error` and counts the attempt. Downloads answer 409 `access_being_set_up`. Stripe's redelivery of the same event finishes the order; so does `python tools/retry_region_monthly_entitlements.py` (dry run) and `--apply`. Entitlements are unique per order and month and the audit event `region_monthly.order.paid` is written only when rows are created, so nothing is created twice.
- Two payments for the same months (both sessions paid): both are honoured and the audit event `region_monthly.order.overlap_paid` is written for the owner to refund one.
- A session that cannot be recorded after Stripe made it is expired at Stripe and its order closed.
- A stored build whose hash no longer matches is never served (500) and is logged.

### What is stubbed and what is real

Real in the tests: Postgres 15 (the full migration set), the FastAPI app, the shared webhook with real HMAC signing and verification, the guard triggers, the PDF writer. Stubbed: the Stripe gateway (`RegionMonthlyStripeStub` replaces `Session.create`, `retrieve`, `expire` and `Price.retrieve`; no network). Never exercised: a real Stripe account, test or live; Stripe Tax; invoice delivery (`invoice_creation` is requested but not observed); the hosted frontend (there are no order or checkout pages yet; the success and cancel URLs point at `/region-monthly/orders/<id>` and `/region-monthly`).

### Hosted test-mode steps still required

Owner steps, in order, on a preview deployment with an isolated database, never production. Variable names only; values are set by the owner and never written in the repository.

1. Take a verified Neon recovery point, then apply migration 077 to the preview database.
2. In Stripe test mode create three one-time GBP Prices with lookup keys `region_monthly_single_gbp_oneoff_v1` (4900 pence), `region_monthly_six_gbp_oneoff_v1` (24500) and `region_monthly_twelve_gbp_oneoff_v1` (44500), each on an active product.
3. Set `STRIPE_SECRET_KEY` (a test key), `STRIPE_WEBHOOK_SECRET` (the preview endpoint's signing secret), `STRIPE_PRICE_REGION_MONTHLY_SINGLE`, `STRIPE_PRICE_REGION_MONTHLY_SIX`, `STRIPE_PRICE_REGION_MONTHLY_TWELVE`, `B2B_TERMS_VERSION`, `B2B_TERMS_SHA256`, `B2B_EVIDENCE_HASH_KEY` (optional), `APP_URL`, `BILLING_CHECKOUT_ENABLED`, `REGION_MONTHLY_ENABLED` and `REGION_MONTHLY_CHECKOUT_ENABLED`. Point a test-mode webhook endpoint at `/api/v1/billing/webhook` for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.expired` and `charge.refunded`.
4. Build some months on the preview database with `tools/build_region_monthly.py --write`.
5. Run in test mode: a one-month purchase of a built month, a six-month purchase that includes a future month, a double submit, a repeated webhook delivery, a card needing authentication, an expired session, a full refund and a partial refund. Check the order status, each download's SHA-256 against `X-Content-SHA256`, and the audit log.
6. Confirm the invoice and receipt wording and the VAT line (open question 11) before any live key is used.

### Entitlement rules (as built)

- An entitlement is a set of specific months for one region and one service, bought as one, six or twelve consecutive months, held by the buying account.
- A built month is downloadable at once. A future month included in the purchase is downloadable only once a build exists for it.
- A download serves the latest build version of the month at the time, and says which version it is. Older versions stay stored.
- The price is read from `PURCHASE_KINDS` and is checked again against the payment provider's price at checkout and at payment.
- Nothing is charged for a request that `resolve_purchase` refuses or for months the account already holds.

## Open questions for the owner

1. First supported month: April 2026 (the first month wholly after rating recording began) or something else? Months before it are refused.
2. Rating month coverage: should months after 11 August 2026 stay "not available", or should the rating history collection be repaired first and the builds rerun? Nothing is mixed in from `rating_status_changed`.
3. Is the 12-month limit on future months right, and should a buyer be allowed to buy future months at all in the first release?
4. Terms, immediate-supply consent, refund wording and VAT wording for this product (not decided here).
5. Correction policy: who authorises a correction, and what is told to a buyer who already downloaded the earlier version?
6. Whether to turn on the build schedule, and who sets `REGION_MONTHLY_BUILD_APPROVED`.
7. Whether the "active locations at month end" figure should be added once CareGist stores a monthly snapshot, and from which month.
8. Wording review: the eight limit templates, the four metric definitions and the refusal messages need independent review before the flag is turned on.
9. Migration number: settled. Operator History uses 074 and 075; Region Monthly uses 076.
10. Refunds: a full refund withdraws access to every month of the order, including months already downloaded. Should a partial refund change anything (for example, withdraw months pro rata), or stay as built (no change)? Should months already downloaded be refundable at all? The terms need an immediate-supply or cancellation clause.
11. VAT and invoices: the Checkout Session requests an invoice. The wording ("no VAT added" on the Territory Brief) is not decided for this product, and neither is whether Stripe Tax applies.
12. Price records: are the three catalogue prices (4900, 24500, 44500 pence) final, and who creates and signs off the Stripe Prices and their lookup keys?
13. Retention: how long are paid orders, entitlements and acceptances kept, and what is told to a buyer who asks for erasure? Orders are never deleted by the product.
14. Terms: which B2B terms version and hash apply, and does Region Monthly need its own (the shared B2B terms are used as built)?
15. Overlap and replacement: buying a month the account already holds is refused. Should a refunded or a corrected month be re-sold, and should a buyer be told when a corrected version replaces one they downloaded (open question 5)?
16. Checkout flag behaviour: with `REGION_MONTHLY_CHECKOUT_ENABLED` off the checkout answers a plain 503 (as Operator History does) rather than the 404 used when the whole module is off. Which should it be?
