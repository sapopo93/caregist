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
