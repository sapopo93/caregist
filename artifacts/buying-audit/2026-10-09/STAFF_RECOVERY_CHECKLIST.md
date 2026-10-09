# Staff recovery checklist — preparation only

**Date:** 2026-10-09
**Status:** Proposed operating handoffs; not approval to accept payment, deliver, contact customers, or activate a commercial gate.
**Basis:** buying-process audit for release `3d3f3e42e95d3f1829387df19731eb819d93e993` (live observations about 09:07–09:10 UTC), current terms page, email queue and dead-letter checker. The audit records no real customer transaction, outbound message, refund, valid production download, or exercised staff rota. Technical synthetic evidence is identified per scenario below.
**Owner convention:** every operational role below is **NOT ASSIGNED**. Role labels describe the needed handoff only; they do not identify a person or establish availability.

## Operating boundary

Keep checkout, paid fulfilment, outbound delivery, and any customer-money action fail-closed until their gates pass. The public Territory Opportunity Brief terms say £745, written scope and source-path confirmation before payment, payment in full before work begins, and a three-working-day delivery **target** (Monday–Friday excluding England public holidays) after both confirmations; it is not a guaranteed SLA. They describe cancellation by email before work begins for a full refund and source-issue remedies. This checklist records those published statements without interpreting or extending them. The Weekly Digest is an enquiry offer with an unapproved terms gap: do not use a draft remedy or Digest-specific delivery/payment promise as approved policy.

Use only synthetic identities and a test payment/provider/storage environment when rehearsing these scenarios. A test pass establishes only the exercised boundary. Never use a real customer, send an external message, create a real payment, or issue a refund as part of this preparation checklist.

For every synthetic case, preserve a case ID, scenario ID, timestamps, evidence references, status transitions, and reviewer result. Redact credentials, payment secrets, and access tokens. Record customer-visible messages as test fixtures only; no message is to be sent from this checklist.

## Handoff register

| Handoff | Needed role | Owner | Evidence of handoff | Current evidence status |
|---|---|---|---|---|
| Enquiry intake and acknowledgement | Sales/intake operator | NOT ASSIGNED | Synthetic enquiry record, received timestamp, acknowledgement fixture, assigned case ID | UI email/copy paths and scope changes observed; mailbox receipt, acknowledgement, assignment not verified |
| Scope, source path, capacity and delivery date | Research/fulfilment operator | NOT ASSIGNED | Written scope record, source-path check, capacity decision, target-date calculation and customer agreement fixture | Published terms and page copy observed; human handoff/order record not verified |
| Payment and reconciliation | Authorised finance/operator role | NOT ASSIGNED | Synthetic merchant event, matching order/payment evidence, amount/currency/product/consent checks | Closed production health and local tests observed; no sandbox/live transaction or actual reconciliation |
| Pack production and independent review | Producer plus separate reviewer | NOT ASSIGNED / NOT ASSIGNED | Input edition, scope, source links/dates, output hashes, checklist results, reviewer sign-off | Synthetic pack and database tests exist; approved product and independent operational review not established |
| Email, delivery and link support | Delivery/support operator | NOT ASSIGNED | Queue/provider event, recipient match, delivery/access check, incident and resolution record | Queue logic and tests observed; real provider acceptance, inbox receipt, bounce and operator response not verified |
| Refund decision, execution and reconciliation | Authorised refund operator plus independent reconciler | NOT ASSIGNED / NOT ASSIGNED | Order/payment match, authority record, merchant refund ID/status, ledger reconciliation, customer-notice fixture | Local refund repair/tests described; no actual refund or completed customer/bank outcome |
| Customer acceptance or dispute | Support/acceptance operator | NOT ASSIGNED | Customer acceptance/rejection fixture linked to order, files and resolution | Formal acceptance and resolution workflow not verified |

## Scenario checklist

### 1. Enquiry receipt and acknowledgement

**Observed:** Pricing presents a £745 Territory Opportunity Brief and a £150 four-week Weekly Digest enquiry. The browser audit exercised the email and copy paths, scope changes, clipboard failure, and coverage retry. No email was sent; actual mailbox receipt, acknowledgement, intake record, and operator assignment are unverified. A `mailto:` click does not prove receipt or an order.

