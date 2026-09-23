# TOP BLOCKERS — CareGist

**Refreshed:** 2026-09-23 02:27–03:50 BST against live production, GitHub Actions and the
repository.
Ranked by what actually stops an external invoice settling.

---

## Current ranking (authoritative)

1. **Reconciliation reliability — Critical.** Last complete run: 2026-09-16, 57,151/57,151.
   Latest run `35545070099` failed after five CQC HTTP 500s for `1-147345129`; health correctly
   remains partial and checkout closed.
2. **Signal-poll schedule coverage — High.** 17 starts from 28 opportunities in seven days,
   below the unchanged minimum of 24. Completed starts were all successful. The `:37` schedule
   change is unproven until observed for a full window.
3. **Release smoke configuration — High.** Both live surfaces serve current `origin/main`
   (`9ece886…`), but scheduled smoke expected stale `a1357fee…` and failed. Served identity is
   fixed; the deployment variables still need an approved update.
4. **Legal/operational checkout gates — Critical for self-serve.** Legal approval and a full
   disposable-environment commercial proof are still absent. Checkout and delivery remain off.
5. **CI evidence pending — High.** Territory fulfilment and scope lifecycle are wired to the
   disposable Postgres job, but no CI run for this local change set exists yet.

The detailed entries below retain the historical record. Where they conflict with this current
ranking, this section and `CURRENT_VERDICT.md` take precedence.

---

## B1 — Authoritative CQC reconciliation has never completed — **CLOSED 2026-09-23**
**Class:** data / product integrity · **Severity:** Critical (was)
**Closing evidence:** a reconciliation **completed** on 2026-09-16T12:00:07Z. Source 57,151 vs
checked 57,151 — counts agree (`artifacts/cqc-nightly/2026-09-23-report.json`,
`watermark.reconciled_at`). The defensible sourcing claim now exists.
**But see B9:** it completed once and has failed five times since. The capability is proven;
its reliability is not, and the freshness clock it sets expires ~2026-09-24 12:00Z.

<details><summary>Original entry</summary>

**Class:** data / product integrity · **Severity:** Critical
**Evidence:** `/api/v1/health` → `reconciledAt: null`, `sourceRetrievedAt: null`,
`countsReconciled: false`, `freshnessStatus: "partial"`, reason
`latest_authoritative_attempt_incomplete`; last attempt `status: "failed"`,
21,000 of 57,085 locations (**36.79 %**). `cqc-reconciliation` last run
2026-09-03, failed, 4 h 05 m.
**Why it blocks revenue:** the £745 brief is sold on the strength of official-source
verification. Without a completed reconciliation there is no defensible sourcing claim.
**Fix class:** operational run + capacity, not new code.

</details>

## B2 — CQC source is over its freshness SLA
**Class:** data / compliance claim · **Severity:** Critical
**Evidence:** source `02_september_2026_CQC_directory.csv`, `sourcePublishedAt` 2026-09-02,
`slaHours` 192. Age at 2026-09-11 00:15 = **216.2 h (9.01 days) → overdue by 24.2 h**.
`source_fresh: false`.
**Fix class:** depends on B1.

## B3 — Freshness monitoring is crash-failing and silent — **CLOSED 2026-09-23**
**Class:** operations / detection · **Severity:** High (was)
**Closing evidence:** `.github/workflows/freshness-watchdog.yml` now has an explicit
"Install watchdog dependencies" step running `pip install -r requirements-api.txt`, so the
`pydantic_settings` import graph is present, and sets `APP_URL: https://caregist.co.uk` so
`validate_production()` no longer kills the import. A separate always-run step reports monitor
health and source freshness as two distinct verdicts.
**Residual:** `WATCHDOG_NOTIFICATIONS_ENABLED` still defaults `false`, so the watchdog runs but
stays silent — five consecutive reconciliation failures raised no alert. Detection is fixed;
**notification is not**. Turning it on is a founder decision.

<details><summary>Original entry</summary>

**Class:** operations / detection · **Severity:** High
**Evidence:** `Freshness Watchdog` fails every scheduled run in ~17 s:
`ModuleNotFoundError: No module named 'pydantic_settings'`
(`tools/check_new_registration_pipeline.py` → `api/config.py`). The workflow has **no
dependency-install step**. `WATCHDOG_NOTIFICATIONS_ENABLED: false`.
**Why it matters:** B2 went unnoticed. The alarm that should surface B1/B2 does not run.
**Fix class:** workflow step addition. Small, testable, reversible.

</details>

## B4 — Release identity is unverified; smoke gate cannot pass
**Class:** release assurance · **Severity:** High
**Evidence:** smoke expects `61513e9…` (2026-09-03 repo var) but `61513e9` **is not an
ancestor of `origin/main`**. Production serves backend `9127923` (= main) and frontend
`1c98de7` (2026-09-03, 9 commits behind). Red on every scheduled run since 2026-09-03.
**Fix class:** correct the repo variables to real SHAs; fix `CAREGIST_RELEASE_SHA`
preference in `frontend/lib/release.ts` so the frontend stops misreporting.

