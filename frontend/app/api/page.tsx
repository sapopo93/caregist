import ApiApplicationForm from "@/components/ApiApplicationForm";
import type { Metadata } from "next";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrackedLink from "@/components/TrackedLink";
import {
  CQC_INDEPENDENCE_LINE,
  NEW_REGISTRATION_MONTHLY_AVG,
  NEW_REGISTRATION_MONTHLY_AVG_CAVEAT,
  NEW_REGISTRATION_SOURCE_LINE,
} from "@/lib/caregist-config";

export const metadata: Metadata = {
  title: "CareGist API — New Provider Intelligence, CRM Integration, and UK Care Data",
  description:
    "No-code exports, CRM and webhook workflows, and developer API for newly registered CQC providers and UK care-market data.",
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

const DELIVERY_SECTIONS = [
  {
    title: "No-code exports",
    tag: "Dashboard & CSV",
    desc: "Export filtered provider lists for outreach, research, and CRM upload. Filter by region, service type, registration window, and confidence score — then download as CSV or Excel without writing a line of code.",
    bullets: [
      "Filter and export newly registered providers weekly",
      "CSV and Excel output for immediate outreach or CRM upload",
      "Saved filter views for repeatable lead-list workflows",
      "Free sample · Data Starter and above for workflow volumes",
    ],
  },
  {
    title: "CRM and webhook workflow",
    tag: "Data Business",
    desc: "Push new-provider opportunities and registration movement into your sales workflow automatically. Data Business plans can register outbound webhooks that receive signed payloads for every new CQC registration matching your saved filter.",
    bullets: [
      "Outbound webhooks for feed.new_registration and provider.rating_changed",
      "HMAC-SHA256 signed payloads for secure CRM and ops delivery",
      "Filter by region and service type at the webhook level",
      "1s, 2s, 4s retry backoff with dashboard delivery log",
    ],
  },
  {
    title: "Developer API",
    tag: "All paid plans",
    desc: "Use the CareGist API for structured provider lookup, geospatial search, new-provider feed access, monitoring, and integration. The same data layer powers the dashboard, exports, and webhooks.",
    bullets: [
      "Provider search, detail, nearby, and bulk export endpoints",
      "New registration feed with filter, pagination, and digest APIs",
      "PostGIS geospatial search by postcode and radius",
      "Monitoring and rating-change tracking endpoints",
      "Plan-based rate limits and field visibility",
    ],
  },
];

const API_TIERS = [
  {
    name: "Alerts Pro",
    price: "£49 + VAT/mo",
    features: "Provider monitoring and rating-change alerts · saved watchlists · CSV export for monitored providers · 5 req/sec · 200/day",
    recommended: false,
  },
  {
    name: "Data Starter",
    price: "£99 + VAT/mo",
    features: "New registration feed · 3 saved filters · weekly digest · 500-row export · 15 monitors · 10 req/sec",
    recommended: false,
  },
  {
    name: "Data Pro",
    price: "£199 + VAT/mo",
    features: "20 saved filters · 10 digests · 5,000-row export · 100 monitors · 3 included seats · 25 req/sec",
    recommended: true,
  },
  {
    name: "Data Business",
    price: "£499 + VAT/mo",
    features: "Webhooks for new registrations and rating changes · full fields · 10,000-row export · 500 monitors · 10 included seats · 60 req/sec",
    recommended: false,
  },
];

const WEBHOOK_EXAMPLE = `POST /webhooks
{
  "url": "https://ops.example.com/caregist/webhooks",
  "events": ["feed.new_registration"],
  "filters": { "region": "London", "service_type": "home care" }
}

Headers on delivery:
X-CareGist-Event: feed.new_registration
X-CareGist-Signature: sha256=<hmac>

Retries:
1s, 2s, 4s backoff before final failure`;

export default function ApiLandingPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <TrackEventOnMount eventType="api_docs_visit" eventSource="api_landing" />

      {/* AEO Block */}
      <section className="bg-parchment border-b border-stone px-6 py-4 rounded-t-lg text-sm text-charcoal leading-relaxed mb-8">
        <p>
          CareGist provides daily-refreshed UK care-provider data through no-code exports, CRM-ready
          webhooks, and a developer API — all built on the same new-provider intelligence layer that
          powers the dashboard. The core product is the new registration feed: a recurring workflow for
          finding newly registered CQC providers before competitors build the relationship.
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">
        New-provider intelligence for no-code exports, CRM workflows, and developer integration
      </h1>
      <p className="text-dusk mb-2" style={{ fontFamily: "Lora" }}>
        CareGist tracked an average of {NEW_REGISTRATION_MONTHLY_AVG} newly registered CQC providers
        per month from January to March 2026. Use the data in the way your team actually works.
      </p>
      <p className="text-xs text-dusk mb-10">{NEW_REGISTRATION_MONTHLY_AVG_CAVEAT}</p>

      {/* Three delivery sections */}
      <div className="grid md:grid-cols-3 gap-4 mb-12">
        {DELIVERY_SECTIONS.map((section) => (
          <div key={section.title} className="bg-cream border border-stone rounded-lg p-5 flex flex-col">
            <span className="inline-block text-xs font-mono font-bold uppercase tracking-wide text-moss bg-moss/10 px-2 py-0.5 rounded mb-3 self-start">
              {section.tag}
            </span>
            <h3 className="font-bold text-bark text-base mb-2">{section.title}</h3>
            <p className="text-xs text-dusk mb-3 flex-1">{section.desc}</p>
            <ul className="space-y-1">
              {section.bullets.map((b) => (
                <li key={b} className="text-xs text-charcoal">
                  <span className="text-moss mr-1">✓</span>{b}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Sample Response */}
      <div className="mb-12">
        <h2 className="text-xl font-bold mb-3">Sample API response</h2>
        <pre className="bg-charcoal text-cream rounded-lg p-5 text-xs overflow-x-auto font-mono leading-relaxed">
          {SAMPLE_JSON}
        </pre>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-12">
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">CRM and webhook delivery</h2>
          <p className="text-sm text-dusk mb-4">
            Data Business plans can register outbound webhooks for{" "}
            <code className="bg-parchment px-1 rounded">feed.new_registration</code> and{" "}
            <code className="bg-parchment px-1 rounded">provider.rating_changed</code>. CareGist signs
            each payload with HMAC-SHA256 in{" "}
            <code className="bg-parchment px-1 rounded">X-CareGist-Signature</code>.
          </p>
          <p className="text-sm text-dusk mb-4">
            Failed deliveries remain visible in the dashboard so teams can spot broken endpoints without
            digging through support tickets. Retries use 1s, 2s, and 4s backoff.
          </p>
          <p className="text-xs text-dusk">
            Webhooks are designed for operational sync and CRM push — not a substitute for scheduled batch exports.
          </p>
        </div>
        <div>
          <h2 className="text-xl font-bold mb-3">Webhook example</h2>
          <pre className="bg-charcoal text-cream rounded-lg p-5 text-xs overflow-x-auto font-mono leading-relaxed">
            {WEBHOOK_EXAMPLE}
          </pre>
        </div>
      </div>

      {/* Pricing */}
      <div className="mb-12">
        <h2 className="text-xl font-bold mb-4">Plans</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {API_TIERS.map((t) => (
            <div
              key={t.name}
              className={`bg-cream border rounded-lg p-5 text-center ${
                t.recommended ? "border-clay shadow-sm" : "border-stone"
              }`}
            >
              <h3 className="font-bold text-bark">{t.name}</h3>
              {t.recommended && (
                <p className="text-[10px] uppercase tracking-[0.2em] text-clay mt-1">Recommended</p>
              )}
              <p className="text-2xl font-bold text-clay mt-2">{t.price}</p>
              <p className="text-xs text-dusk mt-2 text-left">{t.features}</p>
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
        <h2 className="text-xl font-bold mb-2">Request CRM integration</h2>
        <p className="text-sm text-dusk mb-6">
          Data Starter, Data Pro, and Data Business can begin self-serve from the pricing page. Use this
          form if you want help scoping a CRM integration, webhook workflow, higher-volume export path, or
          enterprise procurement route.
        </p>
        <ApiApplicationForm />
      </div>

      <p className="text-center text-xs text-dusk mt-8">
        {NEW_REGISTRATION_SOURCE_LINE}
        {" "}
        {CQC_INDEPENDENCE_LINE}
      </p>
    </div>
  );
}
