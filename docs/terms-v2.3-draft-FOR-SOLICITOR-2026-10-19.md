# CareGist: legal review and Business Terms v2.3 draft

## DRAFT FOR SOLICITOR REVIEW: NOT LEGAL ADVICE, NOT IN FORCE

Prepared 19 October 2026 for H-Kay Limited (company 10417923). It was written by an AI assistant from the repository, the live Terms (v2.2, in force 18 October 2026) and current public commentary on UK law. It is meant to make the solicitor's review faster, not to replace it. Nothing below should be published or relied on until a solicitor has approved it.

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

### B1. Personal data in the Brief, the preview and the directory (UK GDPR, DPA 2018, PECR). **High**

**Facts.** The Brief CSV carries the organisation name, location, postcode, service types, rating and CQC IDs. It has no emails or phone numbers. Where the provider is an individual or a partnership, the name together with a postcode is personal data. CareGist is the controller of that processing, and the buyer becomes a separate controller when it receives the CSV.

**Issues.**

1. **Lawful basis.** The basis is legitimate interests (Art. 6(1)(f)). This needs a written legitimate interests assessment (LIA) covering reuse of public CQC data for B2B research and supplying it to buyers. None is in the repository.
2. **Transparency (Art. 14).** The data is not collected from the individuals themselves. The "disproportionate effort" exemption in Art. 14(5)(b) may apply, but it requires a public privacy notice that explains the processing. Check that `/privacy` covers provider data reused from CQC, and does not only cover customer data.
3. **Right to object (Art. 21).** Individuals need a working route to object or be suppressed. The Terms and the privacy notice should describe it.
4. **Downstream marketing (PECR).** Buyers use the Brief to approach providers. Under PECR, **sole traders and partnerships are "individual subscribers"**: unsolicited marketing email or SMS to them needs prior consent, and the soft opt-in cannot apply to a buyer who has never dealt with them. Calls must be screened against TPS, or CTPS for corporates. Unsolicited email to companies ("corporate subscribers") is allowed with identification and an opt-out. Commentary reports that the **Data (Use and Access) Act 2025 raised maximum PECR fines to UK GDPR levels, with main commencement on 5 February 2026**. Confirm the commencement regulations for the PECR provisions.
5. **What the founder has already decided.** The public preview names only Organisation and NHS Body providers, never individuals or partnerships, and never names rating changes (19 October 2026). The Brief has no equivalent filter.

**Recommended actions.**
- Write an LIA and update the privacy notice for provider data.
- Add the buyer obligations in the draft §5 below.
- Choose one of two options: **(a)** exclude individual and partnership providers from the Brief, or **(b)** flag them in the CSV with a "PECR individual subscriber: consent rules apply" column. Option (b) keeps the product more useful. The solicitor should confirm which is defensible.

### B2. The Terms list products that are not for sale. **High**

v2.2 section 1 still describes Radar Regional, Radar National, Intelligence Feed Pilot and Embedded Enterprise, and section 6 describes Radar renewals. The founder's catalogue (`deploy/stripe-price-manifest.json`, catalogue `2026-09-two-product`) sells only the Brief and the Digest. Describing products that are not offered can mislead business buyers (Business Protection from Misleading Marketing Regulations 2008) and blurs which terms apply. **Action:** remove them, or move them to "not currently offered; any future offer will be on separate written terms".

### B3. Overclaims in the Terms and marketing. **High**

- "**CRM-ready** CSV dataset" in v2.2 §1 and on the Brief page conflicts with the sales manual, which says not to promise CRM compatibility. Change it to "CSV dataset".
- The Digest promises "newly published ratings". Production rating events currently lack effective dates (34,332 undated at review). Deliver from CQC report pages, or narrow the promise.
- The video and preview are marketing communications. **The CAP Code applies to business-to-business advertising too.** Keep substantiation on file for every factual claim. For example, "55,000+ locations" is supported by the live active count of 57,159 on 19 October. Keep "illustrative" labels on all sample rows.
- The CSV column `opportunity_score` may read as a prediction. The Terms disclaim predictive scores. Consider renaming it to `prioritisation_score`.

### B4. Liability and remedies (Unfair Contract Terms Act 1977). **Medium**

- v2.2 §10 caps liability for the Brief, but **sets no cap for the Digest**. Add one.
- "Indirect or consequential loss" does not reliably exclude **loss of profit or business**, which courts may treat as direct loss. Exclude these expressly if that is the intent.
- On standard business terms, caps must satisfy the UCTA reasonableness test. A cap equal to the fee is common for low-value research products, but ask the solicitor to confirm. Consider professional indemnity insurance and whether to quote it.

### B5. Contract formation, payment and invoices. **Medium**

