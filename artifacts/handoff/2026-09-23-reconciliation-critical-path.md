# Reconciliation critical-path investigation

**Checked:** 2026-09-23T03:51:39Z  
**Production mutations performed:** none  
**Watermark deadline carried from the war room:** 2026-09-24T12:00:00Z

## Verdict

The 2026-09-23 02:15Z scheduled event was not proven missing when it was checked.
Both previous scheduled reconciliation events were created roughly five and a
half hours after their declared cron slots:

| Run | Declared slot | `created_at` | Delay | Result |
|---|---|---|---:|---|
| `35069788326` | 2026-09-16 02:15Z | 2026-09-16 07:41:07Z | 5h26m07s | success |
| `35497685490` | 2026-09-20 02:15Z | 2026-09-20 07:44:37Z | 5h29m37s | cancelled |

At the last check, 2026-09-23T03:51:39Z, today's slot was only 1h36m39s old.
It had not reached the delay already observed twice. Re-check after 07:45Z.

There is no evidence of a repository-side suppression:

- workflow `330711851` reports `state: active`;
- repository Actions report `enabled: true` and `allowed_actions: all`;
- `main` is the default branch and the workflow exists on it;
- the public repository was pushed at 2026-09-23T03:28:42Z, ruling out the
  60-day public-repository inactivity disablement;
- a job-level `if:` condition cannot explain the absence of a workflow-run
  record because those conditions are evaluated after an event creates a run.

The supported diagnosis is therefore **GitHub schedule delivery delay, with
drop not yet distinguishable from delay**. GitHub documents that scheduled
events may be delayed during high load and may be dropped when load is high
enough. The first two project samples show the delivery is consistently late,
but two observations are not enough to claim a general GitHub root cause.

Official reference:
<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>

## Correction: what ran on `a1357fee`

Run `35545070099` was created at 2026-09-20T23:34:58Z with
`head_sha=a1357fee5bd2a63dafcee75ab6129e659b0b5ef7`. Its checkout log independently
prints that same SHA. The handoff's claim that it ran on `d6e9aeb` is false.

The narrower statement remains true: the credential-bearing **finalize job was
never exercised**. Shard 2 failed on `1-147345129` after five HTTP 500 responses;
the other seven shards completed; `finalize` was skipped; `abort-incomplete`
closed the batch. Thus the commit was present, but its finalize credential path
is still operationally unproved.

## Minimum action before the watermark breach

The smallest no-code action is an explicitly approved manual dispatch from
`main` with `dry_run=false`. It writes a new production reconciliation batch and
normally takes about 4h15m, so it should not be left until the final hours before
2026-09-24T12:00Z. Henry must approve exactly this production data mutation; no
checkout, deployment, Stripe, outbound delivery, or threshold change is part of
that approval.

This is the minimum action, not a guaranteed success: the same upstream record
may still return HTTP 500. Do not cancel a late scheduled run merely to replace
it with a manual run; the non-cancelling workflow concurrency group serializes
them.

## Should acknowledgement be exposed?

Yes, but only as an explicit manual boolean that defaults to false. The CLI's
own error tells an operator to rerun with
`--acknowledge-unconfirmed-deactivations`, but the current workflow has no way
to pass it. That makes the documented recovery path unreachable from Actions.

The accompanying workflow change:

- exposes `acknowledge_unconfirmed_deactivations`, default `false`;
- rejects it on dry runs;
- rejects it on scheduled events;
- passes the CLI flag only when the manual input is exactly `true`;
- preserves the CLI semantics: unconfirmed candidates stay ACTIVE, their IDs
  and count are recorded, and residual identity mismatch still refuses the
  batch.

This input does not address a shard HTTP 500. It only makes the existing
finalize recovery path reachable after all shards complete.

## Verification

`tests/test_reconciliation_schedule_inputs.py` and
`tests/test_incremental_update.py`: **96 passed** on Python 3.12.13.

