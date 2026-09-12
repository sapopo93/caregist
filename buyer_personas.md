# Buyer Persona Dossiers

> **Superseded persona research — historical and non-operative.** The rankings,
> packages, prices, targeting directives, forecasts, and outreach recommendations
> below predate catalogue `2026-08` and are not current go-to-market authority.
> Use `docs/CAREGIST_MASTER_STRATEGY.md` and
> `deploy/stripe-price-manifest.json`.

## Ranking by Revenue Potential (2026)
| Rank | Persona | Estimated Annual Spend | Ease of Reach | Speed to Close | Priority |
|------|---------|------------------------|---------------|----------------|----------|
| 1 | Equipment & Vendor Suppliers | £4,800 – £24,000 | High | 14-30 days | 🔥 Attack first |
| 2 | Recruitment & Training Firms | £3,600 – £18,000 | High | 7-21 days | 🔥 Attack first |
| 3 | Real Estate & Lenders | £12,000 – £60,000 | Medium | 45-90 days | 🎯 Nurture |
| 4 | Insurance Brokers / Underwriters | £6,000 – £30,000 | Medium | 30-60 days | 🎯 Nurture |
| 5 | CQC Compliance Consultants | £2,400 – £12,000 | High | 14-30 days | 🎯 Nurture |
| 6 | Investors / Private Equity | £24,000 – £120,000 | Low | 90-180 days | 💎 Whale hunt |
| 7 | Local Authorities / ICBs | £8,000 – £40,000 | Low | 90-365 days | 💎 Whale hunt |

---

## Persona 1: Equipment & Vendor Suppliers
**Also known as:** Medical device reps, PPE distributors, care furniture sellers, hygiene services, laundry equipment, pharmacy delivery services.

### The Problem
New providers make their largest capital and supply decisions in the **first 30-60 days** after registration. Once a provider signs with Medline for gloves, or Rentokil for hygiene, or a pharmacy for blister packs, those contracts are locked in for 2-3 years. The vendor who contacts them in week 1 wins. The vendor who contacts them in month 4 is locked out.

### Current Workaround
Sales Development Reps (SDRs) manually check the CQC register every Monday morning, copy new names into a spreadsheet, and cold-call. This is:
- **Slow:** 3-5 days lag between registration and first contact.
- **Inaccurate:** No enrichment; SDRs don't know if it's a 6-bed domiciliary agency or a 60-bed nursing home.
- **Demoralising:** 90% of calls fail because the SDR lacks context.

### Decision-Maker Job Titles
- **Primary:** Sales Director, Business Development Manager, National Account Manager
- **User:** SDR / BDR, Inside Sales Executive
- **Budget Holder:** Managing Director (SMEs), VP Sales (enterprise vendors)

### Use Case Workflow
1. **08:00** — CQC Signal webhook fires: new provider "Rosewood Care Ltd" registered in Birmingham.
2. **08:05** — SDR opens Intelligence Dossier: 42-bed nursing home, leasehold property, former hotel conversion, 8 active job postings (hiring RNs and care assistants), director previously managed a Four Seasons site.
3. **08:15** — SDR calls the director. Pitch: *"Congratulations on Rosewood, Jane. I saw you're hiring RNs—we supply nurse-call systems and we've worked on three hotel-to-care conversions in the Midlands. Can I send you a specification?"*
4. **Result:** 40% meeting conversion rate (vs. 4% on cold blind lists).

### Budget & Willingness to Pay
- **SME supplier (£1-5M revenue):** £249-£749/mo for Signal Feed + 50 dossiers/mo.
- **Enterprise supplier (£20M+ revenue):** £2,499/mo for unlimited API + CRM sync + territory filters.
- **Trigger event:** New provider registrations are a **leading indicator** of Q3/Q4 sales pipeline. Easy ROI calculation: one £15k nurse-call system sale pays for 2 years of data.

### Messaging That Converts
> *"Your competitor's SDR checks CQC on Monday. You know on Friday."*
> *"Stop calling closed doors. Call providers that opened this morning."*

---

## Persona 2: Recruitment & Training Firms
**Also known as:** Care staffing agencies, registered manager recruitment specialists, mandatory training providers, NVQ/QCF assessors.

### The Problem
New providers have **urgent, time-bound hiring needs**. They need:
- A Registered Manager before CQC will allow them to open (legally required).
- RNs and care staff before first residents arrive.
- Mandatory training (Moving & Handling, Safeguarding, Fire Safety, MCA/DoLS) for compliance.

