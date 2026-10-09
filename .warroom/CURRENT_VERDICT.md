## 2026-10-09 buying audit — current dated checkpoint

PARTIAL. Observed production at 09:07 UTC serves `3d3f3e42e95d3f1829387df19731eb819d93e993`. Discovery and enquiry initiation work; receipt, staff handling and complete paid delivery are unverified. Reviewed local repair branch `codex/buying-process-audit-20261009` fixes refund schema/audit atomicity, failed-generation payment evidence, immutable identity/consent, refund replay ordering and enquiry-only coverage semantics. Final local validation: 1,400 backend/Postgres passed, two explicitly skipped; 82 recovery checks; 183 frontend checks; six live-page browser scenarios. Independent technical re-review clears the HIGH findings for the bounded fail-closed repair; MEDIUM commit/interruption/orphan cleanup remains. Product/criteria, Digest terms, deployable source and real operational receipts remain unverified. This checkpoint is not deployment or commercial approval. [Full evidence](../artifacts/buying-audit/2026-10-09/BUYING_PROCESS.md).

Older dated entries below are historical.

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

Engineering defects addressed: provider-level shortlist deduplication; future
CQC publication dates retained through event construction and ledger INSERT;
undated rating-summary refusal; stale RI evidence dates/context and generation-
based recency scores; visible registration metadata gaps; CSV-only Brief
promises; named £150 four-week manual Digest price. Founder confirmed September
two-product manifest authority; strategy now records that supersession.

---

# CURRENT VERDICT — CareGist

> **2026-10-02 commit/deploy correction:** [COMMIT_DEPLOY_TRUTH.md](COMMIT_DEPLOY_TRUTH.md) is authoritative for release identity. The active checkout, local main, GitHub main, successful Production deployment and both public services match `1a62f84`. PR #75 is merged and Production Smoke 37004402261 PASSED. Local uncommitted work is preserved separately. Older release/smoke claims below are historical; no commercial gate approval is implied.

Commit/deployment consistency PASS: all current release surfaces match 1a62f84; both production smoke runs, Schema Drift and exact-merge CI passed. This is release identity/automated validation evidence, not independent commercial acceptance.


## 2026-10-01 Territory Brief follow-up — PARTIAL, no release approval

Evidence: `artifacts/product-research/2026-10-01/TERRITORY_VERDICT_CHECK.md`
and its saved SQL, served-release source excerpts and workflow results.

- All 34,332 rating-change ledger rows have NULL effective dates. The requested
  90-day query returns zero but cannot measure recent source-effective changes.
- The exact 115-location RI sample has 115 publication dates; none is within
  12 months. Latest stored publication: 2024-04-26.
- London homecare registration supply is 35 provider IDs in 90 days, only 21
  with URL/hash/date metadata; national social care is 302 / 147 respectively.
  Metadata completeness is not independent source acceptance.
- Served-release Brief code still consumes raw NDJSON and slices location
  candidates without provider deduplication; fulfilment emits PDF/CSV, not XLSX.
- Latest scheduled main Production Smoke and Freshness Watchdog runs passed
  on October 1. This supersedes old failing-job statements, not commercial gates.

Keep the Brief candidate; do not sell a recent-rating-change edition or describe
automated fulfilment as ready. All named gates remain closed.

## 2026-10-01 product research — read-only observations, no release approval

Research is saved in `artifacts/product-research/2026-10-01/PRODUCT_RECOMMENDATION.md`.
This is a producer's evidence report, not independent gate acceptance.

- Live public probes at 14:48–14:49 UTC report frontend/backend SHA
  `b2f519aa8aaebe33197076bd8f2fed6f60a56595`, fresh source and 57,139/57,139
  checked source locations, reconciled 2026-09-30T12:28:47Z with zero failures.
- `checkoutReady=false`; successful seven-day polls are 15 against 24 required;
  outbound delivery is disabled. No gate was changed.
- Read-only database aggregates agree with the 59,108 stored / 57,205 active
  location scale. The social-care subset is 30,591 active locations / 18,103
  distinct provider IDs; do not call all CQC locations care businesses.
- No paid application subscriptions, CRM deals, territory orders or recorded
  customer outcomes were found. Manual/bank sales and live Stripe balances are
  not independently verified; the direct Stripe CLI key is expired.
