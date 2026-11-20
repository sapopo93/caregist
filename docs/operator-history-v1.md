# Operator History, stage 1 (design note)

Operator History is a one-off, per-operator report of CQC's published record of one care operator: its locations, their registration dates, closures and rating history, with every item dated and sourced. This stage builds the resolver, the record builder and the free coverage preview. It has no checkout, no payment, no delivery and no export. The product price (£95) and the terms are not decided here.

Status: code only, behind `OPERATOR_HISTORY_ENABLED` (default false). Off returns the same 404 as an unknown route and reads nothing. It stays off until the wording has independent review.

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

1. Price, terms and checkout are untouched. Do you want a fixed-price checkout gate modelled on the Territory Brief's, or a manual order first?
2. The cutoff: should history be held back by a fixed period after observation (the brief mentions seven days), and if so from which date: observation, edition retrieval or generation? The hook exists; the rule is yours.
3. A location that CQC moved from one Provider ID to another is indistinguishable here from an error, so it refuses the operator as `identity_disputed`. Is refusing right, or should a documented transfer be shown?
4. Who resolves `operator_identity_disputes` rows, and what evidence is needed to resolve one?
5. Should the directory CSV edition (Provider name, CQC Provider ID) be imported as a second name source? It would give names for operators the API providers file lacks, but the edition tables hold no row for it today.
6. Should the report name the date the edition was retrieved (what the data records) or an "as of" date? The tables hold no CQC publication date for an edition.
7. Should `invalid_input` stay as a separate code, or fold into `not_found`?
8. Wording review: the status labels, the event sentences and the six limit templates need independent review before the flag is turned on.