**Proposed handoff:** Customer submits an enquiry via their own email client or copies it to webmail. Intake operator checks the intended inbox, records the original enquiry and received time under a synthetic case ID in rehearsal, acknowledges receipt using an approved template, and assigns the case to a named operational role once one exists. If there is no receipt/acknowledgement evidence, classify it as **unconfirmed enquiry**, not a sale; do not collect payment.

**Synthetic acceptance scenario:** Submit a fixture enquiry through both UI paths. Verify the generated recipient, subject, and requested region/group/service criteria; simulate mailbox acceptance and a missing acknowledgement. Confirm the case is only marked received when the simulated inbox evidence exists, and that the missing-ack state is visible to the intake role. Exercise clipboard failure and show the customer-facing fallback remains usable. Do not transmit externally.

**Required proof:** fixture enquiry payload; UI/browser result; simulated inbox receipt ID and timestamp; acknowledgement fixture; case ID; role assignment; evidence that no order/payment state was created by enquiry alone. Mark actual mailbox and human response **NOT VERIFIED** until separately exercised with authorised synthetic infrastructure.

**Owner:** Intake operator — **NOT ASSIGNED**.
**Gate:** no paid action. The smallest remaining gate for this handoff is a documented, assigned intake route plus a synthetic receipt-to-acknowledgement rehearsal with retained evidence.

### 2. Written scope, source path, capacity and date agreement

**Observed:** Current Brief terms require written scope confirmation identifying territory and buyer/factual selection criteria, plus a source-path check before payment. The delivery target is three working days after both are complete, excluding England public holidays; it is a target, not a guarantee. Live copy agrees an actual date. Audit found no verified human order record. Current discovery criteria include provider group and optional service type, while the dormant generator request contract does not carry those selections; generated samples also lack the promised per-organisation qualification question. Coverage count alone is not source-supported fulfilment readiness. Digest-specific terms remain incomplete and its draft is expressly unapproved.

**Proposed handoff:** Research operator compares the exact requested criteria with actual source records and confirms whether the promised outputs can be produced. Fulfilment role checks capacity and calculates a proposed target date only after the written scope and source-path checks are complete. Send a written scope/date/fee/recipient/output confirmation fixture for agreement. Record acceptance and both check timestamps. If criteria cannot be supported or capacity/date is unavailable, pause and resolve the scope before any payment request. For Digest, hold the purchase path until approved product-specific terms and sequence/recovery evidence exist; do not turn draft language into a promise.

**Synthetic acceptance scenario:** Use one supported synthetic scope and one unsupported/filter-mismatch scope. Confirm the supported case records criteria, source paths, outputs (including qualification questions if promised), fee and date, and computes the stated target only after both checks. Confirm the unsupported case cannot advance to payment. Test a changed scope invalidates the previous confirmation/date and requires fresh source/capacity checks. Exercise a Digest enquiry as intake-only; assert that no approved payment or remedy is inferred.

**Required proof:** immutable scope version; territory and criteria; source record IDs/edition and timestamps; explicit supported/unsupported decision; capacity record; target-date calculation and its two prerequisites; customer agreement fixture; separate reviewer check; Digest terms approval reference before any future paid path. No legal interpretation is added here.

**Owners:** Research operator — **NOT ASSIGNED**; fulfilment scheduler — **NOT ASSIGNED**; customer scope approver — customer role, not assigned.
**Gate:** scope/source/capacity acceptance before any payment request. Smallest remaining gate: reconcile the actual enquiry criteria with the production method and demonstrate a recorded synthetic scope-to-date handoff. Digest additionally needs its own approved terms and delivery/recovery evidence.

### 3. Authorised payment and payment confirmation

**Observed:** Production health reports `checkoutReady:false`, `shadowCoveragePassed:false`, and `delivery.enabled:false`; source freshness is degraded. Live UI remains enquiry-only despite an API `canCheckout:true` field. Return-page copy says payment status is unconfirmed and “Do not pay again.” Local tests reject closed/unconfigured/legal/source/price gates and forged, unpaid, wrong-price, or wrong-scope evidence. Hosted checkout was simulated; no Stripe sandbox or live transaction occurred. Digest payment mechanism is unverified.

