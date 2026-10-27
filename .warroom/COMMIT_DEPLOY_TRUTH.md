## 2026-10-27 02:46 UTC — CQC register reconciliation finalized

Batch `65b9501d-743c-41c7-9fe8-37a68451f71d` (run 40417162953, main `9e44060`) finalized from CQC's 22 Oct 2026 directory (57,107 locations, 100% coverage, 0 fetch failures): active 57,165, 33 confirmed-deregistered locations deactivated, 44 confirmed still registered kept active, 12 that CQC's API returns HTTP 404 for (1-29359742625…799, 1-29363204826…930) kept ACTIVE under the workflow's operator acknowledgement. Freshness watchdog (run 40440532731): reconciled 3.7 h ago against a 192 h SLA; status `partial` solely because 15 locations are quarantined (the 3 from 18 Oct plus these 12). Clearing it needs CQC to restore those records or an operator decision to deregister them; no code change.

How it got here: run 40267054399 (04:03 UTC 26 Oct) lost shards 1, 4 and 5 to deadlocks with a CQC ratings import apply this session ran concurrently (fixed: #136 ordered locking and retry, #138 the import now shares the reconciliation concurrency group). Run 40380378132 completed all shards but correctly refused to finalize 12 unconfirmed candidates; its single resume wave (run 40415436179) then lost the finalize lock to an hourly signal poll (fixed: #140 bounded finalize lock retries). Also merged: #139 report-index health from #90.

---

## 2026-10-26 — rating rule, Terms v2.3 and trading release

Merged under founder authorization (26 Oct, "push and we ship"), each with every PR check passing:
[#125](https://github.com/sapopo93/caregist/pull/125) report readiness (resolver, competitor scan and P12 flags all off; independent review passed with features disabled) `1b10f91`;
[#123](https://github.com/sapopo93/caregist/pull/123) file-sourced ratings in Brief and pages, data-driven labels, edition-dated staleness, integrated with #125 using the reviewed #127 resolution `833ec13`;
[#130](https://github.com/sapopo93/caregist/pull/130) Business Terms v2.3 and Privacy Notice v2.1, in force 26 Oct 2026 (AI legal review with three corrections; no solicitor review yet) `5990e63`;
[#131](https://github.com/sapopo93/caregist/pull/131) CQC ratings import workflow `0354e85`;
[#132](https://github.com/sapopo93/caregist/pull/132) coverage check excludes quarantined locations `1534c7f`;
[#133](https://github.com/sapopo93/caregist/pull/133) operator pilot layer `d9f4906`;
[#134](https://github.com/sapopo93/caregist/pull/134) rating rule: ratings file first, newer CQC page check wins, API fills gaps, source and disagreement on every row `1cb7b40`;
[#135](https://github.com/sapopo93/caregist/pull/135) set-based ratings apply `ebad475`; [#136](https://github.com/sapopo93/caregist/pull/136) ordered locking and deadlock retry `9ba69e8`.
Production Smoke PASS on `1b10f91`, `833ec13`, `5990e63` and `1cb7b40`; Vercel runtime errors: none in the hour after the rule release.

Production data: migration 069 applied 25 Oct (Freshness Watchdog run 40205848533); migration 070 applied 26 Oct after Neon recovery branch `recovery/pre-migration-070-20261026`; schema check PASS. Ratings file `01_October_2026_Latest_ratings.ods` (sha256 aba66fd8…c59cd, edition 2026-10-01) re-imported with its edition date by Import CQC ratings run 40277186502 (32,161 rows; staleness check OK, 25 days old). Two earlier applies committed nothing: run 40272405511 hit the 30-minute limit (row-by-row) and run 40276188706 deadlocked with the CQC reconciliation; #135 and #136 fix both.

Commercial model unchanged: human-led (written scope, Stripe Payment Link, manual fulfilment). Self-serve checkout and delivery gates remain closed.

Open: #129 (Territory Preview recovery, migration 066, draft by its author's terms) and #90 (report-index health, also migration 066) need rebasing on the rating rule and a production migration. 35 stale PRs closed; remote branch deletion awaits the founder (session not permitted to delete branches). Source reconciliation remains `partial` (3 quarantined locations; watermark 2026-10-18).

---

## 2026-10-24 22:08 UTC — read-only observation

Production backend `/api/v1/version` and frontend `/api/health/directory` both serve `bd23b392d4483beac579cd26b7dbd523872de075`, which equals GitHub `origin/main` (PR #124). This supersedes the c5b92a6 entry below as the current release identity. Observation only: nothing was deployed. Report-readiness work is on the unmerged branch `feat/report-readiness-20261024` and is not deployed.

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
