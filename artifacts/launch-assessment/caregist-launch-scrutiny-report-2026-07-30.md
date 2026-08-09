# CareGist procurement-concierge launch scrutiny

**Date:** 30 July 2026
**Decision:** **NO-GO for external launch or sale in its current form**
**Strategic direction:** **CONDITIONAL GO for a tightly controlled validation sprint after governance/privacy prerequisites are cleared**
**Confidence:** High on the no-launch decision; medium on eventual commercial viability because no observed buyer/provider behaviour exists.

## Executive conclusion

The four-page collateral is a competent **internal design proof**, not a launch package. Its own red labels say that it must not be published, sent, quoted or used for pricing. The previous independent QA tested layout, source transcription, contrast and responsive rendering. It expressly did **not** validate demand, delivery, CQC-data provenance, privacy, pricing, VAT, terms or launch operations.

Launching the offer now would be a hit-and-miss bet for five independent reasons:

1. **The supposed advantage is not evidenced.** CQC's official public API/datasets describe active and inactive registered providers and locations. They do not, on the evidence reviewed, provide a public pre-registration/application feed. CareGist's current 100-provider supply list consists of already registered providers. Claims that CareGist reaches providers “from pre-registration onwards”, knows about a registration application, or reaches providers before they appear in public data are therefore unsupported by the demonstrated source pipeline.
2. **No demand has been validated.** The repository contains 100 researched supplier prospects, including 11 CareTech/software businesses, but every row is held for same-day verification and outreach approval. A prospect list is not willingness to pay. No completed buyer interviews, letters of intent, paid pilots, accepted price tests or observed conversion data were found.
3. **The unit economics are poor under reasonable assumptions.** Five pilot demos generate £875 net of VAT. The independently recalculated scenarios require approximately 14–65 completed procurement audits and 49–155 direct hours. Even the illustrative upside case loses about £110 at £20/hour before outreach, software, legal, insurance and overhead. Base-case contribution is about **−£648** at £20/hour.
4. **The service cannot currently be evidenced, invoiced or defended.** There is no approved contract, objective demo-acceptance rule, replacement cap, CRM/system of record, complaint owner/deputy, privacy/recording workflow, invoice controls or verified entity/VAT status.
5. **Governance and evidence integrity are incomplete.** No production-effective UK Country Pack, role registry, approval register, portfolio/platform registers or founder setup intake was found. The current PDF and desktop image hashes do not match the hashes recorded in the QA report; the desktop capture appears to have been replaced after the report. The HTML and mobile hash do match. This is not evidence of malicious tampering, but it means the “blocker resolved / final pass” statement lacks a formal QA addendum tied to current hashes.

The idea is not rejected. The underlying two-sided problem is plausible: newly registered providers have setup decisions, and care-software vendors value well-timed qualified conversations. But plausibility is not enough for a launch where reputation matters. The correct next move is **validation before fulfilment commitment**.

---

## 1. What the earlier report actually proves

### Proven

- The HTML is editable and the PDF is four-page A4.
- The current desktop image is 1440×6040 and mobile image is 390×10455.
- The design is readable, responsive and contains CQC-independence warnings.
- The supplied source wording and draft commercial terms were largely transcribed faithfully.
- The collateral registers eight open claims and labels all as unverified, unapproved or blocked.

### Not proven

- That new providers want a 45-minute audit.
- That they will disclose budget and purchasing deadlines.
- That software selection occurs at the claimed stage.
- That CareGist has lawful/credible access to registration applications or pre-registration providers.
- That a vendor will pay £175 per demo or commit to five.
- That CareGist can deliver five accepted demos in ten weeks.
- That demos will convert, be non-disputed or be contribution-positive.
- That “around 14 purchases”, comparative meeting prices, “vetted”, “higher intent”, “unreachable through normal channels”, “before first inspection” or “48-hour written plan” are substantiated.
- That the entity, VAT, terms, privacy, recording, support and invoicing controls are ready.

### Evidence mismatch

The QA report records abbreviated hashes beginning:

- HTML `6577060e…` — **matches current HTML**.
- Mobile `aead50f9…` — **matches current mobile image**.
- Desktop `f2eb4451…` — **does not match current `c897cbfb…`**.
- PDF `e3e6ff77…` — **does not match current `486e4211…`**.

File times show the desktop image was modified six seconds after the QA report, consistent with the reported recapture. That is understandable, but the QA record still says `CONDITIONAL PASS` and contains no post-correction addendum with the new full hashes. A clean design pass should not be claimed until the reviewer checks the current artifacts and issues that addendum.

