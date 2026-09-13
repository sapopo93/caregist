# TOP BLOCKERS — CareGist

**Refreshed:** 2026-09-11 00:30 BST (previous: 2026-08-20)
Ranked by what actually stops an external invoice settling.

---

## B1 — Authoritative CQC reconciliation has never completed
**Class:** data / product integrity · **Severity:** Critical
**Evidence:** `/api/v1/health` → `reconciledAt: null`, `sourceRetrievedAt: null`,
`countsReconciled: false`, `freshnessStatus: "partial"`, reason
`latest_authoritative_attempt_incomplete`; last attempt `status: "failed"`,
21,000 of 57,085 locations (**36.79 %**). `cqc-reconciliation` last run
2026-09-03, failed, 4 h 05 m.
**Why it blocks revenue:** the £745 brief is sold on the strength of official-source
verification. Without a completed reconciliation there is no defensible sourcing claim.
**Fix class:** operational run + capacity, not new code.

## B2 — CQC source is over its freshness SLA
**Class:** data / compliance claim · **Severity:** Critical
**Evidence:** source `02_september_2026_CQC_directory.csv`, `sourcePublishedAt` 2026-09-02,
`slaHours` 192. Age at 2026-09-11 00:15 = **216.2 h (9.01 days) → overdue by 24.2 h**.
`source_fresh: false`.
**Fix class:** depends on B1.

## B3 — Freshness monitoring is crash-failing and silent
**Class:** operations / detection · **Severity:** High
**Evidence:** `Freshness Watchdog` fails every scheduled run in ~17 s:
`ModuleNotFoundError: No module named 'pydantic_settings'`
(`tools/check_new_registration_pipeline.py` → `api/config.py`). The workflow has **no
dependency-install step**. `WATCHDOG_NOTIFICATIONS_ENABLED: false`.
**Why it matters:** B2 went unnoticed. The alarm that should surface B1/B2 does not run.
**Fix class:** workflow step addition. Small, testable, reversible.

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

---

## Not blockers (verify before repeating them)
- The public site is **up** and serves real DB-backed data.
- The signal poll **is** running and green.
- Feature flags are **correctly** fail-closed.
- The branch's code is **not** the problem — 60/60 backend and 10/10 frontend tests pass.
