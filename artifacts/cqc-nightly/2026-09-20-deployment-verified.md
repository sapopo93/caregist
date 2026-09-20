# Deployment record — CQC reconciliation fixes are LIVE

**Status: DEPLOYED AND VERIFIED.** Operator directive: *"fix and deploy"*.
Date: 2026-09-20. Recorded by: ai-company-governed (Chief of Staff).
Evidence label: **VERIFIED — live production journey, not a summary.**

## Release identity (both surfaces, read from the running service)

| Surface | Endpoint | Field | Value |
|---|---|---|---|
| Frontend | `/api/health/directory` | `release.gitSha` | `565f2f2472a19dd7a63de4dacd20b4eb2c1d156f` |
| Backend | `/api/v1/health/freshness` | `release.git_sha` | `565f2f2472a19dd7a63de4dacd20b4eb2c1d156f` |

Both equal main's tip — the PR #63 merge commit. The deploy is real, not inferred.

## Path taken

1. Integration branch `integration/cqc-ready-20260920` assembled: finalize identity guard
   (`6ac1888`), bounded lock + no-DB-URL refusal (`de5406a`), RLS harness fix (`80724aa`),
   ratings public-read-path fix (`e478030`), report tool + evidence gate (`de7ede14`).
2. PR **#63** opened against `main`.
3. **Three CI defects found on the way, all ours, all fixed before merge** — none was waived:
   - `api/services/pipeline_health.py` had lost `import asyncpg` while still annotating with
     `asyncpg.Connection` (4 × F821). Inert at runtime because of
     `from __future__ import annotations`, which is why it survived review. Restored. (`86eb355`)
   - `tools/nightly_cqc_db_check.py:4282` — F541, f-prefix with no placeholders. Text unchanged.
   - `tests/test_cqc_evidence_completeness.py:741` — B905, `zip()` without `strict=`.
     Added `strict=False`, preserving existing iteration semantics exactly.
   - `Backend` job checkout was shallow, so the new history-derived schedule tests collapsed to
     one epoch. Added `fetch-depth: 0` to that job (`ff2251f`). This **restores** the check; no
     assertion, threshold or tolerance was weakened.
4. CI: **all 5 required checks pass** — Backend, Frontend, Migration replay (real Postgres +
   PostGIS), Container images, Secret scan — plus Vercel and the preview release-SHA check.
5. Merged to `main` as `565f2f2` (merge commit, history preserved).
6. Vercel and Render both deployed `565f2f2`; confirmed by reading the live identity endpoints.
7. Release-identity pins re-promoted `14fc563d…` → `565f2f2472a19dd7a63de4dacd20b4eb2c1d156f`
   (read back after write). Production smoke had been red since before this merge precisely
   because the pins still named the 2026-09-15 SHA while production ran something else.
8. Production smoke run `35503238605` on `565f2f24`: **success**.

## Live journey evidence (production smoke, run 35503238605)

```
HEALTH: OK - status=ok operatingMode=database readMode=database writeMode=database
        notificationMode=email databaseReason=ok gitSha=565f2f2472a19dd7a63de4dacd20b4eb2c1d156f
DATA_STATUS: OK - /data-status rendered
BACKEND_BINDING: OK - freshnessStatus=partial activeLocationCount=57151
        gitSha=565f2f2472a19dd7a63de4dacd20b4eb2c1d156f
PROVIDER_SITEMAP: OK - provider sitemap index rendered
SEARCH: OK - found 'London Care (East London)' for q='East London' service_type='Homecare Agencies'
PROVIDER: OK - /provider/london-care-east-london-london rendered 'London Care (East London)'
EXPORT_GUARD: OK - anonymous export access is blocked with HTTP 401
```

## Local pre-merge evidence on the merged tree

- Full DB-enabled suite at the merged tree: **1202 passed, 2 skipped**.
- Targeted gates at the merged tree: **45 passed**.
- Unit suite as the Backend job runs it: **1135 passed, 1 skipped**.
- `ruff check api/ tools/ db/ tests/`: **All checks passed**.
- Evidence language guard: passed. Migration governance: passed.
- Falsification: the new public-serving test file is **4 failed at the reviewed parent** and
  **9 passed at the merged tree**; `SERVED_RATING_NORMALISED` does not exist at the parent.