---

## 2. Product and market logic

### Customer A — new care provider

**Plausible problem:** CQC confirms that a provider must be properly prepared, with locations, staff and supporting evidence in place before applying. New providers therefore do face coordinated setup decisions.

**Unproven proposition:** The collateral turns this into a fixed “around 14 purchases” journey, says sequencing errors burn cash or cause inspection unpreparedness, and promises a complete written procurement plan in 48 hours. No source inventory, methodology, professional-scope boundary, user research or fulfilment test supports that promise.

**Trust risk:** The audit says it is “for you, not for suppliers” while its economic purpose is to qualify paid supplier meetings. The disclosure that suppliers pay is good, but provider trust can still be damaged if recommendations are influenced by paying vendors, exclusivity or commission. The provider-interest rule, conflict register and shortlist methodology must be explicit and demonstrable.

### Customer B — software vendor

**Plausible problem:** Vendors want early, relevant conversations and may value evidence of need, decision-maker attendance, budget fit and timing.

**Unproven proposition:** No vendor has accepted the four qualification criteria, the £175 price, the five-demo minimum, the replacement policy or the evidence standard. The repository's 11 CareTech/software prospects are research targets, not demand signals.

**Vendor objection likely to be decisive:** “Why should we pay for an attended meeting if the prospect does not trial or buy?” The current draft protects CareGist only if all four criteria hold, but it does not define the evidence hierarchy, objection deadline, who adjudicates disputes or whether poor outcomes can be relabelled as failed qualification.

### Competitive advantage

The claimed moat is early timing plus documented qualification. The demonstrated data pipeline currently supports **recent registration signals**, not pre-registration exclusivity. CQC states that its API includes active/inactive providers and locations and is updated daily; its public spreadsheets are also available. Competitors can access the same base data under the Open Government Licence. Therefore the defensible advantage must come from:

- provider permission and trust;
- audit quality and proprietary structured needs data;
- reliable fulfilment and acceptance evidence;
- vendor conversion outcomes;
- repeatable operational learning.

None of those moats is yet evidenced.

---

## 3. Claim-by-claim launch assessment

| Claim / promise | Verdict | Why |
|---|---|---|
| “From pre-registration onwards” | **Remove unless independently evidenced** | Public CQC evidence reviewed covers registered providers/locations, not an application feed. |
| “Congratulations on [service]’s registration application” | **Do not use from current list** | The 100-provider list contains registration dates and live CQC provider pages; it does not prove an application-stage signal. |
| “Before they appear in public data they have already bought” | **Unsupported and self-contradictory** | CareGist's demonstrated leads come from public CQC registration data. |
| Providers must choose software before first inspection | **Unverified** | CQC requires readiness and records security but the reviewed guidance does not mandate purchase of a particular care-management platform. |
| “Around 14 significant purchases” | **Unsupported** | No taxonomy, applicability logic or source; purchase count varies by service model. |
| Wrong sequence burns cash / risks inspection | **Potentially misleading without evidence** | Objective outcome claim requiring substantiation and careful qualification. |
| “Vetted shortlist” | **Blocked** | No vetting standard, monitoring, eligibility or conflict method exists. |
| “We know what they need, their budget and deadline” | **Only case-by-case after a completed lawful audit** | Cannot be a general market claim; records and consent/sharing controls are absent. |
| “48-hour pre-demo brief” and written plan | **Unproven operational promise** | No template, staffing evidence, dry run or service record. |
| Higher-intent than generic agencies | **Unsupported comparison** | No like-for-like data or independent benchmark. |
| £20–£200+ / £240–£600 meeting benchmarks | **Remove until sourced** | No dated comparable sources in evidence. |
| Non-billable and replaced free | **Commercially dangerous as drafted** | No evidence rule, replacement cap, objection window or end-of-pilot treatment. |
| £175 + VAT | **Not approved** | Pricing economics and VAT/entity status unresolved. |
| “Genuinely free / you never pay” | **Conditional only** | Must be true in practice and disclose any provider commitments and supplier-funded model clearly. |
| “Recorded consent” | **Rewrite after privacy design** | Recording, holding details and supplier sharing are separate processing purposes; one bundled recorded statement is not a complete mechanism. |

ASA/CAP Code section 3 requires documentary substantiation before publishing objective claims, prohibits material omissions and misleading qualifications, and sets specific rules for VAT-exclusive prices and “free” claims. Red warning labels make an internal draft safer; they do not make the underlying claims publishable once the labels are removed.

