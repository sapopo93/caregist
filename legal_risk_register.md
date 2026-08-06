# Legal Risk Register & Compliance Checklist

## CQC Data: Open Government Licence v3.0 (OGL v3.0)

### What CQC Data Is Covered
CQC publishes open data under the Open Government Licence v3.0. This typically includes:
- Provider names, locations, and service types
- Inspection ratings and reports
- Registration dates and regulatory history

### Permitted Use Under OGL v3.0
- **Copy, publish, distribute, and transmit** the data.
- **Adapt** the data (including for commercial use).
- **Exploit** the data commercially, including by combining it with other data.

### Mandatory Conditions
1. **Attribution:** Must state: *"Contains CQC data © Care Quality Commission, used under the Open Government Licence."*
2. **No endorsement:** Must not imply CQC endorses our product.
3. **No misrepresentation:** Must not mislead others or misrepresent the data.
4. **Same licence:** If we republish the raw CQC data, downstream users must also use OGL v3.0. **However**, if we create a "value-added" product with significant enrichment, it is likely considered a derivative database with its own rights, though the underlying CQC facts remain under OGL.

### Risk: High
| Risk | Severity | Mitigation |
|------|----------|------------|
| CQC changes licence terms or restricts API access | Medium | Build ingestion redundancy; maintain good faith attribution; avoid scraping if API is available |
| Failure to attribute correctly | Low-High | Hard-code attribution into every export, report footer, and API metadata response |
| CQC alleges we imply official partnership | Medium | Legal review of all marketing copy; explicit disclaimers on every page |

---

## Companies House Data

### Legal Basis
Companies House data is governed by the **Companies Act 2006** and the **Companies House data reuse terms**.

### What We Can Do
- Use, reuse, and redistribute basic company data (names, numbers, addresses, officer names, filing history) **freely**.
- The government has committed to making Companies House data free and open.

### Restrictions
- **Images of filed documents:** Subject to Crown copyright and require separate licensing if reproduced.
- **Data accuracy:** We must not present data in a way that is misleading.
- **Direct marketing:** Using director names for unsolicited marketing is **not prohibited by Companies House terms**, but is restricted under **PECR** and **GDPR** (see below).

### Risk: Medium
| Risk | Severity | Mitigation |
|------|----------|------------|
| Director names used for cold outreach trigger complaints | High | Ensure GDPR lawful basis (legitimate interest assessment); provide clear opt-out; screen against TPS/CTPS |
| CH API rate limits or pricing changes | Low | Cache aggressively; budget for API fees (£0.02-£0.10 per call if bulk API introduced) |

---

## GDPR / UK Data Protection Act 2018

### Personal Data We Hold
- Director names (personal data)
- Director contact details (email, phone) if scraped or inferred
- Registered manager names
- Any employee data from job boards

### Lawful Basis for Processing
**Recommended: Legitimate Interests (Article 6(1)(f) GDPR)**
- We process business-relevant personal data (director identities) to provide a B2B intelligence service.
- We are not processing sensitive data (special category) unless we hold health data, which we should not.
- **Requirement:** We must conduct and document a **Legitimate Interests Assessment (LIA)** balancing our commercial interests against the privacy rights of directors.

**Alternative: Consent**
- Impractical for scraped data. Not recommended as primary basis.

### Direct Marketing & PECR
- **Email:** Under PECR, we cannot send unsolicited marketing emails to individual subscribers (e.g., `jane.smith@gmail.com`) without consent. **Corporate subscribers** (`jane.smith@carecompany.co.uk`) are permissible for B2B marketing, provided the email is relevant to their role.
- **Phone:** Must screen against **TPS** (Telephone Preference Service) and **CTPS** (Corporate TPS) before cold calling.
- **Post:** Generally permissible under PECR but GDPR still requires lawful basis.

### Risk: High
| Risk | Severity | Mitigation |
|------|----------|------------|
| ICO enforcement for unlawful direct marketing | High | Never sell consumer email addresses; only provide B2B corporate contacts; mandatory LIA; clear opt-out in every outreach |
| Data breach (unauthorised access to dossiers) | High | Encrypt at rest (AES-256) and in transit (TLS 1.3); RBAC; annual penetration test |
| Right to erasure requests from directors | Medium | Automate deletion workflow; 30-day SLA; purge from backups within reasonable timeframe |
| Cross-border data transfer (non-UK customers) | Medium | UK GDPR adequacy decisions cover EU; use Standard Contractual Clauses for US/other |

---

## Web Scraping & Third-Party Data

### LinkedIn
- LinkedIn's **User Agreement** prohibits scraping.
- **HiQ v LinkedIn** (US case) established that scraping public data is not a CFAA violation in the US, but UK position differs.
- **UK Computer Misuse Act 1990:** Scraping behind a login or circumventing technical barriers may be an offence.
- **Database Right (UK):** LinkedIn may claim a database right in its compiled profiles.

