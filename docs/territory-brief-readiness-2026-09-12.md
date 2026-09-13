# Territory Opportunity Brief: release decision

**NOT READY.** Inspected 12 September 2026, branch `feat/territory-self-serve-scope`, starting HEAD `1f86c9818aa1bf2d82fcc938fc05fc0be0571cee`. Changes are local and uncommitted. No deployment, live Stripe mutation, payment or customer email was performed.

A live £745 base-price Payment Link exists. A customer buying through it is **not proven to receive the promised pack**. The existing public offer still advertises £795 and ends in a manual scope enquiry. This is more than an approval-hash problem.

Evidence is in the task output `territory-readiness-evidence/` folder. Stripe reads were captured at 09:01 and 09:29 UTC. Public health and pricing were checked directly during this run. Older Chief of Staff statements were treated as starting points, not current proof.

## Fixes completed

1. **Retry deadlock removed.** The fulfilment handler previously awaited a second connection updating an order still locked by its own webhook transaction. It now carries the generation failure to the webhook boundary, rolls back and releases the connection, then records the failure and increments the retry counter. A regression test checks the exact ordering. Failure recording also preserves a concurrently refunded order.
2. **Pre-payment Price validation added.** Checkout now verifies the configured Stripe Price is active, GBP 74500, one-time, in the correct mode, attached to an active Product, and has the required `territory_opportunity_brief_gbp_oneoff_v2` lookup key. It rejects a wrong or unverified Price before creating an order or Checkout Session. Both billing and Territory checkout flags must be enabled. Missing generation source returns 503 before payment.
3. **Fulfilment validation strengthened.** A paid GBP 74500 total is required. Free/no-payment-required, wrong amounts and currency are rejected. Price metadata, geography, window and shortlist size must match the reserved order.
4. **Territory PDF/CSV downloads implemented.** The export route now reads Territory Brief entitlements only when its own flag is enabled. It hashes the bearer token, atomically consumes one use, requires a fulfilled order, checks expiry and download limits, and uses the existing private Blob signing path. The retired dataset and segmented-export gates remain separate.
5. **Checkout return page added.** The configured success URL now resolves. It explains the email delivery step and explicitly does not infer payment or delivery from a session ID in the URL.
6. **Manifest evidence corrected.** Recorded the Payment Link ID, actual configuration, missing lookup key, third duplicate Product/Price, separate Product/Price active states, and old Payment Link states. Removed the inaccurate `live_and_saleable` status. No approved catalogue hash or approval constant was changed.
7. **Browser test drift corrected.** Updated the old £795 mock and old heading to the current £745 page. Kept the no-payment, error-recovery, stale-response and mobile-layout assertions, and added a return-page payment-proof test.

## Founder approvals/actions still required

- Authorize and perform the live Stripe corrections: assign the required v2 lookup key to the £745 Price and deactivate superseded £795 Prices. The two old live Payment Links are already inactive. The £795 test Product, Price and Payment Link remain active. Create the matching £745 test objects and record their actual IDs.
- Keep the current £745 Payment Link out of automated sales. It contains no scope fields or order metadata, requires no terms acceptance, and does not route to this branch's fulfilment handler. A manual sale still needs its separate scope, terms and delivery process. Decide whether to deactivate this link while the automated route is completed.
- Resolve the actual payable total and billing terms. The live Payment Link enables automatic tax and disables invoice creation. £745 is verified as the base Price, not as the completed buyer total. Do not describe a Stripe receipt as an invoice.
- Obtain approval of the actual published Territory Brief terms and immediate-supply wording. The current branch's terms page identifies itself as version 2.0; previous notes about version 2.1 are not proof of the current implementation. Do not populate consent/terms hashes from placeholder text to open the gate.
- Approve a final catalogue contract **after** Stripe IDs and evidence are complete. The verifier pins August 2026, four product keys, four Product IDs and three Price IDs. The candidate manifest is September 2026 with six catalogue entries and nine live identifiers. Re-pinning only the digest would not fix the version/key/count mismatches. Changes to these approval assumptions need explicit approval of the final contract, with strict missing-ID and uniqueness checks retained.
- Resolve migration 059 approval through the existing governance process. Its `ALTER COLUMN TYPE` is rejected unless destructive-migration approval is explicitly provided. No approval override was set here.
- Authorize the production source reconciliation, required migration/config deployment and matched frontend/backend release after staging evidence passes. The repository's `.warroom/README.md` reserves production deployment, live Stripe changes and live data mutation for founder approval.
- Supply or identify an isolated staging deployment, test database, private Blob store and approved test inbox. No suitable staging environment was identified in this run. Do not use the test webhook's current production URL as proof of isolation.

