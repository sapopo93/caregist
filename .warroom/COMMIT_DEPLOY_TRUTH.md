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
