# CQC report-index poller: sampled run history (S1)

Source: final JSON line of the `Poll approved CQC sources in shadow mode` step in GitHub Actions logs for `cqc-signal-poll.yml`. `CQC_REPORT_POLL_ENABLED` was `true` in the 16 Oct log (the only one where the env block was in the retrieved tail).
Read 16 Oct 2026. Sample only: 7 of 623 runs. It does not establish the full history.

| Run # | Run ID | Date (UTC) | Conclusion | report_candidates | new_ids | processed | events |
|---|---|---|---|---|---|---|---|
| 104 | 31868317564 | 2026-08-15 | success | 0 | 0 | 1197 | 49 |
| 174 | 32009930557 | 2026-08-17 | success | 0 | 0 | 1197 | 0 |
| 294 | 32499279506 | 2026-08-21 | success | **3** | 15 | 1215 | 17 |
| 504 | 34088526196 | 2026-09-07 | success | 0 | 0 | 1195 | 6 |
| 564 | 35404755560 | 2026-09-18 | success | 0 | 0 | 1200 | 3 |
| 623 | 38850006539 | 2026-10-16 | success | 0 | 0 | 1198 | 4 |

Run 294 (21 Aug) shows the route has returned results at least once, so it is not zero on every run. Three candidates against the roughly 150 ratings CQC publishes in a week still means it badly under-returns, and every run concluded `success` regardless.

Not established: the full 623-run history, why run 294 differed, what CQC returns to the poller's user agent today, and the page's markup. Those need S2 (outside production, from a machine that can reach cqc.org.uk) and, with approval, a read-only query of `source_snapshots` where `source_type = 'cqc_report_index'`.

## Related finding (S6, not fixed)

Scheduled reconciliation runs of 11 Oct (38126298550) and 14 Oct (38529562912) concluded `failure`. In the 14 Oct run, `shards (2)`, `(1)` and `(3)` succeeded; shards 0, 4, 5, 6 and 7 were all cancelled within the same two seconds (09:22:33-09:22:36), about 1h45m in. Shard 5's log ends `exit code 143` and "The runner has received a shutdown signal", which is what a workflow cancellation produces. `fail-fast` is false and the 330-minute job timeout was not reached. The logs I can read show a run-level cancellation but not who or what issued it. Cause not proven.