- The September two-product catalogue controls: £150 four-week Digest pilot and
  £745 one-off Territory Brief. Ongoing monitoring and a licensed feed are
  proposed research directions, not available subscriptions or approved releases.

Raw SQL/results, live responses, public-page captures and Jev's public-only
comparison are in the research directory. The historical archive qualification
below remains applicable to the older records; these new observations do not
retroactively independently verify them.

## 2026-10-01 archive review — current live status NOT VERIFIED

The September 23 closure below is a historical checkpoint. The saved September 24
nightly report corroborates its 13:18 reconciliation watermark. Saved reports through
October 1 record later reconciliations, but were not independently revalidated live
in this review. See `artifacts/cqc-nightly/ARCHIVE_NOTES.md` for reporting limitations.
Keep all named gates closed pending their separate evidence and independent review.

## 2026-09-23 14:16 BST production reconciliation closure

- Approved manual run `35821214442` completed successfully at 09:44 UTC. Its eight shards
  covered 57,127 / 57,127 source locations with zero collection failures and finalized batch
  `c21571b3-37ec-41e8-83f6-46145f2abb4e`.
- Delayed scheduled run `35833372207` then ran unchanged and completed successfully at
  13:18 UTC. It finalized batch `3c955cd7-dc03-4ef3-af79-3257c1f1b476`; all eight shards
  succeeded, coverage was 57,127 / 57,127 (100%), `countsReconciled: true`, and abort was
  correctly skipped.
- Live `/api/v1/health/freshness` is HTTP 200 `fresh`: source retrieved
  2026-09-23T09:45:30Z, reconciled 2026-09-23T13:18:04Z, checksum
  `bed9e95a1701ade0c4933bdf3acda7a9c4c94e3940a19ad698575a05a66eecb0`, zero failures.
- Live `/api/v1/health` is HTTP 200 `healthy`; the source watermark and count-reconciliation
  checks pass. Reconciliation is no longer blocking sale readiness.
- **Checkout remains closed:** `checkoutReady: false` because seven-day shadow coverage is
  17 successful polls against the required 24, and delivery is disabled. Legal, migration,
  deployment, and payment-journey gates remain separate and unresolved.

This section supersedes older reconciliation and freshness statements below.

## 2026-09-23 02:27–03:50 BST update — supersedes the operational facts below

- **Release identity:** frontend `/api/health/directory` and backend `/api/v1/version` both
  report `9ece88698b0a3a812d9a0a3af1a0fa17aaba091c`, exactly `origin/main`. Served identity is
  aligned. Scheduled smoke run `35799450671` still expected stale `a1357fee…`, so the smoke
  gate remains red because its repository variables lag deployment. Local fix makes the
  frontend prefer `VERCEL_GIT_COMMIT_SHA` over a pinned override.
- **Authoritative source:** the 2026-09-16 reconciliation completed 57,151 / 57,151 with zero
  failures. At the live probe the retrieved source was 162.8 h old against a 192 h SLA, but
  health remained `partial`/`freshness_ok: false` because newer authoritative attempts failed.
- **Latest failure:** GitHub run `35545070099`, shard 2, exhausted five HTTP 500 retries for
  CQC location `1-147345129` after committing 1,750 / 7,129. Seven other shards completed;
  finalization was skipped and abort closed the incomplete batch. The fail-closed gate worked.
- **Signal polls:** 17 completed of 17 started in seven days, below the unchanged readiness
  minimum of 24 and the 28 scheduled opportunities. Completed-run success is 100%; scheduling
  coverage is 60.7%. The old nightly report denominator of 336 was wrong.
- **Commercial readiness:** `checkoutReady: false`, `shadowCoveragePassed: false`, delivery
  disabled and healthy. Checkout stays closed.
- **Scale:** 59,040 location rows; 57,248 active locations; 37,141 distinct active provider
  organisations; 10,004 named group labels.
- **Verification of this change set:** Ruff green; 927 non-Postgres backend tests green;
  184 frontend tests green; TypeScript and production build green; targeted browser journey
  3/3 green. Real-Postgres tests are wired into CI but were not executable locally because no
  Postgres or Docker daemon was available.

