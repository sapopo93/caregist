# Stitch design and client deliverable review

Objective: assess the supplied designs and governance copy against the existing deliverable, and recommend the smallest useful transformation. Review only. No product, billing or production changes.

## Judgement

Keep the visual direction and the client delivery page. It makes the contents of the purchase tangible. Replace the unverified regulatory, staffing and financial claims. The designs currently describe a wider turnaround/M&A advisory service than the evidenced homecare account-research sample.

The deliverable should become a client-specific review pack: a clear scope summary, 25 account cards, source evidence, research questions and the existing downloadable files. A secure client page is a proposed implementation, not a capability verified by these HTML files. A styled standalone HTML/PDF pack would demonstrate the experience before building account access or a wider platform.

## Design assessment

Rendered the homepage, delivery page and commissioning form locally at the browser's existing 1280 x 720 viewport. Read all six HTML attachments and the governance document. Two commissioning attachments are byte-identical, leaving five distinct screen designs. Mobile layout was not visually tested.

- Keep the warm off-white background, dark primary actions, serif headings and restrained colour palette. These suit a research product. The download block on the delivery page communicates what the client receives directly.
- Strengthen the desktop layout. Current sections stretch across the viewport, producing long lines and oversized horizontal controls. Use a bounded reading width with an optional sidebar for scope and downloads.
- Increase essential text above the many 9–13px labels. Remove `user-scalable=no` and `maximum-scale=1.0` from the viewport settings so users retain browser zoom.
- Reduce repeated badges: “statutory”, “reconciled”, “SHA-256”, “verified”, “audit” and “guarantee” compete with the actual account information. Put technical provenance in expandable evidence details.
- Use one primary homepage action for the first sale: “View sample brief” or “Discuss your territory”. The current homepage sends users towards Radar and the free directory before explaining the paid deliverable.
- On desktop, move persistent navigation out of the mobile-style bottom bar. For client delivery, emphasise “Your brief”, “Accounts”, “Evidence” and “Downloads”.
- Prefer “Your selection criteria”, “Why included” and “What to check next” over “Strategic ICP Parameters”, “statutory catchment” and “exposure vectors”.

## Content corrections before external use

| Design statement | Evidence / contradiction | Correction |
|---|---|---|
| 371 records, 40 shortlisted, 25 ready | The current [data model](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/pack-data.json) has 353 locations, 329 providers and 25 shortlisted providers for Birmingham/Solihull domiciliary care. | Generate counts from the displayed scope. Do not relabel these as ICB, all-care or national figures. |
| Live “51 matches”, text says 40 | Commissioning JavaScript adds hard-coded checkbox weights and a bed-slider adjustment. It does not query provider records. | Label as a prototype or connect to actual filtered results. Care-type/boundary selection must affect the query. |
| “72h SLA”, “72 Hours” | Documented offer says three working days, with scope/start/delivery agreed. | Use three working days with an agreed start date. Do not claim an SLA was met for a prototype order. |
| £150 single-provider dossier / five provider audits | The two designs disagree. Neither matches the separately documented four-week Radar pilot. | Remove the new pilot from this offer pending an explicit new product decision. Preserve existing prospects' terms. |
| £159 VAT, £954 total; 14-day BACS; instant Stripe receipt | Arithmetic is correct if 20% applies, but the design is not evidence of VAT status, agreed credit terms or working checkout. | Use only confirmed tax treatment, terms and payment methods. |
| 16/25 Reg 12 breaches, 38% vacancies, 22–35% EBITDA discounts, 60-day acquisition window | No supporting evidence is supplied. The existing pack contains none of this analysis. | Remove. Such claims require separate primary research and an explicit method, not more persuasive wording. |
| Named providers, inspector quotations, safeguarding alerts, unstaffed shifts | No specific supporting reports are linked. Multiple “verified” links point to `#`; the homepage report link points to CQC's homepage. Provider IDs and bed counts also differ between screens. | Treat as unverified mock content. Use real pack records and exact source URLs, or clearly labelled fictional examples with no real identifiers. |
| “Dr. C. Howard”, clinical lead, digital signature, analyst team | No identity, qualifications, review or signature evidence is supplied. | Remove unverified identities and titles. Record the actual reviewer and review date only after review. |
| Daily 04:00 reconciliation, “zero lag”, statutory release time | The sample proves a dated local source route, not this daily operational service. CQC reports daily API updates, usually weekly directory and monthly filtered files, and known file delays. | Show source edition and actual checked time. A scheduled time alone is not a successful reconciliation. |
| New registration means leadership vacuum or manager absence | No such causal link is established. Missing ratings also do not establish lack of inspection. | State registration date and recorded rating status separately, then pose a qualification question. |
| September 12 registration called yesterday; September 18 urgent notice | Both dates are in the future relative to this 8 September review. | Populate dates from source data and calculate relative labels consistently. |
| Exactly 25 actionable targets guaranteed | Filter results need not contain 25 supported matches. | Check scope first. Disclose a shortfall instead of padding or claiming intent. |
| Financial distress index, churn telemetry, breach propensity, DCF-ready workbook | None appears in the existing verified pack. | Treat as a separate proposed product expansion with its own evidence and acceptance tests. |