**Proposed handoff:** After scope and source checks, and only when the relevant gate is independently open, an authorised payment role issues the approved payment method and links it to the reserved order. Confirm payment from authoritative merchant state/webhook, matching order, product, exact amount and GBP currency, consent, and customer identity. A redirect, customer-supplied session ID, screenshot, or late email is not confirmation. Tell the customer not to pay a second time while status is unresolved. Do not start work on unconfirmed payment.

**Synthetic acceptance scenario:** With payment gates closed, verify no payment session/charge is created. In isolated test mode, exercise valid matching payment, wrong product/amount/currency/order, forged event, delayed event, duplicate/replay, and customer return before webhook. Only the valid authoritative event may transition the synthetic order once; return-page state remains unconfirmed until then. Verify duplicate/retry does not create duplicate work or payment. Never use production credentials or a real card.

**Required proof:** gate snapshot/config source; approved scope/order ID; consent version; signed synthetic webhook and verified merchant object; amount/currency/product/customer/order match; idempotency/replay record; order transition audit; no-charge evidence for rejected paths. Actual payment and reconciliation remain **NOT VERIFIED**.

**Owner:** Authorised payment/reconciliation operator — **NOT ASSIGNED**.
**Gate:** checkout readiness and source/legal/configuration gates independently pass. The smallest named release gate in the buying audit is to preserve and reconcile trusted paid evidence across generation failure, then independently test the complete failed-generation → refund → no-replay path. No activation is authorised by this checklist.

### 4. Generation or storage failure after payment

**Observed:** Synthetic real-PostgreSQL tests store consent, paid/fulfilled timestamps, files, hashes, token hashes and one queued email; generation failure tests prevent fulfilled state, tokens and email, and a separate recorder tracks attempts. Five failed generation attempts require manual review. External payment, Blob storage, and sending are synthetic. An open defect is specifically documented: payment evidence may be rolled back before a failed order is recorded, leaving refund handling unable to match that order by payment intent. The refund repair described by the audit is local, not part of the observed release.

**Proposed handoff:** Producer stops fulfilment on generation/upload failure and records order ID, stage, attempt number, error class, and durable trusted merchant reference without exposing secrets. Support role checks that no download entitlement or delivery email exists and opens a recovery case. Notify the customer only through an approved, actually monitored route after operational activation; obtain agreement to any revised date/scope under the published terms, or route the case for the applicable refund decision. A retry must be controlled, idempotent, and reviewed; a retry is not a customer remedy.

**Synthetic acceptance scenario:** Inject generation failure before output creation, after partial output, and after upload/storage failure. Verify there is no `fulfilled` state, usable token, or paid delivery email; preserve order/payment correlation across transaction rollback. Retry with idempotency and verify no duplicate files/tokens/emails. Exercise retry exhaustion/manual review and the failure → refund-match → replay attempt; assert refunded entitlement stays disabled and replay cannot fulfil. Include storage unavailable and hash mismatch. Until the documented payment-reference defect is fixed and independently closed, this recovery scenario is a **FAIL / OPEN**, even if other subcases pass.

**Required proof:** correlated order and trusted merchant reference durable through rollback; attempt/error audit; output/storage state and hashes; entitlement and queue state; retry/idempotency record; alert or manual-review case receipt; refund matching and replay evidence; independent reviewer result. External storage and customer notification remain **NOT VERIFIED**.

**Owners:** Fulfilment operator — **NOT ASSIGNED**; recovery/support operator — **NOT ASSIGNED**; independent reviewer — **NOT ASSIGNED**.
**Gate:** resolve durable payment-reference matching and pass the full synthetic recovery/no-replay scenario. This is the smallest technical gate named by the buying audit; no live order is needed to demonstrate it.

### 5. Email failure, bounce, or missed/expired link