Sales are made by written scope plus a payment link or invoice sent by hand. The Terms should say:
- when the contract forms (on CareGist's written confirmation of the agreed scope, or on payment)
- that the payment link or invoice incorporates these Terms
- when payment is due
- who the counterparty is

Invoices and payment pages must show the company name, number and registered office (Companies Act 2006 trading disclosures; Electronic Commerce Regulations 2002). The earlier Digest invoice draft had placeholder bank details. Statutory late-payment interest (Late Payment of Commercial Debts (Interest) Act 1998) applies by default; mention it or vary it.

### B6. CQC data licence and independence. **Medium**

CQC data is reused under the Open Government Licence v3.0. Required:
- the attribution statement
- no implied endorsement (v2.2 §2 covers this)
- no misrepresentation of the data

The site footer uses the generic OGL statement, and the internal risk register suggests "Contains CQC data © Care Quality Commission". **I could not confirm CQC's own required attribution wording.** Check CQC's open-data page and data.gov.uk, and use the exact text in the Terms, footer, PDF and CSV. The Brief CSV already has a `licence` column.

### B7. Naming providers: defamation and malicious falsehood. **Medium-low**

Accurate, dated CQC facts carry low risk. Risk rises with stale or wrong data, or unfair framing such as presenting a downgrade as a sales target. Mitigations already in place:
- quarantined CQC records are excluded from the preview, and their exclusion from the coverage check is open in PR #97
- freshness qualifies the figures shown
- rating changes are never named in public

**Add:** a published corrections and objection route for named providers (draft §2 below), with a response target.

### B8. Other points to confirm

- **VAT.** "No VAT added" is correct while H-Kay Limited is not VAT registered. Monitor taxable turnover against the registration threshold (£90,000 at the last change; confirm the current figure).
- **Processors and AI.** List sub-processors in the privacy notice and hold DPAs: Stripe, Resend, Vercel, Neon, Sentry, Twilio, and the TypeSafe/Jev API, which receives task context. Internal rules already forbid sending personal data to TypeSafe; reflect that in the notice.
- **Outbound calling (CRM/Twilio pilot).** TPS/CTPS screening, caller identification, and lawful basis for any recording. The outbound gate is currently closed.
- **Free Directory (consumers use it).** Consumer law applies here, including the DMCC Act 2024 unfair commercial practices rules in force since April 2025. If reviews are switched on, the fake-reviews rules apply. Cookie consent: the DUAA added exemptions for low-risk analytics cookies; check before relying on them.
- **DMCC subscription regime.** Not relevant now: there is no auto-renewal, the sales are B2B, and commencement is reported as spring 2027 at the earliest.

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
> (b) comply with the UK GDPR, the Data Protection Act 2018 and the Privacy and Electronic Communications Regulations, including screening calls against TPS and CTPS, and not sending unsolicited electronic marketing to individual subscribers (sole traders and partnerships) without the consent the law requires;
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
2. Is the Art. 14(5)(b) disproportionate-effort route available, given that a public privacy notice is published?
3. Are the §10 caps reasonable under UCTA for these products and values? Should professional indemnity insurance be in place before scaling sales?
4. What is CQC's exact required OGL attribution wording?
5. Is "organisations to investigate, not leads" enough to manage misrepresentation risk in sales copy, given the CAP Code?
6. Confirm the commencement of the DUAA's PECR changes and whether any B2B direct-marketing rule changed.
7. Should v2.3 drop the Free Directory claim and correction intake wording, given that verification intake is currently closed?

## Part E: after approval

1. Publish v2.3 on `/terms` with a new version string and in-force date. Record the approved text hash, as was done for the Brief.
2. Update `/privacy` (B1, B8), `/pricing` (Digest by enquiry only) and the Brief page ("CSV dataset", not "CRM-ready").
3. Apply the Brief data decision from B1, then update tests and the sales manual.
4. Keep this file as the record of what was reviewed and approved.

## Sources consulted (public commentary, not primary legislation)

- Data (Use and Access) Act 2025 commencement and PECR fines:
  - [Clifford Chance (Feb 2026)](https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2026/02/key-aspects-of-the-data--use-and-access--act-take-effect.html)
  - [Lewis Silkin (Feb 2026)](https://www.lewissilkin.com/insights/2026/02/09/uk-data-reform-becomes-reality-what-this-means-for-you-and-what-you-need-to-do-n-102mh5x)
  - [Bratby Law](https://bratby.law/duaa-takes-effect-ico-enforcement/)
  - [Clarkslegal](https://clarkslegal.com/?p=34608)
- DMCC Act subscription regime timing:
  - [Taylor Wessing (Apr 2026)](https://www.taylorwessing.com/de/insights-and-events/insights/2026/04/subscription-contracts)
  - [Osborne Clarke](https://www.osborneclarke.com/insights/uk-digital-markets-competition-and-consumers-act-subscription-contracts-regime-take-shape)
- CQC datasets listed under the OGL: [ODI certificate](https://certificates.theodi.org/en/datasets/3012/certificate)
