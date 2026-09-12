# CURRENT VERDICT — CareGist

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
| **Customer ordering** | `NOT RUNNING` | The only paid offer (£795 Territory Opportunity Brief) has a `mailto:` CTA — no online order capture anywhere on production. |
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
| £795 Territory Opportunity Brief | `NOT READY (self-serve)`. **Manual sale only.** | No checkout, no deployed generator, and the underpinning CQC evidence is over its freshness SLA. Deliverable by hand only if a buyer appears and a human accepts the sourcing risk. |
| Radar Regional / National, Intelligence Feed, Full Dataset | `NOT READY` | Roadmap. Correctly gated out of checkout. |

**Honest headline: no offer is ready for autonomous purchase on 2026-09-11.** The only
paid offer can be sold solely through a manual, human-scoped conversation on stale evidence.

---

## Readiness gate

`NOT READY` — remaining gap: (a) authoritative CQC reconciliation never completed
(36.79 % last attempt, 24.2 h over SLA), (b) release identity unverified
(phantom expected SHA + frontend/backend skew), (c) freshness monitoring crash-failing and
silent, (d) instant-delivery code unmerged, legally blocked and undeployed.
