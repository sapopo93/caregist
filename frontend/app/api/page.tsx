import ApiApplicationForm from "@/components/ApiApplicationForm";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CareGist API — CQC Provider Data for Developers",
  description:
    "Programmatic access to 55,818 CQC-registered care providers. Search, filter, and export UK care data via REST API. Updated weekly.",
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
  { title: "Search & Filter", desc: "Query by name, postcode, region, rating, and service type." },
  { title: "Geographic Radius", desc: "Find providers within a radius of any UK postcode." },
  { title: "Full Provider Data", desc: "Ratings, coordinates, contact details, inspection history." },
  { title: "Bulk Export", desc: "CSV and JSON exports with enriched fields." },
  { title: "Rating Webhooks", desc: "Get notified when providers change rating (Enterprise)." },
  { title: "Daily Refresh", desc: "Data synced from CQC public register daily at 3am." },
];

const TIERS = [
  { name: "Standard", price: "\u00A3499 + VAT/mo", features: "Core search/filter endpoints, fair-use cap" },
  { name: "Pro", price: "\u00A31,250 + VAT/mo", features: "Higher rate limits, bulk endpoints, SLA" },
  { name: "Enterprise", price: "from \u00A33,500 + VAT/mo", features: "Custom terms, webhooks, named support, onboarding" },
];

export default function ApiLandingPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      {/* AEO Block */}
      <section className="bg-parchment border-b border-stone px-6 py-4 rounded-t-lg text-sm text-charcoal leading-relaxed mb-8">
        <p>
          CareGist provides programmatic access to 55,818 CQC-registered care providers across
          England via a REST API. Data is cleaned, normalised, and refreshed weekly from the CQC
          public register.
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">CareGist API</h1>
      <p className="text-dusk mb-10" style={{ fontFamily: "Lora" }}>
        Build on top of the most complete UK care provider dataset.
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
            <div key={t.name} className="bg-cream border border-stone rounded-lg p-5 text-center">
              <h3 className="font-bold text-bark">{t.name}</h3>
              <p className="text-2xl font-bold text-clay mt-2">{t.price}</p>
              <p className="text-xs text-dusk mt-2">{t.features}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Application Form */}
      <div className="bg-cream border border-stone rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Apply for API Access</h2>
        <p className="text-sm text-dusk mb-6">
          Tell us about your use case. We review applications within 2 business days.
        </p>
        <ApiApplicationForm />
      </div>

      {/* Trust */}
      <p className="text-center text-xs text-dusk mt-8">
        Data sourced from CQC public register · Updated daily · All plans include SLA
      </p>
    </div>
  );
}
