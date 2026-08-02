# Legal and governance blocker register

“Resolved” here means either evidenced closed or technically fail-closed with a
named Human Gate decision. It does not mean legal advice was supplied.

| Blocker | Evidence/disposition | Status before Gate 1 |
|---|---|---|
| Operator/controller | **CLOSED 2026-08-01.** Founder named H-Kay Limited (10417923) as operator, contracting party and controller. Registered office verified at Companies House. Terms, privacy notice and acceptable-use page now agree | GREEN — named; brand/IP assignment still outstanding below |
| Brand/IP authority | No executed assignment/licence inspected | RED — document required |
| CQC database rights | OGL commercial reuse and attribution evidenced | AMBER — field-level personal-data and presentation review still required |
| CQC personal data | OGL expressly excludes personal-data rights; public directory excludes known manager names | RED — LIA/ROPA and qualified review required before broader use |
| Privacy notice | Feature-state and supplier disclosures now match the fail-closed implementation | RED — processor register, retention, transfer assessment, LIA/ROPA and qualified approval remain required |
| Terms | Draft B2B terms v1.1 identify H-Kay Limited and block consumer self-service | RED — no paid terms version is approved or configured; solicitor approval remains mandatory |
| VAT | No VAT registration, invoice or tax-treatment position is inferred in the paid journey | RED — Bilberry/accountant evidence is required before Stripe tax and invoice presentation can be configured |
| Country Pack | v0.3 sourced baseline created | AMBER — qualified approval required to become production-effective |
| Provider claims | Identity/authority/evidence/moderation controls built; intake false by default | RED — procedure, approvers and activation decision required |
| Reviews/enquiries | Intake false; review policy labelled draft; retention built | RED — safeguarding/moderation/lawful-basis approval required |
| Exports/billing | Checkout, monitoring activation, export delivery and lead intake are fail-closed. Checkout additionally requires an exact approved B2B terms version and immutable acceptance evidence | RED — legal, privacy, VAT, Stripe staging, cancellation and release evidence required before activation |
| Outreach/marketing | No action taken; ICO channel rules recorded | RED — LIA/consent/suppression/channel plan required |

Human Gate 1 can approve internal proof work only. It cannot silently convert any
RED item to production approval; named qualified owners must provide the evidence.

## External evidence register

Sensitive originals belong in the controlled document system, not this repository. A gate may
move only when all evidence columns are populated and independently verified.

| Deliverable | Controlled document ID | Approver | Approval date | Version | SHA-256 | Status |
|---|---|---|---|---|---|---|
| Approved B2B terms and liability/cancellation position | pending | pending solicitor | pending | pending | pending | RED |
| Privacy notice, processor register, LIA/ROPA and transfer assessment | pending | pending privacy/legal approver | pending | pending | pending | RED |
| Acceptable-use, OGL/enrichment and controller/customer/DPA position | pending | pending solicitor | pending | pending | pending | RED |
| Country Pack and claims/reviews/enquiries/moderation/outreach controls | pending | pending solicitor/safeguarding owner | pending | pending | pending | RED |
| H-Kay VAT status, invoice and reconciliation controls | pending | pending accountant | pending | pending | pending | RED |
| CareGist brand/IP assignment or licence to H-Kay Limited | pending | pending corporate approver | pending | pending | pending | RED |

## Unreviewed draft issues — 2 August 2026

The B2B terms draft and Privacy Notice were drafted in-house without qualified legal
review. Paid checkout is blocked. A solicitor should be pointed at these specifically:

1. **Liability cap** — fees paid in the preceding 12 months. Untested against the
   Unfair Contract Terms Act 1977 and, for any consumer subscriber, the Consumer Rights
   Act 2015.
2. **B2B-only boundary** — consumer self-service is blocked in code and the draft contains
   no consumer cooling-off waiver; the complete sales and support journey still needs review.
3. **VAT** — H-Kay's registration status is unconfirmed. If registered, invoices must
   carry the VAT number and rate, and the price presentation may need revisiting.
4. **Brand/IP authority** — no executed assignment or licence of the CareGist brand to
   H-Kay Limited has been inspected. This remains RED above and the terms assert our
   ownership of the software and presentation without that evidence.
5. **Resale restriction vs OGL** — clause 6 restricts bulk redistribution while clause 7
   confirms the OGL grants rights directly. The boundary between our enrichment and the
   underlying public sector information has not been legally tested.
6. **Data-protection split** — the notice makes H-Kay controller for account data and the
   customer controller for their own downstream processing. No data processing agreement
   is offered, which Enterprise buyers are likely to require.