If a recruiter isn't in the door within 14 days, the provider has either:
- Hired directly (job boards), or
- Signed with a competitor agency.

Training providers face the same window: providers need staff trained *before* CQC inspection.

### Current Workaround
Recruiters spam every care home in a 20-mile radius via post or generic LinkedIn outreach. Response rates <1%. Training providers buy stale lists from industry magazines.

### Decision-Maker Job Titles
- **Primary:** Director of Business Development (agency), Franchise Owner (training network)
- **User:** Recruitment Consultant, Training Coordinator
- **Budget Holder:** Managing Director, Operations Director

### Use Case Workflow
1. **Day 0** — New domiciliary care provider registered in Manchester.
2. **Day 1** — Recruiter sees Dossier: director has no previous care management experience (high risk = high need for experienced Registered Manager). 12 active job posts = rapid scaling.
3. **Day 1 (afternoon)** — Recruiter calls director: *"Hi Sarah, congrats on the registration. I specialise in placing Registered Managers into new domiciliary agencies—I've placed 8 in Manchester in the last year. Are you still looking for an RM?"*
4. **Result:** Provider is relieved; search is delegated immediately.

### Budget & Willingness to Pay
- **Small agency:** £499/mo for Signal Feed + 30 dossiers.
- **Regional recruiter:** £1,499/mo for 200 dossiers + CRM integration.
- **Training franchise:** £749/mo for location-targeted alerts + bulk discount codes.

### Messaging That Converts
> *"New care providers don't know which recruiter to trust. Be the first name they hear."*
> *"They need a Registered Manager in 28 days. Do they know you exist?"*

---

## Persona 3: Real Estate & Lenders
**Also known as:** Care property investors, commercial agents (Savills, Knight Frank healthcare teams), development finance lenders, high-street banks with care-sector desks, bridging lenders.

### The Problem
New providers are **capital-hungry**. Hotel conversions cost £3k-£8k per bed. New-builds cost £150k-£250k per bed. Most new entrants need:
- Property finance (acquisition or development)
- Refurbishment loans
- Lease negotiations

The lender who relationships the provider **pre-registration** gets first look at the deal. But most lenders only discover providers 6-12 months later when they seek expansion capital.

### Current Workaround
Commercial agents rely on word-of-mouth or planning portal monitoring (which captures applications, not operational providers). Lenders buy LaingBuisson reports annually—too slow for deal origination.

### Decision-Maker Job Titles
- **Primary:** Healthcare Property Director (agent), Origination Director (lender), Relationship Manager (bank)
- **User:** Analyst, Surveyor
- **Budget Holder:** Investment Committee, Head of Healthcare Lending

### Use Case Workflow
1. **Week 1** — New provider registered; Dossier shows property acquired via 25-year lease from a known healthcare REIT.
2. **Week 2** — Lender's analyst sees: director has 2 previous care home exits (good track record), but company has no charges registered at CH yet (unencumbered = lendable).
3. **Week 3** — Lender invites director to coffee: *"We specialise in care-sector refinancing. When your initial development loan comes up for renewal, we'd love to show you our terms."*
4. **Result:** Relationship established 18 months before refinancing event.

### Budget & Willingness to Pay
- **Broker/Agent:** £1,499/mo for regional alerts + property tenure data.
- **Lender:** £4,999/mo for national coverage + survival index + white-label reports.

### Messaging That Converts
> *"The best care-sector deals never reach the open market. You find them at registration."*
> *"Our Survival Index flags which new providers will need expansion capital in 18 months."*

---

## Persona 4: Insurance Brokers / Underwriters
**Also known as:** Care-sector insurance specialists, commercial combined brokers, medical malpractice underwriters.

### The Problem
New providers need insurance **immediately**:
- Employers' liability (legally required)
- Public liability
- Professional indemnity
- Property and contents
- Cyber (increasingly required by CQC)

Many new entrants buy through comparison sites or generalist brokers and are underinsured. A specialist broker who intervenes early can design appropriate cover and retain the client for decades.

### Current Workaround
Brokers buy general "new business" lists or rely on local networking. No targeting by risk profile.

### Decision-Maker Job Titles
- **Primary:** Care Sector Lead (broker), Underwriter (insurer), Head of New Business
- **Budget Holder:** Branch Director, National Sales Manager

### Use Case Workflow
1. **Alert** — New 60-bed nursing home registered.
2. **Dossier** — Property is leasehold with cladding remediation notice (high property risk). Director has no previous nursing home experience (high PI risk). 15 job posts = rapid staff growth (high EL risk).
3. **Broker calls** with a tailored quote addressing each risk explicitly.
4. **Result:** Provider feels understood; broker wins against 3 generic competitors.