The design's ICB list, boundaries, radius counts and national total were not independently validated here. They must not be presented as verified geographic coverage. The current sample uses local-authority boundaries.

## Governance document corrections

Keep independence, attribution, identifiers, source references and the separation of public facts from analysis. The uploaded guidance is proposed internal policy, not independent statutory approval.

1. SHA-256 is a file-integrity checksum. A checksum alone is not a digital signature, proof of factual truth, identity verification or legal defensibility. Retain full hashes in evidence details and use specific check labels.
2. Replace “100% defensibility” and “zero hallucination” guarantees with what was checked, when, against which source, and what remains unknown.
3. A missing breach citation should say “Not stated in the reviewed source”. “Unrated” and “No Published Rating” describe rating fields, not an absent breach finding.
4. Section 29 Warning Notices must not be described as automatic cancellation notices. Record the exact enforcement instrument and source, without inferring deregistration. [CQC Warning Notices](https://www.cqc.org.uk/guidance-regulation/providers/enforcement/warning-notices).
5. Avoid invented publication-delay estimates, but retain CQC's own relevant limitations. Suppressing a documented source limitation is not neutrality. [CQC Using CQC data](https://www.cqc.org.uk/about-us/transparency/using-cqc-data).
6. OGL permits commercial reuse subject to its conditions, but excludes personal data. A statement about OGL does not by itself resolve reuse of named managers or directors. Distinguish any licence on CareGist's original analysis from rights in upstream public information. [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
7. CQC provider IDs and Companies House company numbers are separate identifiers. Entity matches need evidence, and a company number is not available for every organisational form. Do not promise every record is cross-matched before doing that work.

## Smallest useful transformation

Adapt the delivery screen around the actual pack before rebuilding the homepage, directory or Radar.

1. Scope header: Birmingham/Solihull, domiciliary care, source editions 1 and 2 September, checked 8 September. Clearly label the example selection criteria.
2. Summary: 353 locations, 329 providers, 25 organisations to review. Explain the two review routes and service overlap.
3. Account cards: provider and representative location names/IDs, observed fact, why included under the buyer's criteria, suggested qualification question, uncertainty and exact CQC link. Display public facts separately from CareGist's interpretation.
4. Downloads: the existing workbook, two CSVs and four-page PDF. Display actual file contents and version; avoid “fulfilled” or “delivered” until those events occur.
5. Evidence details: source edition, checked timestamp, checks performed, coverage limitations and full file hash. Keep this accessible without overwhelming each card.

Example using an existing checked record: Advance Health Care UK Ltd has four qualifying local domiciliary locations under one provider ID. The research action is to coordinate account ownership before splitting branches. The question is whether supplier selection is central or local. Buying intent and staffing demand remain unknown. This is a useful source-linked account card without inventing a staffing crisis.

For a compliance-consultancy buyer, add a small evidence-backed report extract with exact findings and page references only after inspecting the actual inspection report. That would be new research. For an M&A buyer, financial valuation and ownership analysis require a separately scoped deliverable. Do not bundle either into the first offer by changing labels alone.

Price defence: the interface would make the work easier to understand and review. The £795 still depends on meaningful selection against an agreed buyer question. Better appearance does not establish willingness to pay or make unsupported intelligence real.

## Handoff

Files changed: this review only. Attachments and existing product files unchanged. Checks: all attachment text read, duplicate commissioning files hash-compared, commissioning script inspected, three screens rendered, current sample fields/counts inspected, official CQC/OGL guidance checked. No end-to-end order, download, security or responsive-device acceptance test was performed.

Unresolved issues affecting use: unsupported claims and demo interactions; buyer fit and scope; VAT/payment/Terms confirmation; operational claims and reviewer identity not established. These designs do not close the existing commercial release conditions.

Exact next action: build a local version of the delivery screen using `pack-data.json`, connect the real local downloads, remove unsupported labels, and review it with the chosen buyer against their account-selection task. This review does not claim that implementation is complete.

COMPLETE: no escalation needed. Applies to this design/content review only, not approval to publish or sell the expanded service.

## Attachment references

- [Governance guidance](/Users/user/.codex/attachments/df6f8bdd-5991-4450-91d8-2739844b0ba7/pasted-text.txt)
- [Commissioning form](/Users/user/.codex/attachments/13657de0-1cab-487e-9af6-a71af755637a/pasted-text.txt) and [identical duplicate](/Users/user/.codex/attachments/6ec80bbb-a679-4e22-a473-9d1251a5e6c0/pasted-text.txt)
- [Client delivery](/Users/user/.codex/attachments/1cf7a346-e488-4f52-b284-bcbae8ceb52d/pasted-text.txt)
- [Radar](/Users/user/.codex/attachments/ce12201b-6aa9-48da-8d53-f6a464348a33/pasted-text.txt)
- [Homepage](/Users/user/.codex/attachments/dc73e7c2-c871-4d57-99e0-ed3b8922a700/pasted-text.txt)
- [Directory](/Users/user/.codex/attachments/5a60d915-fa63-4ef1-83f9-9f4e405f3992/pasted-text.txt)
