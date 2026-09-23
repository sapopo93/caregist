# Division of work — Codex / Claude / Henry

**Written:** 2026-09-23 03:39Z by the Claude session (Repository audit).
**Why this file exists:** the previous Codex account ran out of credits mid-task.
The reconciliation investigation below was dispatched and **died before producing
anything** — treat it as NOT STARTED. This file carries the context forward so a
fresh Codex session does not re-derive it.

---

## Hard deadline

`trusted_event_ledger` watermark `reconciled_at` = **2026-09-16T12:00:07Z**.
SLA 192h → **breach at 2026-09-24T12:00Z** (~32h from writing).
Only a *successful* reconciliation resets this clock.

---

## CODEX owns

### 1. Reconciliation critical path — NOT STARTED, highest priority

Three questions:

1. **Why are scheduled runs not firing at all?** Last run of any kind:
   2026-09-20T23:34:58Z (run `35545070099`, failure). The Wednesday
   2026-09-23 02:15Z slot did **not** fire — checked at 03:33Z, 80+ min late.
   The prior Sunday slot fired at 07:44Z instead of 02:15Z (5h29m late).
   Distinguish GitHub cron drift from a workflow condition, a disabled
   schedule, or repo-inactivity rules. **Evidence, not inference.**
2. **Minimum action for ONE successful reconciliation before the breach**, and
   exactly what Henry must approve to do it.
3. **Should `--acknowledge-unconfirmed-deactivations` be a `workflow_dispatch`
   input?** It exists in `incremental_update.py` on main but is not exposed, so
   the remedy the error message itself names is unreachable from the UI.

**Already diagnosed — do NOT redo:**
- A shard aborts on a persistent CQC HTTP 500 for a single location
  (`1-147345129`, 5 retries all 500). Because `finalize` is
  `needs: [prepare, shards]` with **no `always()`**, one bad shard skips
  finalize and discards all 8 shards' work — in `35545070099`, 7 shards
  succeeded and ran to 03:47 before the whole ~4h run was thrown away.
- `finalize` separately refused on **126 unconfirmed deactivation candidates**.
- `psycopg2.OperationalError: SSL connection has been closed unexpectedly`
  in finalize after a ~4h run.
- `max-parallel: 4` over 8 shards → ~4h13m against a 5h budget. Deliberate
  (holds the CQC request rate down), not a bug, but <1h headroom.
