# CareGist route/API/facility atlas — public exhaustive, authenticated partial — 30 July 2026

## DELIVERABLE RETURN
- **What was produced:** Source-exhaustive route/API/facility atlas with exhaustive public-route-family coverage and partial authenticated live coverage, classified against production where tested.
- **Assumptions made:** A route is not classified as live merely because code exists. Read-only GET rendering or supplied authenticated screenshot is required for live-observed status.
- **Known weaknesses / open questions:** Authenticated Business dashboard could not be navigated live after session expiry; only its top portion was visually evidenced. Admin and provider-owner states were not accessed.
- **Compliance flags:** No writes, exports, account changes, moderation, billing, key operations, claims, emails or destructive actions were performed.
- **Ready for QA:** yes.

## Evidence classes
- **Live-observed:** production GET/render or supplied authenticated screenshot.
- **Coded-wired:** executable frontend/backend path found, but not safely exercised end-to-end.
- **Broken-live:** production route rendered a failure, false zero or 503.
- **Fixture/sample:** deliberately illustrative or fallback-backed.
- **Protected-unverified:** redirects safely when signed out; authenticated runtime not inspected.

## Inventory totals
- 32 `frontend/app/**/page.tsx` routes.
- 7 Next route handlers.
- 24 backend router modules.
- 72 distinct `/api/v1/...` references found by delegated engineering inventory.
- 12 test files covering routing, middleware, API configuration, exports, lead requests, groups, provider paths and pricing CTAs.

## Page-route atlas

### Public marketing and policy
| Route | Purpose | Classification | Runtime evidence / issue |
|---|---|---|---|
| `/` | Opportunity-led homepage | Live-observed | 56,742 stock; 91 new registrations; 53 Inadequate; 2,904 Requires Improvement; 20,989 Not Yet Inspected. Several cohort labels are unsafe because of stale and inverted dates. |
| `/pricing` | API/intelligence/provider-profile plans | Live-observed | Real tier CTAs and entitlements; sells alerts/daily workflows before freshness is proven. |
| `/api` | API and webhook product documentation | Live-observed | Documents search, nearby, exports, monitors, webhooks and rate limits. “Daily-refreshed” conflicts with visible registration lag. |
| `/why-caregist` | Positioning/evidence narrative | Live-observed | Unlinked statistics lack visible sources; daily-refresh and normalisation claims conflict with runtime. |
| `/sample-report` | Assessment demonstration | Live-observed; fixture | Fictional provider. Claims every provider has an assessment, but component is not imported by provider route. |
| `/story-video` | Timed narrated animated story | Live-observed | Start/pause/progression worked; possible education/white-label content facility. |
| `/privacy` | Privacy policy | Live-observed | Says weekly refresh while product says daily; claims scores are informational/data-completeness while UI calls them care quality. |
| `/terms` | Terms | Live-observed | Plan names lag live pricing; broad accuracy disclaimer conflicts with commercial freshness claims. |
| `/acceptable-use` | API/data/outreach controls | Live-observed | Prohibits unsolicited marketing while product copy encourages immediate outreach/CRM use. |
| `/review-policy` | Review moderation/safeguarding | Live-observed | Process specified, but claim/respond mechanism is broken and moderation capacity unproven. |
| `/cookies` | Storage/cookie policy | Live-observed | Says API key and tier are stored in localStorage; banner mentions traffic analysis while policy says no analytics cookies. |

### Discovery, listing and intelligence
| Route | Purpose | Classification | Runtime evidence / issue |
|---|---|---|---|
| `/search` | Full directory and opportunity filters | Live-observed | 56,742 records. Search works. Date inversions and historical inspections appear in “Not Yet Inspected.” |
| `/search?opportunity=new_90` | Rolling new registrations | Live-observed | 91 rows across 4 pages; latest visible registration 29 May 2026, 62 days before review. |
| `/search?opportunity=inadequate` | Inadequate cohort | Live-observed | 53 rows; many old inspection dates, so “currently” is not proven. |
| `/search?opportunity=requires_improvement` | RI cohort | Live-observed | 2,904 rows; same freshness/current-state concern. |
| `/search?opportunity=not_yet_inspected` | Uninspected cohort | Live-observed | 20,989 rows; includes old registrations and records with historical inspection dates. Not a clean early-stage cohort. |
| `/search?opportunity=stale_inspection` | >3-year/no-date cohort | Live-observed | 51,883 records, 91.44% of directory. Combines missing and old dates, so not useful prioritisation. |
| `/lead-list` | Filtered lead-list request | Live-observed | Email + filters create a production request. No price, SLA, freshness guarantee or schema at request point; not submitted. |
| `/find-care` | Postcode/radius/category search | Live-observed | BH1 1AA/10 miles reported 644 providers but rendered 3 and said 197 more; “Skip” did not reveal more. Export not exercised. |
| `/compare` | 2–3 provider comparison | Live-observed | Direct query works. Pricing advertises up to 5, code allows only 2–3. Uses mislabelled completeness score as care quality. |
| `/groups` | Multi-location group table | Live-observed | Strong location/group graph. Unrated groups show near-100 “average quality” because field is completeness score. |
| `/groups/[slug]` | Group portfolio details/report | Live-observed | Locations, ratings, beds, regions, inspection dates and print. For Voyage, the list showed 98.7 average quality and 91.7% Good+, while the detail page rendered both headline values as “—”. |
| `/provider/[slug]` | Provider details, review and enquiry | Live-observed | Rich CQC/provider/family surface. Unpriced Stripe “wider access” link visible. No assessment component. |
| `/claim/[slug]` | Claim workflow | Broken-live | Real provider route rendered “Something went wrong.” Source inspection suggests, but runtime evidence did not prove, failure of the server-side provider lookup. |
| `/region/[slug]` | Region discovery | Broken-live | London publicly stated 0 providers and “search unavailable.” |
| `/services/[slug]` | Six service verticals | Broken-live | Valid `/services/home-care` returned zero/unavailable while main search had thousands. |
| `/care-homes/[slug]` | City discovery | Broken-live | Bournemouth stated zero despite radius search finding 644 within ten miles. |
| `/good-care-homes/[slug]` | Rating/city SEO | Broken-live | Same server-side data failure. |
| `/outstanding-care-homes/[slug]` | Rating/city SEO | Coded-wired | Same route family/backend as tested broken city pages; family failure is inferred, not separately asserted live. |
| `/requires-improvement-care-homes/[slug]` | Rating/city SEO | Coded-wired | Same route family/backend as tested broken city pages; family failure is inferred, not separately asserted live. |

