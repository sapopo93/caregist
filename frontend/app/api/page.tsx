import ApiApplicationForm from "@/components/ApiApplicationForm";
import type { Metadata } from "next";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrackedLink from "@/components/TrackedLink";

export const metadata: Metadata = {
  title: "CareGist API — Workflow-Ready UK Care-Provider Data",
  description:
    "Use CareGist data in dashboard, exports, and API workflows. Daily-refreshed, cleaned, normalised, and geospatially useful on top of the CQC register.",
  alternates: { canonical: "https://caregist.co.uk/api" },
};

const SAMPLE_JSON = `{
  "data": [{
    "id": "1-123456789",
    "name": "Sunrise Care Home",
    "slug": "sunrise-care-home-bournemouth",
    "type": "Social Care Org",
    "status": "ACTIVE",
    "overall_rating": "Good",
    "town": "Bournemouth",
    "postcode": "BH1 1AA",
    "region": "South West",
    "service_types": "Care home service with nursing",
    "quality_score": 82,
    "quality_tier": "GOOD",
    "latitude": 50.7192,
    "longitude": -1.8808,
    "phone": "01202 000000"
  }],
  "meta": { "total": 1, "page": 1, "per_page": 20, "pages": 1 }
}`;

const CAPABILITIES = [
  { title: "Dashboard-first workflow", desc: "Start with search, nearby discovery, saved comparisons, exports, and monitoring before writing integration code." },
  { title: "Geospatial search", desc: "Query by postcode, region, service type, and nearby radius using cleaned coordinates and locality fields." },
  { title: "Operational exports", desc: "Move lists into analyst and operator workflows with plan-based CSV exports and field visibility." },
  { title: "API access", desc: "Use the same cleaned dataset programmatically when you need embedding, product integration, or recurring automation." },
  { title: "Monitoring layer", desc: "Track providers for rating changes so teams do not have to poll the raw register manually." },
  { title: "Daily refresh", desc: "Data syncs against the public CQC register every day; we avoid claiming live source updates." },
];

const TIERS = [
  { name: "Starter", price: "\u00A339 + VAT/mo", features: "Nearby search, 500-row export, 15 monitors, 10 requests/sec" },
  { name: "Pro", price: "\u00A399 + VAT/mo", features: "5,000-row export, 100 monitors, 3 included users, 25 requests/sec, recommended for recurring team use" },
  { name: "Business", price: "\u00A3399 + VAT/mo", features: "Full fields, webhooks, 10,000-row export, 500 monitors, 10 included users, 10,000 requests/day" },
];

export default function ApiLandingPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <TrackEventOnMount eventType="api_docs_visit" eventSource="api_landing" />
      {/* AEO Block */}
      <section className="bg-parchment border-b border-stone px-6 py-4 rounded-t-lg text-sm text-charcoal leading-relaxed mb-8">
        <p>
          CareGist exposes daily-refreshed UK care-provider data through the same layer that powers
          the dashboard and exports. The goal is not raw feed access alone. The goal is operationally
          usable regulatory data.
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">Dashboard, exports, and API on one data layer</h1>
      <p className="text-dusk mb-10" style={{ fontFamily: "Lora" }}>
        Use CareGist in the way your team actually works: browser first, export next, API when embedding and automation matter.
      </p>

      {/* Capabilities */}
      <div className="grid md:grid-cols-3 gap-4 mb-12">
        {CAPABILITIES.map((c) => (
          <div key={c.title} className="bg-cream border border-stone rounded-lg p-4">
            <h3 className="font-semibold text-bark text-sm mb-1">{c.title}</h3>
            <p className="text-xs text-dusk">{c.desc}</p>
          </div>
        ))}
      </div>

      {/* Sample Response */}
      <div className="mb-12">
        <h2 className="text-xl font-bold mb-3">Sample Response</h2>
        <pre className="bg-charcoal text-cream rounded-lg p-5 text-xs overflow-x-auto font-mono leading-relaxed">
          {SAMPLE_JSON}
        </pre>
      </div>

      {/* Pricing */}
      <div className="mb-12">
        <h2 className="text-xl font-bold mb-4">Pricing</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {TIERS.map((t) => (
            <div key={t.name} className={`bg-cream border rounded-lg p-5 text-center ${t.name === "Pro" ? "border-clay shadow-sm" : "border-stone"}`}>
              <h3 className="font-bold text-bark">{t.name}</h3>
              {t.name === "Pro" && <p className="text-[10px] uppercase tracking-[0.2em] text-clay mt-2">Recommended</p>}
              <p className="text-2xl font-bold text-clay mt-2">{t.price}</p>
              <p className="text-xs text-dusk mt-2">{t.features}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-dusk mt-4 text-center">
          <TrackedLink href="/pricing" eventType="pricing_cta_click" eventSource="api_landing">
            <span className="text-clay underline">See full pricing details</span>
          </TrackedLink>
        </p>
      </div>

      {/* Application Form */}
      <div className="bg-cream border border-stone rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Need a reviewed integration path?</h2>
        <p className="text-sm text-dusk mb-6">
          Starter, Pro, and Business can begin self-serve. Use this form if you want help scoping a higher-volume integration or enterprise procurement path.
        </p>
        <ApiApplicationForm />
      </div>

      {/* Trust */}
      <p className="text-center text-xs text-dusk mt-8">
        Data sourced from the CQC public register · Updated daily · Built to make raw regulatory data usable inside workflows
      </p>
    </div>
  );
}
