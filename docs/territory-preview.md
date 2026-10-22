# Free territory preview

The public, read-only preview on `/pricing/territory` reports distinct providers, registered locations and recorded movement for the selected region and service. It appears after the coverage check. It covers all providers in that region/service, not only the provider group selected above, and says so beside the counts.

## Evidence and wording

- Counts use active CQC directory locations. Distinct providers are counted separately from locations. Coverage/enquiry wording consistently identifies location counts.
- The inclusive 90-day window ends at the most recent non-future, non-quarantined active registration recorded in the directory. This is a global event-date anchor, not a claim of fresh collection.
- Source freshness is shown separately. Incomplete or unconfirmed source evidence makes all preview figures provisional. Undated rating events are unavailable/partial, never silently zero.
- Public examples are new registrations only, up to three distinct providers. Only `Organisation` and `NHS Body` ownership types may be named. Individuals, partnerships, missing/unknown types and unresolved quarantine are excluded. An empty examples list does not mean no registrations occurred.
- A preview does not establish shortlist suitability. The Brief includes up to 50 providers, with exact quantity and suitability confirmed before payment. `brief.fits` is null when a nonempty scope still needs review; there is no unconditional 25-provider minimum.
- Examples are not ranked recommendations, leads or evidence of buying intent. Official CQC links and Open Government Licence attribution are included.

## Data consistency and gates

`TERRITORY_PREVIEW_ENABLED` controls both API routes. It defaults false; off returns 404 before source queries. `NEXT_PUBLIC_TERRITORY_PREVIEW_ENABLED` controls the frontend and requires a rebuild. Both are needed for the public panel. These switches do not enable checkout, delivery, export, claims, collectors or lead capture.

API routes are rate-limited public GETs at `/api/v1/territory-preview` and `/territories`. Geography columns come from an enum; names and shared-taxonomy service aliases are bound parameters. Missing quarantine schema fails closed. All source reads use one repeatable-read, read-only transaction. Cache keys include scope, freshness, reconciliation time and quarantine revision; a request reflects its database snapshot, and subsequent snapshots see changed quarantine. A request concurrent with a newly committed decision may still reflect its earlier snapshot. Cache lifetime is at most ten minutes.

The browser request times out after 15 seconds with a visible unavailable message. Re-running the coverage check retries. Selection changes clear/unmount the old panel and abort its request.

## Verification, 22 October 2026

User authorized release of quarantine handling followed by the preview. Quarantine PR94 was independently reviewed, CI checked and deployed first. Its migration was already present in production; no migration or source-row write was performed.

Local tests cover flag-off/no-query, missing schema, input validation, aliases, undated and mixed rating events, quarantine cache invalidation and public copy. A disposable-Postgres integration test executes the real SQL against multi-location providers, an individual, an inactive location and a quarantined location; counts, naming exclusion, provider deduplication and quarantine resolution are checked.

Read-only production SQL on 22 October: West Midlands homecare had 1,413 distinct providers, 1,616 locations and 21 new registrations in 23 July–20 October; London nursing 229 providers, 393 locations and 11 registrations; Rutland nursing three providers/locations and no registrations. Undated rating events were reported unavailable. Aggregate queries took 42–64 ms on a warm connection. These are dated observations, not contractual quantities. All 97 recent West Midlands registrations across services had blank ownership type, so naming remains withheld; do not fill this gap by assuming organisation status.

Backend unit suite: 1,541 passed / one skipped (outside integration suite). Frontend: 192 passed. Production build with frontend preview enabled passed. Independent final candidate review, hosting preview, live browser and exact-release smoke receipts are recorded in the release artifact; local passes alone do not establish production completion.

## Remaining boundaries

Production source freshness is still partial and checkout/delivery remain closed. Manual sales materials and the separate database-source prototype need their own reconciliation with current main. The legacy coverage query still has its own counting/filtering behaviour; this preview explicitly distinguishes its broader region/service scope and quarantine exclusions. No legal approval is asserted by displaying official organisation records.