- **CORRECTED 2026-09-23 04:00Z — the earlier claim here was wrong.** Claude
  previously wrote that `a1357fe` (#69, "give finalize the CQC credential") had
  never been shipped to a run, inferring it from commit timestamps. Codex
  challenged that and Codex is right. `gh run view 35545070099 --json headSha`
  returns **`a1357fee5b`**: the run DID check out the fix. The inference was
  bad method — git `%cd` carries the commit's own UTC offset, so comparing the
  strings misordered them, and commit order is not what a workflow checks out
  anyway. Ask the run, not the log.
  **What is actually unproven is narrower and still matters:** the finalize path
  never executed in that run, because shard 2 aborted on five consecutive CQC
  HTTP 500s and `finalize` was skipped. So #69 is untested because the run never
  reached finalize, not because it was absent.

### 2. PR #71 follow-through
- Rebase onto current `origin/main` (`78f3647`). The PR head `dca1045` is **not**
  based on it, so its green CI never covered the merge result.
- See the review findings below; they are verification results, not objections.

---

## CLAUDE owns

- **Real-Postgres verification.** It runs locally **without Docker** — this is
  the correction that matters most: `/opt/homebrew/opt/postgresql@15/bin`,
  `initdb` to a temp dir, start with `-k /tmp/cgpg` and `LC_ALL=C`. The long
  default socket path and the locale are the only two gotchas. A previous Codex
  report said this was impossible; it is not.
- **Independent review of Codex PRs.** Repo doctrine: a producing model cannot
  approve its own work.
- **Offered, not started:** a line-read of PR #71's scope-intake security logic
  (HMAC identifiers, opaque write-only references, durable quotas, guarded state
  transitions). Build-and-test green is not a security review.

---

## HENRY decides

Merges, production reconciliation runs, enabling checkout, solicitor sign-off on
immediate-supply terms, turning on watchdog notifications.

---

## Verified state (do not re-derive)

| Fact | Value |
|---|---|
| `origin/main` | `78f3647` — CI run `35814477812` **success** |
| Suite on `78f3647` | **1240 passed**, 2 skipped, with real Postgres |
| PR #71 head `dca1045`, real Postgres | **1233 passed**, 1 skipped |
| main + PR #71 merge result | **no conflicts**; **1254 passed**, 1 skipped; ruff clean; migration governance clean; frontend 186 passed; type-check clean |
| Migration `064_territory_scope_requests.sql` | applies cleanly on top of `060`–`063`; lifecycle test passes on real Postgres |
| Migration numbering collision | **resolved** (was `061`, now `064`) |

**Correction to an earlier Codex report:** "Backend: 927 passed" was measured on
`hermes/cqc-nightly-evidence-20260920`, 21 commits behind `origin/main`. The true
baseline at that time was **1157**. Verify against `origin/main`, not a stale
branch — the stale base was missing migrations 061–063 and the finalize fixes
(#65, #67, #68, #69) that bear directly on the reconciliation diagnosis.

---

## Standing constraints

Checkout, collectors, outbound delivery, leads, claims and exports stay
**fail-closed**. No merge, deploy, live Stripe change, live data mutation or
outbound customer message without Henry's explicit approval. A producing model
cannot approve its own work.

---

## SETTLED DIVISION — 2026-09-23 03:50Z

Agreed by both sides (Codex stated its claim in its own session; Claude observed
it and stood down from the overlapping item). **Do not cross these lines without
saying so here first.**

### Codex owns (producer)
- **Reconciliation evidence** — the three questions above. Still the first real
  pass; nothing has run yet.
- **The intake limiter fix** — `getRequestSource()` in
  `frontend/lib/territory-scope-request.ts` falls back to the literal
  `"unknown"` off-Vercel and whenever `x-vercel-forwarded-for` / `x-real-ip` are
  both absent, so every unresolved requester shares ONE `requesterFingerprint`.
  The quota rejects at `source_count >= 5` per hour, so five requests can
  globally rate-limit the £745 intake for everyone. **Claude found this and has
  deliberately NOT fixed it** — the file is Codex's.
- **Rebasing PR #71** onto `origin/main` (`78f3647`).

Already done by Codex in `21c1747` (verified by Claude): quota keys moved from
raw `contact_email` to `contact_fingerprint`, the duplicate path no longer
returns another requester's `public_reference`, and an attempts table was added.

### Claude owns (independent reviewer)
- Real-Postgres verification of anything Codex produces. **Correction to the
  Codex session's note:** the real-Postgres pass WAS done — PR #71 head 1233
  passed, merge result 1254 passed, ruff and migration governance clean. Only
  the line-read of the security logic was additional.
- Independent review. A producing model cannot approve its own work.

### Still unowned / Henry only
Merges, production reconciliation runs, enabling checkout, solicitor sign-off,
watchdog notifications.

---

## GREEN CHECKLIST — morning readiness

Maintained by Claude (planner/reviewer). Codex: update your rows as you land
work; do not mark a row green without the evidence column filled.
**A claim is not evidence.** Every row below was checked, not assumed.

| # | Item | Owner | Status @ 03:52Z | Evidence / gap |
|---|---|---|---|---|
| G1 | CI green on `origin/main` | — | RUNNING | `68121f8`, runs 35815841736 (CI) + 35815841728 (Smoke) |
| G2 | Intake limiter fail-open (`getRequestSource` → one shared `"unknown"` fingerprint; 5 requests globally 429 the £745 intake) | **Codex** | **OPEN** | Claimed taken at 03:50Z; **verified unchanged at `6199417`**. Not started or not finished. |
| G3 | PR #71 rebased onto `origin/main` | **Codex** | **OPEN** | PR head `dca1045`; main is `68121f8`. Local branch `6199417` is ahead but **unpushed**, so the PR still shows the old head. |
| G4 | PR #71 independently reviewed + real-Postgres verified | **Claude** | DONE for `dca1045` | head 1233 passed; merge result 1254 passed; ruff + migration governance clean. **Must be re-run after G3.** |
| G5 | PR #71 merged | **Henry** | BLOCKED | Needs G2, G3, G4. |
| G6 | Why scheduled reconciliation runs are not firing | **Codex** | IN PROGRESS | No run of any kind since 2026-09-20T23:34:58Z. Wed 02:15Z slot did not fire. |
| G7 | One successful reconciliation before **2026-09-24T12:00Z** | **Henry** (approval) + Codex (execution) | **OPEN — hard deadline** | Watermark 2026-09-16T12:00:07Z. Writes production, so Henry approves. |
| G8 | VA packs + readiness check factually accurate | **Claude** | **DONE** | `68121f8`: terms and VAT rows corrected to PASS with section-level evidence; per-deal vs structural blockers separated; verdict deliberately unchanged. |
| G9 | Live pages carry the shipped VAT wording | **Claude** | **DONE** | `/pricing/territory`, `/terms`, `/territory-opportunity-brief` all 200 and all show "£745 fixed fee. No VAT added." Verified against production, not the repo. |
| G10 | Stripe policy links + Terms acceptance at checkout; one checked paid journey | **Henry only** | **OPEN** | No agent can clear these. They are what keeps G-overall short of "can take payment". |

### What "green" does and does not mean

Green on G1–G9 means the repo is correct, verified and safe to hand a VA at 8am:
accurate pricing wording everywhere, accurate readiness guidance, and no known
fail-open on the intake path.

It does **not** mean payment can be taken. **G10 is Henry's alone**, and until it
lands the VA's ceiling is: agree scope in writing, quote £745, record the buyer's
criteria. No payment link, no accepted order. Checkout staying fail-closed is the
gate working.

---

## REVIEW ROUND 1 — Claude → Codex, 2026-09-23 04:02Z

PR #71 head `f7ed109`. Verified independently, not taken on claim.

### Passing (credit where due)
- **G2 limiter: FIXED and verified.** `getRequestSource` now falls back to
  `contact:${email}` instead of a shared `"unknown"`, so one requester can no
  longer 429 the whole £745 intake. Email is HMAC'd into the fingerprint, the
  normalized address is used, and `network:` / `contact:` prefixes keep the two
  namespaces from colliding. Good fix.
- **Dedupe window: fixed better than I proposed.** The fixed-window boundary I
  flagged is gone entirely, replaced by a required `Idempotency-Key` header.
  `TerritoryScopePicker` sends it and reuses the same key on retry (`||=`),
  which is correct idempotency semantics.
- **G3 rebase: DONE.** `origin/main` is an ancestor of `f7ed109`; merge is clean,
  zero conflicts.
- ruff clean, migration governance clean, **1253 of 1254 passing** on real
  Postgres.

### FAILING — Codex to fix

**F1. Your own test fails on your own branch.** CI Backend job is red
(`35815991792`), and it reproduces locally:
`tests/test_nightly_cqc_db_check.py::test_round2_9_epoch_start_dates_use_the_earliest_commit_a_schedule_was_in_force_from`

```
At index 4: ('37 18,21,0,3 * * *', 2026-09-23T04:51:24+01:00, '0f8b02c...')
       != ('37 18,21,0,3 * * *', 2026-09-23T03:22:10Z,      '12d0584...')
```

`0f8b02c` and `12d0584` are the *same commit* before and after your rebase. The
test pins a literal commit SHA and timestamp derived from git history, so **any**
rebase invalidates it — it will break again the next time the branch moves.
Updating the expected SHA is not the fix; deriving the epoch rather than pinning
it is. Your call, but please don't leave a test that fails on every rebase.

**F2. Not yours — do not try to fix it.** "Production schema is current" is red
because production has not applied migration `064`. That is the schema-drift gate
(#65) doing its job. Clearing it is a production write, so it is **Henry's**, and
it means PR #71 cannot merge tonight no matter how green the code gets.

### Claude's own error, corrected
I claimed `a1357fe` was never shipped to a run. Wrong — see the CORRECTED entry
above. Codex caught it. Method note for both of us: ask the run what it checked
out; do not infer deployment from commit timestamps.

---

## G11 — Production Smoke red on `main`. NOT a broken deploy.

Diagnosed 2026-09-23 04:08Z. This is warroom **B4**, now precisely located.

`production-smoke.yml` compares the deployed SHA against repo variables
`CAREGIST_EXPECTED_FRONTEND_GIT_SHA` / `CAREGIST_EXPECTED_BACKEND_GIT_SHA`, both
pinned to `a1357fee5bd2a63dafcee75ab6129e659b0b5ef7`. The log shows the check
retrying 14 times against a deployed SHA that was *correct the whole time*:

```
deployed frontend Git SHA '68121f80fe...' did not match expected 'a1357fee5b...'
```

**Deployment is healthy — this is the good news.** Production picked up
`78f3647` and then `68121f8` within minutes of each push. Verified independently
of the smoke check: `GET /api/health/directory` returns
`release.gitSha = 68121f80fe`, `status: ok`, and the three buyer-facing pages
serve the correct VAT wording. Production is live on current `main`.

The pin is stale, so the gate can now only ever fail — it names a commit that
will never be deployed again.

**Deliberately NOT fixed by Claude.** Setting expected = deployed while nobody
is watching turns a release-assurance gate into a tautology, and it goes stale
again on the next merge. The durable fix is the deployment-derived release
identity already in PR #71 (Codex's lane, item 5). If that cannot merge tonight
— it is blocked on F2, which is Henry's — then the interim is one command for
Henry in the morning, run only after confirming production really is on `main`:

```bash
gh variable set CAREGIST_EXPECTED_FRONTEND_GIT_SHA --body "$(git rev-parse origin/main)"
gh variable set CAREGIST_EXPECTED_BACKEND_GIT_SHA --body "$(git rev-parse origin/main)"
```

---

## REVIEW ROUND 2 — 2026-09-23 04:25Z. PR #71 is code-green.

**F1 is CLOSED — Codex fixed it itself**, in `457a5ca` "test(polling): keep
schedule history rebase-safe", and fixed it the right way: it pins the four
settled epochs (commits on main, stable) and asserts durable properties for the
newest one instead of a SHA git rewrites. Arguably tighter than the patch Claude
had prepared, because it bounds the epoch below by the originally reviewed
timestamp rather than only by ordering. Claude's patch was discarded unpushed —
no duplicate work landed.

**Independently verified by Claude at `457a5ca`** (not taken on claim):
`origin/main` is an ancestor · ruff clean · migration governance clean ·
**1254 passed, 1 skipped on real Postgres**. CI agrees: Backend, Frontend,
Migration replay, Container scan, Secret scan and preview SHA all pass.

### The only red left on PR #71 is not a code problem
`Production schema is current` fails because production has not applied
migration `064`. That is the schema-drift gate (#65) working exactly as intended
— it refuses to let code merge ahead of the schema it needs. Clearing it is a
production write. **Henry only.**

---

## MORNING STATE — what is green, what is not, and who owns what

| | State | Owner |
|---|---|---|
| `main` CI (`68121f8`) | **GREEN** | — |
| Production deployment | **HEALTHY** — serving `68121f8`, `/api/health/directory` `status: ok` | — |
| Buyer-facing VAT wording, all surfaces | **GREEN**, verified live | — |
| VA packs + readiness check | **GREEN**, corrected and evidence-backed | — |
| PR #71 code | **GREEN**, independently verified on real Postgres | — |
| PR #71 merge | **BLOCKED** — needs migration `064` in production | **Henry** |
| `main` Production Smoke | **RED** — stale SHA pin only; deploy is healthy (see G11) | **Henry** |
| Reconciliation SLA | **BREACHES 2026-09-24T12:00Z** | **Henry** approves the run |
| Stripe policy links + checked paid journey | **OPEN** | **Henry** |

### Henry's morning list, shortest path first

1. **Re-pin the smoke SHAs** (one command each, in G11 above). Claude verified
   production is genuinely on `main` but was correctly blocked from writing repo
   variables unsupervised. This turns `main` fully green.
2. **Apply migration `064` to production**, then PR #71 merges. Everything else
   on it is already green.
3. **Reconciliation before 12:00Z.** Codex established the schedule is *not*
   disabled — Actions are enabled, the workflow is on the default branch, and the
   two prior cron events arrived 5h26m and 5h30m late, so the "missing" Wednesday
   slot was judged too early to call lost. A manual run is the reliable path and
   it writes production, so it is yours to authorise.
4. **Stripe policy links + one test transaction** — the last things standing
   between the VA and taking money.

### Known-incomplete, so nobody claims it later
- The manual-only `--acknowledge-unconfirmed-deactivations` workflow input
  Codex reported as prepared with 96 passing tests is **not on the pushed
  branch** (`grep` over `457a5ca` finds nothing). It is local to Codex only.
- The reconciliation *report and patch* Codex was generating had not landed at
  the time of writing.
- No reconciliation has run since 2026-09-20T23:34:58Z.

---

## RECONCILIATION — go/no-go check for the morning, 2026-09-23 04:45Z

Checked before Henry spends four hours on a run that might be doomed.

### The blocker that killed the last run has CLEARED
`1-147345129` — the location that returned five consecutive HTTP 500s and
aborted shard 2 in run `35545070099` — **now returns HTTP 200** against the live
CQC API. A second previously-unconfirmed id (`1-10057845166`) also returns 200.
That outage was transient and is over. A fresh run has a real chance of
completing.

### The amplifier is still UNFIXED — this is the residual risk
`finalize` on **both** `origin/main` and `origin/codex/release-evidence-gates-main`
is still:

```yaml
  finalize:
    needs: [prepare, shards]     # no always()
```

So **any single** shard failure still skips finalize and discards the whole run.
Across 57,151 locations in a ~4h15m window, one transient upstream 500 anywhere
costs the entire attempt. The specific poison is gone; the mechanism that turns
one bad location into a total loss is not.

### Resume exists — a failure does not cost the full four hours again
`workflow_dispatch` accepts `resume_batch_id` (failed batch UUID) plus
`resume_run_id` (the Actions run holding the immutable manifest). A run that dies
part-way can be resumed from its manifest rather than restarted. Both inputs are
required together.

### Recommendation for Henry
With ~32h to the breach and ~4h15m per attempt there is room for two or three
tries, and the known blocker is clear, so **triggering a run is now reasonable**
— it was a coin flip 24h ago, it is not now. Two things to know going in:

1. If a shard dies on a transient 500, **resume it** with `resume_batch_id` +
   `resume_run_id` rather than starting over.
2. If finalize is reached and refuses on unconfirmed deactivations, there is no
   way to clear it **from the Actions UI**. It is not a dead end, though —
   *(corrected 04:55Z; an earlier line here called it one, which overstated it)*
   — `--acknowledge-unconfirmed-deactivations` exists on `origin/main` today as
   an argparse flag (`incremental_update.py:2578`), so the recovery path is
   available by running the tool directly against production.

   It is also already manual-only by construction, which is the property that
   matters: it defaults to false and the workflow never passes it, so a
   *scheduled* run cannot acknowledge unconfirmed deactivations no matter what.
   That safety property is what must survive if the input is ever added to
   `workflow_dispatch` — an input wired so a scheduled run could reach it would
   let automatic reconciliation silently accept deactivations CQC never
   confirmed, which is exactly the "never assert what the source did not say"
   rule. Claude deliberately did not add that input unsupervised at 05:00 for
   this reason; the gating deserves a reviewer who is awake.

Still a production write. Still Henry's call.
