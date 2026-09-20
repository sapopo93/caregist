# Integration branch verification, 2026-09-20

**Branch:** `integration/cqc-ready-20260920` at `de5406a`, off `main` (`e38841c`).

## What was merged

| Branch | Head | Content |
|---|---|---|
| `fix/cqc-nightly-report-20260920` | `de7ede1` | `80724aa` RLS harness role fix; `de7ede1` evidence-completeness gate |
| `fix/cqc-finalizer-guard-20260920` | `5c3224a` | `118e14a` lock-held guard test; `5c3224a` guard fix |

Both merged with no conflicts. `fix/cqc-finalizer-guard-20260920` was subsequently
rebased to `6ac1888`; `git diff 5c3224a..6ac1888` is empty, so the merged content is
that branch's current content under different SHAs.

## Corrections to the 07:47 status

- **The DB-enabled re-run had already completed** when that status was written.
  `proc_a1974d5308df` finished `verify_db_exit=1` with `2 failed, 1112 passed,
  2 skipped` — the predicted shape, the two known RLS harness failures, no new
  failure. It was reported as "running now".
- **The predicted post-fix total of ~1114 was wrong, and low.** That baseline was
  measured in `cqc-race-c192eb6`, which carries only the guard branch. The
  integration branch carries both branches' new tests, so the correct total is
  1193. The prediction was not adjusted for the tree it was being applied to.

## Defect found and fixed in the guard commit

`5c3224a` took `LOCK TABLE care_providers IN SHARE ROW EXCLUSIVE MODE` with the wait
unbounded, and its comment asserted the finalize "aborts on the caller's
statement_timeout". No `statement_timeout`, `lock_timeout` or `PGOPTIONS` is set by
`incremental_update.py` (bare `psycopg2.connect` at `:1799`), by
`.github/workflows/cqc-reconciliation.yml`, or in the connection string — the claim
had no backing. Because that lock mode conflicts with the `ROW EXCLUSIVE` every
writer takes and Postgres queues lock requests, a waiting finalize also stalls the
live writes queued behind it (`api/routers/billing.py`,
`api/routers/provider_profile.py`, `api/queries/claims.py`, `api/queries/reviews.py`,
`api/queries/enquiries.py`, `api/routers/internal.py`), bounded only by the
workflow's 30-minute job timeout.

`SET LOCAL lock_timeout = '5s'` now precedes the lock. On contention the finalize
raises `LockNotAvailable` and the batch is not finalized — the outcome this guard
already treats as safe and `abort-incomplete` already handles.

## The skip-inflated green

The `1061 passed, 55 skipped` run was not a misconfiguration that can be fixed by
remembering the variable: `hermes verify` **cannot** set it. `agent/verify/recipes.py`
`Recipe` has no `env` field and `agent/verify/runner.py:27` passes no `env=` to
`subprocess.run`, so the recipe can only inherit its launching shell.

The refusal therefore lives in the repo. `scripts/run_tests.sh` exits 2 when
`CAREGIST_TEST_DATABASE_URL` is unset, unless `CAREGIST_ALLOW_UNIT_ONLY=1` states the
narrower scope deliberately. The saved manifest's `test` command and both CI test
steps now route through it.

## Results

Throwaway cluster `127.0.0.1:5599`, role `cqctest`.

| Run | Result |
|---|---|
| `test_crm_security_invariants.py` | **9 passed** (was 2 failed, 7 passed) |
| `test_finalize_guard_pg.py` + `test_finalize_guard_concurrency_pg.py` | **13 passed** |
| `tests/test_operational_workflows.py` (CI-contract assertions) | **7 passed** |
| Full suite, DB enabled, via `scripts/run_tests.sh` | **1193 passed, 2 skipped, exit 0** |
| `hermes verify --phase test` **with** DB | `ok: true`, exit 0, 47.7s, `1193 passed, 2 skipped` |
| `hermes verify --phase test` **without** DB | `ok: false`, **exit 2**, no tests run |

The 2 remaining skips are explicit opt-ins — `CAREGIST_RUN_WHISPER_INTEGRATION` and
`TB_PG_URL` — not database skips.

Note `--phase test` records scope `targeted`, not a full workspace green.

## Still outstanding

The two independent verdicts (`c192eb6` ratings, `72b391c` report completion) are
**NOT VERIFIED**: neither PASS nor FAIL. Nothing above changes that, and the
verification recorded here is the author's own, not a reviewer's. `de5406a` itself
has had no independent review.

Not covered by the suite: contention between two concurrent finalizers, a writer that
deadlocks against the lock, and privilege-dependent lock behaviour (the harness runs
as a superuser role, so the lock's privilege requirement is not exercised).
