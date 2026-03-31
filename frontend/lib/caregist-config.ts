import type {
  BuyerSegment,
  GateKey,
  Gate,
  PricingTier,
  AddOn,
  LaunchPrice,
  RevenueControl,
  UnitEconomic,
  DefensibilityPoint,
  SegmentStrategy,
  SeoPageFamily,
  AeoRule,
  FlywheelSide,
  CrmEvent,
  PageSpec,
  ActionType,
  Priority,
} from "@/lib/types";

// ── Brand Colors ──
// Spec hex values for non-Tailwind contexts (emails, PDFs, charts).
// Tailwind theme colors in globals.css are the primary UI palette.
export const BRAND = {
  brown: "#5C3317",
  brownDark: "#3d2010",
  amber: "#C8862A",
  cream: "#F5F0E8",
  creamDark: "#E8E0D0",
  text: "#2C1A0E",
  muted: "#8a6a4a",
} as const;

// ── Buyer Segments ──
export const BUYERS: BuyerSegment[] = [
  { label: "Developers / data buyers",    color: "#3b82f6", value: 4 },
  { label: "Consultants / commissioners", color: "#8b5cf6", value: 3 },
  { label: "Operators / providers",       color: "#C8862A", value: 2 },
  { label: "Families",                    color: "#10b981", value: 1 },
];

// ── Gate Types ──
export const GATES: Record<GateKey, Gate> = {
  none:   { label: "Open",            color: "#10b981" },
  email:  { label: "Email gate",      color: "#C8862A" },
  login:  { label: "Login gate",      color: "#3b82f6" },
  paid:   { label: "Paid gate",       color: "#8b5cf6" },
  manual: { label: "Manual approval", color: "#ef4444" },
};

// ── Pricing Ladder ──
export const PRICING_LADDER: PricingTier[] = [
  {
    tier: "Free",
    forWho: "Families, public users, researchers",
    color: "#10b981",
    price: "\u00A30",
    priceNote: "Always free",
    includes: [
      "Search all 55,818 providers",
      "Browse provider profiles",
      "Limited compare (2 providers)",
      "View ratings and inspection dates",
      "Radius Finder (email gate for PDF)",
      "Weekly CQC Movers (email subscribe)",
    ],
    limit: "No CSV export \u00B7 no alerts \u00B7 no monitors",
    pricingLogic:
      "Traffic engine, not cash engine. Keep the gate on email, not payment.",
  },
  {
    tier: "Pro Alerts",
    forWho: "Consultants, commissioners, care managers",
    color: "#8b5cf6",
    price: "from \u00A339 + VAT/mo",
    priceNote: "Solo \u00A339 \u00B7 Team \u00A379 \u00B7 Enterprise \u00A3149",
    variants: [
      { name: "Solo",       price: "\u00A339/mo",  features: "25 monitors, saved comparisons, PDF export, instant alerts" },
      { name: "Team",       price: "\u00A379/mo",  features: "100 monitors, team sharing, area movers, benchmark exports" },
      { name: "Enterprise", price: "\u00A3149/mo", features: "Multi-user, priority support, custom area packs" },
    ],
    includes: [
      "Everything in Free",
      "Provider monitors (25\u2013unlimited)",
      "Instant rating-change alerts",
      "Saved comparisons + PDF export",
      "Weekly area movers digest",
      "Benchmark exports",
    ],
    limit: "No bulk export \u00B7 no API",
    pricingLogic:
      "Intentionally below carehome.co.uk Enhanced (\u00A382.50/mo) while being intelligence-led. Easy yes for care consultants and managers.",
  },
  {
    tier: "Provider Pro",
    forWho: "Care home operators, group managers",
    color: "#C8862A",
    price: "from \u00A389 + VAT/mo per location",
    priceNote: "Location \u00A389 \u00B7 Plus \u00A3149 \u00B7 Group from \u00A3399",
    variants: [
      { name: "Location", price: "\u00A389/location/mo",  features: "Enhanced listing, visibility analytics, competitor benchmarking" },
      { name: "Plus",     price: "\u00A3149/location/mo", features: "Adds improvement toolkit, richer analytics, benchmark snapshots" },
      { name: "Group",    price: "from \u00A3399/mo",     features: "Up to 5 locations, then +\u00A359/location" },
    ],
    includes: [
      "Claimed + verified listing badge",
      "Visibility analytics",
      "Local competitor benchmarking",
      "Rating trajectory history",
      "Enhanced search placement",
      "Post-inspection improvement toolkit",
    ],
    limit: "No data export \u00B7 no API",
    pricingLogic:
      "Just above carehome.co.uk Enhanced (\u00A382.50) and below Platinum (\u00A3165) \u2014 but selling benchmarking + intelligence, not listing uplift. Defendable wedge.",
  },
  {
    tier: "Data Pro",
    forWho: "Research teams, analysts, procurement",
    color: "#3b82f6",
    price: "from \u00A3129 + VAT/mo",
    priceNote: "Starter \u00A3129 \u00B7 Standard \u00A3249 \u00B7 Advanced \u00A3399",
    variants: [
      { name: "Starter",  price: "\u00A3129/mo", features: "2 exports/mo, 5,000 rows each" },
      { name: "Standard", price: "\u00A3249/mo", features: "8 exports/mo, 10,000 rows each" },
      { name: "Advanced", price: "\u00A3399/mo", features: "20 exports/mo, priority support, scheduled feed" },
    ],
    includes: [
      "Enriched CSV bulk export",
      "All provider fields incl. contacts + coords",
      "Segmented, comparison-ready output",
      "Weekly refresh data feed",
      "Priority support (Advanced)",
    ],
    limit: "No programmatic API",
    pricingLogic:
      "CQC API gives free raw access. CareGist\u2019s value is cleaned, queryable, segmented, and export-ready output \u2014 not the raw register.",
  },
  {
    tier: "API",
    forWho: "Developers, SaaS builders, procurement platforms",
    color: "#ef4444",
    price: "from \u00A3499 + VAT/mo",
    priceNote: "Standard \u00A3499 \u00B7 Pro \u00A31,250 \u00B7 Enterprise from \u00A33,500",
    variants: [
      { name: "Standard",   price: "\u00A3499/mo",        features: "Core lookup/search/filter endpoints, fair-use cap" },
      { name: "Pro",        price: "\u00A31,250/mo",      features: "Higher rate limits, bulk endpoints, SLA" },
      { name: "Enterprise", price: "from \u00A33,500/mo", features: "Custom terms, onboarding, named support, webhook/change feed" },
    ],
    includes: [
      "Full REST API access",
      "1k req/min standard \u00B7 10k pro",
      "All provider fields + filters",
      "Radius + rating queries",
      "SLA + dedicated onboarding",
    ],
    limit: "Manual qualification required",
    pricingLogic:
      "Priced as infrastructure, not a hobby product. Raw CQC API exists free \u2014 CareGist price reflects cleanliness, history, filters, uptime, and implementation speed.",
  },
];