**Observed:** Queue code authorises paid Brief delivery only for a fulfilled order and the matching paid recipient/idempotency key when outbound communications are otherwise closed. It rechecks authorization just before external send, uses three attempts with backoff, and marks terminal failure after the third failed send. `check_email_dead_letters.py` reports failed entries older than 24 hours by default (and exits non-zero when any exist). Queue tests cover retry, terminal failure, deferred-after-refund and recipient/order checks. Provider sending is mocked; real acceptance, inbox receipt, bounce processing, queue ownership and response are unverified. A `delivery.deadLetter:0` health signal is not proof the paid Brief queue has no dead letters. Links promise 30 days/up to five downloads; invalid token returned 401, but valid production retrieval, private Blob fetch, and support reissue were not tested. A Blob failure may consume a download count before retrieval/signing.

**Proposed handoff:** Delivery operator monitors provider result and paid-email queue/dead-letter report, matching every message to the fulfilled order and paying address. A provider acceptance ID is not inbox receipt. For terminal send failure or bounce, support case is created and delivery stays unresolved; verify the buyer using the approved process before arranging safe replacement access or communication. For a missed, expired, exhausted, or storage-failed link, verify entitlement/order and file availability, record whether quota was consumed, and recover access only through an authorised, auditable path. Never forward another buyer’s token or expose it in logs. Refund state must suppress further sends and access as implemented/verified.

**Synthetic acceptance scenario:** Simulate provider timeout, three send failures, provider accepted but no inbox, hard bounce, wrong recipient, refund between claim and send, and dead-letter age below/above 24 hours. Verify only the matching fulfilled buyer can be queued; rejected cases never send; refunded case is deferred; old failed message alerts and recent/sent messages do not. Separately test valid, expired, exhausted, unknown, missing-file and storage-error links, including whether failed retrieval consumes quota. Exercise support verification and an audited synthetic reissue/recovery path. No external email is sent.

**Required proof:** order/recipient/entitlement match; queue row ID, attempts, status and timestamps; provider event/message ID fixture; dead-letter output and alert receipt; bounce fixture; customer-notice fixture; token/access audit with redacted token; quota before/after; private file existence/hash; refund suppression; support case and reviewer sign-off. Real provider, inbox, bounce, valid private storage retrieval and reissue remain **NOT VERIFIED**.

**Owners:** Delivery monitor — **NOT ASSIGNED**; customer support — **NOT ASSIGNED**; storage/access operator — **NOT ASSIGNED**.
**Gate:** demonstrate monitored queue-to-case ownership, actual alert receipt in synthetic setup, and safe access recovery. A zero signal-outbox dead-letter count alone does not pass this gate.

### 6. Customer acceptance, rejection and closure

**Observed:** Tests and terms describe entitlements and the customer-facing link window/quota; no signed acceptance, real customer download, or completed dispute/resolution was observed. `fulfilled` means pack prepared/entitled, not proof the customer received or accepted it. The customer-pack README says later client signature/acceptance fields are onboarding tasks and synthetic organisations can exercise role workflows.

**Proposed handoff:** Once delivery is independently evidenced, support requests/records acceptance or rejection against the agreed scope and exact delivered file hashes. Record “received” separately from “accepted.” If the customer reports a missing or out-of-scope item, keep the case open, compare against the written order and source evidence, and route to correction, agreed revised date/scope, or the applicable remedy process. Do not infer acceptance from email provider status, download counter, or silence.

**Synthetic acceptance scenario:** Use a synthetic buyer role to download both expected files, review the criteria/source edition and submit acceptance. Then run rejection cases: missing file, mismatched hash, unsupported criterion, inaccessible link, and no customer response. Verify each event attaches to the same order and exact artifact hashes; only explicit acceptance records accepted, while received/downloaded remain distinct. Confirm a resolved case records the correction/revised agreement or refund outcome and independent review. No real buyer signature is solicited.

**Required proof:** written agreed scope/date; delivered file list and hashes; provider and access evidence; explicit synthetic acceptance/rejection timestamp and actor role; issue-to-resolution chain; any revised agreement fixture; refund merchant status if applicable; final independent review. Actual customer acceptance and resolution remain **NOT VERIFIED**.

**Owners:** Acceptance/support operator — **NOT ASSIGNED**; fulfilment reviewer — **NOT ASSIGNED**.
**Gate:** a complete synthetic delivery-to-acceptance/rejection-to-resolution record with a separate reviewer. This does not itself open sales or fulfilment gates.