Current candidate manifest digest, **evidence only, not approved**:
`03fe805c4c63cd25873485265968b691a1264f46f28ca0c90c4cbc2f2bdb02ab`

Unchanged approved digest:
`66860dbd7143625e69b6c37650b6824805c4d7a27f81f293c2e3099b38ea2df6`

## External Stripe evidence still required

Verified directly:

| Object | Current evidence |
|---|---|
| £745 Product | `prod_VESD16ql3keycy`, active |
| £745 live Price | `price_1UDzJP4mijLHzRRkfYJG3OZZ`, active, GBP 74500, one-time, lookup key **null** |
| £745 Payment Link | `plink_1UEkzy4mijLHzRRkWjk3pFVW`, active, quantity 1, correct £745 Price |
| Old live £795 Price | `price_1UDf2t4mijLHzRRkRqbNA1rd`, active; parent Product archived; Payment Link inactive |
| Third duplicate live £795 Price | `price_1UDZAQ4mijLHzRRkvwXjtaQK`, active; parent `prod_VE1CdaKNxE0yVP` archived; Payment Link inactive |
| Old test £795 Price | `price_1UDft34mijLHzRRklUMJR6F2`, active; Product and Payment Link active |
| Webhook endpoints | Live and test endpoints exist with completed, async-success, expiry and refund events. Both point to the production CareGist URL. Endpoint existence is not successful event processing. |

Still required:

- Fresh API evidence after corrections: matching live/test £745 IDs, v2 lookup key, amount, currency, mode, Product and Price active states, and all superseded Price/link states.
- Verify no already-open old Checkout Sessions or other customer-facing paths still sell the superseded offer. Complete Payment Link inventory found five live and two test links, with no pagination or line-item errors, but open Checkout Sessions were not inventoried.
- A completed real Stripe **test-mode** purchase through an isolated deployment, using the same scope reservation and Checkout Session route intended for production. Capture session/event IDs, exact total, mode, invoice/receipt result, legal acceptance, order correlation and successful signed-webhook processing.
- Actual private Blob uploads, email receipt in the approved test inbox, working PDF/CSV downloads, and refund/replay/failure recovery evidence. None of these external steps was substituted with a mock transaction and called complete.

## Exact release acceptance criteria

All items must pass. Several still require engineering, not merely founder signatures.