**Status: implemented locally; database and independent verification pending.** This is not
release approval. Collection freshness/reliability and scheduled poll coverage remain below
existing gates. Scope requests are durable, fail-closed enquiries only; nothing is deployed
or enabled, and checkout remains closed.

---

**Established:** 2026-09-11 00:07–00:30 BST
**Method:** live production probes, GitHub API, repository inspection, local test execution
**Previous version:** 2026-08-20 (22 days stale — superseded)
**Target date under assessment:** 2026-09-11

---

## 1. Production release identity — MISMATCHED

| Surface | Reported SHA | Source |
|---|---|---|
| Backend | `91279238b8ef781711f35ba22314c5ec0fd7a9ee` | `GET /api/v1/version` → `release.git_sha` |
| Frontend | `1c98de7bcbf9f37f48ca93e3c57ceb23b147f04a` | `GET /api/health/directory` → `release.gitSha` |
| Smoke gate expects | `61513e986be337c8b292311d635f9105474a5ad1` | GitHub repo vars (set 2026-09-03T11:30Z) |

- Backend `9127923` **is** `origin/main` → backend is current.
- Frontend `1c98de7` is a **2026-09-03** merge (PR #39), 9 commits behind `main`.
- Expected `61513e9` **is not an ancestor of `origin/main` at all** — it is the tip of the
  local `codex/production-completion-20260903` worktree branch.

**Consequence:** the Production Smoke gate has been **structurally unable to pass since
2026-09-03**. It is not detecting drift; it is comparing production against a phantom SHA.
`releaseGitSha()` prefers `CAREGIST_RELEASE_SHA` over `VERCEL_GIT_COMMIT_SHA`
(`frontend/lib/release.ts`), so a stale injected env var also misreports the deployed frontend.

**Release identity is NOT verified for the 2026-09-11 target.**

---

## 2. "Running" — defined separately per layer

| Layer | Verdict | Primary evidence |
|---|---|---|
| **Public site** | `RUNNING` | `/` `/pricing` `/search` `/territory-opportunity-brief` `/data-status` `/why-caregist` `/examples/birmingham-solihull/index.html` all HTTP 200. Vercel, DB-backed. |
| **Data collection** | `PARTIAL` | Signal poll green every ~2–5 h (`cqc-signal-poll`, last success 2026-09-10T21:48Z; `latestObservedAt` 2026-09-10T21:54:08Z). **Authoritative reconciliation has never completed** — `reconciledAt: null`, `sourceRetrievedAt: null`, `countsReconciled: false`, reason `latest_authoritative_attempt_incomplete`. Last attempt **failed at 21,000 / 57,085 = 36.79 %**. |
| **Customer ordering** | `NOT RUNNING` | The only paid offer (£745 Territory Opportunity Brief) has a `mailto:` CTA — no online order capture anywhere on production. |
| **Payment** | `NOT RUNNING` | `/api/v1/health` → `commercialReadiness.checkoutReady: false`. No Stripe checkout route is deployed. |
| **Fulfilment** | `MANUAL ONLY` | No generator is deployed on `main`; `api/services/territory_brief*.py` exist **only** on the unmerged branch. Delivery is human work, quoted at "three working days". |
| **Operations** | `DEGRADED` | Freshness watchdog **crash-fails in 17 s** (`ModuleNotFoundError: No module named 'pydantic_settings'` — the workflow has no dependency-install step). Production smoke red (see §1). Watchdog alerting disabled (`WATCHDOG_NOTIFICATIONS_ENABLED=false`), so **failures are silent**. |

---

## 3. Data freshness — SLA BREACHED

- CQC source in production: `.../2026-09/02_september_2026_CQC_directory.csv`
- `sourcePublishedAt`: **2026-09-02** · `slaHours`: **192** (8 days)
- Measured age at assessment: **216.2 h = 9.01 days**
- **Overdue by 24.2 h (1.01 days).**

`freshness_ok: false`, `source_fresh: false`, `feed_fresh: true`.
The public product's core sourcing claim is stale, over SLA, and **unmonitored** because the
watchdog crashes before it can check anything.

Live scale (verified): 58,937 location rows · 57,188 active · 37,111 active provider
organisations · 10,006 named group labels.

---

## 4. Branch `feat/territory-self-serve-scope` — preserved, but NOT mergeable as-is

- Tip `9fcd697` (preservation commit). Base `fba66d7`. **39 behind / 12 ahead** of `origin/main`.
- **Production is not an ancestor of the branch.**
- 46 files are additive over `main`.

**Confirmed duplication.** The branch re-commits work already on `main` under different SHAs:

| File | Branch SHA256 | Main SHA256 | |
|---|---|---|---|
| `api/services/provider_intelligence.py` | `e609086332295d56…` | `e609086332295d56…` | **identical** |
| `db/migrations/058_crm_provider_intelligence.sql` | `e4388608418c48de…` | `e4388608418c48de…` | **identical** |

`a846b04` (branch) and `bb8419a` (main) are the same work. `53511dc` (branch) duplicates
`ee72dce` (main). **A wholesale merge would collide on `PricingCTA.tsx`,
`pricing-provider-cta.test.ts`, `caregist-config.ts`, `provider_intelligence.py` and
migration 058.**

**Genuinely new and additive** (the real value): `api/services/territory_brief.py`,
`territory_brief_delivery.py`, `territory_brief_fulfilment.py`, `territory_brief_render.py`,
`db/migrations/060_territory_brief_fulfilment.sql` (+down),
`frontend/lib/territory-scope.ts`, `frontend/app/pricing/territory/page.tsx`,
`frontend/components/TerritoryScopePicker.tsx`,
`frontend/app/api/territory/coverage/route.ts`, 5 test modules,
`tools/generate_territory_opportunity_brief.py`, solicitor terms draft, design doc.

**Migration numbering:** `main` max = **058**; branch adds **059** (`widen_provider_phone`)
and **060** (`territory_brief_fulfilment`). Not yet applied to production.

### Test evidence (reproduced locally this session, no external effects)
- Backend territory-brief suite: **60 passed in 1.72 s** (`test_territory_brief.py`,
  `test_territory_brief_fulfilment.py`, `test_territory_brief_integration.py`,
  `test_billing_territory_brief_checkout.py`).
- Frontend: `lib/territory-scope.test.ts` — **10 pass / 0 fail**.
- `tests/test_territory_brief_pg_integration.py` **not executed** (requires an isolated
  Postgres). Remains `NOT VERIFIED`.

Code quality is not the blocker. **Authority and data are.**

---

## 5. Fail-closed flags — correctly OFF

`api/config.py` defaults, all `False`: `billing_checkout_enabled`,
`territory_self_serve_checkout_enabled`, `radar_checkout_enabled`, `crm_enabled`,
`outbound_communications_enabled`, `outbound_delivery_enabled`,
`cqc_location_index_poll_enabled`, `directory_export_delivery_enabled`.

Production Vercel has `TERRITORY_BRIEF_CHECKOUT_ENABLED` and `STRIPE_PRICE_TERRITORY_BRIEF`
in the **Production** environment (created ~19 h before assessment). **No code on `main`
reads either variable** (`git grep` over `api/` and `frontend/` returns nothing). They are
inert today, but they are production config written for undeployed code — a governance
defect to reconcile, not a live exposure.

---

## 6. Offers realistically ready for 2026-09-11

| Offer | Ready? | Why |
|---|---|---|
| Free Directory / search | `READY` | Live, DB-backed, serving. |
| £745 Territory Opportunity Brief | `NOT READY (self-serve)`. **Manual sale only.** | No checkout, no deployed generator, and the underpinning CQC evidence is over its freshness SLA. Deliverable by hand only if a buyer appears and a human accepts the sourcing risk. |
| Radar Regional / National, Intelligence Feed, Full Dataset | `NOT READY` | Roadmap. Correctly gated out of checkout. |

**Honest headline: no offer is ready for autonomous purchase on 2026-09-11.** The only
paid offer can be sold solely through a manual, human-scoped conversation on stale evidence.

---

## Readiness gate

`NOT READY` — remaining gap: (a) authoritative CQC reconciliation never completed
(36.79 % last attempt, 24.2 h over SLA), (b) release identity unverified
(phantom expected SHA + frontend/backend skew), (c) freshness monitoring crash-failing and
silent, (d) instant-delivery code unmerged, legally blocked and undeployed.
