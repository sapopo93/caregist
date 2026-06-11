# Data Protection Impact Assessment (DPIA) — CareGist

**Prepared by:** [Name / role]
**Date initiated:** [Date]
**Version:** 1.0 (template — owner must complete before launch)
**Status:** DRAFT — owner action required

> **ICO guidance:** A DPIA is required where processing is "likely to result in a high risk to individuals" (UK GDPR Article 35). CareGist processes account data, user-generated reviews, payment metadata, and aggregated CQC provider data. Complete all steps below before taking signups at scale.

---

## Step 1 — Identify the need for a DPIA

Score the processing activities against the ICO's nine criteria. A DPIA is mandatory if two or more apply.

| Criterion | Applies? | Notes |
|-----------|----------|-------|
| Evaluation or scoring | Partial | CQC ratings are aggregated; no individual scoring of natural persons |
| Automated decision-making with legal or significant effect | No | No automated decisions affecting individuals' rights |
| Systematic monitoring | Partial | IP / session logs for rate limiting and security |
| Sensitive data or data of a highly personal nature | No | No special category data (Article 9) processed |
| Data processed at large scale | TBC | Volume depends on user growth — review at 10,000 users |
| Matching or combining datasets | No | CQC public data combined with user submissions — low individual risk |
| Data concerning vulnerable individuals | No | Care-seekers may be vulnerable; no profiling of individuals |
| Innovative use or applying new technological or organisational solutions | No | Standard web application stack |
| Prevents data subjects from exercising a right or using a service | No | — |

**Assessment:** DPIA is required as a precautionary measure given (a) session monitoring and (b) potential scale. Complete this template before launch.

---

## Step 2 — Describe the processing

### 2.1 Nature of processing

- Collection of name, email, password hash on account registration.
- Collection and public display of user-authored reviews (with consent).
- Aggregation and display of CQC public-domain provider data.
- Payment metadata processed via Stripe (card data never touches CareGist servers).
- Session tokens and IP logs retained for 90 days.
- API / pipeline logs retained for 30 days.

### 2.2 Scope

- **Data subjects:** registered users (care seekers, care-sector professionals, B2B subscribers), care providers who claim profiles.
- **Volume:** [Insert current and projected user numbers.]
- **Geographical reach:** United Kingdom (primary); some sub-processors in US under SCCs.

### 2.3 Context

- CareGist is a commercial intelligence and consumer-facing directory.
- No special category data is collected.
- Data is not sold to third parties.

### 2.4 Purposes

| Purpose | Lawful basis |
|---------|-------------|
| Account creation and management | Art. 6(1)(b) — contract |
| Payment processing | Art. 6(1)(b) — contract |
| Publishing reviews | Art. 6(1)(a) — consent |
| CQC data aggregation and display | Art. 6(1)(f) — legitimate interest |
| Security monitoring (IP logs, rate limits) | Art. 6(1)(f) — legitimate interest |
| Marketing emails | Art. 6(1)(a) — consent (PECR) |

---

## Step 3 — Consultation

| Stakeholder | Role | Date consulted | Outcome |
|-------------|------|---------------|---------|
| H-Kay Limited directors | Data controller sign-off | [Date] | [Outcome] |
| Legal counsel | Terms and DPIA review | [Date] | [Outcome] |
| Engineering lead | Technical controls verification | [Date] | [Outcome] |
| DPO (if appointed) | Independent review | N/A — DPO not required at current scale | — |

---

## Step 4 — Necessity and proportionality

### 4.1 Lawful basis assessment

- **Contract (Art. 6(1)(b)):** Processing account data and payment metadata is strictly necessary to deliver the service. Without it we cannot authenticate users or process subscriptions.
- **Legitimate interest (Art. 6(1)(f)):** CQC data aggregation serves clear public interest in transparency of care quality. Session/IP logging is the minimum necessary for security. LIAs are on file.
- **Consent (Art. 6(1)(a)):** Marketing emails are opt-in only, granular, unbundled from service terms, and revocable. Review publication is consent-based; reviews cannot be published without explicit submission.

### 4.2 Data minimisation

- Passwords are never stored in plain text — only salted hashes.
- Card numbers, expiry dates, and CVV codes are never processed by CareGist (Stripe handles all card data).
- Only the minimum fields required for each feature are collected.

