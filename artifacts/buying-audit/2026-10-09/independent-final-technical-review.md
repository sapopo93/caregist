# Independent final technical re-review — 2026-10-09

**Narrow verdict: both previously reported HIGH findings are cleared by the named corrections. No new critical defect blocking merge of this fail-closed repair was identified in the reviewed diff. Limited technical clearance applies to the repair only, with the MEDIUM recovery gaps below still open and the supplied parent full-suite run now complete (1400 passed, two skipped).** This is not commercial readiness, production certification, deployment approval or authorisation to open any gate. The producing worker does not approve its own work; model agreement is not green.

## Scope and method

Re-reviewed the current production diff in `api/routers/billing.py`, territory fulfilment/delivery, audit and the enquiry-only territory helper; inspected the four buying integration files, relevant changed unit tests and the supplied final logs. Repository operating instructions and output-quality-gate requirements were read in the original review and retained for this re-review. The original findings are archived in `independent-review-before-identity-fix.md`; this document supersedes their unresolved HIGH verdict for the corrected code only.

**Tests were not rerun.** This was static source and supplied-log review only. No network, secrets, app writes, database queries, external actions or production changes were performed. Only this review artifact was updated. The completed parent full-suite log is supplied evidence, not independent reviewer execution. `validated-source-manifest.json` records 14 code/test SHA-256 hashes; all 14 were independently compared with current file bytes and matched during this factual update. The parent reports those bytes unchanged since testing. This establishes current source-to-manifest consistency; it does not independently attest test execution.

## HIGH findings — cleared

| Original finding / promised correction | Current source evidence | Assessment |
| --- | --- | --- |
| Territory success could overwrite payment identity and ignore conflicting consent | `territory_brief_fulfilment.py:143–189,280–364`: locked SELECT includes durable intent, amount and currency; validators reject conflicts before generation and before the fulfilled duplicate return; writes preserve existing values with COALESCE; consent is compared again after insert. `territory_brief_delivery.py:248–269,297–319` uses the same validators. | **HIGH cleared.** A conflicting payment binding cannot be replaced by the success path. Conflicting immutable consent cannot silently pass through a fulfilled duplicate. |
| Legacy dataset could grant access after refund committed before payment binding | `billing.py:1687–1775`: validated authoritative intent/amount/currency, shared payment advisory lock before order lock, durable full-refund audit check in the following SELECT, existing payment and consent comparison before paid duplicate return or grant. Refund retains that same payment-lock protocol and strict audit write. | **HIGH cleared.** Refund-first rejects the later grant; checkout-first permits initial fulfilment, then the waiting refund revokes its entitlement. |

The territory real-Postgres conflict tests seed failed orders with a different durable payment intent or different consent terms, supply otherwise valid synthetic authoritative checkout evidence and assert no generation and unchanged durable state. The unit test `test_conflicting_existing_consent_fails_before_generation_even_for_duplicate` covers the fulfilled duplicate case. This supports the named corrections; it does not claim every conflict field/state has been independently exercised.

The new dataset file includes actual overlapping transaction attempts on separate checkout/refund connections:

- `test_refund_lock_blocks_checkout_until_commit_then_checkout_rejects`: refund retains its transaction lock, the checkout task stays pending during a shielded 0.2-second wait, refund commits, and checkout rejects with no token, consent or queued email grant.
- `test_checkout_lock_wins_then_refund_revokes_and_delivery_stays_gated`: checkout retains its transaction lock, refund stays pending, checkout commits and refund completes; the order is refunded, token expiry prevents access and the test's token-consumption SQL returns no entitlement. A delivery email remains queued, but the test explicitly disables outbound communications and asserts the queue claims none.

These tests improve on the earlier sequential-only evidence. They assert waiting and final outcomes; they do not inspect PostgreSQL lock wait metadata, test every interleaving/isolation level or prove that an enabled sender cancels an already queued message. Their validity depends on explicit enclosing transactions, as supplied by the production webhook. Ordinary READ COMMITTED isolation permits the post-lock SELECT to see the preceding refund commit. No deployed isolation setting was verified.

