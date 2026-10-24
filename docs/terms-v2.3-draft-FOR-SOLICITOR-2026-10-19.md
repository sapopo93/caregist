# CareGist: legal review and Business Terms v2.3 draft

## DRAFT FOR SOLICITOR REVIEW: NOT LEGAL ADVICE, NOT IN FORCE

Prepared 19 October 2026 for H-Kay Limited (company 10417923). It was written by an AI assistant from the repository and the live Terms (v2.2, in force 18 October 2026). Each legal point was checked on 19 October 2026 against the revised text on legislation.gov.uk, or the published licence text, and cites the provision it relies on (see Part F). It is meant to make the solicitor's review faster, not to replace it. Revised legislation can lag recent amendments, so the solicitor should confirm each provision is current. Nothing below should be published or relied on until a solicitor has approved it.

This draft supersedes two earlier ones:

- `docs/territory-brief-terms-draft-FOR-SOLICITOR-2026-09-09.md` drafted wording for instant self-serve checkout. That model is not current: the Brief is sold by scope confirmation followed by a payment link sent by hand. Park that draft.
- `docs/weekly-digest-pilot-terms-draft-FOR-SOLICITOR-2026-10-01.md`. Its wording is now in v2.2.

---

## Part A: what is being sold, and to whom

| Product | Price | How it is sold | Status |
| --- | --- | --- | --- |
| Territory Opportunity Brief | £745 once, no VAT added | Scope agreed in writing, then a Stripe payment link sent by hand. PDF, CSV and source manifest delivered within about 3 working days. | On sale, human-led |
| Weekly Digest pilot | £150 once for four weekly digests | Invoice or payment link sent by hand | **On sales hold** until terms and fulfilment are approved. Enquiry only. |
| Free Directory | £0 | Public website | Live |
| Territory preview (free) | £0 | Panel on `/pricing/territory` | Built, switched off (PR #96) |

Buyers are businesses that sell to, advise or invest in care providers. The paid services are business-to-business, and v2.2 already says they are not for personal use. The **data subjects** are CQC-registered providers. Most are companies, but **4,304 are registered as individuals and 7,857 as partnerships**, according to the directory export's `ownership_type` field.

---

## Part B: legal review, highest risk first

### B1. Personal data in the Brief, the preview and the directory. **High**

**Facts.** The Brief CSV carries the organisation name, location, postcode, service types, rating and CQC IDs. It has no emails or phone numbers. Where the provider is an individual or a partnership, the name together with a postcode is personal data. CareGist is the controller of that processing, and the buyer becomes a separate controller when it receives the CSV.

**The Open Government Licence does not cover this data.** OGL v3.0, "Exemptions": "This licence does not cover: personal data in the Information". Reusing individual and partnership providers' details therefore rests on UK GDPR, not on the CQC licence.

**Issues, with the provisions they rest on.**

1. **Lawful basis: UK GDPR Art. 6(1)(f), legitimate interests.** Art. 6(11)(a), in force 5 February 2026 by the Data (Use and Access) Act 2025, lists "processing that is necessary for the purposes of direct marketing" as an example of processing that may be a legitimate interest. A balancing test is still required. Write a legitimate interests assessment; none is in the repository.
2. **Transparency: UK GDPR Art. 14.** The data is not collected from the individuals. **Art. 14(5)(b) was omitted on 5 February 2026** (DUAA 2025 s. 77). The exemption is now **Art. 14(5)(e)**: providing the information individually "is impossible or would involve a disproportionate effort". Under **Art. 14(6)**, that depends on "the number of data subjects, the age of the personal data and any appropriate safeguards". **Art. 14(7)** requires "appropriate measures", including "making the information available publicly". In practice this means a public privacy notice that covers provider data reused from CQC.
3. **Right to object: UK GDPR Art. 21.** Under Art. 21(1), processing based on 6(1)(f) must stop unless there are "compelling legitimate grounds". Under Art. 21(2)–(3), an objection to direct marketing is absolute, and the data "shall no longer be processed for such purposes". Publish a suppression route.
4. **Buyers' marketing: PECR (SI 2003/2426).**
   - **Reg. 2(1):** "individual" "means a living individual and includes an unincorporated body of such individuals". This covers sole traders and English and Welsh partnerships. A "partnership in Scotland" is a **corporate subscriber**.
   - **Reg. 22:** marketing email or SMS to individual subscribers needs prior consent. The soft opt-in in reg. 22(3) only applies to the sender's own customer relationship, "similar products and services only", so a buyer using a CareGist list cannot rely on it.
   - **Reg. 21(1)(b) and reg. 26:** no unsolicited marketing calls to numbers on the preference register. The register covers corporate subscribers too (reg. 26(1A), (2A)), which is the CTPS.
   - **Penalties:** since 5 February 2026, the new PECR Schedule 1 (substituted by DUAA 2025 Sch. 13, commenced by SI 2026/82) applies DPA 2018 s. 157(2)(a) to breaches of regs 21, 22 and others. Those therefore carry the **higher maximum amount**: £17,500,000 or 4% of worldwide annual turnover, whichever is higher (DPA 2018 s. 157(5)).
5. **What the founder has already decided.** The public preview names only Organisation and NHS Body providers, never individuals or partnerships, and never names rating changes (19 October 2026). The Brief has no equivalent filter.

**Recommended actions.**
- Write the legitimate interests assessment, and extend `/privacy` to cover provider data (Art. 14(7)).
- Add the buyer obligations in the draft §5 below.
- Choose one: **(a)** exclude individual and partnership providers from the Brief, or **(b)** flag them in the CSV with a "PECR individual subscriber: consent rules apply" column. The solicitor should confirm which is defensible.

### B2. The Terms list products that are not for sale. **High**

v2.2 section 1 still describes Radar Regional, Radar National, Intelligence Feed Pilot and Embedded Enterprise, and section 6 describes Radar renewals. The founder's catalogue (`deploy/stripe-price-manifest.json`, catalogue `2026-09-two-product`) sells only the Brief and the Digest. **Business Protection from Misleading Marketing Regulations 2008 (SI 2008/1276) reg. 3** prohibits misleading advertising to traders. Under reg. 3(3), misleadingness is judged by reference to a product's characteristics, including its **availability**, its price and the **conditions of supply**. Describing products that are not available also blurs which terms apply. **Action:** remove them, or move them to "not currently offered; any future offer will be on separate written terms".

### B3. Overclaims in the Terms and marketing. **High**

- "**CRM-ready** CSV dataset" in v2.2 §1 and on the Brief page conflicts with the sales manual, which says not to promise CRM compatibility. Change it to "CSV dataset".
- The Digest promises "newly published ratings". Production rating events currently lack effective dates (34,332 undated at review). Deliver from CQC report pages, or narrow the promise.
- The same reg. 3 of the 2008 Regulations applies to the video and the preview. The **CAP Code** (self-regulatory, enforced by the ASA, not legislation) also applies to business-to-business advertising. Keep substantiation on file for every factual claim. For example, "55,000+ locations" is supported by the live active count of 57,159 on 19 October. Keep "illustrative" labels on all sample rows.
- The CSV column `opportunity_score` may read as a prediction. The Terms disclaim predictive scores. Consider renaming it to `prioritisation_score`.

### B4. Liability and remedies: Unfair Contract Terms Act 1977. **Medium**

- **s. 2(1):** liability for death or personal injury caused by negligence cannot be excluded. **s. 2(2):** other negligence liability can be excluded only "in so far as the term ... satisfies the requirement of reasonableness".
- **s. 3:** where the customer deals on CareGist's "written standard terms of business", exclusions of liability for breach, or of the right to perform "substantially different" from what was expected, must be reasonable. The Terms are standard terms.
- **s. 11(1):** a term is reasonable if it was "fair and reasonable" given what the parties knew when contracting. **s. 11(4):** for a cap at a specified sum, the court looks at "the resources which he could expect to be available" and "how far it was open to him to cover himself by insurance". **s. 11(5):** CareGist bears the burden of proof.
- v2.2 §10 caps liability for the Brief but **sets no cap for the Digest**. Add one.
- "Indirect or consequential loss" does not reliably exclude **loss of profit**, which courts can treat as direct loss. Exclude it expressly if that is the intent.
- Because of s. 11(4), consider professional indemnity insurance. Holding cover strengthens the case that a cap is reasonable.

### B5. Contract formation, payment and disclosures. **Medium**

Sales are made by a written scope plus a payment link or invoice sent by hand. The Terms should say when the contract forms, that the link or invoice incorporates the Terms, when payment is due, and who the counterparty is.

- **Companies Act 2006 and the Trading Disclosures Regulations (SI 2015/17):**
  - **reg. 24:** the registered name on business letters, order forms, invoices and "other demands for payment", and "on its websites".
  - **reg. 25:** on letters, order forms and websites, the part of the UK where the company is registered, its registered number and its registered office address.
  - Check payment links, invoices and email signatures.
- **Electronic Commerce (EC Directive) Regulations 2002, reg. 6(1):** the website must make the following "easily, directly and permanently accessible": name, geographic address, email, the register entry and number, and a VAT number if registered. The Terms page has these; check that the site footer does too.
- **Late Payment of Commercial Debts (Interest) Act 1998, s. 1:** statutory interest is implied into qualifying business contracts. The Terms may refer to it, or vary it under Part II.

### B6. CQC data licence and independence. **Medium**

OGL v3.0 imposes two conditions:
- **Attribution:** "acknowledge the source of the Information" by including the attribution statement the provider specifies. Where none is given, the default is "Contains public sector information licensed under the Open Government Licence v3.0." Link to the licence where possible.
- **Non-endorsement:** the licence gives no right to use the Information "in a way that suggests any official status" or endorsement.

OGL v3.0 has **no separate "do not mislead" condition**; misleading-marketing risk sits under the 2008 Regulations (B2). It also **excludes personal data** (B1). The site footer uses the default statement. **I could not find a CQC-specified statement.** If CQC specifies one on its open-data or reuse page, use it in the Terms, footer, PDF and CSV. The Brief CSV already has a `licence` column.

### B7. Naming providers: defamation. **Medium-low**

**Defamation Act 2013, s. 1(1):** a statement is not defamatory unless it "has caused or is likely to cause serious harm" to reputation. **s. 1(2):** for a body trading for profit, harm is not serious "unless it has caused or is likely to cause the body serious financial loss". Truth is a defence under s. 2.

Accurate, dated CQC facts carry low risk. Risk rises with stale or wrong data, or framing that implies something the record does not say. Mitigations already in place:
- quarantined records are excluded from the preview, with the coverage check fix open in PR #97
- freshness qualifies the figures shown
- rating changes are never named in public

**Add:** a published corrections and objection route (draft §2 below).

### B8. Other points

- **VAT:** "No VAT added" is correct while H-Kay Limited is not registered. **VAT Act 1994, Sch. 1 para. 1(1)(a):** the registration threshold is **£90,000** of taxable supplies in a rolling 12 months (SI 2024/307, from 1 April 2024). Monitor turnover against it.
- **Processors and AI:** UK GDPR Art. 28 requires a contract with each processor. Hold DPAs with Stripe, Resend, Vercel, Neon, Sentry and Twilio, and with TypeSafe/Jev, which receives task context. Internal rules forbid sending personal data to TypeSafe; say so in the privacy notice.
- **Outbound calling (CRM/Twilio pilot):** PECR reg. 21 and the reg. 26 register (TPS and CTPS), caller identification, and a lawful basis for any recording. The outbound gate is currently closed.
- **Free Directory:** consumers use it. **DMCC Act 2024 Sch. 20 para. 13** (in force 6 April 2025, SI 2025/272) bans submitting or commissioning fake or concealed-incentive consumer reviews. Para. 13(3) also requires reasonable steps to prevent and remove them. This matters if reviews are switched on.
- **DMCC subscription regime (Part 4, Ch. 2):** not relevant. Under s. 254 a subscription contract is "a contract between a trader and a consumer"; most of the chapter is still prospective; and CareGist products neither renew automatically nor sell to consumers.

---

## Part C: proposed v2.3 wording, by section

Sections not shown keep the v2.2 wording, apart from removing references to retired products (B2).

### §1 Products and scope (replace)

> **Free Directory:** public search of CQC-registered locations, with source dates and links to the official CQC record.
>
> **Territory Opportunity Brief:** a one-off research pack for an England territory agreed in writing. It contains a shortlist of 25 to 50 distinct provider organisations to investigate, a stated factual reason for each, a CSV dataset, a three to five page summary, and a source manifest with links and observation dates. The written scope confirmation is the order form for the purchase and prevails over general statements on this site.
>
> **Weekly Digest pilot** *(available by enquiry only)*: four weekly digests for one agreed England region, reporting new registrations and newly published CQC ratings in that region, each linked to the CQC record and dated. It is not a subscription, dashboard, API or alert service. The written confirmation of region, start date and delivery dates is the order form.
>
> CareGist does not currently offer any other paid service. Any future service will be offered on separate written terms.
>
> Outputs identify organisations to investigate. They are not leads, and they do not state or imply need, budget, vacancies, contract timing or intent to buy.

### §2 Source data and evidence (add at end)

> **Corrections and objections.** A provider named in CareGist output, or a person whose details appear in it, may ask us to correct, update or stop using that information by emailing legal@caregist.co.uk. We aim to respond within 10 working days. Where the information is accurate and we have a lawful basis to continue, we will explain why. Requests about personal data are handled under our Privacy Notice.

### §5 Customer data and outcomes: new paragraphs (add)

> **Personal data in outputs.** Some providers are registered with CQC as individuals or partnerships, so outputs may contain personal data. Each customer is an independent controller of any personal data it receives from CareGist. The customer must:
> (a) have its own lawful basis for any use;
> (b) comply with the UK GDPR, the Data Protection Act 2018 and the Privacy and Electronic Communications (EC Directive) Regulations 2003, including screening calls against TPS and CTPS, and not sending unsolicited electronic marketing to individual subscribers (sole traders and partnerships) without the consent the law requires;
> (c) honour objections and opt-outs promptly; and
> (d) not use outputs to profile, or take decisions about, an individual's suitability, creditworthiness or employment.
>
> **Buyer's own communications.** The customer is solely responsible for the content, lawfulness and targeting of any communication it sends to a provider. Outputs must not be presented to a provider as coming from or endorsed by CQC.

### §6 Fees, payment and cancellation (replace)

> **Formation.** A contract for a paid product forms when CareGist confirms the agreed scope in writing and the customer pays the payment link or invoice that refers to these Terms.
>
> **Prices.** Prices are as stated in the written scope or invoice. H-Kay Limited is not currently registered for VAT, and no VAT is added. Payment is due in full before work begins. Card payments are processed by Stripe; H-Kay Limited does not store full card details. Unpaid invoices accrue statutory interest under the Late Payment of Commercial Debts (Interest) Act 1998.
>
> **Territory Opportunity Brief.** £745. The customer may cancel by email before work begins and receive a full refund. Once work has begun on the agreed bespoke Brief, the fee is non-refundable, except where CareGist fails to deliver the agreed scope or a remedy cannot lawfully be excluded. If a source problem after payment prevents delivery of the agreed scope, CareGist will offer a revised date or an alternative scope, or a full refund if neither is agreed.
>
> **Weekly Digest pilot.** £150 for four digests, available by enquiry. *(Keep the v2.2 cancellation, late-delivery and no-renewal wording unchanged.)*

### §9 Intellectual property and licence (replace the customer-licence sentence)

> For a one-off product, the customer receives a non-exclusive, non-transferable, perpetual licence to use the outputs for its internal business purposes. Resale, publication, redistribution, sublicensing or bulk sharing of outputs requires CareGist's written agreement. Outputs must keep the supplied CQC and Open Government Licence attribution *(exact CQC wording to be confirmed, see B6)* and the CareGist source metadata.

### §10 Disclaimers and liability (replace the liability paragraph)

> Nothing in these Terms limits liability for death or personal injury caused by negligence, for fraud or fraudulent misrepresentation, or for any other liability that cannot lawfully be limited.
>
> Subject to that, neither party is liable for: loss of profit, revenue, business, contracts or anticipated savings; loss or corruption of data; loss of goodwill; or any indirect or consequential loss.
>
> CareGist's total liability arising from a product is limited to the fee paid for that product: £745 for a Territory Opportunity Brief, and £150 for a Weekly Digest pilot. A signed agreement may set a different limit.

---

## Part D: questions for the solicitor

1. Is legitimate interests a sound basis for supplying individual and partnership provider names to B2B buyers? Should the Brief exclude them (B1 option a) or flag them (option b)?
2. Is the Art. 14(5)(e) disproportionate-effort route available (Art. 14(6) factors), given a public privacy notice under Art. 14(7)?
3. Are the §10 caps reasonable under UCTA ss. 3 and 11, particularly the insurance factor in s. 11(4)? Should professional indemnity insurance be in place before scaling sales?
4. Does CQC specify an OGL attribution statement, or does the default statement apply?
5. Is "organisations to investigate, not leads" enough to manage misrepresentation risk in sales copy, given the CAP Code?
6. Confirm that the revised texts relied on (PECR regs 2, 21, 22, 26 and Sch. 1; UK GDPR Arts 6, 14, 21) reflect all amendments in force, and whether any further DUAA commencement affects B2B marketing.
7. Should v2.3 drop the Free Directory claim and correction intake wording, given that verification intake is currently closed?

## Part E: after approval

1. Publish v2.3 on `/terms` with a new version string and in-force date. Record the approved text hash, as was done for the Brief.
2. Update `/privacy` (B1, B8), `/pricing` (Digest by enquiry only) and the Brief page ("CSV dataset", not "CRM-ready").
3. Apply the Brief data decision from B1, then update tests and the sales manual.
4. Keep this file as the record of what was reviewed and approved.

## Part F: provisions relied on (checked 19 October 2026)

| Instrument | Provision | Used in |
| --- | --- | --- |
| UK GDPR | Art. 6(1)(f), 6(11)(a) | B1 |
| UK GDPR | Art. 14(5)(e), 14(6), 14(7) (14(5)(b) omitted 5 Feb 2026) | B1 |
| UK GDPR | Art. 21(1)–(3) | B1 |
| UK GDPR | Art. 28 | B8 |
| PECR, SI 2003/2426 | reg. 2(1) "individual", "corporate subscriber" | B1 |
| PECR | regs 21, 22 (incl. 22(3)), 26 | B1, B8 |
| PECR | Sch. 1 (substituted by DUAA 2025 Sch. 13, SI 2026/82) | B1 |
| Data Protection Act 2018 | s. 157(2)(a), 157(5) | B1 |
| Data (Use and Access) Act 2025 | ss. 77, 109–116, Sch. 13 | B1 |
| Unfair Contract Terms Act 1977 | ss. 2, 3, 11 | B4 |
| Business Protection from Misleading Marketing Regs 2008, SI 2008/1276 | reg. 3 | B2, B3 |
| Company, LLP and Business Names (Trading Disclosures) Regs 2015, SI 2015/17 | regs 24, 25 | B5 |
| Electronic Commerce (EC Directive) Regs 2002, SI 2002/2013 | reg. 6(1) | B5 |
| Late Payment of Commercial Debts (Interest) Act 1998 | s. 1, Part II | B5 |
| Defamation Act 2013 | ss. 1, 2 | B7 |
| Value Added Tax Act 1994 | Sch. 1 para. 1(1)(a) (SI 2024/307) | B8 |
| Digital Markets, Competition and Consumers Act 2024 | Sch. 20 para. 13; Part 4 Ch. 2, s. 254 | B8 |
| Open Government Licence v3.0 | Attribution, Non-endorsement, Exemptions | B1, B6 |

Sources: [legislation.gov.uk](https://www.legislation.gov.uk/) revised texts at the provisions above, and the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

## Background commentary (superseded by Part F where they differ)

- Data (Use and Access) Act 2025 commencement and PECR fines:
  - [Clifford Chance (Feb 2026)](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2026/02/key-aspects-of-the-data--use-and-access--act-take-effect.html)
  - [Lewis Silkin (Feb 2026)](https://www.lewissilkin.com/insights/2026/02/09/uk-data-reform-becomes-reality-what-this-means-for-you-and-what-you-need-to-do-n-102mh5x)
  - [Bratby Law](https://bratby.law/duaa-takes-effect-ico-enforcement/)
  - [Clarkslegal](https://clarkslegal.com/?p=34608)
- DMCC Act subscription regime timing:
  - [Taylor Wessing (Apr 2026)](https://www.taylorwessing.com/de/insights-and-events/insights/2026/04/subscription-contracts)
  - [Osborne Clarke](https://www.osborneclarke.com/insights/uk-digital-markets-competition-and-consumers-act-subscription-contracts-regime-take-shape)
- CQC datasets listed under the OGL: [ODI certificate](https://certificates.theodi.org/en/datasets/3012/certificate)
