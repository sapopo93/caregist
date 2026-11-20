# Operator History, stages 1 and 2 (design note)

Operator History is a one-off, per-operator report of CQC's published record of one care operator: its locations, their registration dates, closures and rating history, with every item dated and sourced.

Stage 1 builds the resolver, the record builder and the free coverage preview. Stage 2 (the last major section of this note) makes the record purchasable in code: business checkout, signed payment event, an immutable delivered CSV and PDF, an account-scoped download and refund handling. The price is £95 one-off, fixed in code as 9500 pence. The terms, the refund policy and the VAT wording are not decided here (see "Open owner decisions").

Status: code only, behind two switches that are both off by default.

- `OPERATOR_HISTORY_ENABLED` gates every Operator History route. Off returns the same 404 as an unknown route and reads nothing.
- `OPERATOR_HISTORY_CHECKOUT_ENABLED` gates the paid checkout only. It also needs `BILLING_CHECKOUT_ENABLED`. Off returns a plain 503 and makes no Stripe call.

Both stay off until the wording has independent review and a hosted Stripe test-mode run has passed. The free coverage preview (stage 1) is unchanged by stage 2.

## Identity rule

An operator is one CQC Provider ID (`care_providers.provider_id`, for example `1-101234567`). A name never identifies an operator.

- A Provider ID lookup must match `^1-[0-9]{3,15}$`.
- A name search matches the provider names held in stored CQC editions, first as an exact match (case and spacing ignored), then as a literal substring (`%` and `_` are escaped). If it finds more than one Provider ID it refuses and lists up to 10 candidates (Provider ID, name, location count). It never picks one.
- Names are bound to Provider IDs through the stored editions. `territory_brief_source_locations.payload` holds the CQC `providerId` of each edition location, and the row holds the provider name read from the same import's providers file. The pair (edition, Provider ID) therefore gives the name. No importer change was needed; the existing importer (`tools/import_territory_brief_source.py`) already writes both. The directory CSV ("Provider name", "CQC Provider ID") is not read by anything in this stage.
- Identity is disputed (refused) when any of these holds:
  - a location CareGist holds under this Provider ID is listed in a stored edition under a different Provider ID, or the reverse;
  - one stored edition gives this Provider ID two different names;
  - a `status_changed` observation for one of its locations carries a different Provider ID;
  - an open row (`resolved_at IS NULL`) exists in `operator_identity_disputes` for it.

## Data sources per field

