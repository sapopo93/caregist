# CareGist source discovery recovery — 17 November 2026

Status: candidate code repair tested locally; production source refresh NOT performed.

## Release and stopped workflows

Read-only GitHub API and both public health endpoints identify current main and production as `fd140c7a377545feee8e0d66546631dbdd3df73e`.

GitHub Actions workflow inventory reports `disabled_manually` for reconciliation, primary/backup signal polls, Freshness Watchdog, ratings import and Production Smoke. Primary poll last ran successfully on 10 November ([42803677983](https://github.com/sapopo93/caregist/actions/runs/42803677983)); reconciliation last succeeded on 8 November ([42465222079](https://github.com/sapopo93/caregist/actions/runs/42465222079)). Both poll-enable repository variables are true. [PR 161](https://github.com/sapopo93/caregist/pull/161) explicitly records ratings import manually disabled on 10 November and intentionally uses a separate manual-only workflow to avoid resuming scheduled writes. The actor and reason for pausing all collectors were not established; no workflow was enabled or dispatched.

The last poll's final JSON recorded `processed=1200`, `events=0`, `report_candidates=1`, `report_index_status=pagination_incomplete`. A green workflow was not proof of complete report discovery.

## Reproduced defects and candidate repair

Public CQC search HTML on 17 November wraps location hrefs in whitespace/newlines, for example `/location/1-13878557294`. The old regex returned zero location IDs for a page with ten matching anchors. The source also supplies `rel=next`; old code fetched only page one and still allowed the source snapshot to be marked verified.

The candidate parses actual same-CQC anchors after trimming whitespace, follows explicit next links within the approved HTTPS search path with a 30-page bound, and rejects repeated pages, unsafe/conflicting links, changed source totals, count shortfalls, challenges, unknown empty pages and fetch failures. Single-page evidence bytes retain their existing form; multi-page bytes are length-framed to avoid concatenation ambiguity. Previous-page navigation does not imply a missing next page. Incomplete discovery raises before report-index snapshot insertion.

## Live public source validation: FAIL CLOSED

Using the candidate against the source's own linked URLs retrieved twenty result pages with 194 recognised unique location IDs. CQC search stated 211 results and linked page 21, which returned HTTP 404. The candidate refused discovery and returned no verified dataset. Later additional read-only source requests also encountered HTTP 403. These responses were not treated as a terminal page or permission to bypass source restrictions. No claim is made that the recognised IDs cover all source results or service types.

The official `/changes/location` API was probed using the existing client and returned HTTP 404; it is not a working fallback. The existing full reconciliation path uses the authoritative directory plus detail fetching independently of this HTML search, but its production execution and complete current report coverage were not established here.

## Existing prepare dry run: PASS, bounded

The current `_prepare_batch(... dry_run=True)` was exercised against the configured production database with PostgreSQL `default_transaction_read_only=on` and a read-only transaction. It reported:

```
DRY RUN — validated batch 502df2ac-d503-4843-b62f-c12049becce3: 57179 locations, 8 shards; no files or database rows were written.
prepare_dry_run_exit 0
```

This validates the current directory snapshot/reconciliation projection. It does not establish a fresh production watermark, resolve the fourteen quarantined locations, execute detail shards or repair the HTML source.

## Focused verification

61 tests passed using the existing Python environment:

```
python -m pytest tests/test_poll_report_index_health.py tests/test_cqc_signal_poll.py tests/test_cqc_reconciliation_workflow.py tests/test_reconciliation_schedule_inputs.py tests/test_reconciliation_acknowledgement_input.py -q
```

They cover whitespace hrefs, full pagination, previous navigation, unverified/challenge pages, pagination bound and loops, unsafe hosts, later-page HTTP failure, count shortfalls and drift, existing poll failure evidence, workflow and reconciliation input protections. No full application suite, paid customer journey, production refresh or independent approval is claimed.

## Independent review

A separate reviewer reproduced a false-completeness case where numbered forward links without `rel=next` could be accepted when no source total was present. The candidate now parses page-query links separately and refuses ambiguous forward/opaque pagination; explicit previous and lower-numbered navigation remains allowed. The reviewer independently reran all 61 focused tests and passed the bounded code repair after the correction. An additional 93 existing incremental/list-scan tests passed locally. This is code acceptance only, not production source recovery.

## Next acceptance

The exact candidate has passed the bounded independent code review. Resolve source enumeration or approve and validate an authoritative alternative before restoring complete report discovery. Separately restore approved collection schedules and obtain fresh reconciliation/poll/alert evidence. Checkout and delivery remain separate gates.
