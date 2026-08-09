# CareGist full-portfolio revenue and unit-economics assessment

**Date:** 2026-07-30
**Scope:** CareGist UK/England portfolio only. Read-only assessment. No pricing, contract, spend, invoice, or external-contact changes.

## Executive view

CareGist has a **credible sub-£1m ARR path** in the current live portfolio, but **£1m recognised revenue within 12 months is not credible from £0 on the current evidence**.

The strongest commercial lines are:

1. **Recurring data subscriptions** — live, clear pricing, highest confidence.
2. **Provider visibility** — live, recurring, and potentially the largest supply-side scale lever.
3. **One-off filtered lead packs / datasets** — visible on the site, but manual and operationally constrained.
4. **Enterprise/API / strategic reports** — potentially high ACV, but currently custom and unproven as repeatable demand.
5. **Qualified introductions** — should be treated as a gated premium experiment, not a core forecast line.

The key distinction is this:

- **£1m ARR exit run-rate** = month-12 monthly recurring revenue of roughly **£83k**.
- **£1m recognised revenue in the year** = much harder, because a ramp from zero means only part-year revenue is recognised.
- Under a simple linear ramp from zero to the exit run-rate, **£1m recognised revenue requires ~£166.7k month-12 MRR** or equivalent one-off/enterprise revenue to bridge the gap.

## Evidence used

- `pricing-snapshot.md` live prices:
  - Alerts Pro £49/mo
  - Data Starter £99/mo
  - Data Pro £199/mo
  - Data Business £499/mo
  - Provider Pro Listing £99/location/mo
  - Sponsored Listing £149/location/mo
  - Enterprise custom / contact
- `product_specification.md`
  - Signal Feed maps to live Starter/Pro/Business feed capabilities.
  - Intelligence Dossier, dossier API/credits, Intelligence tier, and Strategic Analytics are roadmap concepts unless a later release note says otherwise.
- `buyer_personas.md`
  - Supplier/recruitment/lender/insurer/LA/investor personas and indicative willingness-to-pay.
- `artifacts/launch-assessment/caregist-launch-scrutiny-report-2026-07-30.md`
  - Qualified introductions / attended meetings are **not validated** as a core commercial line.
- `artifacts/launch-assessment/caregist-controlled-launch-plan-2026-07-30.md`
  - The qualified-demo service is explicitly framed as a narrow validation programme, not approved launch pricing.
- `docs/va-sales-product-spec.md`
  - Filtered lead lists and dataset packs are visible on the live website and fulfilled manually while demand is being validated.
- `technical / repository evidence`
  - 55,818 active providers referenced in the technical completion report.
  - 340 average new registrations/month from the pricing snapshot.
  - 56,742 matching new-registration ledger events cited in the task brief.

## Portfolio classification

| Line | Status | Commercial role | Notes |
|---|---|---|---|
| Alerts Pro / Data Starter / Data Pro / Data Business | **Live** | Core recurring data subscription ladder | Best evidence and cleanest MRR engine |
| Provider Pro Listing / Sponsored Listing | **Live** | Supply-side recurring monetisation | Potentially large scale if claim-to-paid conversion works |
| Filtered lead pack / full dataset / regional pack | **Live route, manual fulfilment** | One-off bridge revenue | Website route exists; price not public, so modelled below |
| API / enterprise custom | **Live contact path** | High-ACV custom deals | Pricing is custom; demand and cycle time unproven |
| Strategic reports / market maps / data room | **Roadmap or custom enterprise** | Highest ACV, lowest cadence | Not a repeatable self-serve SKU yet |
| Qualified introductions / attended meetings | **Unproven premium service** | Potential high-margin experiment | Do not underwrite the business on this line |

## Demand-side and supply-side capacity

Two capacity anchors matter:

- **Supply of events:** 340 new registrations/month ≈ **4,080/year**.
- **Installed provider base:** **55,818 active providers**.

That means CareGist is **not supply constrained**. The bottleneck is converting attention into paid usage.

### What it takes to reach £1m ARR on each live recurring line alone

| Product line | Monthly price | Customers / locations needed for £1m ARR |
|---|---:|---:|
| Alerts Pro | £49 | 1,701 |
| Data Starter | £99 | 842 |
| Data Pro | £199 | 419 |
| Data Business | £499 | 168 |
| Provider Pro Listing | £99/location | 842 locations |
| Sponsored Listing | £149/location | 560 locations |
| Enterprise custom retainer | £5,000/mo assumption | 17 accounts |

### Provider visibility share of base needed

At the live provider base of 55,818:

- **Provider Pro Listing**: 842 locations = **1.51%** of provider base.
- **Sponsored Listing**: 560 locations = **1.00%** of provider base.
- A blended £119/location/mo average would need about **700 paid locations**, or **1.25%** of base.

That is **numerically feasible** but **behaviourally unproven**.

## Scenario model

### Modelling assumptions

