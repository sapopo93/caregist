# Brief evidence engineering correction

Base: main 1a62f84. Developer verification is not independent product acceptance.
All commercial gates remain closed. No backfill, deploy or live mutation.

## Rating dates

Root cause: `clean_location` retains CQC report dates as `rating_report_date`,
`upsert_provider` passes that evidence to event construction, and ledger INSERT
copies the event fields. `_rating_transition_event` unconditionally set the
rating event's effective date to NULL. This is an event-construction defect,
not loss in the INSERT. The stored fixture contains CQC `currentRatings.reportDate`
and `currentRatings.overall.reportDate`; existing extraction also supports
`currentRatings.overall.date`.

Future rating movements carry only their destination's published report date,
labelled as a publication date and with its source field. Inspection dates,
historic dates, observation times and retrieval times are never substitutes.
Existing NULL rows remain unchanged. Backfill needs a separately reviewed
migration, source evidence per event, and founder approval before production.
Publication date is not asserted to be the actual transition's effective time.

The Brief independently reads NDJSON rather than the ledger. Undated current
ratings disable the recent-rating summary and produce an explicit unavailable
message; dated movements are only partial evidence where coverage is incomplete.

## Freshness and coverage

The former Brief reason used the newest source date as its recency clock, which
could make an old snapshot appear fresh. Reasons now use the generation date.
RI records remain visible in an evidence appendix even when no in-window event
qualifies them for ranking. Each shows its published date or explicit absence,
and freshness against the generation date (calendar 12 months).

Registration rows in the window show recorded URL/hash/date gaps. A generated
CQC reference link does not imply stored source metadata exists. These are gaps
in the supplied snapshot, not a claim that CQC failed to publish data. Nothing
is filled from an inspection date or collection clock. PDF/JSON carry context;
shortlist CSV includes date, freshness and metadata-gap columns.

## Verification

Synthetic regression tests cover extraction to event to INSERT, missing dates,
undated-summary refusal, stale RI context and incomplete registration metadata.
The full migration chain and real-Postgres fulfilment were exercised locally.
See the final engineering report for aggregate test output.

## Workflow changes awaiting permission

`workflows/run-feed-cycle.md`: publication vs observation date rules and no
historical backfill without a migration and founder approval.
`workflows/apply-migrations.md`: use an isolated local port for disposable replay;
run the actual `tests/test_territory_brief_pg_integration.py` path with TB_PG_URL.
These workflow files have not been edited.