**Mitigation:**
- Only scrape **publicly visible** profiles (no login).
- Respect `robots.txt`.
- Rate-limit aggressively.
- **Safer alternative:** Use LinkedIn Sales Navigator API (formal partnership) or buy enrichment from providers like Apollo, Clearbit, or Lusha who bear the scraping risk.

### Job Boards
- Most prohibit scraping in their ToS.
- Similar risks to LinkedIn.

**Mitigation:**
- Use official APIs where available (Indeed, Reed).
- Aggregate from multiple sources to reduce dependency.
- Consider partnerships with niche care job boards.

### Land Registry
- HM Land Registry data is **open data** under OGL.
- **Price Paid Data** and **Ownership Data** are freely available.
- **Title registers** require a small fee (£3 per title) but can be resold as part of an enriched product.

### Planning Portals
- Most local authorities publish planning data under OGL or local open data policies.
- Scraping individual portals is generally low-risk if public-facing and no login required.

### Risk: Medium-High
| Risk | Severity | Mitigation |
|------|----------|------------|
| Cease & desist from LinkedIn | Medium | Do not scrape LinkedIn directly. Use third-party enrichment providers. |
| Database right infringement claim | Medium | Ensure our product is a transformative derivative (analysis + enrichment), not a mere repackaging |
| CFAA / CMA 1990 investigation | Low | Never circumvent technical barriers; never use fake accounts |

---

## CQC Brand & Passing Off

### What We Cannot Do
- Use the CQC **logo** without explicit permission.
- State or imply we are **affiliated with, endorsed by, or partnered** with CQC.
- Use domain names like `cqc-data.co.uk` in a way that confuses consumers about official status.

### What We Must Do
- Include clear disclaimer: *"[Our Company] is an independent data intelligence provider and is not affiliated with the Care Quality Commission. CQC data is used under the Open Government Licence v3.0."*
- Avoid CQC in product name if it implies official status (e.g., "CQC Pro" is risky; "CQC Signal" may be acceptable if clearly independent).

### Risk: Medium
| Risk | Severity | Mitigation |
|------|----------|------------|
| Trademark infringement / passing off | Medium | Brand audit by solicitor; no CQC logo use; prominent disclaimers |

---

## Insurance & Liability

### Recommended Cover
| Type | Limit | Purpose |
|------|-------|---------|
| Professional Indemnity | £1M - £2M | Covers claims if data inaccuracies cause customer loss |
| Cyber Liability | £1M | Covers breach response, ICO fines (where insurable), ransomware |
| Directors & Officers | £1M | Covers personal liability of founders |

---

## Compliance Checklist

### Pre-Launch
- [ ] ICO registration completed (£40-£2,900 depending on size).
- [ ] Privacy Policy drafted and published (lawful basis, retention periods, data subject rights).
- [ ] Terms of Service drafted (limitation of liability, acceptable use, data accuracy disclaimer).
- [ ] Legitimate Interests Assessment documented for director data.
- [ ] Cookie policy and consent mechanism (if using analytics/marketing cookies).
- [ ] Data Processing Agreements (DPAs) signed with all sub-processors (hosting, enrichment APIs).

### Operational
- [ ] Attribution footer on every report/export: *"Contains CQC data © Care Quality Commission, used under the Open Government Licence."*
- [ ] All marketing materials reviewed for CQC endorsement implication.
- [ ] TPS/CTPS screening before any phone outreach.
- [ ] Email marketing only to corporate addresses with relevant role targeting.
- [ ] Unsubscribe/opt-out mechanism in every communication.
- [ ] 30-day data subject request (DSR) workflow operational.
- [ ] Annual data protection impact assessment (DPIA).
- [ ] Encryption at rest and in transit.
- [ ] Access logging and anomaly detection.

### Vendor/Sub-Processor Due Diligence
- [ ] Cloud hosting: UK/EU region preferred (AWS London, GCP Europe-west2).
- [ ] Enrichment APIs: confirm they have lawful basis for data they provide.
- [ ] No transfer of UK personal data to inadequately protected jurisdictions without SCCs.

---

## Verdict: Can We Launch Tomorrow?

**Conditional Yes.**

We can legally launch a paid product using **CQC open data + Companies House data** tomorrow **IF**:
1. We include proper OGL attribution.
2. We do not use the CQC logo or imply endorsement.
3. We do not scrape LinkedIn or job boards directly; we use legitimate APIs or third-party enrichment.
4. We conduct a Legitimate Interests Assessment before using director data for marketing.
5. We register with the ICO before processing personal data.
6. We screen all phone numbers against TPS/CTPS.
7. We have a published Privacy Policy and Terms of Service.

**Biggest Blocker:** Using scraped director contact details (personal emails, mobile phones) for resale without clear lawful basis. **Safest path:** Sell only corporate contact data (role-based emails) and enrich via legitimate B2B data providers (Apollo, Lusha, Cognism) who carry the compliance burden.