### 4.3 Retention justification

| Data type | Retention | Justification |
|-----------|-----------|---------------|
| Account data | 7 years post-deletion | HMRC tax record-keeping (Finance Act 2008, Schedule 37) |
| Reviews | Indefinite, name redacted | Public interest in care-provider review history; privacy balanced by redaction |
| Sessions | 90 days | Security monitoring — proportionate minimum |
| API / pipeline logs | 30 days | Operational monitoring — proportionate minimum |

---

## Step 5 — Risk register

| Risk ID | Risk description | Likelihood (1–5) | Impact (1–5) | Inherent risk score |
|---------|-----------------|-------------------|--------------|---------------------|
| R1 | Cross-tenant data leak (one user accessing another's data) | 2 | 5 | 10 |
| R2 | Audit log tampering (admin actions not recorded or altered) | 2 | 4 | 8 |
| R3 | Encryption key compromise (KMS key exfiltration) | 1 | 5 | 5 |
| R4 | Vendor/sub-processor breach (Stripe, Resend, Sentry, AWS, Neon) | 2 | 4 | 8 |
| R5 | Session token theft via XSS | 2 | 4 | 8 |
| R6 | Unauthorised access via credential stuffing | 3 | 3 | 9 |
| R7 | Review data attributed to wrong user post-deletion | 2 | 3 | 6 |

---

## Step 6 — Risk mitigation

| Risk ID | Mitigation measure | Control type | Owner | Status |
|---------|--------------------|--------------|-------|--------|
| R1 | Row-level security in PostgreSQL; API authentication middleware validates tenant scope | Technical | Engineering | [Status] |
| R2 | Append-only audit log table (`db/migrations/028_audit_log.sql`); admin action hooks in `api/utils/audit.py` | Technical | Engineering | [Status] |
| R3 | KMS-managed CMK for backup encryption; key rotation schedule set; access limited to CI/CD role | Technical | Engineering / DevOps | [Status] |
| R4 | Sub-processor DPAs in place; DPA links documented in Privacy Policy section 5; vendor security reviews annually | Contractual | Owner | [Status] |
| R5 | Session cookies set `HttpOnly`, `Secure`, `SameSite=Lax`; Content Security Policy headers enforced | Technical | Engineering | [Status] |
| R6 | bcrypt password hashing; rate limiting (`api/middleware/rate_limit.py`, Redis-backed in production); account lockout on repeated failure | Technical | Engineering | [Status] |
| R7 | Account deletion procedure redacts author name to "Former user" before unlinking profile | Technical | Engineering | [Status] |

### Residual risk assessment

After mitigations, owner must confirm all residual risks are acceptable. If any residual score exceeds 6, escalate before launch.

| Risk ID | Residual likelihood | Residual impact | Residual score | Acceptable? |
|---------|---------------------|----------------|----------------|-------------|
| R1 | 1 | 5 | 5 | Yes |
| R2 | 1 | 4 | 4 | Yes |
| R3 | 1 | 5 | 5 | Yes |
| R4 | 1 | 4 | 4 | Yes |
| R5 | 1 | 4 | 4 | Yes |
| R6 | 2 | 2 | 4 | Yes |
| R7 | 1 | 3 | 3 | Yes |

---

## Step 7 — Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Data controller (H-Kay Limited director) | [Name] | [Signature] | [Date] |
| Legal counsel | [Name] | [Signature] | [Date] |
| DPO (if applicable) | N/A | — | — |

**Decision:** [ ] Processing may proceed  [ ] Processing may proceed with conditions  [ ] Processing must not proceed

**Conditions (if any):**
[Insert any conditions before processing can begin]

---

## Step 8 — Review schedule

| Review trigger | Action |
|---------------|--------|
| Annual review (every 12 months from sign-off) | Re-assess all risks; update residual scores |
| Material change to processing activities | Initiate new or updated DPIA |
| Sub-processor change | Assess whether new DPIA is required |
| Security incident | Re-assess affected risks within 30 days of incident closure |
| User count exceeds 10,000 | Re-evaluate "large scale" criterion in Step 1 |

**Next scheduled review date:** [Date — 12 months from sign-off]

---

*This template follows the ICO's recommended DPIA structure. Refer to the ICO DPIA guidance at [https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/) for full guidance.*