## B5 — Instant-delivery branch is unmergeable as-is
**Class:** engineering integration · **Severity:** High
**Evidence:** `feat/territory-self-serve-scope` (tip `9fcd697`) is 39 behind / 12 ahead of
`origin/main`; production is **not** an ancestor. `api/services/provider_intelligence.py`
and `db/migrations/058_crm_provider_intelligence.sql` are **byte-identical** to `main`
(`e609086332295d56…`, `e4388608418c48de…`) under different SHAs.
**Consequence:** a wholesale merge collides with live work.
**Fix class:** extract only the 46 additive files / 7 additive commits onto current `main`
in an isolated worktree.

## B6 — Instant self-serve delivery is legally blocked
**Class:** legal / consumer terms · **Severity:** Critical (for the self-serve offer)
**Evidence:** published Business Terms describe a **manual, cancellable,
three-working-day** service. The branch implements **fully-instant** delivery with
immediate-supply consent (`docs/territory-brief-terms-draft-FOR-SOLICITOR-2026-09-09.md`,
and the flag comment in `api/config.py`).
**Consequence:** enabling `territory_self_serve_checkout_enabled` without solicitor sign-off
would sell under terms that contradict what is published.
**Fix class:** **solicitor sign-off — non-delegable to any agent.**

## B7 — Production config for undeployed code
**Class:** governance / config hygiene · **Severity:** Medium
**Evidence:** Vercel **Production** holds `TERRITORY_BRIEF_CHECKOUT_ENABLED` and
`STRIPE_PRICE_TERRITORY_BRIEF`; no code on `main` reads them.
**Fix class:** reconcile or remove. No live exposure today.

## B8 — Production deployment record disagrees with served code
**Class:** release assurance · **Severity:** Medium
**Evidence:** GitHub records a Production deployment for `9127923` (2026-09-09T01:25Z);
the deployed frontend reports `1c98de7`. Either the record is optimistic or the frontend
deploy did not promote.
**Fix class:** reconciles with B4.

## B9 — Reconciliation succeeds about one run in six — **OPENED 2026-09-23**
**Class:** data / product integrity · **Severity:** Critical
**Evidence:** `artifacts/cqc-nightly/2026-09-23-report.json` — `runs_by_type.reconciliation`
= **5 failed, 1 completed**. The one success was 2026-09-16T12:00:07Z; `watermark.age_hours`
157.0 against a 192 h SLA, so the freshness clock it set **expires ~2026-09-24 12:00Z**. The
schedule is Sunday and Wednesday 02:15Z, so 2026-09-20 did not succeed.
**Why it matters:** B1 proved reconciliation *can* complete. This is the harder problem — it
does not complete *reliably*, and the £745 sourcing claim depends on a clock only a successful
run resets. B2 recurs on its own unless this is fixed.
**Fix class:** diagnose the five failures first. Likely an operational run; **needs Henry's
approval** because a real reconciliation writes to production.

## B10 — Signal polling lands ~60 % of its scheduled runs — **OPENED 2026-09-23**
**Class:** operations / collection · **Severity:** High
**Evidence:** cron is four slots a night (28/week). `polls_7d` = **17 completed of 17 runs**
— i.e. ~11 scheduled runs never started at all, not 11 that failed. `polls_24h` = **2** of 4.
**Why it went unseen:** the nightly report compared this against a hardcoded `336`
(48/day × 7), a cadence retired on 2026-09-15, so the line read "17 of 17 (required 336)"
every night — permanently alarming and therefore permanently ignored.
**Status of the fix:** a concurrent session introduced
`api/services/cqc_polling_policy.py`, moving the cron to `:37` to avoid the start-of-hour
Actions scheduling peak and making the cron, timeout, budget and minimum one shared source
(`MINIMUM_POLLS_IN_WINDOW` = 24, tolerating one missed night). Whether `:37` actually recovers
the missing runs is **unproven** — it needs a week of observation.

---

## Not blockers (verify before repeating them)
- The public site is **up** and serves real DB-backed data.
- ~~The signal poll **is** running and green.~~ **Withdrawn 2026-09-23 — see B10.** The poll is
  running and its completed runs are green, but it lands ~17 of 28 scheduled runs. "Green when
  it runs" was being read as "running as scheduled"; those are different claims.
- Feature flags are **correctly** fail-closed.
- The branch's code is **not** the problem — 60/60 backend and 10/10 frontend tests pass.
  *(2026-09-23: the backend suite is now 920 passed / 34 skipped, and every skip is a real-
  Postgres integration test that CI does run. One exception is now fixed — see below.)*
- **Closed 2026-09-23:** `tests/test_territory_brief_pg_integration.py` was gated on a
  `TB_PG_URL` that no workflow set, so the only real-schema proof of the paid fulfilment path
  silently skipped everywhere while the suite reported green. It now lives in
  `tests/integration/`, runs on CI's Postgres service, and passes.