## MEDIUM finding — partially repaired, explicitly still open

**In-function persistence failure recovery is repaired.** `territory_brief_fulfilment.py:321–448` now wraps payment binding, consent insertion/validation, generation/uploads, fulfilled status, tokens, email insertion and the fulfilment audit call in the contextual exception boundary. The webhook can roll back and release its locks before the fresh-connection recorder restores trusted payment/consent. `test_post_upload_database_failure_recovers_evidence_then_refund_blocks_replay` injects a failure at the fulfilled-status write after both synthetic uploads, uses real rollback and recorder SQL, then verifies refund prevents generation or delivery on replay.

**Still unrepaired: outer transaction commit failure, process death/interruption before the recorder, and orphaned uploaded-artifact cleanup.** The function returns before the webhook transaction commits. A commit failure or later outer-webhook failure cannot be captured by its in-function try block. A worker dying after rollback but before successful recording loses the in-memory payment/consent context. Uploaded blobs use random paths and are not transactionally removed when later database work fails. The new module documentation acknowledges these limits; it does not implement reconciliation or cleanup.

Consequence: an order can retain no durable payment/consent binding after such interruption. If refund then commits before the binding exists, its audit guard prevents subsequent territory fulfilment, but that rejected replay does not itself restore the payment evidence or mark the local order refunded. Orphan blobs can remain after rollback and retry. These remain MEDIUM recovery/accounting and storage defects; they are not evidence of a new refund-bypass entitlement grant. They do not block merging the bounded repair while commercial gates remain closed.

Required separate closure evidence: durable reconciliation across outer commit failure and interrupted recording, an explicit orphan cleanup policy, and failure injection covering those boundaries. The supplied post-upload test uses synthetic upload references and a delegated connection wrapper raising a Python exception; it does not simulate an actual server-side SQL error, uncertain commit outcome, process death or storage deletion.

## Supplied tests and claim limits

- `full-final-tests.log` reports **1400 passed, two skipped, two warnings in 60.56s**. The full-suite status is complete; skipped cases are not passes. Tests were not rerun by this reviewer.
- `recovery-final-tests.log` reports **82 passed in 8.59s**: 33 territory unit cases, 23 billing webhook-handler cases, eight billing-entitlement cases, four buying refund cases, five generation recovery cases, three webhook recovery cases and six dataset refund cases. This is supplied evidence, not a reviewer test run.
- `frontend-final-tests.log` reports **183 passed, zero failed/skipped**. The helper diff keeps `canCheckout=false` for every count band and removes ranked-shortlist readiness claims. The Node log does not prove the Playwright journey ran or any deployed purchase/delivery path works.
- Basic direct refund tests without an explicit outer transaction do not establish advisory locking across all handler statements. The new dataset contention tests do supply enclosing transactions and separate connections.
- The null-payment refund characterisation explicitly represents a legacy row created before payment-context recovery; its docstring no longer describes the current recorder as error-only. That case remains characterisation, not recovery acceptance. The repeated direct-handler test is now named `test_repeated_refund_handler_invocation_preserves_revoked_state`, accurately distinguishing it from webhook event deduplication.
- Repeated invocation of one failure recorder advances the capped attempt counter. Evidence insertion is idempotent; exactly-once counting of distinct generation attempts is not established.
- Fulfilment audit calls still use the audit helper's default best-effort mode; strict propagation is specifically enforced for refund audit. The wider try boundary does not turn swallowed fulfilment-audit failures into strict failures.
- Signature construction, authoritative Stripe responses, pack generation, upload and outbound behavior are synthetic or gated. Neither test totals nor reviewer agreement approve commercial operation.

## Merge disposition

No remaining HIGH from the original review and no new critical merge blocker found within this re-review's source/test scope. The fail-closed repair receives limited technical clearance, with the explicit MEDIUM exceptions above, the completed supplied full-suite result and 14 matching source-manifest hashes. Checkout, outbound delivery, collectors, leads, claims and exports retain their separate named gates. Commercial readiness remains unapproved.
