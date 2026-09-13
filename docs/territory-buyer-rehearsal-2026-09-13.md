# Territory Brief buyer rehearsal, 13 September 2026

Status: PARTIAL. Production pricing is deployed. No completed payment or inbox delivery has been claimed.

## Fixes completed

- Added a read-only operator rehearsal command for the currently advertised manual service. It preserves region, buyer criterion and service type. It exports the full qualifying location population, a shortlist of distinct provider organisations, a workbook and a separate executive brief.
- Provider names are fetched from the official CQC provider API, never inferred from location names. Source checks, query extraction time and inspection/registration dates remain distinct. Every export remains marked DRAFT, even when its source checks pass. These tools do not constitute automated fulfilment or authorise customer delivery.
- Guards reject missing/duplicate identifiers, unsupported buyer criteria and insufficient shortlist populations. Source reconciliation/freshness failures remain explicit blockers. CSV/workbook text is protected against spreadsheet formula injection.
- Stripe test Product `prod_VFgg1p9PhKCIS4` and Price `price_1UFBJE4mijLHzRRkqw0jLNPW` now exist at GBP 74500, one-time, with lookup key `territory_opportunity_brief_gbp_oneoff_v2`.
- Test Payment Link `plink_1UFBQH4mijLHzRRkGKLtatYu` was created and inspected in the browser: Sandbox, Territory Opportunity Brief, GBP 745.00. No test payment submitted yet. Live and superseded object checks are recorded separately in the task evidence.
- The factual deployment manifest now records the corrected lookup key, test IDs, disabled automatic tax and inactive superseded objects. The verifier requires one Product and one Price in BOTH modes. Empty test identifiers no longer pass.
- The approval constant was not changed. The candidate canonical manifest digest is `1fa8b0d5c4c23d2a1e5f73623664280d97837835d9bd0771f0da0451ab66d5ed`. The existing pin remains `23fe0d48bd63ec42fb60f0a1797b993ccc11189f3c603d840477024faa42a002`.
- Fixed frontend release identity to prefer the actual Vercel build SHA over a stale configured SHA, retaining explicit SHA support outside Vercel.

## Real-data rehearsal

Scope: West Midlands, Requires improvement, all service types. Captured 13 September 2026 at 11:15 UTC. Read-only repeatable-read transaction against the canonical database produced 386 matching locations, 341 distinct providers and a 30-provider shortlist. Official CQC API lookups supplied the 30 shortlisted provider names. Export checks reopened the workbook and CSVs, and all four PDF pages were rendered and visually inspected.

This is a point-in-time research population. It does not prove rating changes, closures, ownership or buying intent. The published promise of notable movements still requires separately verified before/after evidence. The draft does not make up movements to fill this gap.

## Source refresh in progress

Read-only workflow dry run: https://github.com/sapopo93/caregist/actions/runs/34753712184 (PASS).

Founder-authorised production refresh: https://github.com/sapopo93/caregist/actions/runs/34753758031 . Batch `66b53f7f-2fba-4079-abb6-9b33bacbd684`, immutable source count 57,151. Prepare passed and processing started. At the first checkpoint 1,250 rows had processed with zero fetch or cleaning failures. This is progress, not completed reconciliation. No second run should be started while this batch is active. Require finalization and its source/manifest checksums before treating the source as reconciled.

## Validation

- New manual-pack tests: 6 PASS. New missing-test-objects regression PASS.
- Full backend suite after factual manifest correction: 865 passed, 28 skipped, 3 failed. The three failures are the unchanged Stripe tests expecting an approved repository manifest. Offline structural runs with synthetic, correctly shaped environment values pass 11/12 in each mode; only the unchanged hash gate fails. These synthetic runs are not live deployment credential verification.
- Frontend tests: 181 passed. Release identity regression tests include a stale explicit SHA and invalid Vercel SHA.
- Frontend production build PASS with explicit public API configuration.
- Ruff and diff whitespace checks PASS.
- Migration governance PASS. Read-only coarse reconciliation verifier PASS, but it does not prove that the new batch completed.
- Stripe CLI verifiers were run in both modes without production secrets injected: they fail on missing runtime configuration and the manifest approval gate. No secret values were printed.
- Production smoke FAIL: the public frontend health reports old SHA `1c98de7...`, while the backend reports deployed merge `9328b79...`. The frontend fix is prepared in this branch, not deployed.
- Product-polish verifier FAIL: a packaged asset does not match its recorded byte size. This predates the new code changes.
- Historical generator and digest determinism checks could not run: their external snapshot inputs are missing in the fresh worktree. They are not claimed PASS.

## Founder actions still required

- Supply an inbox under founder control for the receipt/delivery test (question pending in this task).
- Obtain the solicitor terms approval already being arranged. Preserve the manual service's agreed scope, delivery date and cancellation terms. Do not use placeholder immediate-supply consent for this manual rehearsal.
- Review the complete evidence and exact candidate manifest before any hash re-pin. General price approval has not been treated as approval of these new manifest bytes.
- Independent review of this branch and its evidence is still required. The producing agent cannot approve its own work.

## External evidence still required

- Successful authoritative reconciliation, checksum/watermark publication and refreshed real-data pack.
- Test checkout completed using the actual hosted Payment Link, with GBP 74500, one-time payment and no added tax verified in the resulting Stripe Session/PaymentIntent.
- Test payment associated with the agreed scope and a durable manual order record. This Payment Link is not wired to automatic Brief fulfilment.
- Receipt and all four promised output files arrive in the selected inbox and reopen correctly from the delivered copies.
- Cancellation/refund rehearsal, plus recovery procedure if generation or delivery fails.
- A complete manual pack with verified movement evidence, or explicit written scope agreement documenting the absence of supported movements.

## Release acceptance criteria

1. Public offer, written scope, final GBP 745 price and applicable approved terms agree.
2. Source verification passes for the agreed region, buyer criterion and service type before requesting payment. Confirm 25-50 distinct organisations, not 25-50 locations of fewer providers.
3. The buyer receives the correct one-time Payment Link; Stripe records a successful GBP 74500 payment tied to that order. No real charge is authorised by this rehearsal.
4. The manual operator delivers the territory CSV, editable Excel workbook, distinct-organisation shortlist and 3-5 page executive brief by the agreed date. Files retain source IDs, dates, reasons, qualification questions and limitations.
5. The selected recipient verifies receipt and opens every delivered file. Hashes match the reviewed pack.
6. Cancellation/refund and failure recovery are demonstrated. No duplicate fulfilment is produced for the same payment.
7. Independent review accepts the frozen code and evidence. Founder approves the exact manifest before its pin changes. Required release checks then pass on the reviewed commit.
8. Deploy the release-identity correction through the normal pipeline and verify both production SHA endpoints. Automated checkout and delivery remain OFF until their additional staging, terms and lifecycle gates pass.
