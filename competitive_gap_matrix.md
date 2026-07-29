# Competitive Gap Matrix: CQC Data Vendor Landscape

## Executive Summary
The CQC data market is dominated by **incumbent research houses** selling annual subscriptions to broad, slow-moving datasets. **No competitor owns the "new registration" signal.** Our opportunity is to become the real-time intelligence layer for newly registered providers, exploiting a temporal gap that incuments ignore because their business models are built on static reports, not live signals.

---

## Competitor Profiles

### 1. LaingBuisson / CQC Insight
| Attribute | Detail |
|-----------|--------|
| **Pricing** | £3,500 – £15,000+ pa (institutional licences) |
| **Data Freshness** | Monthly / Quarterly report cycles |
| **Delivery** | PDF reports, Excel dashboards, analyst calls |
| **Target Segment** | Investors, corporates, local authorities, NHS |
| **Unique Feature** | Deep financial benchmarking (P&L ratios, fee rates, occupancy) |
| **Critical Gap** | No real-time new-provider feed. Data is 4-12 weeks stale. No director contact data. No pre-inspection scoring. |

**Why they won't copy us quickly:** LaingBuisson is a research publisher, not a SaaS/data platform. Their cost structure assumes high-price, low-volume analyst-led sales. A £249/mo API product would cannibalise their £8k reports and destroy their margin model.

---

### 2. Skills for Care
| Attribute | Detail |
|-----------|--------|
| **Pricing** | Free / grant-funded reports; paid workforce datasets (£500-£2,000) |
| **Data Freshness** | Annual (Workforce Intelligence) |
| **Delivery** | PDF, interactive dashboards, sector profiles |
| **Target Segment** | Workforce planners, local authorities, training providers |
| **Unique Feature** | National Minimum Data Set for Social Care (NMDS-SC); vacancy/turnover rates |
| **Critical Gap** | No provider-level commercial intelligence. No registration dates. No sales-contact data. |

**Why they won't copy us:** Public-interest mission; not a commercial intelligence vendor. They lack incentive and capability to build a real-time B2B sales feed.

---

### 3. Beauhurst
| Attribute | Detail |
|-----------|--------|
| **Pricing** | £6,000 – £20,000+ pa |
| **Data Freshness** | Daily (funding/events), weekly (company updates) |
| **Delivery** | SaaS platform, API, CRM integrations |
| **Target Segment** | Investors, government, corporates, advisors |
| **Unique Feature** | Investment and high-growth company tracking; grant data; equity rounds |
| **Critical Gap** | Care-sector granularity is weak. They track *companies*, not *CQC registrations*. A care provider can be registered for months before taking external funding, so Beauhurst misses the earliest signal. No inspection data. |

**Why they won't copy us quickly:** Beauhurst's ontology is "fundable companies," not "regulated care providers." Building CQC-specific enrichment (inspection ratings, service types, bed counts) is outside their core graph.

---

### 4. Endole / Companies House Data Vendors
| Attribute | Detail |
|-----------|--------|
| **Pricing** | £29 – £299/mo |
| **Data Freshness** | Real-time (CH filings) |
| **Delivery** | Browser SaaS, API, bulk CSV |
| **Target Segment** | Credit risk, sales prospecting, due diligence |
| **Unique Feature** | Company credit scores, director networks, filing alerts |
| **Critical Gap** | Zero CQC overlay. They don't know if a company is a care provider, a coffee shop, or a consultancy. No inspection data. No service-type classification. |

**Why they won't copy us:** Commoditised CH data market. Adding CQC enrichment requires sector expertise and regulatory data partnerships they don't have.

---

### 5. Care Home Directories (carehome.co.uk, Lottie, etc.)
| Attribute | Detail |
|-----------|--------|
| **Pricing** | Free to consumer; care homes pay for enhanced listings / lead gen |
| **Data Freshness** | User-generated / provider-updated (irregular) |
| **Delivery** | Website, consumer app |
| **Target Segment** | Families choosing care, providers seeking residents |
| **Unique Feature** | Consumer reviews, photos, pricing transparency |
| **Critical Gap** | B2B intelligence is non-existent. No registration dates. No director data. No API for vendors. |