---

## 4. Data, marketing and regulatory assessment

This is a risk screen, not binding legal advice.

### CQC data

CQC's official page, updated 2 July 2026, says:

- its API/data sheets may be used under the Open Government Licence;
- users should acknowledge use of CQC information;
- the API includes active/inactive providers and locations and is updated daily;
- the directory includes registered locations and can include registered-manager information;
- published files currently have update delays while CQC moves systems.

This means commercial reuse is not automatically prohibited, but accuracy, attribution, non-endorsement, field purpose and personal-data obligations still matter. CQC's data-delay warning weakens any “real-time/current” promise.

The collateral's independence footer is good. It does not contain the repository risk register's proposed CQC/OGL attribution wording. Whether attribution is needed on each item depends on what CQC information is reproduced, but the operating standard must be defined before outreach/data sharing.

### Direct marketing

ICO guidance updated in 2026 says organisations must plan direct marketing by design, identify a lawful basis, collect data fairly and transparently, and respect the absolute right to object/opt out.

PECR regulation 22 expressly applies consent restrictions to unsolicited email sent to **individual subscribers**. The corporate/individual classification therefore matters; named work addresses can still be personal data even where PECR's individual-subscriber rule does not apply. LinkedIn/email outreach should not be treated as automatically lawful merely because it is “B2B”.

PECR regulation 21 restricts unsolicited marketing calls where the subscriber has objected or the number is on the relevant suppression register, subject to the regulation's conditions; caller identity/contactability must be presented. The current 100-provider list contains many mobile numbers and named managers. A same-day verification, TPS/CTPS/suppression workflow and contact-record standard are necessary before calling.

### Audit recording and supplier sharing

Before collecting budget, purchase intent and decision-maker details, CareGist needs an approved data map covering:

- controller/entity identity;
- purpose and lawful basis for audit, recording, matching and marketing;
- whether recording is necessary and what non-recorded alternative exists;
- privacy information at collection;
- retention and access;
- provider instruction/choice for each introduction;
- minimum data in the vendor brief;
- vendor recipient obligations;
- rights, objection, deletion and complaint handling;
- processor/AI restrictions and transfer controls.

The ICO data-sharing code emphasises fairness, transparency, lawfulness, security, rights, accountability and data-sharing agreements. Its page warns that the code is under review following the Data (Use and Access) Act, reinforcing the need for current qualified review.

### Entity, VAT and contracting

The legal/contracting entity is unresolved. Existing project material names H-Kay in places and N Dumane Consultancy Ltd elsewhere. No offer, invoice, privacy notice or agreement should be issued until the entity and authority/IP chain are verified.

HMRC's current GOV.UK guidance states compulsory VAT registration generally applies when taxable turnover exceeds £90,000 over the previous 12 months or is expected to exceed it in the next 30 days; voluntary registration is possible below that. This does not establish CareGist's actual status. “+ VAT” must not be charged until status is confirmed. CAP 3.18 also limits VAT-exclusive advertising to an audience clearly able to recover VAT and requires prominent VAT information.

### Existing legal risk register

`legal_risk_register.md` is useful as an issue list but must not be treated as verified launch clearance. Its “Conditional Yes — launch tomorrow” conclusion conflicts with later evidence and includes over-broad statements, including that corporate-address B2B email is simply permissible and that enrichment vendors carry the scraping/compliance burden. CareGist remains accountable for its own processing and source due diligence. The register should be superseded by a versioned, primary-source-reviewed UK Country Pack and obligations register.

---

## 5. Economics and fulfilment

### Verified scenario calculation

For five accepted demos:

`billable demos = completed audits × qualification × booking × attendance × acceptance`

| Scenario | Billable yield/audit | Audits for 5 | Demo attempts | Direct hours | Revenue/hour | Contribution at £20/hour |
|---|---:|---:|---:|---:|---:|---:|
| Downside | 7.735% | 64.64 | 9.05 | 154.59 | £5.66 | **−£2,216.89** |
| Base | 18.90% | 26.46 | 7.41 | 76.17 | £11.49 | **−£648.39** |
| Upside | 36.338% | 13.76 | 6.19 | 49.26 | £17.76 | **−£110.19** |

Revenue is `5 × £175 = £875`, excluding VAT. At £20/hour, break-even permits only 43.75 total hours. The model excludes prospecting, failed audit bookings, sales, legal, software, insurance, overhead and bad debt, so it is optimistic.

