## 2026-10-27 — production migrations 066 and 071 applied (schema only, no code release)

Applied to production Neon (London) by Codex under Henry's authorisation, after staging. Exact SQL taken from PR #90 head `8b759acd5aa9df2084444f3cb6aae598ca620e0a`: `066_territory_brief_source_editions.sql` (sha256 `7b5ff3427c85477ebbc7b99055f27ee300feb87d6923bf733e6fd75b6de59a22`) and `071_territory_brief_buyer_scope.sql` (sha256 `63adfdc3017347c60fb8f7922a778340cbfbf24691c627bea2dd9353f5496dfc`). Each file ran in its own transaction with a ledger entry. Evidence: `artifacts/recovery/2026-10-27/` (`README.md`, `before.json`, `after.json`, `staging.json`, `recovery-validation.json`, `health-after.json`).

Recovery: one retained Neon branch `recovery/pre-066-071-20261027` (`br-quiet-shape-absfw674`, parent `br-nameless-glitter-abix2cgn`, created 06:43 UTC, expiry Never). This is a snapshot check, not a restore drill.

Counts before and after: 57,165 ACTIVE and 2,252 INACTIVE, unchanged. Health after: `status=degraded`, `freshness_ok=false`, 15 quarantined locations, `checkoutReady=false`, `deliveryEnabled=false`. The degraded state predates this change (see 25 Oct below).

Not established by this entry: the six protection triggers listed in the README were not re-queried here, and the Neon branch was not independently re-read. The "Go" message in the CQC website changes review thread was reported by Codex with a screenshot; it was not re-checked.

No application code was released. The Postgres-backed Territory Brief source-edition code that reads these tables remains local on `feature/territory-preview` and is not deployed. Releasing it needs its own gate. Stripe Projects still points at an older US database (read-only check only); this is unresolved.

---

## 2026-10-25 22:15 GMT — release identity and checkout reconciliation