| Field | Source | Note |
|---|---|---|
| Legal provider name, edition | `territory_brief_source_editions` + `territory_brief_source_locations` | Latest edition holding the Provider ID gives the name. Earlier different names are listed with their edition dates. Edition is shown by retrieval date, source-as-of date and the SHA-256 of the providers file and locations file. The tables hold no CQC publication date for an edition. |
| Locations, name, service types | `care_providers` where `provider_id` = the operator | Sorted by (registration date, location ID). |
| Registration date | `care_providers.registration_date` (CQC's registration date) | Source link is the CQC location page. |
| Current status | `care_providers.status` | `ACTIVE` is "On CQC's active directory", `INACTIVE` is "No longer on CQC's active directory", anything else is "Status not held". |
| Closure, reinstatement | `trusted_event_ledger`, `event_type = 'status_changed'`, `observed_at` | `ACTIVE` to `INACTIVE` is a closure observation. `INACTIVE` to `ACTIVE` is a reinstatement observation. Only the observation date is known. |
| Rating history | `provider_rating_history` (`overall_rating`, `inspection_date`, `report_url`, `recorded_at`) | Sorted by inspection date. A CQC sentinel value (for example "Not Yet Inspected") is listed as quoted but is never a rating event. |
| Limits | fixed templates, dates computed from the data | See below. |

Never read: `ownership_changed` (a seeding artefact: the old value is a category and the new value is empty, so it is not a change), `group_movement`, `integration_connectivity`, `rating_changed`, `rating_status_changed`, `new_registration` (the registration date comes from `care_providers`).

## The record

`build_operator_history()` returns a dict: Provider ID, legal name and edition, a summary of counts and dates, the locations, a chronological events list, the limits, `history_cutoff` and `content_sha256`.

Events are only these kinds: `registration`, `closure_observed`, `reinstatement_observed`, `rating_published`. Each carries a date, the location, a fixed sentence and a source.

`content_sha256` is the SHA-256 of canonical JSON (sorted keys, compact separators) of the whole record except the hash itself. It holds no generation time and no database serial number (no ledger, history or edition IDs), so the same data gives the same hash whatever order it was inserted in. This is tested.

`coverage_preview()` (the free summary) returns the legal name, edition, earlier names, location counts (on the directory, no longer on it, status not held), earliest and latest registration dates, rating record count and inspection date range, observed closure and reinstatement counts with the first closure observation date, `history_cutoff` and the limits. It returns no location list and no event list.

## Limits (verbatim templates)

`{date}` is filled from the data as "31 March 2026".

1. Closure dates are the date CareGist first observed a location absent from CQC's active directory, not CQC's deregistration date. The record does not say why a location left the directory.
2. CareGist began recording changes to a location's status on {date}. A location that is not on the active directory and shows no observation date has no status change recorded by CareGist. (Date: the earliest `status_changed` `observed_at` in the whole ledger. If none: "CareGist has recorded no changes to any location's status.")
3. CareGist recorded rating history from {date}; earlier rating dates are CQC inspection dates captured later. (Date: earliest `recorded_at` among the operator's rating rows. If none: "CareGist holds no rating records for this operator's locations.")
4. Provider names are held only from the CQC editions CareGist has stored; renames before {date} are not shown. (Date: the earliest edition holding the Provider ID.)
5. This record covers only the locations CareGist holds. This operator may have had other locations that CareGist does not hold.
6. This record includes CareGist's observations up to {date}. Later observations are not shown. (Date: `history_cutoff`. If no observation date exists: "CareGist holds no observation dates for this operator's locations.")

Template 5 differs from the brief's wording. The brief's example said the record "is not a complete list of every location an operator has ever had", but the same brief also requires that the limits contain no phrase such as "every location" or "complete". The template above says the same thing without those words. A test fails if any limit, event sentence, status label or refusal message contains completeness, scoring, ranking, prediction or risk wording.

## The cutoff

The repo has no seven-day publication cutoff that applies to history. The nearest things are a 90-day registration window in the territory preview, a seven-day window in the sample generators, and seven-day readiness gates for pipeline health. None of them is a rule about when history may be published, so none was reused and none was invented. `history_cutoff` is therefore the latest observation date included (the latest closure or reinstatement observation or rating record date), or null if there is none. `build_operator_history(..., observed_through=date)` is an optional hook that leaves out later observations and sets `history_cutoff` to that date; nothing calls it yet. Registration dates are CQC dates, not observations, so the hook does not filter them.

## Refusal codes

All refusals are stable codes with plain messages. The HTTP body is `{"detail": {"code": ..., "message": ...}}`.

| Code | HTTP | When |
|---|---|---|
| `not_found` | 404 | No location, edition row or open dispute exists for the Provider ID, or the name matches nothing. |
| `ambiguous` | 409 | A name matches more than one Provider ID. Adds `candidates` (up to 10: `provider_id`, `name`, `location_count`) and `total_matches`. Nothing else about a candidate is returned. |
| `identity_disputed` | 409 | Any dispute condition above. Adds `reasons` (`recorded_dispute`, `edition_names_conflict`, `location_under_another_provider_id`, `observation_under_another_provider_id`). |
| `no_legal_name_held` | 409 | No stored edition gives a provider name for the Provider ID, or no edition is held at all. The operator is not sellable. |
| `not_enough_history` | 409 | The operator has a held name but zero locations in `care_providers`. |
| `invalid_input` | 422 | Neither or both of `provider_id` and `name`, a malformed Provider ID, or a name outside 3 to 120 characters or with control characters. `invalid_input` is not in the brief's list; it is the answer for input that never reaches the database. |

## Endpoint

`GET /api/v1/operator-history/coverage?provider_id=...` or `?name=...`. Public, no key, same per-IP rate limit (30 a minute) as the territory preview. One repeatable-read, read-only transaction. All values are bound parameters.

## Migration 074 (additive)

`db/migrations/074_operator_history.sql`:

- table `operator_identity_disputes` (owner-maintained; an open row blocks that Provider ID);
- index `territory_brief_source_provider` on `territory_brief_source_locations ((payload->>'providerId'), edition_id)`;
- index `idx_care_providers_provider_id` on `care_providers (provider_id)`.

No existing column, row or constraint changes, and the edition tables stay immutable. Rollback (`db/migrations/down/074_operator_history.down.sql`) drops the two indexes and the table. Per the migration governance policy, do not run a down script against production as an ordinary rollback; a Neon recovery point comes first. `CREATE INDEX` is not concurrent, so it takes a short write lock on `care_providers`, about 59,600 rows, and on the edition location table, which is empty in production today.

## What the data cannot do (stated plainly)

- A closure date is never CQC's deregistration date. Only the date of CareGist's first observation exists, from 10 August 2026 for the ledger and only for changes CareGist saw. A location that was already `INACTIVE` before CareGist began observing shows as absent with no observation date.
- The production edition tables are empty today, so every operator is refused with `no_legal_name_held` until an edition is imported. Name history only accumulates from editions CareGist stores from now on.
- Rating history was first recorded by CareGist on 31 March 2026. Earlier dates are CQC dates captured later, and CareGist cannot show what it did not record.
- The legal provider name is the CQC providers-file name at each edition. CareGist does not hold company numbers, trading names or deregistered operators that CQC no longer lists.

## Open questions for the owner

1. (Answered in code by stage 2: a fixed-price checkout gate modelled on the Territory Brief's. The price, terms, refund policy and VAT wording are still yours to decide: see "Open owner decisions".)
2. The cutoff: should history be held back by a fixed period after observation (the brief mentions seven days), and if so from which date: observation, edition retrieval or generation? The hook exists; the rule is yours.
3. A location that CQC moved from one Provider ID to another is indistinguishable here from an error, so it refuses the operator as `identity_disputed`. Is refusing right, or should a documented transfer be shown?
4. Who resolves `operator_identity_disputes` rows, and what evidence is needed to resolve one?
5. Should the directory CSV edition (Provider name, CQC Provider ID) be imported as a second name source? It would give names for operators the API providers file lacks, but the edition tables hold no row for it today.
6. Should the report name the date the edition was retrieved (what the data records) or an "as of" date? The tables hold no CQC publication date for an edition.
7. Should `invalid_input` stay as a separate code, or fold into `not_found`?
8. Wording review: the status labels, the event sentences and the six limit templates need independent review before the flag is turned on.

---

# Stage 2: the paid path

## Order state machine

One row in `operator_history_orders` per purchase attempt. The database enforces the transitions (trigger `operator_history_orders_guard`), so application code cannot skip a step.

| State | Meaning |
|---|---|
| `pending_payment` | Record built and pinned, Checkout Session open. At most one per account and operator. |
| `paid` | Stripe confirmed payment. Not yet delivered, or delivery failed (the order keeps `last_error` and `delivery_attempts`, which is the visible recovery state). |
| `delivered` | CSV and PDF stored, their SHA-256 values written to the order. |
| `refunded` | A full refund was recorded. Downloads are refused. Nothing else changes. |
| `failed` | Delivery failed 5 times. Still recoverable by the retry command (`--include-failed`) or a Stripe redelivery. Needs a person to look. |
| `expired` | Checkout was never paid (past its one-hour lifetime, taken under older terms, or its session could not be recorded). |

Allowed moves: `pending_payment` to `paid`, `expired` or `refunded`; `expired` to `paid` or `refunded`; `paid` to `delivered`, `failed` or `refunded`; `failed` to `paid`, `delivered` or `refunded`; `delivered` to `refunded`. `refunded` is final.

Never updated after the order is created (the trigger raises): the owner account, provider ID, legal name, price, currency, Stripe Price ID, the pinned record JSON, `content_sha256`, the edition ID, the edition IDs and both edition SHA-256 values, the terms, the checkout expiry and the creation time. Written once, then fixed: the Checkout Session ID and URL, the acceptance reference, the payment intent, the amount, `paid_at`, both file SHA-256 values, `delivered_at` and `refunded_at`. Rows are never deleted. `operator_history_artefacts` is append-only: no update, no delete.

## Flows

### Checkout: `POST /api/v1/billing/operator-history-checkout`

Lives in `api/routers/operator_history_orders.py`. Request: `provider_id`, `email`, `terms_version`, `business_use_confirmed`. The model refuses every other field, so a client cannot send a price, an amount or a name. A signed-in browser session is required (an API key is refused with 403), as for the other paid checkouts. The checks run in this order and the first failure stops the request:

1. `OPERATOR_HISTORY_ENABLED` off: 404, the same as an unknown route, before authentication.
2. Rate limit (the shared per-IP limit, 5 a minute), then authentication (401 without a valid identity).
3. `BILLING_CHECKOUT_ENABLED` and `OPERATOR_HISTORY_CHECKOUT_ENABLED` both on, and `STRIPE_SECRET_KEY` and `STRIPE_PRICE_OPERATOR_HISTORY` set: otherwise a plain 503.
4. The approved B2B terms (`billing._verify_contract_acceptance`, reused): 503 if none are approved, 409 if the version is not the current one, 422 if business use is not confirmed.
5. A verified account whose email matches the request (`billing._verify_request_email`, reused).
6. The source-freshness gate (below): a plain 503 on any gap, with the reason logged only.
7. The stage 1 resolver and builder for that Provider ID, in one repeatable-read read-only transaction. Any stage 1 refusal is returned with its code and HTTP status exactly as the free preview returns it (`not_found` 404, `identity_disputed` 409, `no_legal_name_held` 409, `not_enough_history` 409, `invalid_input` 422). `ambiguous` cannot occur here because checkout takes an ID only.
8. The order is created and committed, pinning the record, its `content_sha256`, the edition ID and SHA-256 values and the price. A double submit finds the pending order instead of creating another.
9. With the order row locked, the Stripe Price is read and verified (GBP, 9500, one-time, active, live mode matching the key, lookup key `operator_history_gbp_oneoff_v1`, active product), then one Checkout Session is created with the idempotency key `caregist-operator-history-<order id>` and the line item taken from the stored Price ID. The session lasts one hour, so a retry with the same key still meets Stripe's 30-minute minimum. Metadata carries the order, user, Provider ID, `content_sha256`, price, Price ID and terms. The shared `b2b_contract_acceptances` row (keyed by the session ID) and the session ID and URL are written in one transaction. If that write fails the session is expired and the order is closed, so the next submit starts clean.

Nothing reaches Stripe before step 9. Steps 1 to 8 make no Stripe call.

Source-freshness gate (`readiness_gap`): the pipeline-health snapshot that `billing._require_radar_commerce_ready` uses must report its checks passed, the CQC source fresh and its counts reconciled; and the newest stored CQC edition must be complete and within the eight-day freshness window. The Radar-only parts (signal-poll shadow coverage, ledger latency, the Radar delivery switch and outbox) are deliberately not asked, because Operator History is not a Radar delivery.

### Payment event

The existing signed `POST /api/v1/billing/webhook` (signature checked by `stripe.Webhook.construct_event`, replay stopped by `stripe_processed_events`) hands a `checkout.session.completed` or `checkout.session.async_payment_succeeded` event whose metadata `type` is `operator_history` to `operator_history_orders.handle_checkout_completed`. It works whatever the two switches say, so an order already paid for is always delivered or refunded. The handler:

1. Reads the authoritative session from Stripe (never the event body) and refuses unless it is paid, GBP 95.00, has the order's Price ID as its only line item, and matches the order's user, Provider ID, `content_sha256`, price, Price ID and terms. A mismatch raises, so Stripe redelivers and nothing is delivered. A session still `unpaid` (a delayed payment method) is left for the later `async_payment_succeeded` event.
2. Requires the matching immutable `b2b_contract_acceptances` row.
3. Takes the same per-payment advisory lock as the refund handler and the order row lock. If a full refund was already recorded for this payment, the order becomes `refunded` and nothing is delivered.
4. Marks the order `paid` (payment intent, amount, `paid_at`) and delivers.
5. A delivered order is a no-op, so a replayed or second event never makes a second delivery.

### Delivery

`deliver_order` verifies that the stored record still hashes to the pinned `content_sha256`, renders both files from that stored record (not from live tables), stores them in `operator_history_artefacts` (bytes, size, SHA-256, filename), writes the two SHA-256 values and `delivered_at` to the order and appends the audit row `operator_history.order.deliver`, all in one savepoint. The files are stored in Postgres, not in Vercel Blob: they are small, an account-scoped API download needs the bytes next to the order, and no extra credential is needed. The database also checks each file against its own hash.

Both files carry the title "Operator History", the CQC Provider ID, the legal name as held, the CQC edition retrieval date and source date, both edition SHA-256 values, the record's `content_sha256`, the stage 1 limits verbatim, the build date, and a fixed statement that the record is fixed at that point and a later CQC edition does not change it. No model writes any text. The CSV (`caregist-operator-history-<Provider ID>-<YYYY-MM-DD>.csv`) has the limits first, then one source-linked row per earlier name, location and dated event, then any CQC rating record that is not a published rating, quoted as held. The PDF (`...pdf`) is built with `pdf_writer`. Both are deterministic: the same record and build date give the same bytes. Cells that start with a formula character are prefixed so a spreadsheet will not run them.

### Download and status

`GET /api/v1/operator-history/orders/{order_id}` and `GET /api/v1/operator-history/orders/{order_id}/download?format=csv|pdf`. Authenticated as the buying account (the same identity check as billing; the order's `user_id` must match). An order that does not exist, is malformed, or belongs to another account gets the same 404 with the same body. For the owner: `pending_payment` and `expired` 402, `paid` and `failed` 409, `refunded` 410. The bytes served are re-hashed and must equal the SHA-256 recorded on the order and on the file row, or the response is a 500 and is logged. Headers: `Content-Disposition` with the stable filename, `X-Content-SHA256`, `Cache-Control: private, no-store`. These two routes need only `OPERATOR_HISTORY_ENABLED`, so switching checkout off never strands a paying customer. No download token exists, so none is stored.

### Refund

`billing._handle_refund` (existing path) calls `mark_refunded` for a full refund. The order becomes `refunded` and `refunded_at` is set; the pinned record and the delivered files stay as they were (a test compares them byte for byte). A refund that arrives before the payment event is held by the audit record and the order is marked `refunded` when the payment event arrives, with nothing delivered.

Partial refunds: a partial refund changes nothing on the order. The existing handler records `billing.charge.refund` with `fully_refunded` false, the order stays `delivered` and the download keeps working. This is a default, not a decision. Marked for owner review: should a partial refund withdraw access, and should the order say it was part-refunded?

Refund policy: not decided and not invented here. The code only reacts to a refund already issued in Stripe; it never issues one. Whether and when CareGist refunds a delivered record is an open owner question.

## Wiring into `billing.py`

The webhook dispatch and the refund hook are the only changes to `api/routers/billing.py`: one import, one dispatch in `_handle_checkout_completed`, one call in `_handle_refund` and `operator_history_orders.DeliveryError` added to the existing post-rollback `except` (the Territory Brief's failure recorder uses the same hook). Nothing was refactored.

## Migration 075 (additive)

`db/migrations/075_operator_history_orders.sql` creates, with `IF NOT EXISTS`:

- table `operator_history_orders` (columns and checks as described above; owner scope is `user_id` referencing `users(id)`, the same account scope the Radar checkout uses);
- unique partial index `operator_history_orders_one_pending` on `(user_id, provider_id) WHERE state = 'pending_payment'`, plus two lookup indexes;
- table `operator_history_artefacts` with `UNIQUE (order_id, format)`, a `byte_size` check and a check that `artefact_sha256` equals the SHA-256 of `content`;
- trigger functions `operator_history_orders_guard()` and `operator_history_artefacts_append_only()` and their triggers.

No existing column, row, constraint or table changes. Rollback, `db/migrations/down/075_operator_history_orders.down.sql`: drops the two triggers, the two tables and the two functions, in that order. As the migration policy says, do not run a down script on production as an ordinary rollback; a Neon recovery point comes first. Running it deletes every Operator History order and delivered file. `tools/check_migration_governance.py` passes.

New settings (names only): `OPERATOR_HISTORY_CHECKOUT_ENABLED` and `STRIPE_PRICE_OPERATOR_HISTORY`. `validate_production` refuses to start with checkout on unless `BILLING_CHECKOUT_ENABLED`, `OPERATOR_HISTORY_ENABLED`, `STRIPE_PRICE_OPERATOR_HISTORY`, `B2B_TERMS_VERSION` and `B2B_TERMS_SHA256` are set.

## Failure and recovery

- Delivery fails after payment (renderer error, database error, hash mismatch): the webhook transaction rolls back, then, on a fresh connection, the order is left `paid` with the error and an attempt count (`failed` after 5), and the webhook answers 500. Stripe redelivers the same event; the retry finds the order `paid` and delivers it. Because the event ID was not recorded, the redelivery is processed in full.
- `tools/retry_operator_history_delivery.py` does the same by hand. Dry run by default; `--apply` delivers; `--include-failed` also retries `failed` orders. It takes the database from `--database-url` or the `DATABASE_URL` environment variable and opens no environment file itself (importing the API package behaves as every other tool that imports it does). A production run needs the owner's go-ahead.
- Exactly once: the order row is locked, the state change to `delivered` only matches `paid` or `failed`, files are unique per order and format, and a delivered order is a no-op everywhere.
- Checkout response lost after it was recorded: the same submit returns the stored session with no Stripe call. Session created at Stripe but not recorded: the session is expired and the order closed; the next submit is a new order with a new idempotency key.
- A payment that does not match its pinned order raises before any state change; Stripe keeps retrying and the mismatch is visible in the webhook log.
- Not covered: `checkout.session.expired` is not handled. An unpaid order expires by its own clock the next time the buyer starts a checkout for that operator. A paid order whose acceptance row is missing raises on every retry until someone looks.

## What tests stub

No test calls Stripe or any other service. `tests/operator_history_orders_support.py` replaces `stripe.checkout.Session.create`, `retrieve`, `expire`, `stripe.Price.retrieve` and `stripe.Charge.retrieve`, records every call, and honours idempotency keys (a key reused with different parameters raises, as Stripe does). Webhook bodies are signed with the real Stripe signing scheme and checked by the real `stripe.Webhook.construct_event`. The source-freshness snapshot (`get_pipeline_health`) is replaced in the checkout tests, and its own edition check runs against the real database. Postgres tests (`tests/integration/test_operator_history_orders_pg.py`, 49 cases) run on an isolated local database with the full schema and the stage 1 fixture world. Unit tests (`tests/test_operator_history_orders.py`) cover flags, the price, wording, rendering and the `billing.py` wiring.

What the tests do not prove: that Stripe's hosted checkout accepts these session parameters, that Stripe's real events have exactly the shape the stub builds, that the live pipeline-health snapshot opens on production data, or that the files open in the buyer's tools.

## Hosted test steps still required (Stripe test mode, isolated preview)

Nothing below has been done. An operator must provision these, in an isolated preview with its own database and test-mode Stripe keys, never production:

Environment variable names (values set by the owner, never in a file in the repo): `DATABASE_URL` (isolated preview database), `STRIPE_SECRET_KEY` (a test key), `STRIPE_WEBHOOK_SECRET` (the preview endpoint's signing secret), `STRIPE_PRICE_OPERATOR_HISTORY`, `B2B_TERMS_VERSION`, `B2B_TERMS_SHA256`, `B2B_EVIDENCE_HASH_KEY` (optional, for the hashed IP evidence), `APP_URL`, `BILLING_CHECKOUT_ENABLED`, `OPERATOR_HISTORY_ENABLED`, `OPERATOR_HISTORY_CHECKOUT_ENABLED`. No Resend or Blob variable is needed.

Stripe test-mode objects: a Product and a one-time Price of GBP 95.00 carrying the lookup key `operator_history_gbp_oneoff_v1`; a webhook endpoint for the preview that receives `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `charge.refunded` and `charge.refund.updated`.

Steps:

1. Apply migrations 074 and 075 to the preview database through the governed route.
2. Import a current CQC edition and confirm the freshness gate opens (`readiness_gap` returns None).
3. Sign in with a verified test account; run checkout for a Provider ID that resolves, confirm the Stripe-hosted page shows GBP 95.00 and one line item.
4. Pay with a Stripe test card; confirm the webhook is accepted, the order reaches `delivered`, and both files download and hash to the values on the order.
5. Repeat the double submit and the lost-response cases with the real Stripe API (one session only).
6. Refund fully in the Stripe dashboard (test mode); confirm `refunded` and a 410 download. Refund partially on another order and confirm nothing changes.
7. Force a delivery failure on the preview (for example a temporary renderer fault), confirm the order stays `paid` with its error and that Stripe's redelivery or `tools/retry_operator_history_delivery.py --apply` finishes it once.
8. Confirm both switches off returns 404 and 503 as described, and that an existing paid order still downloads with checkout off.

## Open owner decisions

1. Terms. Checkout reuses the shared B2B terms and contract acceptance (`B2B_TERMS_VERSION`, `B2B_TERMS_SHA256`). Whether those terms cover a one-off digital record, and whether immediate-supply wording is needed as for the Territory Brief, is for the owner and the solicitor.
2. Refund policy. Not decided. Not invented here.
3. Partial refunds. Default is "no change to the order". Needs an owner decision (see Refund).
4. VAT wording. The Price carries no tax setting in this code. The buyer-facing wording ("£95 fixed fee, no VAT added" or otherwise) and the Stripe Price's tax behaviour are the owner's call.
5. Price record. `deploy/stripe-price-manifest.json` has no Operator History entry and `tools/verify_stripe_release.py` does not check one. Adding the product, its lookup key and the £95 figure to the manifest, and any public price page, is a separate owner step. The only price in code is `OPERATOR_HISTORY_PRICE_PENCE`.
6. Frontend. No buy button or page exists. The Checkout Session's success and cancel URLs point to `/operator-history/orders/<order id>` and `/operator-history?cancelled=1`, which are not built.
7. Retention. Delivered files and the pinned record stay in Postgres for as long as the order row does (rows are never deleted). A retention rule is not set.
8. Retry schedule. Nothing runs the retry command on a timer. Stripe's redelivery covers most failures; a scheduled run of the command is a deployment decision.
9. The wording of the fixed deliverable text (the pinned-record notice, the hash notice, the independence and licence line, the rating-record sentences) needs the same independent review as the stage 1 wording.
