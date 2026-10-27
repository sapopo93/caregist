## 2026-10-24 next bounded action — independent review of report-readiness packet

Independent approved-provider review of [REPORT_READINESS_EVIDENCE.md](REPORT_READINESS_EVIDENCE.md) and its PR (branch `feat/report-readiness-20261024`), using the checklist in that file. Review it together with open PR #123, whose API-else-file precedence this resolver contract replaces. Keep `resolved_rating_contract_enabled`, `competitor_scan_enabled` and `p12_list_enabled` false.

After review, smallest next fixes:
- re-check the State of Care reference values;
- decide whether the 51 unreconciled CQC deregistrations need an approved reconciliation run;
- add dual-registration merging to report outputs.

No merge, deploy, production write or gate change is authorised by this entry.

## 2026-10-22 quarantine release preparation

Production read-only verification confirms migration 067 is already applied, with three unresolved quarantined location IDs and 59,382 stored location rows. `db/apply_migrations.py --target production --check` reports no pending migrations for this release candidate. No production migration or source-row mutation was performed. Current-main integration adds persistent quarantine to pipeline evidence/logs and keeps source freshness partial while quarantined ACTIVE records remain; Data Status exposes their count. Local finalizer tests include resolved, manifest-present, inactive, missing-provider and missing-schema cases. Deployment and preview activation still require the exact candidate's CI and independent review. This supersedes older statements below that migration 067 was unapplied; commercial gates remain closed.

## 2026-10-22 single next bounded fix — proposal, not implementation

Prepare a provenance-aware resolved-current-rating input contract for the Territory Brief, consistently carried through current-state tables, narrative, evidence appendix, PDF/CSV/JSON and rating-based scope decisions. Preserve API/file values, publication dates, edition/hash and current/inherited/unresolved status. Do not duplicate unconditional API-first precedence or invent rating-change events from a snapshot. Use the frozen 20 file-backed, five conflict and five unrated fixtures, plus the observed post-snapshot/current-provider cases, as acceptance evidence. No implementation was performed by this audit.

First challenge the [frozen evidence packet](../artifacts/rating-audit/2026-10-22/REVIEW_HANDOFF.md) under the current operating loop. Grok retest and an independent reviewer from an approved provider remain required; DeepSeek is prohibited. Keep all named gates unchanged. No production write, merge or deploy is authorised by this recommendation. [Report](../artifacts/rating-audit/2026-10-22/REPORT.md).

## 2026-10-18 next bounded action

