# Fresh Brief: offer, price defence and sales handoff

Objective: remove the deliverable obstacles to a first sale by 9 September, while preserving the user's prohibition on sending messages, publishing, activating billing or changing production configuration. No sale has been verified. This updates the earlier Luna/Terra review with work completed on 8 September.

## One offer

Use the [Territory Opportunity Brief offer](/Users/user/CareGist/artifacts/sales/2026-09-08-defensible-territory-offer.md): £745 one-off, VAT treatment still unconfirmed. Buyer: a recruitment or staffing business researching an agreed England homecare territory. Deliver 25 provider organisations with evidence and selection reasons, a territory Excel workbook with CSVs and a four-page executive brief. The documented delivery period is three working days, with the actual start and delivery date agreed before ordering.

The [7 September founder decision](/Users/user/.hermes/profiles/ai-company-governed/company-os/chief-of-staff/decisions/2026-09-07-caregist-launch-one-off-products.md) establishes the £745 lead SKU. The [sales playbook](/Users/user/Downloads/caregist-revamped/xx/02-SALES-caregist-playbook.docx) specifies £745, 25–50 organisations, Excel, a 3–5 page brief and three working days. This package uses the lower end of that scope. £150 remains the separate Radar pilot already offered to three recorded contacts. Do not switch those prospects' terms or describe £745 as a correction to their existing offer.

## Claim to evidence

| Claim | Primary evidence and check | Current judgement |
|---|---|---|
| A current published source route is unavailable | September CQC downloads retained with hashes and retrieval times in [pack-data.json](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/pack-data.json). | Contradiction resolved. The bounded local source route now works. Production freshness is a separate question. |
| 353 qualifying locations, 329 organisations | Monthly source filtered for two authorities, domiciliary flag Y and dormant N. Every selected identity matches the weekly directory. [Verification](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/DATA_PATH_VERIFICATION.md). | Verified for the stated editions. Do not reuse the old 371-row count or infer closures from the difference. |
| 25 distinct organisations with inspectable reasons | [Shortlist](/Users/user/CareGist/outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/shortlist-25.csv): 15 multi-location providers and 10 recent-registration selections, with facts, questions, uncertainty, IDs and CQC URLs. | Verified structure and source facts. Buyer relevance remains illustrative. This is not a hiring-demand ranking. |
| Checked CQC evidence | 25 saved representative pages with HTTP 200, matching location names and hashes. | Verified access and representative identity. Not exhaustive live validation of all fields or branches. |
| Excel plus usable CSV | [Workbook](/Users/user/CareGist/outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/caregist-birmingham-solihull-territory-brief.xlsx) and [territory CSV](/Users/user/CareGist/outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/territory-dataset.csv). Final XLSX has zero error cells; CSV fields agree with the data model. | Files completed. Buyer-specific CRM mapping/import remains untested. |
| 3–5 page executive brief | [Four-page PDF](/Users/user/CareGist/output/pdf/caregist-birmingham-solihull-executive-brief.pdf), extracted and visually inspected on every page. | Completed. Includes facts, examples, method, next research steps and limitations. |
| £745 is an approved product price | Founder decision and playbook above, local [manifest](/Users/user/CareGist/deploy/stripe-price-manifest.json). | Documented price verified. No paid acceptance or market validation established. VAT/final total remains open. |
| Three working days | Playbook; fresh local pack built during this work session. | Bounded production is demonstrated. Capacity and a specific order deadline still need agreement. No blanket guarantee for a new territory. |
| More sales, qualified leads or saved research hours | No customer outcome study or paid buyer evidence inspected. | Unsupported promises removed. |

## Plain-English price defence

The £745 pays for a defined piece of territory research: organise the care locations, join branches to provider organisations, select 25 organisations against agreed criteria, show the source facts and explain what the buyer should check next. The buyer receives editable files and a short brief they can inspect before committing.

The source data is public. Access to those rows alone does not defend £745. The paid value must come from doing the selection and explanation for a specific buyer. The refreshed sample now proves the data route, formats and transparent provider grouping. For example, Advance Health Care UK Ltd has four qualifying local locations under one provider ID, which gives an account team a concrete reason to coordinate its research before assigning branches separately. It does not prove central procurement or a staffing requirement.

£745 is the documented price to test, not a demonstrated market valuation. There is no measured time saving, conversion improvement or verified willingness to pay for this Brief. Do not promise a financial return or justify the fee using hypothetical customer wins.

**Verified value:** dated territory extract, provider/location distinction, traceable facts, two explicit review routes and completed editable/readable files. **Assumed value:** these routes matter to this buyer, reduce their work and warrant £745.

**Smallest remaining deliverable improvement:** agree the buyer's service specialisms, territory and exclusions, then revise the existing 25 reasons and order against those criteria. Record which account decision the sample helps them make. Do not build more data infrastructure or add unsupported demand signals. If the buyer only wants an unqualified directory extract, this evidence does not defend the full Brief price for that requirement.

## Only unresolved issues affecting selling now

1. Buyer/order fit: no named £745 buyer, accepted selection criteria, CRM columns or delivery date is recorded in this task. The current sample is an illustrative staffing-buyer pack. Existing £150 conversations retain their own scope.
2. Commercial release: confirmed VAT status/final payable amount, Terms/copy and catalogue alignment, independent sample acceptance and an approved payment route remain required by the founder decision. The local manifest is not proof of live payment readiness. No billing activation was performed.
3. Reply visibility: the attempted Gmail search returned `UNAUTHORIZED / oauth_token_invalid_grant`. Current replies cannot be verified through that connector until reconnection. The stored tracker cannot establish today's buyer response.
4. Action authority: the user explicitly prohibited sending, publishing and billing activation. Those actions were not performed. A concrete send/payment action needs separate authorization once scope and release conditions are resolved.

## Files changed, checks and exact next action

Created the fresh sample directory [bsol-domiciliary-fresh-2026-09-08](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08), including retained source evidence, data model, CSVs, builders, verifier and DATA_PATH_VERIFICATION.md. Created the final workbook and CSVs under `/Users/user/CareGist/outputs/01a080c9-7c69-71e0-ab8d-821ce92d1e44/`, and the PDF under `/Users/user/CareGist/output/pdf/`. Updated the offer and added a supersession notice to the earlier price-defence handoff. Other dirty project files were left untouched.

Checks: source identity/filter assertions PASS; two download hashes and 25 page hashes PASS; CSV field round-trip PASS; 25 unique shortlist provider IDs PASS; final workbook summary totals and all 378 source-link formulas PASS, zero saved error cells; PDF four pages and text extraction PASS; all PDF pages and workbook sheet views visually inspected. [Machine results](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/qa/verification.json). An initial hyperlink export failure was fixed by LibreOffice recalculation and verified from saved XLSX XML. These are producer checks, not independent commercial approval.

**Exact next action:** obtain the confirmed VAT status and the warm buyer's actual request or reconnect Gmail to verify replies. Agree that buyer's selection criteria using this sample, revise the 25 account reasons, and submit the frozen package plus final amount/delivery date for independent commercial acceptance. Then present the exact proposed message and payment action for authorization. Nothing in this handoff proves a sale or authorizes external action.