// ── Add-Ons ──
export const ADD_ONS: AddOn[] = [
  { name: "Extra monitors pack",           price: "\u00A315/mo",               note: "Additional 25 monitors" },
  { name: "Extra team seat",               price: "\u00A312/mo per user",      note: "Pro Alerts Team and above" },
  { name: "Area movers pack",              price: "\u00A319/mo per area",      note: "Additional local authority coverage" },
  { name: "Benchmark PDF pack",            price: "\u00A329/report",           note: "Included in higher plans" },
  { name: "Sponsored placement",           price: "from \u00A399/mo/location", note: "Featured placement on filter and region pages" },
  { name: "Claim verification fast-track", price: "\u00A349 one-off",          note: "24hr instead of standard 48hr review" },
  { name: "White-label consultant report", price: "\u00A379/mo",               note: "Branded PDF reports for consultants" },
];

// ── Launch Pricing ──
export const LAUNCH_PRICING: LaunchPrice[] = [
  { tier: "Free",         price: "\u00A30",                       color: "#10b981" },
  { tier: "Pro Alerts",   price: "\u00A339 + VAT/mo",             color: "#8b5cf6" },
  { tier: "Provider Pro", price: "\u00A389 + VAT/location/mo",    color: "#C8862A" },
  { tier: "Data Pro",     price: "\u00A3129 + VAT/mo",            color: "#3b82f6" },
  { tier: "API",          price: "from \u00A3499 + VAT/mo",       color: "#ef4444" },
];

// ── Revenue Controls ──
export const REVENUE_CONTROLS: RevenueControl[] = [
  {
    tier: "Pro Alerts",
    color: "#8b5cf6",
    trigger: "User creates second provider monitor or saves first comparison",
    upgradeMoment: "Immediately after the second high-intent action in session",
    paywallMessage: "Upgrade to track unlimited providers and get instant alerts.",
    targetConversion: "8\u201312% of watchlist_user + analysis_intent_user",
    targetARPU: "\u00A339\u2013\u00A3149/mo",
    primarySurface: "Provider Profile \u00B7 Compare \u00B7 Movers email",
  },
  {
    tier: "Provider Pro",
    color: "#C8862A",
    trigger: "Claim verified or analytics preview viewed",
    upgradeMoment: "After verified claim and first benchmark preview shown",
    paywallMessage: "Unlock visibility analytics, competitor benchmarking, and enhanced listing placement.",
    targetConversion: "15\u201325% of verified claims",
    targetARPU: "\u00A389\u2013\u00A3399+/mo",
    primarySurface: "Provider Profile \u00B7 Claim Flow \u00B7 Filter pages",
  },
  {
    tier: "Data Pro",
    color: "#3b82f6",
    trigger: "User hits free export row limit or requests enriched columns",
    upgradeMoment: "At export limit boundary \u2014 hard paywall with preview of locked columns",
    paywallMessage: "Upgrade for enriched bulk exports with contacts, coordinates, and inspection history.",
    targetConversion: "5\u201310% of data_intent_user",
    targetARPU: "\u00A3129\u2013\u00A3399/mo",
    primarySurface: "Search Results \u00B7 CSV export gate",
  },
  {
    tier: "API",
    color: "#ef4444",
    trigger: "Repeated bulk export, enterprise inquiry, or stated integration intent",
    upgradeMoment: "After use-case qualification in manual review",
    paywallMessage: "Apply for API access for programmatic search, filters, and provider data at scale.",
    targetConversion: "20\u201340% of qualified applicants",
    targetARPU: "\u00A3499\u2013\u00A33,500+/mo",
    primarySurface: "API Landing \u00B7 Search Results \u00B7 outbound follow-up",
  },
];