### 7. Refund request, execution and reconciliation

**Observed:** Current Brief terms state that a buyer may cancel by email before work begins for a full refund and describe source-issue remedies; this checklist does not interpret those terms. The audit reports local real-schema tests for refund handling and entitlement revocation, but no real refund. Partial refunds retain original order state in the described tests. A full refund is not complete merely because an event was recorded: merchant status can remain pending/fail, and bank/customer receipt was not verified. The missing-payment-reference-after-generation-failure issue remains open. Digest refund/delivery remedies are unapproved and incomplete.

**Proposed handoff:** Support records the request and links it to written scope, work-start state, order, and authoritative payment evidence. The authorised refund operator determines the action under the operative terms and applicable approved process; this checklist supplies no legal interpretation. A separate reconciler checks merchant refund ID, amount, currency, final status, and order entitlement state. Record customer communication only after an approved route is active; distinguish requested, submitted, pending, failed, succeeded, and customer/bank receipt where evidence exists. Do not claim money has returned based solely on webhook/audit entry. On successful full refund, verify access/send suppression and replay safety.

**Synthetic acceptance scenario:** Cover pre-work cancellation/full-refund route, source issue with revised-date fixture and no-agreement/refund route, generation failure with persisted-payment reference, duplicate refund event, partial refund, pending refund, failed refund, successful full refund, and fulfilment replay after refund. Use test mode only. Require one matched refund action per authorised case; refund records and entitlement changes follow tested behavior; replay cannot restore access or send. Explicitly fail the generation-failure case while trusted payment evidence is not durable. Do not test Digest refund amounts or remedies as approved behavior.

**Required proof:** request and scope/work-start evidence; order/payment match; authority and decision record; synthetic merchant refund object/ID, amount/currency and final status; audit event; entitlement/token revocation and send suppression; idempotency/replay evidence; reconciliation result; customer-notice fixture; separate reviewer. No real refund, bank receipt, or customer contact is part of this preparation.

**Owners:** Refund operator — **NOT ASSIGNED**; independent reconciler — **NOT ASSIGNED**; support case owner — **NOT ASSIGNED**.
**Gate:** close durable failed-generation payment matching and independently pass synthetic refund → no replay → entitlement/send suppression. Any live refund requires the separately authorised, operative process and is outside this artifact.

## Digest status

**Digest draft: UNAPPROVED.** The £150 four-week Weekly Digest is an enquiry route; the current terms do not supply Digest-specific delivery, cancellation, or missed-week remedies. A draft proposing £37.50 per missed digest is not operative. Do not quote it, collect for it, or mark Digest acceptance scenarios passed. The minimum Digest gate is approved product-specific terms and order/payment/delivery agreement, followed by four sequential synthetic deliveries and a missed-week recovery scenario with independent review.

## Evidence classification and completion rule

- **Observed:** only the dated buying audit, current terms source, described queue/checker behavior and the cited synthetic/test artifacts. “Observed” does not imply fresh production verification beyond the audit's stated time/release.
- **Proposed:** all staff responsibilities, records, synthetic acceptance cases, evidence requirements, and escalation handoffs in this checklist. No role is staffed by this document.
- **NOT VERIFIED:** any real mailbox acknowledgement, assigned human rota, actual payment/refund, external email/inbox/bounce, valid private-file fetch, customer acceptance, or bank receipt.
- **Open blocker:** durable paid-evidence matching when generation fails before payment reference persists; criteria/generator mismatch; unresolved Digest terms and sequence; unverified staff ownership and external delivery/access recovery.

A scenario passes preparation only when its synthetic evidence is retained and an independent reviewer (role **NOT ASSIGNED**) records pass/fail and limitations. Passing this checklist cannot approve its own work, substitute for the prescribed independent gates, change a legal term, or activate checkout, collectors, outbound delivery, leads, claims, or exports. The smallest remaining release gate is the buying audit's named next step: preserve/reconcile paid evidence across generation failure and independently test failed-generation → refund → no replay fulfilment. Keep commercial buying closed pending that gate and the other product/source/operational blockers.
