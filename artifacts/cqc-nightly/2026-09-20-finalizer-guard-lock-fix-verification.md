# Guard corrective: independent verification of the finalize identity-lock fix

**Date:** 2026-09-20
**Branch:** `fix/cqc-finalizer-guard-20260920` (worktree `/Users/user/.hermes/worktrees/cqc-guard-20260920`)
**Base:** `c192eb6` → test `7ff11f8` → product fix `6ac1888`
**Verdict on my own checks: PASS on every check run. Independent reviewer verdict: OUTSTANDING.**
This is the Chief of Staff's evidence, not a reviewer's verdict.

## What changed

`incremental_update.py`: one executable line added — `LOCK TABLE care_providers IN SHARE ROW EXCLUSIVE MODE`
immediately before the unchanged end-state identity read, plus comments. The diff's 11 deletions are comment
lines only. No migration, threshold, SLA, cap, grace period, schedule or sweep value was touched.

Placement is load-bearing and correct: the lock is requested **after** this transaction's last
`care_providers` write (deactivations, `_repair_missing_slugs`) and after the API confirmation work, so it is
not taken while holding row locks a writer is already waiting on, and it is not held across network I/O.

## Results, each from a command I ran myself

| Check | Command | Raw result | Exit |
|---|---|---|---|
| Falsification vs parent | new test file copied into a worktree at `c192eb6`, then pytest | `1 failed in 1.18s` — "0 of 2 ... refused by a lock wait inside the window", `missing=['1-10007']`, `extra=['1-97001']` | 1 |
| Concurrency test + guard file at the fix | `pytest tests/integration/test_finalize_guard_concurrency_pg.py tests/integration/test_finalize_guard_pg.py -q` | `13 passed in 11.74s` | 0 |
| Focused suite at the fix (unchanged target set) | 7 target files, `-q` | `237 passed in 19.55s` | 0 |
| Lock released on the refusal path | source read of the guard | `conn.rollback()` at `:2212` before the drift evidence is committed separately, so no refusal retains the table lock | - |

The falsification is behavioural, not a collection error, and it names the same two identifiers my own
independent reproduction used — two separate constructions of the same interleaving, agreeing.

## Why the alternatives were rejected, and why that matters

The commit message records that REPEATABLE READ / SERIALIZABLE was **rejected rather than overlooked**: under
those levels the transaction's snapshot is taken at its first statement, which is before the deactivation
writes, so a substitution committed after that point would become invisible and the guard's existing refusal
would silently stop firing — a mechanical "raise the isolation level" fix would have *weakened* this guard.
An advisory lock was rejected because its guarantee evaporates the moment any writer path omits it. Both
rejections are sound.

## Residuals, stated so they are decided rather than discovered

1. **Post-commit drift (acknowledged in the fix).** The lock releases at this transaction's commit; a
   substitution committed after that is not covered by this attestation. That is a genuinely later change
   rather than a false certification, and it is caught by the next batch's coverage check.
2. **Contention (acknowledged in the fix).** If the lock cannot be acquired the finalize waits and, on the
   caller's `statement_timeout`, aborts: a batch that is not finalized, never a batch finalized without its
   evidence. Fail-closed, but it means contention can abort a legitimate batch and needs retry handling.
3. **Lock-upgrade deadlock cycle (my observation, NOT in the commit message).** The transaction holds
   `ROW EXCLUSIVE` from its own deactivation writes and then requests `SHARE ROW EXCLUSIVE`, which conflicts
   with `ROW EXCLUSIVE`. A concurrent writer that already holds `ROW EXCLUSIVE` (its own first write) and is
   *waiting on a row this finalizer already locked* completes a cycle, and PostgreSQL will abort one of the
   two with a deadlock error. Consequences: fail-closed — the batch is not finalized and nothing false is
   certified — but the finalize aborts and needs a retry, and a deadlock error can surface as a failed run.
   The window is narrow: the concurrent writer must be updating the same rows the finalize deactivates, at the
   same moment. Reported for the reviewer to judge, not treated as a blocker.

## Test-quality observation

The new test asserts the mechanism (both substituting statements refused by `lock_timeout`) **and** the
mechanism-independent invariant (a green attestation must never coexist with a disagreeing estate), plus that
a sound batch is still finalized (no spurious refusal). Assertion 1 is coupled to the chosen mechanism: a
future legitimate fix using a different mechanism would fail it even though the invariant held. That is
defensible as regression protection for *this* mechanism; noted so it is a decision, not an accident.