The only plausible escape is to monetise each provider audit across several genuinely needed categories. That is currently unproven and increases conflict/trust risk. It must not be assumed in pricing.

### Cash is later than revenue

With one accepted demo per fortnight and 14-day terms, the commercial review estimated that only £700 would be contractually due by week 10 and at least £175 would still be not due; full on-time cash arrives around week 12. Disputes could reduce week-10 cash to £0–£350. VAT collected, if applicable, is not revenue.

### Missing operating controls

Before live fulfilment, CareGist needs:

- one accepted definition of “qualified demo” and evidence hierarchy;
- fixed vendor objection deadline;
- independent dispute decision;
- replacement eligibility, cap and post-pilot treatment;
- provider-controlled introduction record;
- vendor pricing version for budget fit;
- privacy/recording evidence;
- pre-demo brief template and delivery proof;
- neutral attendance evidence;
- case-ID-to-invoice-to-cash traceability;
- complaint SOPs, named owner/deputy and a system of record.

None is operationally demonstrated.

---

## 6. Collateral and conversion critique

### Strengths

- Professional visual treatment and good contrast.
- Clear four-part qualification definition.
- Honest supplier-funding disclosure.
- Explicit CQC independence.
- Provider-interest principle is directionally right.

### Why it is not launch collateral

- External vendor pages and internal scripts are mixed into one four-page file.
- Every page says “NOT APPROVED”; sending it would destroy confidence.
- Removing warnings would expose eight unresolved claims.
- The vendor pitch is long and defensive before any proof exists.
- The market-comparison paragraph is the weakest section: unsupported, sweeping and easy for a sophisticated vendor to challenge.
- “Qualified demos, clearly defined” is stronger than the evidence system behind it.
- There is no vendor-specific proof: no example anonymised brief, acceptance pack, case study or measured result.
- The provider pitch overpromises a comprehensive procurement plan and vetted shortlist without a demonstrated method.

The launch materials should eventually be split into:

1. **Vendor discovery one-pager:** problem hypothesis, proposed evidence standard, invitation to co-design — no unsupported benchmarks or minimum commitment.
2. **Provider invitation:** narrow free procurement-readiness interview, transparent supplier-funded model, no “14 purchases” or “vetted” until proven.
3. **Internal SOP:** qualification rubric, privacy script, introduction control, evidence and complaints.
4. **Pilot agreement/order form:** acceptance, objections, replacement, price/tax, term, liability and data roles.

---

## 7. Recommended path: validation, not launch

### Stage 0 — mandatory foundations

Human/qualified review must first resolve:

- verified contracting entity, brand/IP authority and Gate 1;
- verified UK Country Pack/obligations register;
- CQC field inventory, OGL attribution and freshness rule;
- controller/data map, lawful bases, notices, recording choice, retention, sharing and suppression;
- VAT status and invoice entity;
- safe system of record, named operational owner/deputy and independent complaint reviewer.

No publication, outreach, recording, data sharing, pricing promise or invoice occurs before these gates.

### Stage 1 — buyer discovery (no fulfilment promise)

After lawful outreach approval, interview **5–8 CareTech vendors**, selected from the 11 researched CareTech prospects. Test:

- how they find newly registered providers now;
- value of registered vs application/pre-registration timing;
- precise definition of a billable qualified meeting;
- acceptable evidence and dispute window;
- whether they would pay £175 and commit to five;
- minimum account value and sales cycle needed for positive ROI;
- willingness to sign a conditional design-partner letter/order subject to provider validation.

**Pass threshold:** at least three genuine buyers independently accept substantially the same qualification/evidence definition; at least two indicate credible willingness to pay at or above the proposed pilot economics; one is willing to proceed subject to the provider-side test. Verbal politeness does not count.

### Stage 2 — provider problem interviews

Run **8–12 permission-led interviews** with recently registered providers, not disguised sales calls. Test:

- actual purchase categories and sequence;
- whether software has already been selected;
- willingness to spend 45 minutes;
- what written output is useful;
- comfort with supplier funding and introductions;
- data/recording preferences;
- whether they will state budget and 90-day intent.

Do not promise a vetted shortlist or send data to vendors.

**Pass threshold:** at least six complete interviews; at least half identify an unresolved near-term software decision; at least four want a supplier shortlist/introduction after clear disclosure; no serious trust/privacy complaint. These are proposed management thresholds, not industry facts.

### Stage 3 — synthetic operational dry run

With synthetic data, execute:

1. accepted case;
2. no-show and replacement;
3. vendor dispute;
4. privacy/recording complaint;
5. invoice and credit-note path.

