# CareGist QA & Customer Support — Executive Synthesis

**Date:** 29 July 2026  
**Producer:** OpenAI Codex GPT-5.6 Sol  
**Independent reviewer:** DeepSeek V4 Pro  
**Independence:** PASS — provider and model differ  
**Design readiness:** CONDITIONAL PASS  
**Operational readiness:** FAIL  
**Launch authority:** NOT GRANTED

## Recommended minimum viable support structure

| Role | Minimum pilot coverage | Independence/control |
|---|---|---|
| Support & Customer Success Lead | One named owner plus named deputy | Owns triage, onboarding and retention; deputy handles conflicts/absence |
| Data Quality & Claims Analyst | One named specialist; fractional acceptable | Owns CQC-source, CareGist-derived and provider-submitted corrections and listing-claim evidence |
| Engineering/Security Resolver | One named primary plus backup | Owns authentication, entitlements, alerts, exports, API/webhooks and incidents; cannot QA own critical fixes |
| Independent QA Reviewer | One named reviewer plus escalation reviewer outside Support | Independently selects samples, verifies source evidence/fixes and reviews material cases |
| Human approval functions | Founder plus qualified legal/privacy/accounting/security/finance owners | Approve gates only; do not disappear into operational roles |

Unsafe combinations: Independent QA cannot also own or coach the sampled case; Engineering cannot independently approve its own critical fix; Finance cannot approve its own requested adjustment; complaint/privacy reviewers cannot review their own conduct.

## Customer journey and quality controls

1. **Discover/search:** show source, freshness and CareGist independence; route care-quality concerns to CQC without losing CareGist complaints.
2. **Free/signup:** approved privacy/terms/consent and correct account/tenant access.
3. **Purchase or listing claim:** approved plan/price/terms; provider identity and location authority verified independently of payment.
4. **Onboarding:** approved entitlements, named admin, supported features and safe test data.
5. **Use:** validate alerts, filters, exports, seats, API and webhook events against source/version and entitlement.
6. **Corrections:** classify every disputed field as CQC-source, CareGist-derived, provider-submitted or mixed conflict; preserve before/after evidence.
7. **Support:** authenticate proportionately; log statement, evidence, owner, timestamps, approvals and outcome; never collect passwords/card credentials.
8. **Complaints/privacy/incidents:** preserve original statement/evidence, contain risk, use independent/conflict-free ownership and escalate immediately.
9. **Cancellation/offboarding:** separate access removal, billing/refund decision, exports and retention/deletion decisions; revoke seats/tokens/API access.
10. **Feedback/retention:** aggregate root causes without continuing contact after opt-out or promising an unapproved roadmap/discount.

## Six operational blockers

1. Founder intake, CareGist Gate 1 and eligible portfolio status are absent; UK-004, UK-005, PORT-001 and IP-001 remain open.
2. No approved helpdesk/CRM, fallback ledger, retention schedule or support system of record exists.
3. `support_quality_hook.py` is fail-open: missing configuration/report and network failure can still return success; schema and hidden-field metrics are hard-coded rather than verified.
4. CQC data terms, licence/reuse assessment, exact fields, recipients, change events and “90-day” rule are unverified/unapproved.
5. The provider “verified badge” has no approved identity/authority standard.
6. The no-personal-data-to-AI rule lacks approved operational/technical enforcement.

## High findings

- Independent QA has no escalation/secondary reviewer for its own blocker findings and methodology.
- Support Lead is overloaded and lacks an explicit deputy/alternate complaint owner.
- “Cancel anytime” does not define effective date, renewal, refunds or post-cancellation access.
- VAT treatment and B2B/B2C classification are unresolved; `+ VAT`/tax-exclusive display cannot be assumed suitable for every buyer.

## Mandatory corrections in dependency order

1. Complete founder setup intake and record CareGist Gate 1.
2. Resolve CQC terms/reuse, field inventory, event definitions and permitted recipients with qualified UK review.
3. Resolve H-Kay IP/company-use and third-party licence chain.
4. Define provider-claim identity/authority tiers, location scope, conflict handling and reverification.
5. Approve the data map, lawful bases, notices, rights, retention, processors/transfers and no-data-to-AI controls.
6. Select and approve the helpdesk/CRM and controlled fallback ledger.
7. Replace the fail-open quality hook with a blocking, evidence-retaining gate that computes real schema/hidden-field results.
8. Approve VAT/customer classification, subscriptions, cancellation, refunds, chargebacks and price presentation.
9. Add Support and Engineering deputies plus an Independent-QA escalation reviewer.
10. Complete security, claims, publishing and final launch gates.

## Root verification notes on DeepSeek wording

- Reviewer independence is evidenced by different provider/model; no conclusion is made about unobservable shared infrastructure.
- CQC reuse is described as **unverified and unapproved**, not conclusively unlawful.
- The applicable internal accessibility target from UK Country Pack v0.2 is **WCAG 2.2 AA**, not WCAG 2.1 AA.
- Any QA verdict should be retained and independently auditable; a cryptographic signature is not assumed unless separately designed.

## Status

Internal design and remediation planning may continue without personal/customer/prospect data or external action. Customer support intake, subscriptions, provider badges, exports, API/webhooks, payments, refunds, personal-data processing, marketing, publication and launch remain blocked.