To keep the model rigorous but bounded, I used:

- Live prices for subscriptions and provider visibility.
- Explicit assumptions for uncatalogued one-off products:
  - **Filtered lead pack:** £250 average
  - **Dataset / regional pack:** £875 average
  - **Strategic report:** £7,500 average
  - **Qualified intro:** £175 per accepted intro, from launch materials, but not treated as a core forecast line
- Linear ramp from zero to year-end recurring MRR for recognised revenue.
- One-off revenue recognised in the year when delivered.

### Scenario inputs and outcomes

| Scenario | Alerts | Starter | Pro | Business | Provider Pro locations | Sponsored locations | Enterprise retainers | Lead packs / year | Dataset packs / year | Strategic reports / year | Year-end MRR | ARR exit run-rate | Recognised recurring revenue in year* | One-off revenue in year | Total recognised revenue in year |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Conservative / evidence-constrained | 20 | 35 | 15 | 5 | 25 | 5 | 0 | 24 | 3 | 3 | £13.1k | £157.7k | £78.9k | £31.1k | **£110.0k** |
| Base / founder-led | 50 | 90 | 35 | 15 | 100 | 20 | 1 | 72 | 12 | 6 | £43.7k | £524.3k | £262.1k | £73.5k | **£335.6k** |
| Stretch / aggressive | 100 | 180 | 70 | 30 | 300 | 80 | 3 | 144 | 36 | 12 | £108.2k | £1.299m | £649.4k | £157.5k | **£806.9k** |

\*Assumes a simple linear ramp from £0 to year-end MRR.

### Interpretation

- The **stretch scenario crosses £1m ARR exit run-rate**.
- But even that stretch case only recognises about **£807k** in year-one revenue under a linear ramp.
- So **£1m ARR exit run-rate is materially easier than £1m recognised revenue**.
- Under this model, the year-one gap to £1m recognised revenue is about **£193k** even after a strong stretch.

### What bridges the year-one gap?

At the stretch case, the remaining ~£193k would require roughly one of:

- **26 more strategic reports** at £7,500 each, or
- **4 more enterprise retainers** at £5,000/mo, or
- a much steeper sales curve than the model assumes.

That is why the year-one **revenue** goal is less credible than the year-end **run-rate** goal.

## Gross-margin constraints by line

### Recurring subscriptions and provider visibility

- Likely highest direct gross margin because delivery is largely automated.
- Real constraint is not raw margin, but:
  - support load,
  - churn,
  - enrichment/data acquisition cost,
  - and sales cost.
- Practical direct gross margin target: **85%+**.

### Lead packs and dataset packs

- Margin is good only if manual curation stays disciplined.
- Practical direct gross margin target:
  - **60–80%** for lead packs,
  - **70–85%** for dataset packs,
  depending on manual hours and data sourcing.

### Strategic reports / custom analytics

- High ACV but analyst-heavy.
- Good margins are possible if the report is templated and data assembly is partly automated.
- Practical direct gross margin target: **50–70%**.

### Qualified introductions

At **£175 per accepted intro**:

- 50% gross margin leaves **£87.50** for direct cost.
- At a fully loaded direct labour assumption of **£25/hour**, that allows **3.5 hours** per accepted intro.
- 70% gross margin allows only **£52.50**, or **2.1 hours** at £25/hour.

**Implication:** if intro fulfilment, dispute handling, and evidence collection take much more than a few hours per accepted intro, the line becomes fragile quickly.

## Ramp vs cash collection

### Why recognised revenue is not the same as cash

- **Monthly subscriptions:** cash collection is usually close to recognition, but not identical.
- **One-off packs and reports:** cash may arrive at order, on invoice, or on acceptance; recognition depends on delivery.
- **Enterprise work:** cash can be ahead of recognition if prepaid, or behind if invoiced on terms.

### Practical finance implication

A company can show strong cash early from one-offs while still having a weaker recognised revenue profile.
For CareGist, that means:

- **Cash-positive pilot** is more achievable than
- **£1m recognised revenue in 12 months**.

## Leading indicators to watch

These are the metrics that actually tell you whether the portfolio is working:

1. **Paid conversion by line**
   - free → paid data plan
   - claimed provider → paid visibility
   - lead request → paid pack
   - enterprise enquiry → signed scope

2. **Repeat behaviour**
   - expansion from Starter → Pro → Business
   - additional locations on provider visibility
   - repeat pack/report orders

3. **Fulfilment efficiency**
   - minutes per lead pack
   - minutes per dataset pack
   - analyst hours per report
   - dispute rate per intro

4. **Retention and churn**
   - monthly churn by plan
   - gross revenue retention / net revenue retention

5. **Sales-cycle proof**
   - time from first touch to paid order
   - time from enquiry to close
   - enterprise procurement duration

6. **Compliance friction**
   - opt-outs
   - privacy complaints
   - manual correction requests
   - claims/review moderation load