---

### 6. Big 4 Consultancies (Deloitte, KPMG, PwC, EY) — Health & Social Care Practices
| Attribute | Detail |
|-----------|--------|
| **Pricing** | £500 – £2,000+ per hour; project-based |
| **Data Freshness** | Bespoke (pulled for each engagement) |
| **Delivery** | Board presentations, strategy papers, due diligence reports |
| **Target Segment** | NHS trusts, private equity, government |
| **Unique Feature** | Strategic narrative, M&A advice, policy interpretation |
| **Critical Gap** | They *consume* data; they don't *sell* it as a product. Their market intelligence is locked inside PowerPoint decks. No self-service API. |

---

### 7. Local Authority Benchmarking Clubs
| Attribute | Detail |
|-----------|--------|
| **Pricing** | £2,000 – £5,000 pa membership |
| **Data Freshness** | Quarterly |
| **Delivery** | Closed forums, shared spreadsheets, peer reports |
| **Target Segment** | Council commissioners, market-shaping teams |
| **Unique Feature** | Local context, peer comparison, commissioner intelligence |
| **Critical Gap** | Siloed by geography. No national real-time view. No vendor sales intelligence. |

---

## Gap Matrix Summary

| Capability | LaingBuisson | Skills for Care | Beauhurst | Endole | Care Directories | Big 4 | LAs | **Our Play** |
|------------|:------------:|:---------------:|:---------:|:------:|:----------------:|:-----:|:---:|:------------:|
| Real-time new registration alert | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ |
| CQC inspection data | ✅ | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Director contact enrichment | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ✅ |
| Pre-inspection risk score | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Survival index / predictive analytics | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ✅ |
| B2B sales workflow integration | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Care-sector granularity (beds, service type) | ✅ | ⚠️ | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ |
| Price point accessible to SMEs (<£500/mo) | ❌ | ✅ | ❌ | ✅ | N/A | ❌ | ❌ | ✅ |

**Legend:** ✅ Strong | ⚠️ Partial | ❌ Absent

---

## SWOT Analysis: Our Position

### Strengths
- **Temporal monopoly:** We are the only signal focused on *day-zero* registrations. By the time LaingBuisson writes about a provider, we have already sold the lead 12 times.
- **Agile cost structure:** No legacy print/research overhead. Pure SaaS margins.
- **Composable data:** We fuse CQC + CH + property + jobs; incumbents operate in silos.
- **Speed to market:** Can ship MVP in 30 days; incumbents need 12-18 months to pivot.

### Weaknesses
- **No brand recognition:** Buyers trust LaingBuisson for care-sector decisions.
- **Data dependency:** CQC could restrict API/bulk data or change licence terms.
- **Single-country:** UK-only; no geographic diversification.
- **Bootstrapped perception:** Without institutional backing, enterprise buyers may demand SOC 2 / ISO 27001 before signing.

### Opportunities
- **Adjacent sectors:** OFSTED (childcare), CQC-style regulators in Wales (CIW), Scotland (Care Inspectorate), Ireland (HIQA).
- **Upstream integration:** Partner with CRM vendors (Salesforce, HubSpot) as a native data provider.
- **Consultancy arbitrage:** Big 4 may become *customers* if we white-label our data for their due diligence decks.
- **Insurance:** Care-sector insurance is underserved; new-provider risk scores are valuable to underwriters.

### Threats
- **CQC builds its own API marketplace:** If CQC launches a paid developer tier with webhooks, our raw signal advantage erodes.
- **Free alternatives:** A motivated seller could manually check CQC registrations weekly and undercut us on price.
- **Data scraping crackdown:** If we rely on scraped enrichment (LinkedIn, job boards), legal risk escalates.
- **Economic downturn:** Care home closures reduce the flow of new registrations, shrinking our addressable market.

---

## Strategic Recommendation

**Do not compete with LaingBuisson on breadth. Destroy them on speed and specificity.**

Our entire go-to-market should revolve around one claim: *"We tell you about a new care provider before they have even unpacked their boxes."*

The incumbents sell **history**. We sell **now**.