1. **One scope from selection through delivery.** The UI currently selects region, buyer type and service type; the backend order captures geography, time window and shortlist target only. Implement one persisted scope contract and use it in coverage, consent, payment, generation and exports. Unknown or changed scope must fail before payment. No static Payment Link may bypass reservation.
2. **Source readiness proven before charge.** Replace the absent `_locations_detail.ndjson` runtime dependency with a supported production source preserving provenance and event history. Validate source freshness, reconciliation, qualifying records and promised shortlist size before taking money. Do not substitute arbitrary current database rows for the generator's historical evidence. Generation must fit measured hosting time/memory limits, or use a durable worker with retry and recovery.
3. **The promised pack is generated.** The local page promises an editable territory CSV and Excel workbook, 25–50 organisations and a three-to-five-page executive brief. Current automated fulfilment uploads only PDF plus shortlist CSV. The fixture run produced 30 location rows representing 29 providers, in an 11-page PDF with appendix, from source edition 18 February 2026. Produce and verify the agreed dataset/workbook and organisation-level shortlist with source links, reasons, qualification questions and uncertainties. Do not silently shrink the advertised product to fit existing output. Ensure the executive section meets the page promise separately from the appendix.
4. **Approved commercial contract.** Publish the approved terms and actual consent wording, set their approved hashes, verify Stripe terms collection, and reconcile the final payable total, VAT wording, receipt/invoice and delivery promise. The live £745 Payment Link currently has no terms collection.
5. **One release and one price.** Local catalogue, checkout, Stripe and public pages agree on £745 and the approved tax treatment. Deploy the same reviewed commit to frontend and backend. Current public frontend reports `1c98de7…`, backend `9127923…`, and this branch started at `1f86c98…`. Public pricing and offer pages were directly verified at £795.
6. **Schema and service wiring proven.** Apply and record the approved migrations to the intended staging and production databases. The database resolved from the repository configuration has all three Territory tables but no 059/060 migration-ledger rows; this does not prove a governed production rollout. Verify private Blob access and email worker credentials in the actual deployed runtime. Table presence is not delivery evidence.
7. **Real buyer journey passes.** Selection → source/scope confirmation → approved consent → exact £745 payment → signed webhook → one order/one generated pack → queued and received email → opened, correct PDF/CSV/workbook. Cover duplicate/concurrent webhook, generation/upload failure and retry, exhausted attempts with operator recovery, wrong price/scope/currency, invalid signature, expired/exhausted/unauthorized downloads, refund and cancellation. A return-page visit alone is not success.
8. **All release controls pass without weakening.** Approve the final catalogue contract explicitly, then update its pin/approved assumptions in a separate reviewed change. Existing Stripe verifier tests must remain strict. Resolve migration governance and source blockers. Require full Python/frontend/browser checks, build, product verification and exact-release deployment smoke. An independent reviewer must confirm the resulting evidence before READY.

Production health remains fail-closed: `checkoutReady=false`, delivery disabled, source retrieval/reconciliation/checksum absent, and seven-day poll coverage 49 total / 45 completed (91.837%) against 336 / 99% required. The reconciliation utility's four coarse checks pass, but its checksum check tests alert state and its watermark check tests feed presence. That green result does **not** overrule the stricter live source-readiness failures.

## Validation results

| Check | Result |
|---|---|
| Full Python suite | **774 passed, 23 skipped, 3 failed**. Baseline was 758/23/3. Same three Stripe approval-contract tests remain red. No xfail or test weakening. |
| Frontend unit suite | **157 passed**, none skipped |
| Entire browser suite against local production build | **3 passed, 1 skipped**. CRM test requires an isolated synthetic session. Territory tests mock coverage and do not exercise Stripe payment. |
| TypeScript and production build | **PASS** |
| Real local PostgreSQL fulfilment test | **1 passed**, migration 060 applied to disposable cluster; Stripe, uploads and email sending injected |
| Real local PostgreSQL download checks | **PASS**, including concurrency and rejection cases described above |
| Generated PDF | Rendered and visually inspected all 11 pages; readable, but historical fixture output is not a current customer deliverable |
| Product-polish verifier | **PASS**, 10 entries, 4 assets, 34 links, existing 4-page brief and 1-page radar preview |
| Stripe verifier, unconfigured shell | Test **4/17**, live **3/19**. Shell lacks deployment secrets/identifiers; this is not a runtime configuration audit. |
| Stripe verifier, explicitly synthetic manifest-matching inputs | Test **16/17**, live **15/19**. Test fails approved manifest; live also fails the three hard-coded identifier-count checks. Not evidence of live readiness. |
| Migration governance | **FAIL**, migration 059 needs explicit approval |
| Deployment verifier | **FAIL**, deployed frontend SHA differs from tested branch SHA |
| Reconciliation utility | **PASS**, limited checks; live authoritative freshness/reconciliation still fail |
| Radar snapshot determinism | **BLOCKED/FAIL**, missing `_locations_detail.ndjson` |
| Fresh ODS digest determinism | **PASS**, byte-identical existing August digest; not fresh September territory evidence |
| Restore invariant verifier | **BLOCKED**, no isolated `RESTORE_DATABASE_URL` supplied; invocation used migration 060 and observed 58,946 / 57,187 row baselines |

The 23 Python skips are reported in `full-tests.log`: isolated database integration, local transcription opt-in and the standalone Territory Postgres test. The latter was separately run successfully against the disposable cluster. Approval controls, Stripe release tests and the verifier source remain unchanged.
