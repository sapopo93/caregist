# Free Territory Brief preview

Status: **prototype, off by default.** Built 19 October 2026 on branch `feature/territory-preview` (PR #96). An independent review on 19 October requested changes; the five findings are addressed below. Not re-reviewed, not deployed, not approved for public use.

## What it does

On `/pricing/territory`, after a buyer runs the existing coverage check, a panel shows:

- the number of distinct providers in the chosen region and care service
- how many new registrations and dated rating changes are recorded in the 90 days to the latest recorded registration, plus the CQC source freshness status
- up to three newly registered locations, one per organisation provider, each dated and linked to its CQC record (rating changes are counted, never named)
- whether the scope has enough organisations for a 25 to 50 organisation Brief

The aim is to let a buyer see real movement in their own territory before they enquire about the £745 Brief.

## What it does not do

- It opens no checkout, payment, delivery, export, lead or claim path. The enquiry and payment controls on the page are unchanged.
- It is not the Brief's ranking engine (`api/services/territory_brief.py`). Examples are the most recent recorded signals, and the panel says so.
- It does not claim need, budget, intent or "leads". Wording follows `docs/manuals/SALES_GTM_MANUAL.md`.

## Switches

Both must be on for anything to appear:

| Where | Setting | Default | Effect when off |
| --- | --- | --- | --- |
| API | `TERRITORY_PREVIEW_ENABLED` (`settings.territory_preview_enabled`) | `false` | Both routes return 404 and run no query |
| Frontend | `NEXT_PUBLIC_TERRITORY_PREVIEW_ENABLED` | unset | The panel renders nothing and makes no request |

## Code

- API: `api/routers/territory_preview.py`
  - `GET /api/v1/territory-preview?kind=region|local_authority&name=…&service=homecare|residential|nursing|supported_living`
  - `GET /api/v1/territory-preview/territories`
  - Both have no auth and use the public per-IP limit of 30 requests a minute.
- Logic: `api/services/territory_preview.py`. SQL: `api/queries/territory_preview.py`. The scope column comes from a whitelist, and all values are bound parameters.
- Frontend: `components/TerritorySignalPreview.tsx`, `lib/territory-preview.ts`, plus the panel inside `components/TerritoryScopePicker.tsx`.
- Tests: `tests/test_territory_preview.py` (29) and `frontend/lib/territory-preview.test.ts` (9).

Data rules:

- **Services** map to canonical slugs in `frontend/data/service-taxonomy.json` and are matched against every stored alias through `api.service_taxonomy`. For example, homecare matches both `Domiciliary care service` (production) and the legacy `Homecare Agencies`.
- **Totals** come from uncapped aggregate queries. Only the example rows are limited (20 per signal type).
- **New registrations** come from `care_providers.registration_date`.
- **Rating changes** come from `trusted_event_ledger` (`rating_changed`). Events without an `effective_date` cannot be placed in the window, so they are reported as `unavailable` or `partial`, never as zero. In production, all 34,332 rating events had no date at review time.
- **Window end** is the newest recorded registration date. This is event recency, not freshness. Source freshness comes from `get_cqc_freshness`. Any status other than `fresh` marks the whole response provisional and adds a visible notice.
- **Exclusions:** only `UPPER(status) = 'ACTIVE'` rows count. Unresolved rows in `reconciliation_quarantined_locations` (migration 067, PR #94) are excluded from every count, example and the window anchor. If that table does not exist, both endpoints return 503.
- **Caching:** responses are cached in process for 10 minutes. The key covers the scope, the freshness status and reconciliation time, and a quarantine revision (unresolved count plus the latest created, updated or resolved time). A quarantine decision therefore takes effect on the next request, not after the cache expires.

## Local check (19 Oct 2026)

Run against a scratch database seeded from `directory_providers.csv` (55,818 locations, newest registration 20 Feb 2026). West Midlands homecare returned 1,383 organisations and 27 new registrations; each query took about 250 ms without indexes. Rutland nursing returned 3 organisations, correctly marked as too small for a Brief. The three rating changes in that run were synthetic rows inserted only into the scratch database, so rating-change wording has not been seen against production ledger data.

## Review findings, 19 October 2026

| Finding | Fix |
| --- | --- |
| P1: service filters used display labels and matched zero production rows | Canonical taxonomy aliases |
| P1: undated rating events produced a misleading zero | `unavailable`/`partial` state with a visible notice |
| P1: event recency presented as source freshness | Real freshness status reported; claims qualified unless `fresh` |
| P2: totals capped at 500 | Separate uncapped aggregate counts |
| P2: unconfirmed locations included | Quarantine exclusion; fails closed without the table |

Re-checked against a production-shaped Postgres fixture with CQC service labels, undated rating events, one quarantined location, one inactive location and no freshness tables. The page was also rendered in the browser. It has not been re-run against production.

## Production re-review, 19 October 2026

- Migration 067 was applied to staging and then production, after a Neon recovery checkpoint. Three IDs are quarantined. Provider totals were unchanged: 59,349 total and 57,159 active.
- A read-only check against production returned 200, three registration examples and no quarantined examples.
- West Midlands homecare: 1,411 providers, 1,614 locations and 21 registrations. Its 905 undated rating changes show as unavailable.
- The window ran from 19 July to 16 October. Freshness was PARTIAL, so the wording was provisional.
- `EXPLAIN ANALYZE` took 32 to 85 ms per query across three scopes, measured on a warm cache.
- One P2 remained: the cache key ignored quarantine changes. Fixed by adding the quarantine revision to every cache key, with regression tests and a real-Postgres check of the revision query.

## Before enabling

These need a reviewer who did not build it (AGENTS.md: a producing model cannot approve its own work):

1. **Founder re-approval of the panel copy.** The copy at `9fb6f98` was approved on 19 October, then changed the same day to implement the naming decision and fix wording from a founder review: CQC service terms, plain-English provisional and rating notices, "newly registered locations", and the coverage check relabelled "Locations in scope". The new copy needs approval.
2. ~~Production read check.~~ Done on 19 October (see above).
3. ~~Apply migration 067 in production.~~ Done on 19 October.
4. ~~Re-run `EXPLAIN ANALYZE` on production after the taxonomy change.~~ Done: 32 to 85 ms per query, warm cache.
5. ~~Named rating-change examples.~~ Founder decision, 19 October 2026: not on the public page. Named examples are new registrations only, and only for providers CQC records as an Organisation or NHS Body. Individuals, partnerships and unknown ownership types are never named. Rating changes are counted but not named, and belong in the private Brief. The panel shows the Open Government Licence attribution. Have the solicitor confirm the UK GDPR position on naming newly registered organisations.
6. ~~A re-review against production by someone other than the author.~~ Done; the cache-key P2 it raised is fixed.

Separate pre-existing issue, outside this PR: the existing coverage check on the same page (`getTerritoryScopeCoverage` in `frontend/lib/directory-db.ts`) does not exclude quarantined locations.