## Capital and people requirements

### Validation sprint level

To validate the portfolio without overbuilding:

- **People:**
  - 1 founder-seller
  - 0.5 ops / research support
  - 0.25 compliance / finance support
- **Cash need:** roughly **£5k–£15k/month** direct burn, plus a working-capital buffer.
- **Buffer recommendation:** **£25k–£50k**.

### Early scale level

To support a meaningful recurring business:

- **People:**
  - 1 founder / GM
  - 1 commercial person
  - 1 ops / customer success person
  - 1 data / engineering person
  - part-time finance/compliance
- **Cash need:** roughly **£20k–£35k/month**.
- **Runway target:** **£150k–£250k** depending sales cycle.

### £1m ARR attempt level

To attempt a genuine £1m ARR build-out:

- **People:**
  - founder / GM
  - 1–2 sales
  - 1 customer success / fulfilment
  - 1 data engineer / analyst
  - part-time finance / compliance
- **Cash need:** roughly **£35k–£60k/month** before full operating leverage.
- **Runway target:** **£300k–£600k** if enterprise/custom work is material.

## Assumptions

- Live prices in the snapshot are the current recurring price points.
- Lead packs, dataset packs, and strategic reports are modelled because the site exposes the route but not the published price.
- Enterprise monthly retainer is modelled at £5k for threshold analysis only; actual pricing is custom.
- Qualified intro economics are modelled from launch materials, but the line is not validated.
- Linear ramp is a simplification; real-world sales usually ramp slower.

## Weaknesses / open questions

1. **Demand evidence is thin**
   - There is no observed paid conversion data for the live portfolio yet.

2. **Provider visibility is the biggest upside, but unproven**
   - It has the clearest numerical path to scale, but current evidence does not show actual willingness to pay at the required conversion rate.

3. **Manual one-off services can help cash, but they cap scale**
   - Lead packs, datasets, reports, and intros are labour-constrained.

4. **Enterprise/custom work is attractive but slow**
   - It can rescue ARR, but not without proof, references, and longer cycles.

5. **Compliance and trust costs may rise faster than expected**
   - Especially for personal-data use, direct marketing, claims, and provider introductions.

## Compliance flags

- UK Country Pack / entity / authority chain unresolved in the source set.
- VAT status unverified.
- CQC attribution and freshness rules must stay explicit.
- PECR / GDPR / UK direct marketing controls are required for outreach and any intro service.
- Provider visibility claims and provider claim moderation create reputational and moderation risk.
- Qualified introductions create conflict-of-interest and complaint-risk exposure.
- No unsupported claims of pre-registration access, regulator endorsement, or predictive risk certainty.

## Bottom line

### Is £1m ARR exit run-rate credible from £0?
**Possibly, but not yet evidenced.**

The cleanest route is a mix of:
- live subscriptions,
- provider visibility,
- and selective enterprise/custom wins.

### Is £1m recognised revenue in 12 months credible from £0 with current evidence?
**No.**

Even a strong stretch case only gets to roughly **£807k** recognised revenue under a linear ramp and already assumes aggressive adoption.

### Bounded validation economics recommendation

Do **not** commit to a full-scale launch forecast. Instead:

- validate one or two lines first,
- keep manual services tightly capped,
- and kill any line that does not show repeatable paid conversion with acceptable labour.

### Kill thresholds

- **Subscriptions:** if paid conversion, churn, or support burden cannot sustain **85%+ direct gross margin**, stop scaling that line.
- **Provider visibility:** if claim-to-paid conversion stays below a low single-digit percentage of claimed providers and churn is high, pause.
- **Lead packs / datasets:** if fulfilment exceeds roughly **1 hour per pack** on average, standardise or stop.
- **Strategic reports:** if the sales cycle is long and repeatability is absent after a few deals, keep it custom-only.
- **Qualified introductions:** if direct labour exceeds **3.5 hours per accepted intro** at the assumed economics, or dispute rates climb, kill the line.

## Deliverable return

- **What was produced:** A full-portfolio revenue and unit-economics assessment covering live subscriptions, provider visibility, one-off lead packs/datasets, enterprise/custom, strategic reports, and qualified introductions.
- **Evidence used:** Pricing snapshot, product specification, buyer personas, launch scrutiny report, controlled launch plan, VA sales product spec, and the technical/provider-base evidence already in the repository.
- **Assumptions made:** Explicit assumptions were used for uncatalogued one-off prices and the custom enterprise retainer; the linear ramp is a simplifying assumption.
- **Known weaknesses / open questions:** No observed buyer conversion data; no verified UK Country Pack; enterprise and intro economics remain unproven.
- **Compliance flags:** GDPR/PECR, claims, attribution, entity/VAT, trust/conflict, and complaint-handling risks remain live.
- **Ready for QA:** **Yes** — the assessment is calculation-backed and evidence-linked, but it should still go through independent QA before Henry treats it as decision-grade.
