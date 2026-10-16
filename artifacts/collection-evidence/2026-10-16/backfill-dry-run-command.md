# Rating-date backfill: read-only dry run

Not run from the cloud session: it has no production database access (no `DATABASE_URL`). Run it locally. A dry run is the default and never writes. The connection also asks PostgreSQL for a read-only session, so a read-write role still cannot write.

```bash
cd /path/to/caregist
export DATABASE_URL='<production read-only connection string>'   # a read-only role is preferred
python3 tools/backfill_rating_change_dates.py --detail-file /tmp/backfill-dry-run-detail.json | tee /tmp/backfill-dry-run.json
```

Do not pass `--apply`.

Output:
- `undated_rating_changed_rows`, `datable_rows`, `rows_written` (must be 0) and `reasons`, a count per skip reason.
- `rollback`, the SQL and the ids that a later apply would write.
- `/tmp/backfill-dry-run-detail.json`, one record per location with ledger id, location id, old and new grade, observation time, proposed date and reason.

Expected from the 1 October evidence: nearly all of the 401 rows in `reasons` as `not_a_grade_to_grade_move` or `superseded_by_later_move`. Those cannot be repaired by dating and must not be reconstructed. Bring the two output files back and the result goes into the thread.

## Result (run by Henry locally, 16 Oct 2026, about 19:44 UTC)

Mode `dry-run`, `rows_written: 0`. Which database the connection string pointed at was not stated; it was loaded from the main checkout's `.env`, so treat it as production only once Henry confirms.

| Reason | Rows |
|---|---|
| Undated `rating_changed` rows in total | 34,332 |
| `dated` (datable) | 1 (ledger id 111286524) |
| `not_a_grade_to_grade_move` | 34,185 |
| `superseded_by_later_move` | 146 |

Reading: the backfill can date one row out of 34,332. Almost all undated rows are not genuine grade-to-grade moves (blank or sentinel values), so there is nothing to reconstruct and nothing should be. The earlier "401 rows in 30 days" figure was a 30-day window; this is the whole table. The single datable row is not worth an `--apply` on its own. The per-row detail file stays on Henry's machine at `/tmp/backfill-dry-run-detail.json`.