// ── Unit Economics ──
export const UNIT_ECONOMICS: UnitEconomic[] = [
  {
    surface: "Homepage email capture",
    color: "#10b981",
    userType: "General / top funnel",
    acquisitionCost: "Low",
    conversionToPaid: "Low",
    strategicValue: "Feeds movers email and regional nurture sequences",
    expectedPayback: "Indirect / long-tail (60\u2013180 days)",
  },
  {
    surface: "Provider Profile monitor",
    color: "#8b5cf6",
    userType: "High-intent intelligence user",
    acquisitionCost: "Medium",
    conversionToPaid: "High",
    strategicValue: "Best retention + alert monetisation surface in the system",
    expectedPayback: "< 60 days",
  },
  {
    surface: "Claim listing",
    color: "#C8862A",
    userType: "Provider-side B2B buyer",
    acquisitionCost: "Low\u2013Medium",
    conversionToPaid: "High after verification",
    strategicValue: "B2B acquisition with recurring revenue. Improves data quality over time.",
    expectedPayback: "30\u201390 days",
  },
  {
    surface: "CSV export",
    color: "#3b82f6",
    userType: "Data-intent user",
    acquisitionCost: "Low",
    conversionToPaid: "Medium",
    strategicValue: "Data Pro and API feeder. Identifies commercial data buyers early.",
    expectedPayback: "< 60 days",
  },
  {
    surface: "API application",
    color: "#ef4444",
    userType: "Enterprise technical buyer",
    acquisitionCost: "Medium",
    conversionToPaid: "Very high when qualified",
    strategicValue: "Highest ARPU segment. Creates platform lock-in via integration dependency.",
    expectedPayback: "< 30 days after close",
  },
];

// ── Defensibility ──
export const DEFENSIBILITY: DefensibilityPoint[] = [
  { point: "Normalised provider identity",                detail: "CQC location records are inconsistently structured. CareGist normalises them into clean, queryable provider records \u2014 a non-trivial data engineering advantage.",                                                                        color: "#C8862A" },
  { point: "Superior search UX",                          detail: "Raw CQC register requires technical knowledge to query. CareGist abstracts this into name, postcode, region, rating, and service type \u2014 accessible to non-technical buyers.",                                                            color: "#10b981" },
  { point: "Historical rating trajectory",                detail: "CQC only shows current ratings. CareGist stores and surfaces historical inspection trajectories \u2014 a dataset that grows in value over time and cannot be rebuilt cheaply.",                                                                  color: "#8b5cf6" },
  { point: "Geographic discovery layer",                  detail: "SEO-optimised filter and region pages create organic distribution that the raw CQC data does not have. This is accumulated marketing infrastructure.",                                                                                           color: "#3b82f6" },
  { point: "Claimed listing data quality loop",           detail: "Provider claims introduce verified human corrections and enrichment. Over time, claimed profiles are more accurate than the raw register. This is a data flywheel.",                                                                             color: "#C8862A" },
  { point: "Benchmarking and comparison layer",           detail: "No comparison or benchmarking product exists in the raw source data. CareGist\u2019s comparison logic and scoring models are proprietary analytical infrastructure.",                                                                             color: "#f97316" },
  { point: "Alerting and watchlist intelligence",         detail: "Monitors and movers convert static public data into workflow value. Users who build workflows on top of CareGist alerts have high switching costs.",                                                                                             color: "#8b5cf6" },
  { point: "API and enriched CSV as operational infrastructure", detail: "When developers and procurement teams integrate CareGist data into their own products, CareGist becomes embedded infrastructure \u2014 not a website. This creates the strongest defensibility.",                                          color: "#ef4444" },
];

// ── Segment Strategy ──
export const SEGMENT_STRATEGY: SegmentStrategy[] = [
  { role: "SEO fuel",          audience: "Families and general public",               insight: "Drive traffic and search demand. Low direct willingness to pay \u2014 high volume justifies SEO investment.",          color: "#10b981" },
  { role: "Recurring revenue", audience: "Consultants, commissioners, care managers", insight: "Pro Alerts subscriptions. Medium-to-high willingness to pay. Habitual users with recurring professional need.",   color: "#8b5cf6" },
  { role: "Provider revenue",  audience: "Operators and care home groups",            insight: "Provider Pro via claims. Medium willingness to pay. Motivated by competitive intelligence and visibility ROI.",    color: "#C8862A" },
  { role: "Highest ARPU",      audience: "Developers and data teams",                 insight: "Data Pro and API. Highest willingness to pay. Build once, extract recurring value. Sales-assisted close required.", color: "#3b82f6" },
];

