# 14 Oct 2026 reconciliation run 38529562912: cancellation analysis

Evidence gathered 16 Oct 2026 from the GitHub Actions API and job logs. Nothing here is inferred unless marked.

## Established

| Fact | Evidence |
|---|---|
| Scheduled run (Wednesday 02:15 UTC cron slot), started 07:37:44Z, ended 09:22:34Z (1h 45m) | run metadata, `event: schedule` |
| Conclusion `failure`; shards 1, 2, 3 succeeded; shards 0, 4, 5, 6, 7 did not | job list |
| Every unfinished job stopped within about 3 seconds, 09:22:33 to 09:22:36Z | job `completed_at` values |
| Shard 6 had only started its step at 09:22:31Z and was killed 4 seconds later | job 115738141222 |
| Shard 7 never received a runner (no runner id); its step was still `in_progress` when the run ended | job 115738141476 |
| Shards 5 and 6 logged `The runner has received a shutdown signal. This can happen when the runner service is stopped, or a manually started runner is canceled.` and `exit code 143` (SIGTERM) | job logs |
| `max-parallel: 4`, so shards 4 to 7 started only as earlier shards finished (09:00, 09:02, 09:21) | workflow + job start times |

## What each cause would look like, and which fits

| Cause | Expected signature | Fits? |
|---|---|---|
| Job timeout | One job stops at its own limit with a timeout message; others carry on. Limits are 330 min (shards), 20 min (prepare) | No. 105 minutes elapsed; all running jobs stopped together |
| Concurrency cancellation | Workflow `concurrency.cancel-in-progress` is `false` and there was no other run in group `cqc-reconciliation-production` on 14 Oct (previous run 11 Oct, ended 12:24Z) | No |
| `fail-fast` matrix cancellation | `fail-fast: false` is set | No |
| Step crash | The failing job would show a Python traceback before exit | No. The only message is the shutdown signal |
| Run-level cancel (person, API call or token) | All in-flight jobs receive the signal at the same moment | Fits |
| Runner or platform shutdown | Same signal text. Fits the shard 7 anomaly, but not distinguishable from a cancel in these logs | Cannot exclude |

## What cannot be established

The cancelling actor is **unknown**.

- The run's `actor` and `triggering_actor` show `sapopo93` on every scheduled run. For scheduled events GitHub attributes the run to the user who last changed the cron schedule, so this does not show who cancelled.
- The Actions API does not expose who cancelled a run.
- A personal account has no audit log, and this environment has no access to one. If `sapopo93` is under an organisation, an owner can search the audit log for `workflows.cancel_workflow_run` on 14 Oct 09:22Z.
- Same pattern on 20 Sep: scheduled run 35497685490 (cancelled at 10:00:34Z after 2h16m) and manual run 35510678221 (cancelled 17:18Z). Same unknown actor. The repo's own runbook says not to cancel a late scheduled run.

## Consequence

No code fix is justified by this evidence, because no code path in the workflow explains the cancellation. A fix would be a guess. What is justified:

1. Ask Henry, and anyone else with write access, whether the run was cancelled on 14 Oct near 09:22 UTC.
2. If the repo is under an organisation, check the audit log entry above.
3. If neither explains it, treat it as a platform event and rely on the existing resume path (`resume_batch_id` and `resume_run_id`), which is built for exactly this.
