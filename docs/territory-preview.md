# Free Territory Brief preview

Status: **prototype, off by default.** Built 19 October 2026 on branch `feature/territory-preview`. Not reviewed, not deployed, not approved for public use.

## What it does

On `/pricing/territory`, after a buyer runs the existing coverage check, a panel shows:

- the number of distinct provider organisations in the chosen region and care service
- how many new registrations and rating changes are recorded in the 90 days to the newest source date
- three dated examples, one per organisation, each with a factual reason and a link to its CQC record
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
- Tests: `tests/test_territory_preview.py` (16) and `frontend/lib/territory-preview.test.ts` (6).

Data: new registrations come from `care_providers.registration_date`; rating changes come from `trusted_event_ledger` (`rating_changed`, joined on `location_id`). Only rows with `UPPER(status) = 'ACTIVE'` are counted. The 90-day window ends at the newest of those source dates, never at today's date, so a stale source cannot read as a quiet quarter.

## Local check (19 Oct 2026)

Run against a scratch database seeded from `directory_providers.csv` (55,818 locations, newest registration 20 Feb 2026). West Midlands homecare returned 1,383 organisations and 27 new registrations; each query took about 250 ms without indexes. Rutland nursing returned 3 organisations, correctly marked as too small for a Brief. The three rating changes in that run were synthetic rows inserted only into the scratch database, so rating-change wording has not been seen against production ledger data.

## Before enabling

These need a reviewer who did not build it (AGENTS.md: a producing model cannot approve its own work):

1. Founder approval of the panel copy as a public claim surface.
2. A production read check: counts against live `care_providers`, and the window anchor against current source freshness.
3. Quarantined or unconfirmed locations. Once PR #94's migration is applied, decide whether quarantined IDs must be excluded from counts and examples.
4. Query cost on production, with `EXPLAIN` on the region-level queries. Consider caching responses per scope for an hour.
5. Whether showing named locations with a rating change on a public sales page is acceptable. The data is public CQC data, but the framing needs a decision.
