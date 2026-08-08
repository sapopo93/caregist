# Data Retention Policy — CareGist

**Data controller:** H-Kay Limited
**Last reviewed:** 2026-05-14
**Review frequency:** Annual (or on material change to processing activities)

---

## Purpose

This policy sets out the minimum and maximum retention periods for each category of personal data processed by CareGist, the legal or business basis for each period, and the deletion / anonymisation method applied at the end of that period.

---

## Retention schedule

| Data category | Data type | Retention period | Trigger event | Legal / business basis | Deletion / anonymisation method |
|---------------|-----------|-----------------|--------------|----------------------|--------------------------------|
| **Account data** | Name, email address, password hash | 7 years from account deletion | Account deletion date | UK tax law — HMRC record-keeping obligations under Finance Act 2008, Schedule 37 | Soft-delete on day 0; hard-delete from primary database after 7 years; backup media purged on next rotation cycle (max 90 days) |
| **Reviews** | Review text, star rating, relationship to provider | Indefinite | Author's name redacted to "Former user" on account deletion | Legitimate interest (Art. 6(1)(f)) — public-interest information about care providers; readers rely on review history | Author name and email replaced with "Former user" at deletion; review content and rating retained; no further personal link |
| **Claims data** | Name, email, phone, role, proof of association | Duration of active claim + 3 years | Claim closure date | Legitimate interest — dispute resolution | Deleted from active tables; purged from backups after 90-day backup rotation |
| **Payment metadata** | Stripe customer ID, subscription tier, transaction history | 7 years from last transaction | Last transaction date | UK tax law (Finance Act 2008, Schedule 37); VAT record-keeping (VATA 1994 s. 58 and Regulations) | Retained in encrypted backup; access restricted to finance/admin roles; purged after 7 years |
| **Session tokens** | Session token, IP address, user-agent, request path | 90 days from session creation | Session creation timestamp | Legitimate interest (Art. 6(1)(f)) — security monitoring and abuse prevention | Automatic TTL expiry in database; purged from backup media after 90-day rotation |
| **API / pipeline logs** | IP address, API key identifier, endpoint, response status | 30 days from log creation | Log creation timestamp | Legitimate interest (Art. 6(1)(f)) — operational monitoring and rate-limit enforcement | Rolling 30-day window; automatic purge via scheduled database job |
| **Password reset tokens** | Token hash, expiry timestamp | 24 hours from issuance | Token issuance | Contract (Art. 6(1)(b)) — minimum necessary for feature | Single-use; expired tokens purged by scheduled job every 24 hours (see migration 021) |
| **Admin audit log** | Admin user ID, action, target record, timestamp | 7 years from log entry | Log entry date | Legitimate interest (Art. 6(1)(f)) — accountability and tamper-evidence; regulatory expectation | Append-only table; purged after 7 years via scheduled maintenance |
| **Enquiry data** | Name, email, phone, message content | 2 years from submission | Submission date | Legitimate interest — evidencing enquiry handling; responding to disputes | Deleted from active tables; purged from backups after 90-day rotation |

---

## Backup and media retention

- Production database backups are retained for **90 days** on a rolling basis.
- All backups are encrypted at rest using KMS-managed customer master keys (CMK).
- Backup media is securely deleted (cryptographic erasure via key rotation) at the end of the 90-day window.
- Offsite backup copies (if any) follow the same 90-day schedule.

---

## Deletion procedures

| Method | Description | When used |
|--------|-------------|-----------|
| **Soft delete** | Record marked `deleted_at`; excluded from application queries | Immediate on user deletion request |
| **Hard delete** | Row physically removed from primary database | After applicable retention period |
| **Pseudonymisation / redaction** | Personal identifiers replaced with a generic token (e.g., "Former user") | Reviews retained post-deletion |
| **Cryptographic erasure** | Encryption key destroyed; data becomes irrecoverable without physical deletion | Backup media at end of 90-day rotation |
| **Automatic TTL expiry** | Database job / scheduled cleanup removes records past their timestamp | Session tokens, pipeline logs, reset tokens |

---

## Roles and responsibilities

| Role | Responsibility |
|------|---------------|
| Data controller (H-Kay Limited director) | Approve and sign off this policy; ensure resources for implementation |
| Engineering lead | Implement and maintain deletion jobs, audit trails, and backup schedules |
| All staff | Report any suspected retention failure to `privacy@caregist.co.uk` within 24 hours of discovery |

---

## Review and audit

This policy must be reviewed:
- Annually (minimum).
- When a new data category is introduced.
- Following a security or data incident.
- When sub-processor relationships change.

**Next scheduled review:** 2027-05-14

---

*Questions about this policy should be directed to `privacy@caregist.co.uk`.*