### Budget & Willingness to Pay
- **Regional broker:** £499-£999/mo.
- **National insurer:** £2,499/mo + per-quote data fee.

---

## Persona 5: CQC Compliance Consultants
**Also known as:** Care startup advisors, CQC application specialists, policy writers, mock inspection providers.

### The Problem
New providers are **terrified of their first inspection**. Many hire consultants to:
- Write policies and procedures
- Train staff on CQC Key Lines of Enquiry (KLOEs)
- Conduct mock inspections
- Prepare evidence folders

The consultant who reaches them in the first 30 days becomes their trusted advisor.

### Current Workaround
Consultants rely on referrals from accountants or property agents. Inconsistent pipeline.

### Decision-Maker Job Titles
- **Primary:** Founder / Director (consultancy)
- **User:** Associate Consultant

### Budget & Willingness to Pay
- **Sole trader consultant:** £249/mo for Signal Feed only.
- **Multi-consultant firm:** £749/mo for dossiers + local authority filtering.

---

## Persona 6: Investors / Private Equity
**Also known as:** Healthcare PE (EQT, Bridgepoint, Waterland), family offices, venture debt providers.

### The Problem
PE firms need **proprietary deal flow**. Everyone sees the same brokered deals. Newly registered providers are:
- Pre-revenue (or early revenue) = lower entry valuation
- Unbanked = less competition
- Often founded by operators with 1-2 sites and ambition to build a chain

### Current Workaround
PE firms pay LaingBuisson £15k+ pa for sector reports and hire origination analysts to manually track registrations. Inefficient and incomplete.

### Decision-Maker Job Titles
- **Primary:** Investment Director, Principal, Origination Lead
- **User:** Associate, Analyst
- **Budget Holder:** Partner, Investment Committee

### Budget & Willingness to Pay
- **Mid-market PE:** £12,000-£24,000 pa for Strategic Analytics + quarterly white-label reports.
- **Large-cap PE:** £50,000+ pa for custom data science, dedicated support, API into internal CRM.

### Messaging That Converts
> *"The next big care chain registered yesterday. We can tell you who."*

---

## Persona 7: Local Authorities & Integrated Care Boards (ICBs)
**Also known as:** Market Shaping Teams, Commissioning Managers, Public Health Intelligence.

### The Problem
LAs and ICBs must **monitor market capacity** and provider failure risk. A sudden wave of new domiciliary agencies may indicate oversupply and future price collapse. A cluster of nursing home registrations may reveal a developer's strategy.

### Current Workaround
LAs subscribe to benchmarking clubs or request ad-hoc reports from internal analysts. Slow and reactive.

### Decision-Maker Job Titles
- **Primary:** Market Shaping Manager, Commissioning Lead, Intelligence Analyst
- **Budget Holder:** Director of Adult Social Services, Chief Strategy Officer

### Budget & Willingness to Pay
- **Single LA:** £4,999-£9,999 pa (funded via benchmarking club or direct procurement).
- **ICB:** £15,000-£40,000 pa for regional analytics + risk modelling.

---

## Cross-Persona Messaging Matrix

| Message Element | Suppliers | Recruiters | Lenders | Insurance | Consultants | Investors | LAs |
|-----------------|:---------:|:----------:|:-------:|:---------:|:-----------:|:---------:|:---:|
| **Speed** | ✅ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ❌ |
| **Enrichment** | ⚠️ | ⚠️ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Risk Score** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Market Map** | ❌ | ❌ | ⚠️ | ❌ | ❌ | ✅ | ✅ |
| **Price Sensitivity** | Medium | Medium | Low | Medium | High | Low | High |

---

## Recommended Attack Order

### Phase 1 (Months 1-3): Land the High-Velocity SMBs
Target **Equipment Suppliers** and **Recruiters** first.
- Fast sales cycles (7-30 days).
- High volume.
- Perfect product-market fit for Signal Feed + Dossier.
- They become evangelists and case studies.

### Phase 2 (Months 4-6): Move Upmarket to Financial Services
Target **Insurance Brokers** and **Real Estate/Lenders**.
- Higher ACV.
- Require Survival Index and property enrichment to close.
- Longer sales cycle acceptable because Phase 1 revenue funds operations.

### Phase 3 (Months 7-12): Capture Institutions
Target **Investors**, **LAs**, and **ICBs**.
- Highest ACV.
- Require white-label reports, custom analytics, and procurement compliance.
- Use Phase 1-2 logos as social proof.