Require fail-closed evidence and timed labour.

### Stage 4 — one-vendor controlled pilot

Only after the above passes and Human Gates 1/2:

- one vendor;
- no exclusivity;
- no 10% conversion commission;
- maximum five accepted demos, not a guaranteed minimum until supply is proven;
- explicit stop conditions;
- fully tracked labour, complaints, replacements, revenue, invoicing and cash;
- weekly independent QA sample.

### Invalidation criteria

Stop or redesign if any of these occur:

- no vendor accepts the evidence definition;
- fewer than two vendors show credible willingness to pay;
- fewer than half of provider interviews have an unresolved software decision;
- providers perceive the audit as disguised lead generation;
- current-source data cannot lawfully/accurately support outreach;
- forecast labour remains above contribution margin;
- privacy/recording incident, missing evidence or serious complaint;
- vendor disputes correlate with non-conversion rather than objective qualification failure.

---

## 8. Final recommendation to Henry

### Can this report/collateral be “our launch”?

**No.** It should not be published or used to sell the pilot. It is an internal design and risk-discovery artifact.

### Can this idea become the launch?

**Possibly, but only after a validation sprint proves three facts:**

1. providers still have the relevant purchase need at the stage CareGist can actually identify them;
2. vendors accept and will pay for CareGist's evidence-backed meeting definition;
3. fulfilment economics work with measured labour and dispute rates.

### Recommended human decision

- **Gate 1 decision now:** approve only a **zero/low-spend validation programme**, not the commercial pilot.
- **Do not approve:** publication, sending this PDF, price quotation, five-demo commitments, provider recording, supplier sharing, invoicing or “pre-registration” claims.
- **Return for Gate 2 only when:** legal/data/entity controls are verified, discovery thresholds are met, synthetic dry runs pass, current artifacts receive a hash-bound QA addendum, and the final separate external materials have independent review.

---

## Sources and evidence accessed 30 July 2026

### Authoritative external

- Care Quality Commission, **Using CQC data**, updated 2 July 2026: https://www.cqc.org.uk/about-us/transparency/using-cqc-data
- Care Quality Commission, **Register as a provider**, updated 25 June 2026: https://www.cqc.org.uk/guidance-regulation/registration/register-provider
- Information Commissioner's Office, **Direct marketing guidance**, latest updates 28 April 2026: https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/direct-marketing-guidance/
- Information Commissioner's Office, **Data sharing: a code of practice**: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/data-sharing-a-code-of-practice/
- UK legislation, **PECR regulation 21 — calls for direct marketing**: https://www.legislation.gov.uk/uksi/2003/2426/regulation/21
- UK legislation, **PECR regulation 22 — electronic mail for direct marketing**: https://www.legislation.gov.uk/uksi/2003/2426/regulation/22
- ASA/CAP, **CAP Code section 3 — Misleading advertising**: https://www.asa.org.uk/type/non_broadcast/code_section/03.html
- HMRC/GOV.UK, **Register for VAT — when to register**: https://www.gov.uk/register-for-vat
- The National Archives, **Open Government Licence v3.0**: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

### Internal evidence

- Four-page HTML/PDF/desktop/mobile artifacts and prior QA report under `artifacts/creative/`.
- QA/support synthesis and independent report under `artifacts/governance/`.
- `legal_risk_register.md`.
- `leads/caregist_customer_acquisition_playbook.md`.
- `leads/caregist_demand_prospects_100.csv` — 100 researched vendor prospects; 11 CareTech/software; all held pending verification/control.
- `leads/caregist_supply_prospects_100.csv` — 100 recently registered providers; all held pending verification/control.
- Finance/Admin + Customer Success red-team return, independently recalculated by the orchestrator.

## DELIVERABLE RETURN

- **What was produced:** Integrated launch-readiness assessment with claim screen, source research, economics, evidence-integrity review and controlled validation plan.
- **Assumptions:** No undocumented interviews, legal advice, approvals, systems or commercial commitments exist; labour scenarios are sensitivities, not observed costs.
- **Known weaknesses/open questions:** Search-provider billing failed, so research used direct authoritative URLs/browser retrieval and repository evidence. No qualified solicitor/accountant opinion was obtained. No external buyer/provider interviews were conducted because outreach is not approved.
- **Compliance flags:** RED — governance/entity, marketing/data, recording/sharing, terms/VAT, support and evidence controls. AMBER — plausible underlying market problem. GREEN — internal read-only analysis only.
- **Ready for independent QA:** Yes.
