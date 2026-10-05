# CareGist customer readiness — 5 October 2026

**Verdict: public directory is live; paid customer fulfilment remains gated.** Existing work in progress was preserved. This review did not deploy, mutate live source data, change pricing/Stripe objects, enable checkout/delivery or send messages to customers.

## Current evidence

- Public directory health returned HTTP 200 and `status=ok`, serving SHA `a0d5b5df564a1d553cc7a9effcca91483a91ab0a`, matching the current checkout.
- Public pipeline health returned HTTP 200 with `checkoutReady=false`, `shadowCoveragePassed=false` and `deliveryEnabled=false`. Its seven-day window contains **15 successful/completed polls**, against the unchanged minimum of **24** and minimum success ratio **0.9**. Current ratio is 1.0; the count gate still fails.
- Latest inspected Production Smoke [37238228401](https://github.com/sapopo93/caregist/actions/runs/37238228401) passed. Latest inspected Freshness Watchdog [37195629684](https://github.com/sapopo93/caregist/actions/runs/37195629684) passed. The later CQC reconciliation [37188960287](https://github.com/sapopo93/caregist/actions/runs/37188960287) failed; this review did not dispatch a replacement collector or assume that an earlier successful source run proves ongoing reliability.
- Frontend: **184 tests passed**.
- Targeted pipeline, billing adversarial controls, Territory Brief checkout/generation/fulfilment and watchdog suites: **109 tests passed**. The suite uses mocked provider/financial integrations and is not proof of live payment or delivery.

The 3 October warroom records the preceding engineering fixes and explicitly keeps commercial gates closed. No historical completed issue was reopened merely to inflate the fix count.

## Remaining paid-customer gates

1. Accumulate the actual seven-day coverage required by the existing gate; investigate collection reliability using current source evidence. Do not manufacture history, lower thresholds or reinterpret incomplete coverage as passing.
2. Complete independent source/scope/journey acceptance and legal review of the actual Digest/Brief deliverables, terms and instant-supply consent where applicable. Missing historical source-effective dates cannot be reconstructed from ingestion dates without evidence and a reviewed migration.
3. Prove the approved payment-to-delivery path and financial reconciliation, with real provider credentials and separate authorised live commercial activation. Mock Stripe/storage/email tests do not establish these outcomes.
4. Verify response ownership and notification delivery, and separately approve checkout/delivery only after the named gates pass.

CareGist is a regulatory-data product rather than a database of one customer's care notes. Customer scopes and entitlements belong in its existing account/order configuration; do not hardcode Lilibeth or apply a blanket healthcare retention period to public CQC source data. See the current warroom for the explicit commercial decision process.

## Additional engineering remediation on 5 October

The following changes are prepared for independent review. They have not been
merged, deployed or used to activate paid services.

- Subscription synchronization now owns a transaction and locks the account,
  keeping the subscription row, API-key tier/rate/seat limits and organization
  entitlement consistent even when the caller has no surrounding transaction.
  A subscription identity cannot be reassigned to another customer. Concurrent
  replacement and cancellation are tested against real PostgreSQL.
- Cancellation or non-entitled reconciliation of an older subscription preserves
  the customer's active replacement plan. It no longer overwrites the new
  organization's entitlement or sends a misleading “returned to Free” notice.
- The subscription reconciliation tool uses the same atomic entitlement path,
  including workspace access and seat revocation. It retrieves each exact Stripe
  object before revocation, preserves an orphan whose absence is unconfirmed,
  validates complete bounded pagination and reports actual fixes. It does not
  grant paid access without the checkout/contract acceptance path.
- CQC detail responses must match the requested location identity. For locations
  in the immutable official directory, bounded 404 retries allow an API
  publication race to recover. Persistent absence still refuses the batch;
  no record is skipped and no reconciliation watermark is fabricated.
- The real PostgreSQL Territory Brief fulfilment journey is now discovered by the
  mandatory isolated database CI job. Previously it was outside that directory
  and skipped unless a separate `TB_PG_URL` was supplied. SQL, PDF/CSV rendering,
  consent persistence, download hashes, delivery outbox and replay behavior run
  for real; Stripe, object storage and sending remain synthetic integrations.
- The historical classification regression now uses frozen public-source
  fixtures, preserving its complete 127/61-entry assertions while nightly
  operational caches continue to refresh independently.

Validation: **1,225 backend unit/service tests passed**. The isolated PostgreSQL
suite covers migration replay, RLS/security invariants, account cancellation,
concurrency, reconciliation and the full Brief persistence journey. Whole-repo
Ruff, migration governance and evidence-language checks passed.

### Remaining source disagreement is verified, not inferred

Reconciliation [37188960287](https://github.com/sapopo93/caregist/actions/runs/37188960287)
failed on CQC location `1-29608453477`, with HTTP 404. A separate read-only probe
confirmed the local API credential works: control location `1-10000302982`
returned HTTP 200 with a matching identity. The disputed ID returned HTTP 404 on
all five bounded attempts; its public CQC page also returned 404. We cannot label
it deregistered, discard it from the immutable source manifest or substitute a
made-up detail record from that evidence. CQC's [official source page](https://www.cqc.org.uk/about-us/transparency/using-cqc-data)
currently describes delays and inconsistencies during its directory system
migration. That explains why disagreement is plausible, but does not resolve
this individual location's registration state.

At `2026-10-05T03:37:19Z`, production still serves `a0d5b5d…`, with **15 completed
polls / 24 required**, success ratio 1.0, latency passed, `checkoutReady=false`
and `deliveryEnabled=false`. The threshold and historical records are unchanged.
No live data, Stripe object, commercial configuration or outbound message was
modified by this remediation.
