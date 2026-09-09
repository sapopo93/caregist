import type { PricingTier } from "@/lib/types";

// The public catalogue is intentionally small. Historical product keys live in
// backend entitlement compatibility code, not in the saleable product model.
export const PRICING_LADDER: PricingTier[] = [
  {
    tier: "Territory Opportunity Brief",
    forWho: "Should your sales team prioritise Birmingham and Solihull, or put its next quarter elsewhere?",
    color: "#C8862A",
    price: "£795",
    priceNote: "One-off · delivered in 3 working days",
    recommended: true,
    includes: [
      "CRM-import-ready territory dataset",
      "Ranked shortlist of 25–50 priority organisations, each with a stated reason",
      "3–5 page brief on territory size, market structure, notable movements, and recommended approach",
      "Observation dates carried through the deliverable",
    ],
    limit: "A 15-minute scoping conversation comes first. Checkout follows by Payment Link only after the delivery gates pass.",
    pricingLogic: "Choose the accounts worth approaching next and see the evidence behind each priority.",
  },
  {
    tier: "Market Movement Report",
    forWho: "See what changed across the care market and decide where your team should look next.",
    color: "#8b5cf6",
    price: "£495",
    priceNote: "One-off · current edition available immediately after the delivery gates pass",
    includes: [
      "20–35 page current-edition report",
      "New registrations, closures, and rating movements where the published record supports them",
      "Regional movement and provider-group activity where supported",
      "Observation dates carried through the report",
    ],
    limit: "Request the sample before any payment ask. Checkout follows by Payment Link only after the delivery gates pass.",
    pricingLogic: "Understand the movements worth reviewing without buying another provider directory.",
  },
  {
    tier: "Free Directory",
    forWho: "Provider discovery and official-source checking",
    color: "#10b981",
    price: "£0",
    priceNote: "",
    includes: [
      "Search CQC-registered providers",
      "Browse profiles, ratings, source dates, and official links",
      "Report factual record issues to CareGist support",
    ],
    limit: "No Radar workspace, event history, API, or webhooks.",
    pricingLogic: "",
  },
  {
    tier: "Radar Regional",
    forWho: "Compliance and quality-improvement firms covering one England region",
    color: "#C8862A",
    price: "Request access",
    priceNote: "Not yet available · no paid checkout",
    includes: [
      "New CQC registrations and rating changes",
      "One England region with direct CQC evidence links",
      "Email and in-app delivery",
      "10 saved views",
      "90-day canonical event export",
      "2 organization users",
    ],
    limit: "Roadmap only. No subscription purchase or checkout is available.",
    pricingLogic: "Access stays closed until the data-quality gate passes.",
  },
  {
    tier: "Radar National",
    forWho: "National compliance and business-development teams",
    color: "#8b5cf6",
    price: "Request access",
    priceNote: "Not yet available · no paid checkout",
    includes: [
      "Everything in Radar Regional across all England",
      "50 saved views and provider lists",
      "365-day canonical event export",
      "5 organization users",
      "Structured onboarding",
    ],
    limit: "Roadmap only. No subscription purchase or checkout is available.",
    pricingLogic: "Access stays closed until the data-quality gate passes.",
  },
  {
    tier: "Strategic Territory Intelligence Assignment",
    forWho: "Bespoke territory work after the evidence spine and history gates pass",
    color: "#64748b",
    price: "Roadmap",
    priceNote: "Not yet available · future scope from £3,500",
    includes: ["Bespoke assignment scope to be defined after the launch gates pass"],
    limit: "Not for sale. No quote, payment, or delivery commitment is available.",
    pricingLogic: "Shown for roadmap context only.",
  },
  {
    tier: "Founding Intelligence Membership",
    forWho: "Continuing intelligence support after the evidence spine and history gates pass",
    color: "#64748b",
    price: "Roadmap",
    priceNote: "Not yet available · future scope £4,500/year",
    includes: ["Continuing monitoring remains a future roadmap option"],
    limit: "Not for sale. No membership payment or delivery commitment is available.",
    pricingLogic: "Shown for roadmap context only.",
  },
  {
    tier: "Intelligence Feed Pilot",
    forWho: "Customers integrating one CQC signal into an operational system",
    color: "#ef4444",
    price: "Roadmap",
    priceNote: "Not yet available · no paid checkout",
    includes: [
      "Scoped canonical event API",
      "Timestamped, signed webhooks",
      "Stable cursors, idempotent replay, and delivery health",
      "Explicit pilot scope and onboarding",
    ],
    limit: "Not for sale. No public or private checkout is available.",
    pricingLogic: "Shown for roadmap context only.",
  },
  {
    tier: "Embedded Enterprise",
    forWho: "White-label, customer-owned provider lists, and regulated enterprise use",
    color: "#64748b",
    price: "Roadmap",
    priceNote: "Not yet available · no quote or checkout",
    includes: [
      "White-label delivery and customer-owned provider lists",
      "Procurement, security, and data-processing review",
      "Contracted SLA, support, and deployment scope",
    ],
    limit: "Not for sale. Future access requires separate technical, security, and contractual approval.",
    pricingLogic: "Shown for roadmap context only.",
  },
];

