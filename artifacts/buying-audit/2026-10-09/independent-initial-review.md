**Verdict: PARTIAL. The incompatible SQL removal is justified; refund recovery remains defective.** Seven read-only tool calls; no tests, network requests, writes or commercial approvals.

Verified evidence:

- [final-tests.log](/Users/user/CareGist/artifacts/buying-audit/2026-10-09/final-tests.log) and JUnit agree: **145 tests, zero failures/errors/skips**. Saved browser results report six expected passes. These are archived results, not independently rerun checks.
- [Migration 046](/Users/user/CareGist/db/migrations/046_billing_operations.sql) confirms the removed insert was invalid: missing columns, unsupported operation/status, absent conflict constraint, and omitted required fields. Removing it corrects that schema incompatibility.
- The refund tests use the full schema and real audit helper. They demonstrate partial-refund state retention and full-refund state changes for **already matched** fulfilled/failed Brief orders.

Critical defects and exact corrections:

1. **Payment identity is lost on generation failure.** Fulfilment writes payment intent, amount, currency, paid timestamp and consent inside the transaction subsequently rolled back. The separate failure recorder saves only status/error/attempts. The characterisation test correctly demonstrates an unmatched refund; it does **not** execute generation failure through recovery. A later checkout replay could therefore fulfil an already refunded payment.

   **Correction:** durably preserve validated payment/consent evidence independently of generation rollback; durably retain unmatched refund evidence and reconcile it before allowing fulfilment. Exercise actual failed generation → rollback → failure recording → refund → checkout replay, asserting refunded status and no new files, tokens or delivery email.

2. **Refund evidence can disappear while the webhook is acknowledged.** [The audit helper](/Users/user/CareGist/api/utils/audit.py:57) uses a nested transaction/savepoint and catches insertion errors. Consequently, the outer transaction can commit entitlement changes and `stripe_processed_events` without a refund audit row. This contradicts the handler’s unconditional atomic-recording claim. The report understates this as merely “unverified”.

   **Correction:** use a mandatory refund ledger/audit write that propagates failure through the webhook transaction. Inject a real audit-write failure and verify rollback of order changes, token expiry and dedup insertion; retry must then succeed.

Unsupported or overstated claims:

3. **“Replay is safe” proves only repeated handler state updates.** [The new tests](/Users/user/CareGist/tests/integration/test_buying_refund_pg.py:10) call `_handle_refund` directly, without the webhook transaction, signature boundary or event deduplication. They deliberately produce duplicate audit rows. The failed-order fixture also contains a token/file references unlike genuine failed generation.

   **Correction:** rename the test/report claim to “repeated handler invocation preserves refunded state”; add full webhook replay, rollback and Refund-object retrieval tests before claiming refund-event replay safety.

4. **“Live discovery and enquiries work” exceeds the evidence.** Saved pages support product display and enquiry links; no mailbox receipt, acknowledgement or recorded enquiry is demonstrated.

   **Correction:** say “discovery pages and enquiry initiation work; enquiry receipt and handling are unverified.”

5. **Commercial output remains unproven.** Saved sales copy promises selected criteria and a qualification question per shortlist entry. The schema/checkout metadata omit provider-group/service filters; the manifest omits qualification questions. Digest-specific terms and four-delivery recovery evidence remain absent.

   **Correction:** persist and enforce agreed criteria, supply per-entry questions, and exercise product-specific delivery/recovery. The original start-to-finish request remains only partially satisfied: payment, inbox delivery, private-file retrieval and staff resolution lack complete observed proof.

The [report’s overall PARTIAL verdict](/Users/user/CareGist/artifacts/buying-audit/2026-10-09/BUYING_PROCESS.md) is supported. Its narrow schema repair must remain distinct from the open recovery defects and uncompleted prescribed independent gates.