export const PRODUCT_RULE =
  "Do not overbuild for the largest audience if it is not the highest-value audience. SEO pages serve families but monetise consultants.";

// ── SEO Engine ──
export const SEO_ENGINE: SeoPageFamily[] = [
  {
    family: "Provider Profiles",
    urlPattern: "/provider/[slug]",
    estimatedPages: "55,818",
    color: "#C8862A",
    primaryKeywords: ["[care home name] CQC rating", "is [provider name] good", "[provider] inspection report", "[care home] review"],
    structuredData: "LocalBusiness + MedicalOrganization + AggregateRating",
    aeoBlock: "Open with: \u2018[Provider name] is rated [rating] by the CQC. Their most recent inspection was on [date], covering [service type] in [location].\u2019 This is the exact pattern AI models pull as a citation.",
    freshnessSignal: "Show \u2018Rating as of [date] \u00B7 Source: CQC public register \u00B7 Updated weekly\u2019 in a visible block above the fold.",
    distributionValue: "55,818 indexed pages. Each is a long-tail keyword with near-zero competition. Compounding SEO asset that grows in authority over time.",
    conversionRole: "SEO entry \u2192 monitor CTA \u2192 Pro Alerts. Also: claim CTA \u2192 Provider Pro.",
  },
  {
    family: "Region / Local Authority Pages",
    urlPattern: "/region/[la-slug]",
    estimatedPages: "~150",
    color: "#8b5cf6",
    primaryKeywords: ["CQC care homes [city]", "care quality [county]", "outstanding care homes [region]", "CQC ratings [local authority]"],
    structuredData: "ItemList + FAQPage",
    aeoBlock: "Open with: \u2018There are [N] CQC-registered care providers in [LA name]. [X%] are rated Good or Outstanding as of [date].\u2019 Definitive factual statement AI models can anchor on.",
    freshnessSignal: "Show provider count, rating distribution, and last-updated date in a summary table at the top of every region page.",
    distributionValue: "~150 pages covering all English local authorities. Medium competition. Strong for commissioner and consultant queries.",
    conversionRole: "SEO entry \u2192 area alert subscribe \u2192 newsletter_lead \u2192 Pro Alerts upsell.",
  },
  {
    family: "Rating Filter Pages",
    urlPattern: "/[rating]-care-homes/[city]",
    estimatedPages: "~2,000+",
    color: "#10b981",
    primaryKeywords: ["outstanding care homes [city]", "good rated care agencies [city]", "CQC outstanding [city]", "best rated nursing homes [city]"],
    structuredData: "ItemList + LocalBusiness",
    aeoBlock: "Open with: \u2018There are [N] Outstanding-rated care homes in [city] as of [date]. The following providers hold this rating:\u2019 \u2014 then the list. AI citation-ready format.",
    freshnessSignal: "Show \u2018[N] providers \u00B7 CQC data \u00B7 Updated [date]\u2019 in the page header. Each provider card shows inspection date.",
    distributionValue: "Rating \u00D7 city matrix. ~500 cities \u00D7 4 ratings = 2,000+ pages. Highest-volume family for consumer search intent. Directly competes with carehome.co.uk.",
    conversionRole: "SEO entry \u2192 browse providers \u2192 provider profile monitor or claim listing \u2192 B2B or Pro Alerts.",
  },
  {
    family: "Service Type Pages",
    urlPattern: "/[service-type]/[city]",
    estimatedPages: "~1,500+",
    color: "#3b82f6",
    primaryKeywords: ["domiciliary care agencies [city]", "nursing homes [city]", "dementia care [city]", "supported living [city]"],
    structuredData: "ItemList + MedicalOrganization",
    aeoBlock: "Open with: \u2018There are [N] CQC-registered [service type] providers in [city]. [X] are rated Good or Outstanding.\u2019 Enables AI to answer \u2018find me a dementia care provider in Bristol\u2019 using CareGist data.",
    freshnessSignal: "Service type + provider count + last updated date shown in page header. Filter rail shows rating distribution.",
    distributionValue: "~10 service types \u00D7 ~150+ cities = 1,500+ pages. Medium competition. Strong for professional and referral queries.",
    conversionRole: "SEO entry \u2192 professional/commissioner user \u2192 CSV export \u2192 Data Pro or Pro Alerts.",
  },
];