// Claims and corrections are free. These historical presentation states remain
// solely so an existing subscriber's already-granted profile fields still render.
export const PROVIDER_TIERS = [
  {
    tier: "claimed" as const,
    label: "Claimed Listing",
    price: "£0",
    priceMonthly: 0,
    priceAnnual: null,
    stripeSlug: null,
    color: "#10b981",
    photos: 0,
    virtualTour: false,
    inspectionResponse: true,
    includes: [
      "Verified listing badge",
      "Respond to a CQC inspection",
      "Keep core provider details accurate",
    ],
    limit: "Claiming your listing is always free",
  },
  {
    tier: "enhanced" as const,
    label: "Legacy enhanced entitlement",
    price: "Existing subscription",
    priceMonthly: 0,
    priceAnnual: null,
    stripeSlug: null,
    color: "#8b5cf6",
    photos: 5,
    virtualTour: true,
    inspectionResponse: true,
    includes: ["Existing enhanced fields", "Up to 5 photos", "Virtual tour link"],
    limit: "Not available for new sale",
  },
  {
    tier: "sponsored" as const,
    label: "Legacy sponsored entitlement",
    price: "Existing subscription",
    priceMonthly: 0,
    priceAnnual: null,
    stripeSlug: null,
    color: "#ef4444",
    photos: 15,
    virtualTour: true,
    inspectionResponse: true,
    includes: ["Existing sponsored fields", "Up to 15 photos", "Legacy badge"],
    limit: "Not available for new sale",
  },
] as const;

export type ProviderTierKey = (typeof PROVIDER_TIERS)[number]["tier"];

export const PLAN_PRIMARY_CTA: Record<string, string> = {
  "territory-opportunity-brief": "Request the sample",
  "market-movement-report": "Book a 15-minute scoping call",
  free: "Compare Radar plans",
  "free-directory": "Open the directory",
  "radar-regional": "Request access",
  "radar-national": "Request access",
  "strategic-territory-intelligence-assignment": "Not yet available",
  "founding-intelligence-membership": "Not yet available",
  "intelligence-feed-pilot": "Not yet available",
  "embedded-enterprise": "Not yet available",
};

export const CQC_INDEPENDENCE_LINE =
  "CareGist is independent and is not affiliated with or endorsed by the Care Quality Commission.";

export const PLAN_NEXT_STEP: Record<string, string> = {
  free: "Radar Regional turns verified CQC changes into an evidence-linked team workflow.",
  "radar-regional": "Radar National adds all-England coverage, deeper history, more views, and onboarding.",
  "radar-national": "The Intelligence Feed Pilot adds a scoped API, signed webhooks, replay, and delivery health.",
  "intelligence-feed": "Embedded Enterprise adds white-label delivery and contracted operating terms.",
  "embedded-enterprise": "Contact us for contracted scope, security review, and support.",
  starter: "This historical plan is no longer sold. Contact support to discuss a Radar migration.",
  pro: "This historical plan is no longer sold. Contact support to discuss a Radar migration.",
  business: "This historical plan is no longer sold. Contact support to discuss a Feed migration.",
};

export const PLAN_LIMIT_SUMMARY: Record<string, string> = {
  free: "Directory access",
  "radar-regional": "1 England region · 2 users · 90-day event export",
  "radar-national": "All England · 5 users · 365-day event export",
  "intelligence-feed": "Contracted API and webhook scope",
  "embedded-enterprise": "Contracted limits and SLA",
  starter: "Historical compatibility entitlements",
  pro: "Historical compatibility entitlements",
  business: "Historical compatibility entitlements",
};