Complete independent review of [PR #94](https://github.com/sapopo93/caregist/pull/94), then apply its migration through the repository's production migration workflow after the restore point is verified. Verify the three IDs are recorded as unresolved exceptions and remain ACTIVE, and confirm the next reconciliation skips their detail calls while preserving identity checks. Ask CQC for the cause of the three HTTP 404s and for the identity/status behind `1-29608453477`; clear each exception only after authoritative evidence. Keep checkout/delivery gates as reported by live health; continue human-led sales only with verified claims. See [run evidence](../artifacts/cqc-nightly/2026-10-18-reconciliation-run-39113995661.md).

---

## 2026-10-16 evening follow-up (Henry's five instructions)

Next single bounded action: Henry runs the read-only backfill dry run locally with the command in [backfill-dry-run-command.md](../artifacts/collection-evidence/2026-10-16/backfill-dry-run-command.md) and returns the two output files. Then review the concrete diff in [STAGE3_REVIEW_PACK.md](../artifacts/product-research/2026-10-16/STAGE3_REVIEW_PACK.md) (migration 066, rollback plan, retention proposal). The 14 Oct cancellation actor is unknown ([analysis](../artifacts/collection-evidence/2026-10-16/reconciliation-cancellation-14-oct.md)). Gates unchanged and closed.

---

## 2026-10-16 next single bounded action
From a machine that can reach cqc.org.uk and the CQC API: capture what the poller's request returns (status, content type, hash, markup, robots.txt for /search), then decide replace, supplement or retire the report-index route (fix list S2, S4). In parallel, founder to approve a read-only production dry run of `tools/backfill_rating_change_dates.py` and name the sample buyer. Details and owner decisions: [IMPLEMENTATION_STATUS.md](../artifacts/product-research/2026-10-16/IMPLEMENTATION_STATUS.md). Older entries below are historical.

---

## 2026-10-09 buying audit — next bounded work

Merge only the independently reviewed fail-closed repair after required CI, using Henry’s standing merge authorization. Keep gates closed. Next engineering proof: durable reconciliation for outer-commit failure/process interruption plus orphan-upload cleanup policy. Next product proof: carry agreed criteria through outputs and supply each promised qualification question. Digest-specific terms need approval before a four-week delivery/recovery rehearsal. Assign actual staff owners and exercise authorized synthetic enquiry/payment/inbox/private-file/acceptance receipts. [Evidence and acceptance checklist](../artifacts/buying-audit/2026-10-09/BUYING_PROCESS.md). Older entries below are historical.

---

## 2026-10-09 — current completion audit (PARTIAL)

Current read-only release: `59310ecc100119d6d775d70e62db758882bf5b8f` on GitHub main and both public services. PR #82 is merged. This dated observation supersedes older release/operational claims below; it does not approve commercial gates. Source reconciliation is stale/incomplete, checkout and delivery are closed. Repair branch `codex/completion-20261009` integrates PR #83 and corrects independently reproduced queue/CSV/shortfall defects. See [the audit](../artifacts/completion/2026-10-09/AUDIT.md) and [33-PR inventory](../artifacts/completion/2026-10-09/PR_INVENTORY.md) for raw evidence, actual checks, uncommitted preservation and remaining work. Grok/DeepSeek provider failures leave the prescribed independent gates uncompleted. Historical entries below are archives, not a new action list.

---

## 2026-10-03 19:25 BST — bounded engineering release checkpoint

Authoritative release: `a0d5b5df564a1d553cc7a9effcca91483a91ab0a`. Primary checkout, local main, GitHub main,
production frontend `/api/health/directory` and backend `/api/v1/version` match.
PRs [76](https://github.com/sapopo93/caregist/pull/76),
[77](https://github.com/sapopo93/caregist/pull/77),
[78](https://github.com/sapopo93/caregist/pull/78) and
[79](https://github.com/sapopo93/caregist/pull/79) are merged under explicit
founder authorization. Production deployment 6831343115 succeeded.
[Exact-main CI](https://github.com/sapopo93/caregist/actions/runs/37143767171) PASS; [Production Smoke](https://github.com/sapopo93/caregist/actions/runs/37143826320) PASS; schema check PASS.
Local verification: 64 migrations applied on disposable PostGIS; real-Postgres
Brief fulfilment PASS; full pytest 1,226 PASS / 70 SKIP; frontend tests 184 PASS;
Next.js 16.3.8 build PASS. Payment, storage and email in paid-path tests are mocks.
Smoke verifies the public directory and release identities, anonymous export
refusal; authorized lead/export delivery is not claimed or tested live.

Live `/api/v1/health`: checkoutReady=false, shadowCoveragePassed=false,
deliveryEnabled=false, delivery.enabled=false. No commercial gate, source
backfill, live Stripe object, balance or production data was changed. This
engineering result is not independent product acceptance or first-sale approval.
Existing protected local changes are preserved and remain uncommitted.
Temporary backup: `/private/tmp/caregist-before-final-release-20261003`.

The named engineering fixes and authorized release are complete. Next actions
are independent journey review and the existing human commercial/legal gates.
Do not fabricate polling history or enable checkout/delivery. Do not retry
historical date backfills without a separate approved migration. PR #71 remains
outside this release. Existing CLAUDE.md, .gitignore, .warroom and .projects work
must not be committed without specific founder authorization.

---

# NEXT ACTIONS — CareGist

> **2026-10-02 commit/deploy correction:** [COMMIT_DEPLOY_TRUTH.md](COMMIT_DEPLOY_TRUTH.md) is authoritative for release identity. The active checkout, local main, GitHub main, successful Production deployment and both public services match `1a62f84`. PR #75 is merged and Production Smoke 37004402261 PASSED. Local uncommitted work is preserved separately. Older release/smoke claims below are historical; no commercial gate approval is implied.

Commit/deployment alignment is complete. Future releases must produce a successful GitHub Production deployment record and pass smoke without a SHA override. Continue only the separately named product/commercial tasks; do not repeat the old branch-alignment work.


## 2026-10-01 Territory Brief next step — proposal, not implementation approval

Freeze one named registration-focused scope with enough provider-deduplicated
candidates and independently review dates, URLs and source evidence before
promising a count. London homecare's preliminary complete-metadata subset is
21; broader social-care scope has 147. These counts are not accepted leads.
Then specify the Postgres source contract, calendar freshness, grouping and
actual deliverable formats. A source adapter alone cannot close all blockers.

For the rating-change edition, first recover independently checkable,
publication-dated before/after history. NULL effective dates are not proof of
no CQC movement. Do not backfill them from observed_at. No source write,
implementation, invoice, outreach, delivery or gate change was performed.

## 2026-10-01 next bounded commercial step — proposal for independent review

Prepare one current-source, independently reviewed £150 four-week Digest pilot
pack for a supported consultancy scope. Verify included events and source links,
align the written scope and terms, and prove the approved manual payment-to-
delivery path. Keep all gates closed until their named acceptance and founder
decisions are recorded. This research does not authorise sending or invoicing.

After those gates pass: validate three paid pilots and require explicit paid
continuations before creating an ongoing offer. Use the £745 Brief only for a
separately qualified territory decision. Reopen a licensed feed only for a
buyer-funded integration; do not build a third product speculatively.

See `artifacts/product-research/2026-10-01/PRODUCT_RECOMMENDATION.md` for buyers,
proposed economics, renewal tests, 2026–2028 sequencing and evidence limitations.

## 2026-10-01 archive review — current live status NOT VERIFIED

The September 23 closure below is a historical checkpoint. The saved September 24
nightly report corroborates its 13:18 reconciliation watermark. Saved reports through
October 1 record later reconciliations, but were not independently revalidated live
in this review. See `artifacts/cqc-nightly/ARCHIVE_NOTES.md` for reporting limitations.
Keep all named gates closed pending their separate evidence and independent review.

## 2026-09-23 14:16 BST ordered checkpoint

1. Treat reconciliation and source freshness as passed: runs `35821214442` and `35833372207`
   succeeded, and production freshness is HTTP 200 `fresh` with 100% coverage.
2. Do not enable checkout. The next measured blocker is shadow coverage: observe until at
   least 24 signal-poll starts exist in the seven-day window with at least 90% completion.
3. Keep delivery disabled until the legal, migration, release, and disposable payment-to-
   fulfilment journey gates pass independently.
4. Continue normal scheduled reconciliation observation; do not dispatch another manual run
   or weaken thresholds based on this closure.

The earlier D1 reconciliation decision is satisfied and no longer requires founder action.

## 2026-09-23 ordered checkpoint

1. Merge and run CI for the current bounded change set; require the migrations job to execute
   territory fulfilment and scope-request lifecycle tests against disposable Postgres.
2. Observe the `:37` signal-poll schedule for seven days. Acceptance: at least 24 starts, at
   least 90% complete, and latest completed poll remains within 16 h.
3. Run the next scheduled reconciliation unchanged. If `1-147345129` still returns HTTP 500,
   preserve full-run evidence and choose an explicit record-level retry/quarantine design;
   do not lower reconciliation or freshness thresholds.
4. Update `CAREGIST_PRODUCTION_FRONTEND_SHA` and `CAREGIST_PRODUCTION_BACKEND_SHA` only through
   the approved deployment process, then require scheduled smoke green.
5. Do not enable checkout. First obtain legal approval, apply migrations through 064, prove a
   real request → review → accepted → paid → fulfilled → downloadable journey in a disposable
   environment, and obtain independent review.

---

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
