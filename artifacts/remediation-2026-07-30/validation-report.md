# Validation report

Date: 30 July 2026
Scope: local worktree and disposable local PostgreSQL databases only.

## Passed

- Backend: `CAREGIST_TEST_DATABASE_URL=postgresql:///postgres pytest -q`
  — 375 passed, 2 skipped.
- Database integration: all 9 lifecycle, clean-migration and subscription-state
  tests passed using isolated `caregist_ittest_*` databases that were dropped afterward.
- Frontend: 71 tests passed.
- TypeScript: `npx tsc --noEmit` passed.
- Production build: Next.js 16.2.12 build passed; all 32 static pages generated.
- Production dependency audit: `npm audit --omit=dev` found 0 vulnerabilities.
- Python compilation: API, tools and pipeline entry points compiled successfully.
- Patch hygiene: `git diff --check` passed.
- Directory fallback: 53 MB CSV verification passed.
- Secret scan: 39 tracked findings manually classified as test-password,
  test-secret or lockfile-hash patterns; no tracked live credential pattern found.

## Known non-failures and residuals

- Two metrics tests skipped because optional `prometheus_client` is not installed
  in this local environment. Metrics no-op behaviour tests still passed.
- Next build reports a non-fatal NFT tracing warning for the intentionally packaged
  CSV fallback reader. The dataset is explicitly included in `next.config.ts` and
  its build-time verification passed; this remains a packaging optimisation item.
- The generic GDPR skill scanner was stopped because it recursively scanned the
  53 MB dataset and did not complete; it is not counted as validation evidence.
- The production CQC baseline remains stale. No production import was run.

## External-state statement

No outreach, publication/deployment, price change, checkout/payment, customer
export, monitor/digest/webhook delivery or provider-claim activation occurred.
Earlier in this remediation sequence, migrations 038 and 039 were applied to the
empty Stripe-managed staging database; an attempted full staging import was
interrupted before provider writes and the run was recorded failed. Migrations
040–042 and all current application changes remain unapplied externally.