// ── AEO Rules ──
export const AEO_RULES: AeoRule[] = [
  {
    rule: "Answer block first",
    detail: "Every page opens with a 2\u20133 sentence factual summary that directly answers the implied search query. This is the block AI models pull. Do not lead with brand messaging or navigation.",
    applies: "All page templates",
    color: "#C8862A",
  },
  {
    rule: "Structured data on every page",
    detail: "Implement Schema.org markup: LocalBusiness and MedicalOrganization on provider pages, ItemList on filter and region pages, FAQPage on informational pages, AggregateRating where ratings are shown.",
    applies: "All page templates",
    color: "#8b5cf6",
  },
  {
    rule: "Stable, intent-matched H1",
    detail: "H1 must match the query exactly: \u2018Outstanding care homes in Birmingham\u2019 not \u2018Find great care in Birmingham.\u2019 AI citation engines anchor on heading text.",
    applies: "Filter pages \u00B7 Region pages \u00B7 Provider profiles",
    color: "#3b82f6",
  },
  {
    rule: "Data provenance block",
    detail: "Every page must show: \u2018Source: CQC public register \u00B7 Last updated: [date] \u00B7 [N] providers.\u2019 This signals freshness to both Google and AI answer engines. Makes CareGist the attributable source.",
    applies: "All page templates",
    color: "#10b981",
  },
  {
    rule: "Factual density",
    detail: "Include rating, inspection date, service type, postcode, and bed count (where available) as machine-readable text \u2014 not just visual design. AI models extract structured facts, not styled UI.",
    applies: "Provider profiles \u00B7 Filter pages",
    color: "#f97316",
  },
  {
    rule: "Canonical URL discipline",
    detail: "One canonical URL per provider, per region, per filter combination. No parameter-based duplicates. Canonical tags on all programmatic pages. Sitemap updated weekly with the data refresh.",
    applies: "All programmatic page families",
    color: "#ef4444",
  },
];

// ── Flywheel ──
export const FLYWHEEL: FlywheelSide[] = [
  { side: "Demand",       color: "#10b981", desc: "Families, researchers, and commissioners find CareGist via Google (SEO filter pages, region pages, provider profiles). They search, compare, and subscribe to alerts.", pages: ["Homepage", "Search Results", "Region pages", "Filter pages"] },
  { side: "Supply",       color: "#C8862A", desc: "Care providers discover their own profile page via Google or direct referral. They claim the listing, verify identity, and unlock analytics and benchmarking.",         pages: ["Provider Profile", "Filter pages", "Compare"] },
  { side: "Intelligence", color: "#8b5cf6", desc: "Monitors, saved comparisons, and weekly movers create habitual return visits from consultants and commissioners. Recurring engagement justifies Pro Alerts.",          pages: ["Provider Profile", "Compare", "Movers email"] },
  { side: "Platform",     color: "#3b82f6", desc: "High-ARPU developers and data teams access the API and bulk export. They integrate CareGist into their own products, creating distribution and enterprise lock-in.",  pages: ["API Landing", "Search Results (CSV)", "Data Pro tier"] },
];

// ── CRM Events & States ──
export const CRM_EVENTS: CrmEvent[] = [
  { event: "Homepage email subscribe",   state: "newsletter_lead",           color: "#10b981" },
  { event: "Search result CSV download", state: "data_intent_user",          color: "#3b82f6" },
  { event: "Compare saved",             state: "analysis_intent_user",      color: "#8b5cf6" },
  { event: "Pricing \u2192 trial started",   state: "trial_user",                color: "#C8862A" },
  { event: "Provider profile monitored", state: "watchlist_user",            color: "#f97316" },
  { event: "Claim submitted",           state: "provider_acquisition_lead", color: "#C8862A" },
  { event: "Claim verified",            state: "provider_customer",         color: "#16a34a" },
  { event: "API application received",  state: "enterprise_data_prospect",  color: "#ef4444" },
  { event: "API application approved",  state: "enterprise_opportunity",    color: "#dc2626" },
  { event: "Trial \u2192 paid conversion",   state: "paying_customer",           color: "#7c3aed" },
];

export const UNIQUE_CRM_STATES = [...new Set(CRM_EVENTS.map((e) => e.state))].length;

// ── Action Colors & Priority Config ──
export const ACTION_COLORS: Record<ActionType, string> = {
  trial:     "#ef4444",
  subscribe: "#C8862A",
  download:  "#3b82f6",
  save:      "#8b5cf6",
  monitor:   "#10b981",
  apply:     "#ef4444",
  claim:     "#f97316",
};

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string }> = {
  now:        { label: "Build Now", color: "#ef4444" },
  "phase-2":  { label: "Phase 2",  color: "#C8862A" },
};