## What this deployment does and does not fix

**Fixes now live:**
- The public read path no longer serves a rating the source has stopped publishing
  (`e478030`) — the one defect in this set that a real user could see.
- Finalization is fail-closed on identity drift and the finalize table lock is bounded
  (`SET LOCAL lock_timeout='5s'`); skip-inflated greens are refused.
- The RLS harness role dependency is fixed, so the security-invariant suite can run.

**Not fixed by this deployment (unchanged, still owed):**
- The **124 confirmed wrong registration statuses** in the database
  (67 deregistered-but-ACTIVE, 57 Registered-but-INACTIVE). The guard stops *new* corruption;
  it does not repair existing rows. Repair needs an authorised ingest/allow-list run.
- **25,755 ACTIVE providers with no overall rating.**
- Signal-poll cadence is still 4/day against a claimed 8/day promise (coverage 19.7%).
- The reconciliation tool's evaluator still fails open in four mutant families
  (23 of 36 oracle escapes); the option-A gate closed `boolean-as-measurement` 6/6.
- Ratings reviewer findings 2–3 (migration rollout safety both directions, CLI help).
- The equality-boundary decision (a registration date equal to the snapshot date) is still open.
- `cqc-reconciliation.yml` is `workflow_dispatch`-only, so deploying the tool does not run it —
  no false green verdict can be produced automatically.

## Readiness gate

`DEPLOYMENT: DONE and VERIFIED.` The CQC *repair* work remains `NOT READY` — it is blocked on the
operator's equality-boundary decision and on authorising a production data run.

## Addendum — 11:01 BST: a pre-fix production run was stopped *before* its finalize step

Verifying the deploy rather than trusting the pipeline status surfaced a live production run:
**`35497685490`** (`schedule` event, created `2026-09-20T07:44:37Z`, pinned to **`e38841c`** — the
pre-merge `main`). Direct inspection:

- `git show e38841c:incremental_update.py` -> **0 x `SHARE ROW EXCLUSIVE`**, **0 x `DEREGISTERED_STATUS_VALUES`**
- `git show 565f2f2:incremental_update.py` -> both present (`:2206` lock, `:2205` `SET LOCAL lock_timeout = '5s'`, `:747` fail-closed classifier)

So production was about to apply the **fail-open** classification logic — the logic whose defects are
measured at 57 Registered-but-INACTIVE and 67 deregistered-but-ACTIVE (124 confirmed) — to live
care-location records. 3 of 8 shards had completed; four were in progress, one queued; **`finalize`
(the committing step) had not started.**

**Action: cancelled before finalize.** Evidence read back after the cancel, not inferred:

| Check | Result |
|---|---|
| `finalize` job | `completed / cancelled` — no batch committed |
| `abort-incomplete` (workflow's designed clean-abort path) | `completed / success` |
| Live `totalSourceLocations` | **57,151** — identical to the 09:47Z pre-cancel read |
| Live release identity | `565f2f2472a19dd7a63de4dacd20b4eb2c1d156f` (deploy intact) |

**Not re-dispatched.** Starting a fresh production run is a live change and requires the operator's
approval; the next scheduled tick (cron `15 2 * * 3` -> Wednesday **2026-09-23 02:15 UTC**) runs the
fixed code automatically. Re-dispatch is available on one word.

**Consequence, stated plainly:** the 09-20 refresh did not complete, so the newest ingested snapshot
remains the 2026-09-16 CSV. The 8-day `SOURCE_FRESHNESS_SLA` still holds to 2026-09-24 — but the
margin is now three days rather than nine. The 124 wrong statuses remain wrong: the guard prevents new
corruption, it does not repair existing rows.

Rationale for acting without an answer: the operator decision form timed out. Cancelling is the
**reversible** side of an asymmetric risk — it destroys no data and is re-dispatchable — whereas a bad
finalize cannot be undone without a full repair exercise. It is also consistent with the fail-closed
posture this deployment installs: a pipeline that now refuses rather than assumes should not itself be
permitted to finalize on logic already judged defective.
