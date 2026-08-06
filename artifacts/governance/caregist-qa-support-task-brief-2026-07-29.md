# TASK BRIEF — CareGist QA and Customer Support Journey

- **Project:** CareGist CQC lead intelligence and provider visibility
- **Country Pack in force:** United Kingdom v0.2 — primary-source researched; production blocked pending approvals
- **Objective:** Define CareGist’s QA and customer-support structure and map it across discovery, signup, purchase, onboarding, product use, data correction, billing/access, complaints, cancellation and retention.
- **Audience:** H-Kay/CareGist operations, support, engineering, data-quality and compliance owners.
- **Deliverable and format:** Design-only operating structure, RACI, journey-stage table, quality gates, support taxonomy, escalation ladder, service targets, pilot staffing, metrics and open decisions.
- **Constraints:** No customer/prospect contact; do not inspect lead CSV row data; no pricing change; no payment/refund; no publishing; no processor or personal-data approval; no production action. CareGist remains first_project_eligible=false.
- **Acceptance criteria:** Cover Free, Alerts/Data subscriptions, one-time dataset/export, provider listing claims, API/enterprise, data accuracy/correction, access/billing, privacy/data rights, complaints and incidents; separate line ownership/coaching from independent QA; define auditable evidence and stop-work controls; distinguish CQC-source data from CareGist-added data and provider-supplied changes; prevent claims of CQC affiliation or guaranteed commercial outcomes.
- **No-touch boundaries:** Read-only product/governance sources. No code, deployment, account, payment, CRM, customer record or production changes.
- **Deadline:** Current design cycle.
- **Producer roles:** Customer Success & Support; Legal, Risk & Compliance.
- **Producer model/provider:** OpenAI Codex GPT-5.6 Sol.
- **Reviewer role and model/provider:** Independent QA & Red Team using DeepSeek V4 Pro.
- **Human gates required:** Founder setup/Gate 1; pricing/refunds; personal-data purpose/processors/retention; contracts; publishing; spend; final launch.

## Known governance state

- Portfolio entry: `caregist-cqc-lead-intelligence`, owned by H-Kay Limited, target GB, candidate, `first_project_eligible=false`.
- Repository mapping: `sapopo93/caregist`, metadata-supported, but company-use/IP assignment remains unconfirmed.
- UK Country Pack v0.2: researched but not production-effective.
- Founder setup intake: invalid/empty.
- Approval register: no CareGist Gate-1 record; register validation currently also reports a duplicate effective Leadgen approval unrelated to CareGist.
- Risks: UK-004, UK-005, PORT-001 and IP-001 remain open and relevant.
- Product ambiguities: CQC change-event/90-day definition, lawful reuse and recipients, product ownership/IP, pricing/terms/VAT/refund controls, privacy/retention, support system and production approvals.