### Authentication/account/protected
| Route | Purpose | Classification | Evidence |
|---|---|---|---|
| `/login` | Session login | Live-observed signed-out | Renders and preserves redirect. |
| `/signup` | Plan-aware signup | Live-observed signed-out | Plan retained, but price/VAT/entitlements/terms not repeated. |
| `/forgot-password` | Password reset request | Live-observed signed-out | Form renders; no email triggered. |
| `/verify-email` | Verification/resend | Live-observed signed-out | Renders; resend disabled without state. |
| `/dashboard` | Customer intelligence workspace | Live-observed (top, supplied authenticated screenshot); Coded-wired (full page) | Business plan and analytics were screenshot-evidenced. Feed, API, team, webhooks and danger zone are executable source-backed but not live-clicked in this pass. |
| `/provider-dashboard/[slug]` | Claimed-provider profile management | Protected-unverified | Signed-out redirect works. Source supports inspection response, logo, fees/funding, photos, virtual tour, contracts, ages and Stripe upgrades. |
| `/admin` | Admin/moderation workspace | Protected-unverified | Signed-out redirect works. Additional master-key gate; source tabs: Dashboard, Claims, Reviews, Enquiries. |

## Authenticated dashboard facility atlas
- Plan entitlement/rate-limit card.
- Provider service-type and primary-type charts.
- 90-day vs prior-90-day service growth chart.
- New-registration ledger feed with filters: query, region, local authority, service type, provider type, postcode prefix and date range.
- Sort by effective date, name, confidence, region or authority.
- CSV/XLSX export.
- Saved views.
- Weekly digest.
- Data explorer and provider-claiming entry points.
- Password-confirmed API-key reveal/copy.
- Included/extra seats and £15+VAT seat quantity update.
- Named API keys per teammate with last-used/revocation state.
- Webhook delivery status for `feed.new_registration` and `provider.rating_changed`.
- Quick-start API request.
- Irreversible account deletion.

## Provider-owner facility atlas
- Claim identity: role, name, work email, optional phone.
- Verification: location ID/free-text proof; optional fast-track checkbox.
- Free public inspection response.
- Logo, funding types, fee guidance and minimum visit duration.
- Paid description, remote photo URLs and virtual-tour URL.
- Contract types and age ranges.
- Provider-profile tier checkout and public-profile preview.

## Admin facility atlas
- Aggregate providers, claims, reviews and enquiries.
- Service-type/provider-type/growth analytics.
- Top-enquired providers.
- Claims queue with claimant proof and approve/reject.
- Reviews queue with reviewer identity/content and approve/reject.
- Enquiries queue with care type, urgency, message and read/responded state.

## Route handlers and platform facilities
- `/api/export`: signed/token-gated export; CSV formula-injection neutralisation is tested.
- `/api/v1/service-types`: live-observed; returned 58 raw labels with legacy/current duplicates.
- `/api/health/directory`: live-observed; database read/write and email mode healthy, but no ingestion watermark or lag.
- `/sitemap.xml`: 200 but only 5 URLs.
- `/provider-sitemap-index.xml`: live 503.
- `/provider-sitemaps/[id]`: tested shard 503.
- `/api/v1/openapi.json`: live 404/`detail: Not Found`; no machine-readable schema at advertised path.
- Middleware: CSP nonce plus protection for dashboard/provider-dashboard/admin found in code/tests.
- Directory fallback datasets exist, which explains why some client-rendered routes work while server-side route families fail.

## Most material engineering findings
1. `quality_score` is generated by `quality_audit.py` as field completeness, explicitly “NOT a quality rating,” but production uses it for quality sorting, local ranking, group averages, comparison and assessment copy.
2. Server-rendered/provider lookup paths fail while client search/radius paths work, splitting production into functioning and false-zero route families.
3. Health reports availability, not source freshness; there is no data-watermark SLO surfaced.
4. Provider sitemaps fail, making the directory difficult to discover organically.
5. Claiming—the gateway to provider participation and profile revenue—is broken.
6. Rating-change/monitor/webhook facilities are extensively coded but operational evidence is absent.
7. The API contract is broad but lacks a live OpenAPI document.

## Acceptance status
- Full executable route/facility inventory: **met**.
- Public live representative route testing: **met**.
- Exhaustive authenticated runtime clicks: **not met; session unavailable**.
- No unsafe side effects: **met**.
