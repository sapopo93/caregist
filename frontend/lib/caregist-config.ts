import type { PricingTier } from "@/lib/types";

// The public catalogue is intentionally small. Historical product keys live in
// backend entitlement compatibility code, not in the saleable product model.
export const PRICING_LADDER: PricingTier[] = [
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
    price: "£299/mo",
    priceNote: "2 users · VAT is not currently charged · Cancel anytime",
    recommended: true,
    includes: [
      "New CQC registrations and rating changes",
      "One England region with direct CQC evidence links",
      "Email and in-app delivery",
      "10 saved views",
      "90-day canonical event export",
      "2 organization users",
    ],
    limit: "No API, webhooks, extra-seat add-ons, or cross-region access.",
    pricingLogic: "Priced below the value of one typical compliance engagement.",
  },
  {
    tier: "Radar National",
    forWho: "National compliance and business-development teams",
    color: "#8b5cf6",
    price: "£799/mo",
    priceNote: "5 users · VAT is not currently charged · Cancel anytime",
    includes: [
      "Everything in Radar Regional across all England",
      "50 saved views and provider lists",
      "365-day canonical event export",
      "5 organization users",
      "Structured onboarding",
    ],
    limit: "No API or webhooks. Integration needs move to the Feed pilot.",
    pricingLogic: "For teams where one timely national engagement can repay the annual cost.",
  },
  {
    tier: "Intelligence Feed Pilot",
    forWho: "Customers integrating one CQC signal into an operational system",
    color: "#ef4444",
    price: "From £6,000/yr",
    priceNote: "One region and one signal at base scope · Sales-assisted",
    includes: [
      "Scoped canonical event API",
      "Timestamped, signed webhooks",
      "Stable cursors, idempotent replay, and delivery health",
      "Explicit pilot scope and onboarding",
    ],
    limit: "Private pilot only; no public or instant checkout.",
    pricingLogic: "Reliability and evidence traceability replace manual monitoring work.",
  },
  {
    tier: "Embedded Enterprise",
    forWho: "White-label, customer-owned provider lists, and regulated enterprise use",
    color: "#64748b",
    price: "Annual quote",
    priceNote: "Contracted scope; quote and invoice only",
    includes: [
      "White-label delivery and customer-owned provider lists",
      "Procurement, security, and data-processing review",
      "Contracted SLA, support, and deployment scope",
    ],
    limit: "Available only after technical, security, and contractual qualification.",
    pricingLogic: "Pricing reflects operational risk, support, and regulated deployment scope.",
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
  free: "Compare Radar plans",
  "free-directory": "Open the directory",
  "radar-regional": "Start Radar Regional",
  "radar-national": "Start Radar National",
  "intelligence-feed-pilot": "Request a Feed pilot",
  "embedded-enterprise": "Discuss Embedded Enterprise",
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
