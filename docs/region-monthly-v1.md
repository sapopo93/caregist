# Region Monthly, stage 1 (design note)

Region Monthly is a monthly, versioned set of counts for one England region and one service type, for one UK calendar month. Customers will buy access to specific months: £49 for one month, £245 for six consecutive months and £445 for twelve consecutive months. This stage builds the month rules, the counting query, the immutable store, the purchase rules, the free coverage preview and the build command. It has no checkout, no payment, no entitlement storage and no download. Terms, tax and refund wording are not decided here.

Status: code only, behind `REGION_MONTHLY_ENABLED` (`region_monthly_enabled`, default false). Off returns the same plain 404 as an unknown route and reads nothing. It stays off until the wording and the numbers have had independent review. The build workflow cannot be scheduled (see "Schedule and backfill").

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
- Entitlements and orders are not stored here. That is stage 2.

Rollback: the down script drops the triggers, the two functions and the table. Under `db/migrations/README.md`, never run it on production as an ordinary rollback. A built month is a published record: turn the flag off, use a forward-fix migration, and take a verified Neon recovery point before any production migration. Migration number: Operator History keeps 074 and 075, so Region Monthly is 076.

## Purchase rules (`resolve_purchase`, no charge)

Prices live in one place, `PURCHASE_KINDS` in `api/services/region_monthly.py`: `single` 1 month 4900 pence, `six` 6 months 24500 pence, `twelve` 12 months 44500 pence (GBP, held as pence like the other products). Stage 2 must read prices from there. The wording about VAT ("no VAT added" on the Territory Brief) is not decided for this product.

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

## Entitlement rules (for stage 2, not built)

- An entitlement is a set of specific months for one region and one service, bought as one, six or twelve consecutive months.
- A built month is downloadable at once. A future month included in the purchase is downloadable only after it is built, on or after the 7th of the following month.
- A download serves the latest build version of the month at the time, and says which version it is. Older versions stay stored.
- The price is read from `PURCHASE_KINDS` and is checked again against the payment provider's price in stage 2, as the Territory Brief does.
- Nothing is charged for a request that `resolve_purchase` refuses.

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
