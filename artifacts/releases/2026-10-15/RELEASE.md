# CareGist release and manual revision

15 October 2026. Requested scope: commit, push and deploy current project work, and update training, user and sales GTM manuals. Application baseline: `2332889fd4c77b7eed17f839b6d33b949eb3eec2` (current origin/main when work began). This release adds documentation and preserved dated evidence; no application feature flag, schema, data backfill or live customer operation is changed.

## Current manuals

The [manual index](../../../docs/manuals/README.md) leads to the user, training, sales GTM, CRM and operations manuals and their printable edition. Older manual/strategy entry points link the maintained suite. Dated 11 October workbook, plan and their review receipts remain historical; their hashes and prior review claims are not silently restamped.

The updated instructions preserve the £150 one-off four-week Digest and £745 one-off Brief, current published VAT wording, distinct-provider counting, later scope/source delivery clock, G0 to G5 before paid commitment, independent final-file review and G6 before release, and confirmed access distinct from acceptance. Digest sales remain held pending product-specific operative terms and fulfilment approval. Exact CRM navigation and suppression recovery reflect the implementation; no authenticated production CRM activity was tested.

## Validation

- Targeted backend tests: **88 passed** (`test_territory_brief`, `test_backfill_rating_change_dates`, `test_verify_deploy`).
- Frontend unit tests: **183 passed**, zero failures or skips.
- Frontend production build: **passed** using local dummy build credentials.
- Evidence language guard on the maintained manuals: **passed**.
- Independent documentation review caught and prompted correction of Digest-hold wording, CRM opt-out/navigation, obsolete entry points and printable ordered-list continuation. Final artifact review and exact-commit CI/deployment receipts are recorded after completion.

Logs from these local checks are preserved in `.tmp/manuals-qa/`. A concurrent draft recorded broader local test counts; those are not substituted for the checks above. Live Postgres, paid checkout, campaign sending, inbox receipt and customer acceptance are separate checks, not implied passes.

## Live boundary before release

[Read-only public evidence](pre-release-public.json), captured at 10:02 UTC, records both services at the baseline SHA. Pricing, Brief, search and data-status paths returned 200. Directory used the database. Backend health was degraded, source freshness false, checkoutReady false and delivery disabled. Anonymous export returned 401 without a token. Anonymous CRM redirected to login. Calling configuration reported enabled; recording, AI and TPS automation were disabled. These observations do not approve any protected capability.

Origin/main CI [38345801225](https://github.com/sapopo93/caregist/actions/runs/38345801225) passed for the baseline; Production Smoke [38686122920](https://github.com/sapopo93/caregist/actions/runs/38686122920) passed. Freshness Watchdog [38710271306](https://github.com/sapopo93/caregist/actions/runs/38710271306) failed with degraded source checks. Releasing documentation does not repair or hide that source issue. Latest saved nightly cadence analysis covers the primary workflow and does not certify aggregate primary/backup coverage.

## Preservation and publication scope

Initial dirty tracked work and nonignored untracked files were archived locally under `.tmp/pre-release-20261015-110023/` before Git operations. Concurrent draft documentation was additionally preserved under `.tmp/manuals-qa/concurrent-docs/` before adding current-manual pointers.

CLI-managed `.projects` changes and nightly local runtime state remain outside publication. Private real-product/prospect research packs, raw buyer-oriented collateral, personal eBay screenshots and render intermediates stay local. Relevant safe dated plans, training sources, reviews, figures and nightly diagnostics are preserved in Git. Deployment must use committed source rather than upload the dirty workspace.

## Release receipt

Pending exact-commit GitHub checks and deployment verification. No commercial readiness or prescribed Grok/DeepSeek operating approval is claimed by this documentation review.