// ── Page Specs ──
export const PAGE_SPECS: PageSpec[] = [
  {
    id: 1,
    status: "exists",
    priority: "now",
    page: "Pricing",
    url: "/pricing",
    audience: "Operators \u00B7 Consultants \u00B7 Developers",
    buyerRank: 4,
    jobToBeDone: "Evaluate whether CareGist is worth paying for and commit.",
    currentGap: "Highest-intent page on the site. Without a frictionless trial CTA and plan pre-selection on click, high-intent visitors bounce without converting.",
    primaryCTA: "Start free \u2014 no card required",
    actionType: "trial",
    gate: "none",
    capturedAsset: "Account created with plan intent recorded in user profile",
    revenuePath: "Free \u2192 paid at trial end. Highest ARPU per visit of any page.",
    upgradeTrigger: "Free trial expires or user hits a feature limit within first 14 days",
    successMetric: "Pricing page visitor-to-trial conversion rate (target: \u22658%)",
    followUpAutomation: "Trial activation email day 0. Feature highlight day 3. Upgrade nudge day 12. Cancellation save day 14.",
    trustLayer: "Show data freshness badge, provider count, weekly refresh cadence, and one operator testimonial. Add cost comparison vs building from raw CQC data.",
    crmOutcome: "trial_user",
    executionScore: { revenueImpact: 10, buildComplexity: 2, paybackSpeed: 10, strategicCompounding: 7 },
  },
  {
    id: 2,
    status: "build",
    priority: "now",
    page: "Provider Profile",
    url: "/provider/[slug]",
    audience: "Families \u00B7 Operators checking competitors \u00B7 Consultants",
    buyerRank: 2,
    jobToBeDone: "Understand a specific provider\u2019s rating trajectory, inspection history, and contact details \u2014 then decide what to do next.",
    currentGap: "No individual profile pages means no SEO surface, no per-provider engagement hook, and no B2B lead capture from the supply side.",
    primaryCTA: "Monitor this provider",
    actionType: "monitor",
    gate: "login",
    capturedAsset: "Identified user + specific provider watchlist item \u2014 strongest intent signal in the system",
    revenuePath: "Watchlist \u2192 Pro Alerts (unlimited monitors, instant alerts). Secondary CTA: \u2018Is this your home? Claim it.\u2019 \u2192 Provider Pro",
    upgradeTrigger: "User monitors second provider or requests instant alert vs daily digest",
    successMetric: "Monitor creation rate per profile view (target: \u22658%)",
    followUpAutomation: "Monitor confirmation email. Rating change \u2192 instant alert. Day 30: \u2018You\u2019re monitoring 3 providers \u2014 upgrade for SMS alerts.\u2019",
    trustLayer: "Show last inspection date, data source label, days since inspection. Flag profiles uninspected >24 months.",
    crmOutcome: "watchlist_user",
    executionScore: { revenueImpact: 9, buildComplexity: 6, paybackSpeed: 8, strategicCompounding: 10 },
    claimFlow: {
      verification: "Provider submits CQC location ID + registered email. System cross-references CQC register. Verification email sent to registered address.",
      claimantRoles: "Registered manager, nominated individual, provider director",
      approvalSLA: "24\u201348 hours manual review",
      freeTier: "Verified badge, editable contact details, basic profile stats visible",
      paidTier: "Visibility analytics, competitor benchmarking, inspection improvement toolkit, enhanced search placement",
      postClaim: "Claim verified \u2192 Provider Pro trial. Day 3: benchmark report sent. Day 7: upgrade prompt with local ranking preview.",
      crmRecord: "provider_acquisition_lead on submission \u2192 provider_customer on first paid month",
    },
  },
  {
    id: 3,
    status: "exists",
    priority: "now",
    page: "Search Results",
    url: "/search",
    audience: "Families \u00B7 Care managers \u00B7 Commissioners",
    buyerRank: 2,
    jobToBeDone: "Find a shortlist of providers matching specific criteria and act on it.",
    currentGap: "Users search, see a list, and leave. Nothing asks them to save, export, or return. High-value query data is logged but not converted.",
    primaryCTA: "Download this list as CSV",
    actionType: "download",
    gate: "login",
    capturedAsset: "Identified user + search query (location, rating, service type) \u2014 high segmentation signal",
    revenuePath: "Login to export \u2192 free basic CSV; Data Pro unlocks enriched CSV with contacts, coordinates, and inspection history",
    upgradeTrigger: "User hits free row limit (100 rows) or selects locked enriched columns",
    successMetric: "CSV click-to-login conversion rate (target: \u226515% of search sessions)",
    followUpAutomation: "Post-export email: \u2018Your list is ready. Want alerts when any of these providers change rating?\u2019 \u2192 Pro Alerts upsell.",
    trustLayer: "\u2018Sourced from CQC public register, refreshed weekly\u2019 in results header. Show record count and last refresh timestamp.",
    crmOutcome: "data_intent_user",
    executionScore: { revenueImpact: 8, buildComplexity: 3, paybackSpeed: 9, strategicCompounding: 7 },
  },
  {
    id: 4,
    status: "exists",
    priority: "now",
    page: "Compare",
    url: "/compare",
    audience: "Operators \u00B7 Consultants \u00B7 Commissioners",
    buyerRank: 3,
    jobToBeDone: "Understand how providers compare on rating, inspection recency, and service type \u2014 then share or save the analysis.",
    currentGap: "Compare exists but likely shows static fields with no post-comparison action. Users do the analytical work and leave with nothing.",
    primaryCTA: "Save comparison / Copy shareable link",
    actionType: "save",
    gate: "login",
    capturedAsset: "Identified user + comparison query (provider IDs, fields compared) \u2014 strongest analysis-intent signal in the system",
    revenuePath: "Saved comparisons \u2192 Pro Alerts: unlimited saves, PDF export, benchmark scoring vs local average and national percentile",
    upgradeTrigger: "User saves second comparison or selects PDF export option",
    successMetric: "Saved comparison rate per logged-in session (target: \u226520%)",
    followUpAutomation: "Saved comparison email. \u2018Get notified if any of these providers change rating.\u2019 \u2192 monitor upsell.",
    trustLayer: "Show inspection date per provider. Flag providers uninspected >24 months. Add data provenance label.",
    crmOutcome: "analysis_intent_user",
    executionScore: { revenueImpact: 7, buildComplexity: 2, paybackSpeed: 8, strategicCompounding: 6 },
  },
  {
    id: 5,
    status: "exists",
    priority: "now",
    page: "Homepage",
    url: "/",
    audience: "All \u2014 families, researchers, general public",
    buyerRank: 1,
    jobToBeDone: "Understand what CareGist is and take a first action.",
    currentGap: "Search is front and centre but there is no email capture. The stats block builds trust but asks for nothing. Traffic leaves without a trace.",
    primaryCTA: "Subscribe to Weekly CQC Movers",
    actionType: "subscribe",
    gate: "email",
    capturedAsset: "Email address + implicit interest in CQC movement data",
    revenuePath: "Warm list \u2192 Weekly movers email \u2192 upgrade prompt to Pro Alerts",
    upgradeTrigger: "User opens two movers emails or clicks a regional alert CTA",
    successMetric: "Homepage email capture rate (target: \u22653% of unique visitors)",
    followUpAutomation: "Welcome email with sample movers report. Week 2: \u20184 rating changes in [LA] this week \u2014 see full report.\u2019 \u2192 upgrade.",
    trustLayer: "Add \u2018Updated weekly from live CQC register\u2019 under stats block. Show last-synced timestamp.",
    crmOutcome: "newsletter_lead",
    executionScore: { revenueImpact: 5, buildComplexity: 1, paybackSpeed: 6, strategicCompounding: 8 },
  },
  {
    id: 6,
    status: "build",
    priority: "now",
    page: "API Landing",
    url: "/api",
    audience: "Developers \u00B7 Procurement platforms \u00B7 Care-tech SaaS \u00B7 Analyst teams",
    buyerRank: 4,
    jobToBeDone: "Determine whether CareGist\u2019s API meets technical and commercial requirements \u2014 and start the access process.",
    currentGap: "No API page means highest-ARPU buyers have no discovery surface. Silent revenue loss from the segment most willing to pay.",
    primaryCTA: "Apply for API access",
    actionType: "apply",
    gate: "manual",
    capturedAsset: "Name, company, use case, request volume \u2014 full commercial profile of the buyer",
    revenuePath: "Manual qualification \u2192 standard (1k req/min), pro (10k req/min), enterprise (custom SLA)",
    upgradeTrigger: "Applicant states high request volume or integration use case during qualification",
    successMetric: "Qualified API application rate \u2014 applications that pass review (target: \u226560%)",
    followUpAutomation: "Application confirmation within 1 hour. Review within 48 hours. Approved: sandbox key + pricing call link. Declined: waitlist + referral to Data Pro.",
    trustLayer: "Show sample JSON response, endpoint schema, rate limits, refresh cadence, SLA commitments. Technical buyers will not apply without this.",
    crmOutcome: "enterprise_data_prospect",
    executionScore: { revenueImpact: 9, buildComplexity: 2, paybackSpeed: 9, strategicCompounding: 9 },
  },
  {
    id: 7,
    status: "build",
    priority: "phase-2",
    page: "Region / Local Authority",
    url: "/region/[name]",
    audience: "Commissioners \u00B7 Journalists \u00B7 Regional consultants",
    buyerRank: 3,
    jobToBeDone: "Understand the care quality landscape in a specific area \u2014 rating distribution, top providers, recent movers.",
    currentGap: "No geographic landing pages means zero organic search footprint for location-based queries.",
    primaryCTA: "Get weekly alerts for this region",
    actionType: "subscribe",
    gate: "email",
    capturedAsset: "Email address + geographic interest \u2014 enables segmented newsletter and localised upgrade",
    revenuePath: "Area subscriptions \u2192 Pro Alerts: area monitoring dashboard, downloadable regional reports",
    upgradeTrigger: "Subscriber opens two area digests or wants full movers report for the region",
    successMetric: "Organic landing-to-subscribe rate per region page (target: \u22655%)",
    followUpAutomation: "Area welcome email with rating snapshot. Week 2: \u20186 rating changes in [LA] this week \u2014 see full report.\u2019 \u2192 upgrade.",
    trustLayer: "Show data freshness date, provider count for the area, last CQC inspection update date.",
    crmOutcome: "newsletter_lead",
    executionScore: { revenueImpact: 6, buildComplexity: 5, paybackSpeed: 5, strategicCompounding: 8 },
  },
  {
    id: 9,
    status: "build",
    priority: "now",
    page: "Free Tool \u2014 CQC Radius Finder",
    url: "/find-care",
    audience: "Families and carers searching for local care options",
    buyerRank: 1,
    jobToBeDone: "Enter a postcode and instantly see all CQC-rated care providers within a chosen radius, filtered by rating and service type.",
    currentGap: "The highest-volume consumer search intent in this space (\u2018care homes near me\u2019, \u2018find care home postcode\u2019) has no dedicated free-tool surface. Families are going to CQC.org.uk, Lottie, or carehome.co.uk instead.",
    primaryCTA: "Email me this list as a PDF report",
    actionType: "subscribe",
    gate: "email",
    capturedAsset: "Email address + postcode + radius + rating preference \u2014 richest consumer segmentation data in the system",
    revenuePath: "Email list \u2192 weekly movers for their postcode area \u2192 Pro Alerts upsell. PDF report is the gate; the list is the asset.",
    upgradeTrigger: "User searches a second postcode or requests more than 10 results",
    successMetric: "Tool email capture rate (target: \u226525% of searches that return results)",
    followUpAutomation: "PDF report delivered by email immediately. Day 3: \u2018Ratings change \u2014 want to be notified?\u2019 \u2192 monitor upsell. Day 7: area movers digest for their postcode.",
    trustLayer: "Show \u2018Powered by CareGist \u00B7 CQC data \u00B7 Updated weekly\u2019 in the tool header. Show last-synced date. Show provider count in the result radius.",
    crmOutcome: "newsletter_lead",
    executionScore: { revenueImpact: 7, buildComplexity: 4, paybackSpeed: 7, strategicCompounding: 9 },
    toolSpec: {
      inputs: "Postcode (required) \u00B7 Radius in miles: 1, 5, 10, 20 \u00B7 Rating filter: All / Outstanding / Good \u00B7 Service type: All / Care home / Domiciliary / Nursing",
      outputs: "Map view + list view of matching providers. Each card shows: name, rating badge, distance, last inspection date, service type.",
      freeLimit: "Show top 10 results. Full list (up to 100) gated behind email. Detailed contact info gated behind login.",
      aeoAngle: "Tool results page has a canonical URL per postcode+radius+rating combo, making it indexable. \u2018Outstanding care homes within 5 miles of BH1\u2019 becomes an indexed page.",
      viralMechanic: "PDF report is shareable. Footer reads \u2018Generated by CareGist \u00B7 caregist.co.uk\u2019. Every shared report is a referral impression.",
      distributionNote: "This tool IS the marketing. A single well-built radius finder will attract more inbound links, social shares, and word-of-mouth than any equivalent ad spend at this stage.",
    },
  },
  {
    id: 8,
    status: "build",
    priority: "phase-2",
    page: "Rating Filter / SEO Pages",
    url: "/outstanding-care-homes/[city]",
    audience: "Families searching Google for top-rated local care",
    buyerRank: 1,
    jobToBeDone: "Find Outstanding or Good-rated care homes in a specific city quickly and confidently.",
    currentGap: "Without these pages there is no organic search footprint beyond branded queries.",
    primaryCTA: "Claim your listing",
    actionType: "claim",
    gate: "manual",
    capturedAsset: "Provider identity, role, contact details, CQC location ID \u2014 full B2B lead record",
    revenuePath: "Claimed profiles \u2192 Provider Pro: enhanced listing, analytics, benchmarking, sponsored placement",
    upgradeTrigger: "Claim verified and provider views benchmark report preview",
    successMetric: "Claim submission rate per page (target: \u22651% of provider impressions)",
    followUpAutomation: "Claim received confirmation. Verified: profile setup steps. Day 7: benchmark report \u2192 upgrade prompt.",
    trustLayer: "Show CQC source badge, last inspection date, and active provider count per filter page.",
    crmOutcome: "provider_acquisition_lead",
    executionScore: { revenueImpact: 7, buildComplexity: 7, paybackSpeed: 4, strategicCompounding: 9 },
  },
];

// ── Execution Score Calculator ──
export function execScore(page: PageSpec): number {
  const s = page.executionScore;
  return (
    s.revenueImpact * 0.4 +
    s.paybackSpeed * 0.3 +
    s.strategicCompounding * 0.2 +
    (10 - s.buildComplexity) * 0.1
  );
}

// ── Tab Constants ──
export const PAGE_TABS = ["Overview", "Gate & Capture", "Automation", "Trust Layer", "Metric"] as const;
export const TOP_TABS = ["Pages", "Pricing Ladder", "Revenue Controls", "Unit Economics", "Flywheel", "CRM Pipeline", "Defensibility", "SEO Engine"] as const;
