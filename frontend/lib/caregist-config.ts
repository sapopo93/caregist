import type { PricingTier } from "@/lib/types";

// The public catalogue is intentionally small. Historical product keys live in
// backend entitlement compatibility code, not in the saleable product model.
export const PRICING_LADDER: PricingTier[] = [
  {
    tier: "Weekly Digest",
    forWho: "Watch one England region week by week: new CQC registrations, rating changes, and closures, each with the published record behind it.",
    color: "#10b981",
    price: "£150",
    priceNote: "One-off · four weekly digests · one England region",
    includes: [
      "Four consecutive weekly digests covering one England region you choose",
      "New registrations, rating changes, and closures where the published CQC record supports them",
      "A direct official-source link on every item",
      "Report and observation dates carried through each digest",
    ],
    limit: "One England region per four-week pack. Email to confirm your region, your buyer type, and a start date. Online ordering is not available.",
    pricingLogic: "Keep the week's movement in view without buying another provider directory.",
  },
  {
    tier: "Territory Opportunity Brief",
    forWho: "Should your sales team prioritise Birmingham and Solihull, or put its next quarter elsewhere?",
    color: "#C8862A",
    price: "£745",
    priceNote: "One-off · confirm your region and buyer type online",
    recommended: true,
    includes: [
      "CRM-import-ready territory dataset",
      "Ranked shortlist of 25–50 priority organisations, each with a stated reason",
      "3–5 page brief on territory size, market structure, notable movements, and recommended approach",
      "Observation dates carried through the deliverable",
    ],
    limit: "Confirm online that the published CQC record supports your exact region and buyer type before any payment. No scoping call required.",
    pricingLogic: "Choose the accounts worth approaching next and see the evidence behind each priority.",
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
  "weekly-digest": "Request the digest",
  "territory-opportunity-brief": "Check territory coverage",
  free: "See the two products",
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
  free: "The Weekly Digest follows one England region week by week; the Territory Opportunity Brief ranks the accounts worth approaching there.",
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