Authoritative release: `18536de02235297ba14bd29593760e49d91196b6` (PR #126) on GitHub main. Production backend `/api/v1/version`, frontend `/api/health/directory` and the latest GitHub Production deployment (7310298710, 25 Oct 07:52 UTC) all match. Supersedes `c5b92a6` below.

Main runs at this SHA: [Production Smoke 40174454256](https://github.com/sapopo93/caregist/actions/runs/40174454256) PASS, [Schema Drift 40174395498](https://github.com/sapopo93/caregist/actions/runs/40174395498) PASS, CQC signal poll PASS. Two ops runs failed on 25 Oct and were not investigated: [CQC reconciliation 40188054162](https://github.com/sapopo93/caregist/actions/runs/40188054162) and [Freshness Watchdog 40179175868](https://github.com/sapopo93/caregist/actions/runs/40179175868). Live `/api/v1/health`: status=degraded, freshness_ok=false, source.freshnessStatus=partial, checkoutReady=false, deliveryEnabled=false.

Primary checkout `/Users/user/CareGist`: branch `feature/territory-preview`, fast-forwarded from stale `7ad6471` to `origin/feature/territory-preview` at `8732a84`. That branch is 15 commits ahead of and 6 behind main. Its 15 commits include merge commits; the unmerged content is the quarantine-evidence carry-through and the territory-preview SQL/wording follow-ups after PR #96. No PR is open for it. It is not deployed.

Uncommitted local work was reapplied on `8732a84`. Five conflicted files took upstream because upstream had already superseded them on 20 Oct: CRM AI local-model gate (#115), Terms 2.2.1, `.env.example`. The four warroom state files kept both dated entries. What remains local and not deployed: the Postgres-backed Territory Brief source editions (`territory_brief_source.py`, migration 066, billing/fulfilment/delivery/brief changes, plus a fix threading `allowed_ids`/`provider_group` through the extracted generator), the homepage Inadequate-in-CQC-file note, AGENTS.md and REVENUE_COMMAND_PLAN DeepSeek removal wording, nightly CQC artifacts, and untracked research/marketing/legal drafts. Local pytest 1,547 PASS / 143 SKIP; frontend `tsc --noEmit` PASS.

Preservation: `/private/tmp/caregist-reconcile-20261025` (HEAD.txt, status.txt, tracked.patch, untracked.tar.gz, temporary), branch `backup/territory-preview-local-20261025` at `7ad6471`, and stash "reconcile 2026-10-25: local work on 7ad6471…". No push, merge, deploy, production data change or gate change occurred. This is identity reconciliation, not product acceptance.

---

## 2026-10-20 06:50 BST — human-led launch release

Authoritative release: `c5b92a6793f9f3ad0e1e5e41101caf93e93d4bb0` on GitHub main; production backend `/api/v1/version` and frontend `/api/health/directory` both serve it. Supersedes `b2e3fe6` below.
Merged under founder authorization after every PR check passed:
[#104](https://github.com/sapopo93/caregist/pull/104) (paid-path real-Postgres test now runs in CI, confirmed `1 passed`; manual Freshness Watchdog dispatch skips the migration job unless a restore point is asserted),
[#105](https://github.com/sapopo93/caregist/pull/105) (Business Terms v2.2 published, founder-approved, in force 20 Oct 2026),
[#106](https://github.com/sapopo93/caregist/pull/106) (Payment Link sales recorded as `manual_sale_paid` instead of erroring; `tools/build_weekly_digest_pilot.py`; `workflows/fulfil-manual-orders.md`).
Exact-main CI, Schema Drift and Production Smoke PASS on `c5b92a6`; live health `healthy`, no failing checks.

Commercial model: human-led. Scope agreed in writing, Stripe Payment Link sent by hand, fulfilled by hand. Self-serve checkout and delivery gates remain closed (checkoutReady=false, deliveryEnabled=false).

Live Stripe changes made by the agent with founder approval: product `prod_VCHYLNWRcvZgJd` renamed to "CareGist Weekly Digest pilot — 4 weekly digests"; product `prod_VESD16ql3keycy` (£745) description corrected to email delivery within about 3 working days after written scope confirmation (it previously claimed automatic delivery and carried stray text). No prices, links or webhooks were created or changed.

Stripe follow-up (20 Oct, founder-approved, done by the agent): the £150 checkout page was checked live and shows "CareGist Weekly Digest pilot — 4 weekly digests" (the "Radar pilot pack" text exists only in the link's stored API line description; no new link needed); £895 combined link `plink_1UIpr94mijLHzRRkDEWL3zYD` deactivated; CareGist webhook `we_1TLKZI4mijLHzRRkzoD75vqv` re-enabled (endpoint answers 400 "Invalid webhook signature" to unsigned requests, so a secret is configured; the first real event proves it matches); `tenderriskassurance.co.uk` webhook `we_1TPJWF4mijLHzRRkwlkiXym0` disabled. Later releases: #108 local Gemma CRM scoring (`6191091`), #109 do-not-contact flagging (`479a0bd`), both with CI, Schema Drift and Production Smoke PASS.
Data finding (corrected 08:50 BST): production rating data is not stale. A full CQC API pull (2026-10-20, 123,010 locations, 0 failures) shows CQC itself published only 3 rating reports nationally since 1 Sep 2026, so `rating_changes` and `last_published_rating_date` faithfully mirror upstream. Weekly Digest ratings sections will be near-empty until CQC resumes publishing.

---

## 2026-10-20 06:10 BST — DeepSeek removal and health fixes released

Authoritative release: `b2e3fe6266642915b8520098dece8898d5d62911` (supersedes `37ad274` from earlier the same morning) on GitHub main. Production backend `/api/v1/version` and frontend `/api/health/directory` both serve it.
Merged under founder authorization in this session: [#100](https://github.com/sapopo93/caregist/pull/100) (DeepSeek removed from CRM AI; AI refuses to enable until an approved provider is wired in), [#101](https://github.com/sapopo93/caregist/pull/101) (11 nightly backup poll slots), [#102](https://github.com/sapopo93/caregist/pull/102) (a cancelled duplicate reconciliation of an already reconciled snapshot no longer degrades health).
Exact-main CI, Schema Drift and Production Smoke also PASSED on `37ad274`. Every PR check passed before its merge.
Live `/api/v1/health` after release: source `fresh`, checkoutReady=false, deliveryEnabled=false, crm ai_enabled=false.
Local evidence: full pytest 1,336 PASS / 1 SKIP; `tests/test_territory_brief_pg_integration.py` PASS against a disposable PostgreSQL 17 + PostGIS 3.6 with init.sql and all 64 migrations from `37ad274` (#103 adds no migration) (CI still skips it: no TB_PG_URL).
Then merged [#103](https://github.com/sapopo93/caregist/pull/103) (a poll in progress within its 50-minute limit no longer degrades health). Exact-main CI, Schema Drift and Production Smoke PASS on `b2e3fe6`; live health `healthy`, no failing checks, feed_fresh=true.
No commercial gate, live Stripe object, production data or migration was changed. Local uncommitted Territory Brief source-edition work (migration 066) is not deployed.

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

This release identity supersedes the historical 1a62f84 identity below. Local uncommitted research and status work is not deployed.

---

# CareGist commit and deployment truth

## 2026-10-02 correction — commit identity aligned

Verified approximately 13:06 BST. Authoritative release commit: `1a62f847970324489c92d84a551f44cf1bc83e59`.

| Surface | Commit | Evidence |
|---|---|---|
| Active /Users/user/CareGist checkout | `1a62f84` | branch codex/production-aligned-20261002, tracks origin/main; ahead 0 / behind 0 |
| Local main reference and main worktree | `1a62f84` | clean main worktree fast-forwarded |
| GitHub main | `1a62f84` | PR #75 merged with matching-head guard |
| Production frontend | `1a62f84` | /api/health/directory; databaseAvailable=true |
| Production backend | `1a62f84` | /api/v1/version |
| GitHub successful Production deployment | `1a62f84` | deployment 6807930249; https://caregist-jfw4xzmiw-henry-mlalazis-projects.vercel.app |

[Production Smoke 37004402261](https://github.com/sapopo93/caregist/actions/runs/37004402261) **PASS** on this commit. Schema Drift **PASS**. [Exact-merge CI 37004321000](https://github.com/sapopo93/caregist/actions/runs/37004321000) **PASS**: frontend, backend, real-Postgres migration replay, containers and secret scan. [Production Smoke 37004586285](https://github.com/sapopo93/caregist/actions/runs/37004586285) also **PASS**, dispatched without an expected_sha override, proving the deployment-history resolver. Both legacy CAREGIST_PRODUCTION_*_SHA repository variables now match `1a62f847970324489c92d84a551f44cf1bc83e59`; main smoke continues to use deployment history rather than those variables.

Preservation: old 272d848 branch retained as backup/primary-cta-before-alignment-20261002. Tracked local changes remain recoverable in stash@{0}, named “preserve tracked work before commit-deploy alignment 2026-10-02”. Local work was restored, generated private packs remain in place and /output/pdf/ is now ignored. The existing privacy exclusions from the remote branch were retained. Uncommitted research/status/CLI state is local and is not part of the production commit. The older release worktree at b2f519a is a historical branch copy, not the current production checkout.

No product code was authored in this reconciliation. The existing PR was merged; its main deployment ran automatically and reported success. No commercial gate was opened, and no claim of independent product acceptance is made. PR #71 is still open and outside this bounded correction.

This correction supersedes all historical commit/deploy statements below and in linked warroom records.

## Historical audit before correction

Verified 2026-10-02 at approximately 13:00 BST. Scope: commit identity and deployment evidence only. This is not independent release or commercial approval.

| Surface | Verified commit | Meaning |
|---|---|---|
| Main checkout /Users/user/CareGist | `272d8480e14ca0fc8481346f0aa6c766a69d11df` | Local branch feat/primary-cta-check-your-territory, with pre-existing uncommitted work |
| GitHub main and local main reference | `da78b85bf3420dc007f1aa7dcdf853968e7ba0dd` | Main is unchanged since September 25 |
| GitHub branch / open PR #75 | `b2f519aa8aaebe33197076bd8f2fed6f60a56595` | 15 commits ahead of main, zero behind; GitHub reports MERGEABLE |
| Reviewed release worktree /private/tmp/caregist-reviewed-release-2026-10-01 | `b2f519aa8aaebe33197076bd8f2fed6f60a56595` | Existing local copy of the served commit |
| Public frontend release endpoint | `b2f519aa8aaebe33197076bd8f2fed6f60a56595` | GET https://www.caregist.co.uk/api/health/directory; HTTP success, database available |
| Public backend release endpoint | `b2f519aa8aaebe33197076bd8f2fed6f60a56595` | GET https://www.caregist.co.uk/api/v1/version |
| Latest successful GitHub Production deployment record | `da78b85bf3420dc007f1aa7dcdf853968e7ba0dd` | Deployment 6657157456, September 25; does not describe the currently served release |

## Corrections to Claude's current screen

The main checkout is **30 ahead / 55 behind main**, not 55 ahead / 30 behind.
Compared with its same-named remote branch, it is **30 ahead / 70 behind**.
Raw commit counts do not imply 30 unique missing changes: range-diff shows rewritten counterparts, including `941002d` = `a0f1824`, and changed counterparts such as `272d848` / `419856d`.
Do not blindly merge or force-push the stale checkout. Preserve its uncommitted changes and reconcile actual content first.
PR #75 already exists and is mergeable on GitHub; the local checkout's divergence does not describe the PR's mergeability.

## Smoke and deployment status

PR #75 CI and Preview Smoke passed at `b2f519a`; its Production Smoke was skipped. This is not proof of a passing production journey.
Latest scheduled Production Smoke [36972879256](https://github.com/sapopo93/caregist/actions/runs/36972879256) failed on October 2: expected frontend `da78b85...`, observed `b2f519a...`. It stopped at release identity, so later journey checks are not established by that run.
Main's workflow auto-resolves the expected SHA from successful GitHub Production deployment records. The latest record is `da78b85...`; it is not using the two old repository SHA variables. Those variables still contain `a1357fe...`, but changing them alone will not repair this main workflow.
GitHub labels deployment 6784172012 for `b2f519a` as Preview. Public endpoint identity corroborates that `b2f519a` is served on the production domain. The exact promotion mechanism and its authorization were not established here.
PR #71 remains OPEN at `c912a0d0ff9c137c6cb0a7833d2da0cad2cdf9fc` and is mergeable; it is not merged merely because its work was rebased or tested.

## Required bounded follow-up

1. Independently review the served `b2f519a` release and its relationship to open PR #75. Resolve whether this is the approved production commit.
2. Reconcile production deployment provenance with the approved commit; then verify the existing smoke resolver selects that commit and require a full production smoke pass. Do not suppress the mismatch by accepting whatever the public endpoint returns.
3. Reconcile the stale main checkout against the reviewed branch in isolation, retaining private/uncommitted artifacts and examining rewritten commit counterparts. Do not reset, force-push or cherry-pick all 30 commits indiscriminately.

## Evidence and preservation

Evidence collected with: `git fetch origin`; `git rev-list --left-right --count origin/main...HEAD` (55 30); same comparison against the remote feature branch (70 30); main versus remote feature branch (0 15); `git range-diff`; `git worktree list`; GitHub commit/PR/deployment APIs; main Production Smoke workflow; failed smoke logs; both public version endpoints.
Pre-existing tracked changes and all non-ignored untracked files were preserved before fetch at `/private/tmp/caregist-truth-20261002T115806Z` (tracked.patch, untracked.tar.gz, status.txt). This is a temporary local backup, not durable remote storage.
Stripe Projects status lists Neon databases only; no deployment provider is linked there. No service provisioned or deployment attempted.
Historical commit/deploy statements in other warroom files are superseded by this file for this scope. Other product, data, legal and commercial evidence retains its own timestamp and acceptance requirements.
No merge, push, reset, production deployment, live configuration change or gate approval occurred during this audit.
