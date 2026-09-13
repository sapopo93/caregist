# NEXT ACTIONS — CareGist

**Refreshed:** 2026-09-11 00:30 BST · One next action per workstream. No competing plans.

---

## Founder decisions required (smallest set — the rest is delegated)

**D1 — Approve the reconciliation run and the CQC source refresh?**
The public product is currently sold on evidence that is 36.79 % reconciled and **24.2 h over
its freshness SLA**. I cannot mutate the live DB without approval.
*Default if yes:* run reconciliation to completion, then ingest the current CQC directory.
*Default if no:* the £745 offer cannot be sold on a defensible sourcing claim; selling stops.

**D2 — Approve the isolated-worktree extraction of the 7 additive commits onto current `main`,
then a PR for review (not a deploy)?**
Extraction is preparation and is safe; the merge is the approval point. I will **not** merge,
and will **not** deploy.
*Default if yes:* I extract, prove migration 060 on a disposable Postgres, and return a PR
with test evidence for your approval.
*Default if no:* the instant-delivery work stays parked and unpurchasable.

**D3 — Engross the solicitor review of the immediate-supply terms?**
Published Business Terms promise a manual, cancellable, three-working-day service; the
self-serve build delivers instantly. These cannot both be true. This is the only gate I cannot
substitute with engineering or evidence.
*Default if yes:* I prepare the exact redline pack for your solicitor and hold the flag off.
*Default if no:* `territory_self_serve_checkout_enabled` stays `False` permanently.

**D4 — Confirm the Stripe and credential readiness for the £745 self-serve brief.**
`STRIPE_PRICE_TERRITORY_BRIEF` sits in Production with no reader on `main`; Blob storage and
Resend keys are unverified. I need you to confirm the live objects, or authorise me to prove
them in Stripe **test** mode only.
*Default if yes:* I verify against test mode and report; live changes remain yours.

**D5 — Approve correcting the production release-identity variables?**
Repo vars `CAREGIST_PRODUCTION_{FRONTEND,BACKEND}_SHA` point at `61513e9`, which is **not on
`main`**. Until corrected, the smoke gate cannot pass and cannot detect a bad release.
*Default if yes:* I set them to the true served SHAs and re-run smoke.
*Default if no:* release assurance stays blind.

---

## Delegated — no approval needed to prepare and test

**A1 · Fix the freshness watchdog crash** — `openai-codex` / `gpt-5.6-terra`, medium reasoning.
- Add the dependency-install step to `.github/workflows/freshness-watchdog.yml`.
- Acceptance: the workflow runs past `import api.config`; on a deliberately stale input it
  exits non-zero with a named reason. Return the run ID and log excerpt.
- Stop rule: do not touch `WATCHDOG_NOTIFICATIONS_ENABLED`; alerting needs D-approval.

**A2 · Fix frontend release identity** — same owner.
- `frontend/lib/release.ts` prefers a stale `CAREGIST_RELEASE_SHA` over the real Vercel commit.
- Acceptance: `/api/health/directory` reports the actual deployed commit; `release.test.ts`
  passes with a stale-explicit-SHA case added.

**A3 · Extract additive territory work onto current `main`** — isolated worktree only.
- Cherry-pick only the 46 additive files. **Drop** the duplicate commits.
- Acceptance: a real-Postgres run proves migration **060** applies on main's schema; the
  territory-brief suite passes on the extracted HEAD; no change to
  `provider_intelligence.py` or migration 058.
- Stop rule: no merge, no deploy, no push to `main` without approval.

**A4 · Independent challenge of the verdict** — `xai-oauth` / `grok-4.6`.
- Falsification attempt on: the phantom-SHA claim, the 36.79 % figure, the byte-identical
  duplication claim, and the 216.2 h SLA arithmetic. Must state its own falsifiers.
- Constraint: `prohibitions: [canonical_record_ownership, final_approval]`.

**A5 · Reconcile production config for undeployed code** — audit only.
- List every Production env var whose reader is absent from `main`. Remove nothing.

---

## Sequencing (dependencies, not parallel projects)

```
D1 ──> N1 ──> N2 ─────────────┐
                              ├──> credible evidence base
A1 ──> N3 (watchdog green) ───┘

A2 + D5 ──> N4 (smoke green, release identity proven)

A3 ──> N5 ──> N6 ──> PR ──[approval]──> deploy ──> N8/D4 ──> flag on
                       ▲
D3 (solicitor) ────────┘  ← hard gate, cannot be reordered or bypassed

A4 ──> challenges CURRENT_VERDICT.md; verdict amended if it falsifies anything
```

Nothing reaches a customer until **D3** and **D1** are satisfied. There is no safe way to
compress that order.
