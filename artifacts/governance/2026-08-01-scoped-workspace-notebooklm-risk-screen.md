# DELIVERABLE RETURN — Scoped Workspace / NotebookLM risk screen

## Binary conclusion

- **Staging:** **REVISE**
- **Live activation:** **BLOCK**

**Screening note:** read-only Gmail is still a high-privacy-risk whole-mailbox processing use case; it is not low-risk just because it cannot send or edit mail.

## What was produced

- A privacy / legal / compliance screen of the exact requested scope:
  - Gmail whole-mailbox read-only
  - Drive / Docs / Sheets / Slides read-write on assigned files/folders via `drive.file`
  - NotebookLM limited to public-source or sanitised research, with no automatic Gmail transfer
- A control-focused assessment split into **safe staging** versus **live activation**.
- A blocker list covering data classes, retention, audit, incident handling, Google DPA / transfer risk, and mailbox risk.

## Decision rationale

### Staging — REVISE
Staging is acceptable only if it is **documentation/synthetic-data only** and does **not** touch live Gmail, live Drive files, or live NotebookLM content. The current package is not yet tight enough to call the staging design fully complete because the operational controls below are still not evidenced:

- exact mailbox data minimisation / exclusion rules
- retention and deletion schedule for mailbox-derived material
- audit log design for mailbox reads and file writes
- incident / quarantine / escalation procedure
- denial-path tests for scope overreach and folder/file allowlist checks

### Live activation — BLOCK
Live activation is blocked because the scope includes **whole-mailbox Gmail read-only**, which is still broad personal-data processing, and because the required privacy / transfer / retention / incident approvals are not yet recorded.

## Critical / High blockers

1. **Critical — whole-mailbox Gmail read-only is still broad personal-data processing.**
   - A read-only mailbox grant still exposes the full inbox, sent items, archived mail, attachments, headers, thread context, and third-party data.
   - This can include sensitive / special-category data or regulated information.
   - No approved lawful-basis, retention, data-subject-rights, or breach-runbook evidence was provided for the mailbox use case.

2. **High — Google CDPA / transfer analysis is not yet evidenced for live use.**
   - Google Workspace / Cloud Identity offer a Cloud Data Processing Addendum (CDPA) that incorporates SCCs for EU / UK / Swiss data protection requirements.
   - Google’s terms also say customer data may be stored or processed anywhere Google or its subprocessors maintain facilities, subject to the CDPA.
   - That means transfer-risk and processor-role review remain mandatory before live mailbox or Workspace AI activation.

3. **High — NotebookLM must remain strictly public-source / sanitised only.**
   - Google’s privacy hub shows NotebookLM prompts / responses are **not retained after session ends** and uploaded files / user-created notebooks follow the CDPA and can be manually deleted or exported.
   - The same Google materials also indicate that when sources are uploaded from Drive, NotebookLM creates a copy of the file.
   - Any automatic Gmail-to-Notebook path, or any import of non-sanitised internal mail/content, would materially increase the privacy and duplication risk.

4. **High — Drive `drive.file` allowlist enforcement is not yet demonstrated.**
   - `drive.file` is the right minimum-scope direction, but live activation still needs proof that every read/write checks the target file or folder ID against the allowlist.
   - Denial-path tests are required to prove nothing outside the assigned scope can be mutated.

5. **High — audit / incident / recovery controls are not yet evidenced.**
   - Need stable object-ID logging, access logging for mailbox and Drive actions, quarantine handling for misfiled content, and an escalation path for suspected breaches.
   - Need revocation / token-loss / restore-rehearsal checks before any live grant.

## Evidence used

### Local governance evidence
- `/Users/user/.hermes/profiles/ai-company-governed/company-os/chief-of-staff/task-briefs/2026-08-01-scoped-workspace-notebooklm.md`
  - lines 4–8: exact scope, constraints, acceptance criteria
  - line 10: qualified privacy/security review required for the Gmail mailbox purpose
- `/Users/user/.hermes/profiles/ai-company-governed/company-os/country-packs/uk.md`
  - lines 45–56: UK data-protection duties, breach handling, transfers, and no personal/confidential data to AI providers without review
  - lines 120–131: human approvals required for personal data / AI provider decisions
- `/Users/user/.hermes/profiles/ai-company-governed/company-os/operating-models/google-workspace-ai-company-v0.1.md`
  - lines 55–58: Phase 1 is manual, private, non-sensitive only
  - lines 119–140: Phase 2 is separately gated for Workspace AI / NotebookLM / Gmail AI
  - lines 142–153: API integration must be separately gated, with service-specific scopes and revocation tests
- `/Users/user/.hermes/profiles/ai-company-governed/company-os/risk-register.md`
  - line 6: UK-002 is a **Critical** AI/privacy risk until controller/processor map, contracts, retention, subprocessors, locations, transfer route, and DPIA are approved

### Google evidence captured during this session
- Google Workspace Privacy Hub snapshot:
  - `/Users/user/.hermes/profiles/ai-company-governed/cache/web/browser-snapshot-7f02f6a55b.txt`
  - lines 200–210: Gemini content stays within the organisation and is not used for other customers / training without permission
  - lines 243–251: Gemini-in-Workspace prompts/responses retention is admin-controlled; inserted/generated content follows the Cloud Data Processing Addendum
  - lines 276–281: NotebookLM uploaded files / notebooks follow the CDPA and can be manually deleted or exported
- Google Support search / page evidence:
  - `https://support.google.com/cloud/answer/13464325?hl=en` — Gmail API is listed among restricted scopes
  - `https://support.google.com/cloud/answer/13807380?hl=en` — Google recommends minimum scopes and specifically discusses `drive.file` as the narrower Drive scope direction
  - `https://knowledge.workspace.google.com/admin/compliance/privacy-compliance-and-records-for-google-workspace-and-cloud-identity` — CDPA incorporates SCCs as a mechanism for security / contracting / data-transfer requirements
  - `https://workspace.google.com/terms/service-terms-20260205/` — customer data may be stored or processed anywhere Google or subprocessors maintain facilities, subject to the CDPA

## Assumptions made

- “Staging” means **paper / synthetic-data / sanitised-data staging only**, not live mailbox or live Workspace access.
- No personal, customer, confidential, or regulated data is intentionally placed into NotebookLM.
- The allowlisted Drive folder structure will be enforced by code before any live write.
- No separate admin-console settings, Vault policy, DLP policy, or transfer-region restriction was provided in the task brief, so they are treated as unresolved until human review.
- The Google sources available in this session are sufficient for screening, but not for final legal approval.

## Known weaknesses / open questions

- Whether the Gmail mailbox contains special-category data, regulated data, or third-party confidential data is unknown.
- Whether Workspace Vault, retention, DLP, and admin logging are configured is unknown.
- Whether the account is subject to a UK / EU data-region commitment or other transfer restriction is unknown.
- Whether the live implementation can actually prevent Gmail content from entering NotebookLM through manual or indirect paths is unknown.
- Whether every Drive / Docs / Sheets / Slides mutation can be proven to stay inside the assigned file/folder allowlist remains untested.

## Compliance flags

- No live auth was performed.
- No Workspace mutation was performed.
- No personal data was entered into the assessment.
- No legal conclusion beyond screening was made.
- This screen does **not** approve activation.
- Qualified privacy / security review and independent QA are still required before any live grant.

## Ready for QA

- **Yes** — this screen is evidence-backed, PII-free, and ready for founder / qualified privacy review plus independent QA.
