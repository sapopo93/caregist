import type { Metadata } from "next";
import SearchBar from "@/components/SearchBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrackedLink from "@/components/TrackedLink";
import {
  CQC_INDEPENDENCE_LINE,
  NEW_REGISTRATION_MONTHLY_AVG,
  NEW_REGISTRATION_MONTHLY_AVG_CAVEAT,
  NEW_REGISTRATION_MONTHLY_AVG_PERIOD,
  NEW_REGISTRATION_SOURCE_LINE,
} from "@/lib/caregist-config";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "CareGist | New CQC Provider Intelligence",
  description: `Find newly registered CQC providers before competitors do. CareGist tracked an average of ${NEW_REGISTRATION_MONTHLY_AVG} newly registered providers per month from January to March 2026.`,
};

const sampleFeed = [
  {
    provider: "Ashwell Community Care Ltd",
    region: "London",
    service: "Home care",
    signal: "Newly registered",
    fit: "High",
  },
  {
    provider: "Northpoint Supported Living",
    region: "North West",
    service: "Supported living",
    signal: "Newly registered",
    fit: "High",
  },
  {
    provider: "Meadowbrook Nursing Services",
    region: "South East",
    service: "Nursing homes",
    signal: "Newly registered",
    fit: "Medium",
  },
];

const buyerUseCases = [
  {
    buyer: "Suppliers to care providers",
    pain: "Find new accounts before competitors win them",
    promise: "Daily new-provider lead feed, filtered by region and service type.",
  },
  {
    buyer: "Compliance consultants",
    pain: "New providers need policies and CQC readiness at setup",
    promise: "Reach providers at the exact moment they are choosing governance support.",
  },
  {
    buyer: "Recruiters and staffing firms",
    pain: "New services need carers and managers fast",
    promise: "Identify newly registered operators by region and service category.",
  },
  {
    buyer: "Software vendors",
    pain: "New providers need systems before legacy tools are embedded",
    promise: "Build outbound lists from live CQC registration movement.",
  },
  {
    buyer: "Care-sector service providers",
    pain: "New entrants need accounts, insurance, training, and marketing",
    promise: "Reach providers while they are choosing suppliers.",
  },
  {
    buyer: "Market analysts and care groups",
    pain: "Track where new care capacity is appearing",
    promise: "Monitor competitors, regions, and ownership movement over time.",
  },
];

const workflowSteps = [
  { step: "Filter", action: "Choose region, service type, and registration window." },
  { step: "Prioritise", action: "High-confidence newly registered providers first. Sort by fit." },
  { step: "Export", action: "CSV, Excel, API, or saved filter for your CRM workflow." },
  { step: "Contact", action: "Reach providers while they are still choosing suppliers." },
  { step: "Monitor", action: "Save the view and track registration movement weekly." },
];

export default function HomePage() {
  const proofPoints = [
    {
      title: `${NEW_REGISTRATION_MONTHLY_AVG}/month`,
      label: "Newly registered CQC providers",
      description: `Average tracked from ${NEW_REGISTRATION_MONTHLY_AVG_PERIOD} 2026.`,
    },
    {
      title: "Daily",
      label: "Registration movement tracking",
      description: "Built around fresh CQC registration changes.",
    },
    {
      title: "Export-ready",
      label: "Commercial lead workflow",
      description: "Filter, prioritise, export, and monitor provider opportunities.",
    },
  ];

  return (
    <div className="bg-cream">
      <TrackEventOnMount eventType="homepage_view" eventSource="homepage" />

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-stone bg-charcoal text-cream">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=1600&q=70&auto=format')",
            backgroundPosition: "center",
            backgroundSize: "cover",
          }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(43,37,32,0.96),rgba(43,37,32,0.86),rgba(43,37,32,0.72))]" />

        <div className="relative z-10 mx-auto grid max-w-6xl gap-8 px-6 py-10 md:py-16 lg:grid-cols-[0.92fr_1.08fr] lg:items-center">
          <div>
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-amber">
              New-provider commercial intelligence for the UK care market
            </p>
            <h1 className="max-w-3xl text-[2.35rem] font-extrabold leading-[1.04] text-cream md:text-6xl">
              Find newly registered CQC providers before your competitors do.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-stone md:text-lg" style={{ fontFamily: "Lora" }}>
              CareGist tracked an average of {NEW_REGISTRATION_MONTHLY_AVG} newly registered CQC providers per
              month from January to March 2026, helping suppliers, consultants, recruiters, software vendors,
              and care-sector service providers reach providers while they are still choosing who to work with.
            </p>

            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <TrackedLink
                href="/dashboard"
                eventType="homepage_cta_click"
                eventSource="homepage_hero"
                meta={{ cta: "see_new_providers_in_my_region" }}
                className="inline-flex min-h-12 items-center justify-center rounded-lg bg-amber px-6 py-3 text-sm font-bold text-charcoal transition-colors hover:bg-cream"
              >
                See new providers in my region
              </TrackedLink>
              <TrackedLink
                href="/pricing"
                eventType="homepage_cta_click"
                eventSource="homepage_hero"
                meta={{ cta: "view_pricing" }}
                className="inline-flex min-h-12 items-center justify-center rounded-lg border border-cream/35 px-6 py-3 text-sm font-bold text-cream transition-colors hover:bg-white/10"
              >
                View pricing
              </TrackedLink>
            </div>

            <div className="mt-7 max-w-xl">
              <div className="grid grid-cols-3 gap-3">
                <div className="border-l border-amber/50 pl-3">
                  <p className="text-sm font-extrabold text-amber leading-none">
                    {NEW_REGISTRATION_MONTHLY_AVG}/month
                  </p>
                  <p className="mt-1 text-[11px] font-medium text-stone leading-4">
                    {NEW_REGISTRATION_MONTHLY_AVG_PERIOD} 2026 average
                  </p>
                </div>
                <div className="border-l border-amber/50 pl-3">
                  <p className="text-xs font-bold leading-4 text-stone">Daily tracking</p>
                  <p className="mt-1 text-[11px] font-medium leading-4 text-stone/75">
                    CQC registration movement
                  </p>
                </div>
                <div className="border-l border-amber/50 pl-3">
                  <p className="text-xs font-bold leading-4 text-stone">Export-ready</p>
                  <p className="mt-1 text-[11px] font-medium leading-4 text-stone/75">
                    CSV, Excel, CRM, or API
                  </p>
                </div>
              </div>
              <p className="mt-3 text-[11px] text-stone/60 leading-5">
                {NEW_REGISTRATION_MONTHLY_AVG_CAVEAT}
              </p>
            </div>
          </div>

          {/* Live preview panel */}
          <div className="rounded-xl border border-white/15 bg-cream text-charcoal shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone px-4 py-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-clay">New provider lead feed</p>
                <p className="mt-1 text-xs text-dusk">Registration window: last 30 days</p>
              </div>
              <span className="rounded-full bg-moss px-3 py-1 text-xs font-bold text-cream">Live</span>
            </div>

            <div className="p-4">
              <div className="overflow-hidden rounded-lg border border-stone bg-white">
                <div className="grid grid-cols-[1.4fr_0.8fr_0.9fr_0.55fr] bg-parchment px-3 py-2 text-[11px] font-bold uppercase tracking-[0.08em] text-dusk">
                  <span>Provider</span>
                  <span>Region</span>
                  <span>Service</span>
                  <span className="text-right">Fit</span>
                </div>
                {sampleFeed.map((row) => (
                  <div
                    key={row.provider}
                    className="grid grid-cols-[1.4fr_0.8fr_0.9fr_0.55fr] items-center border-t border-stone px-3 py-3 text-xs"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-bold text-charcoal">{row.provider}</p>
                      <p className="mt-1 text-[11px] text-moss font-medium">{row.signal}</p>
                    </div>
                    <span className="text-dusk">{row.region}</span>
                    <span className="text-dusk">{row.service}</span>
                    <span className={`text-right font-bold ${row.fit === "High" ? "text-moss" : "text-dusk"}`}>
                      {row.fit}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {["Get this week's lead list", "Save this filter", "Send to CRM"].map((action) => (
                  <span key={action} className="rounded-full border border-stone px-3 py-1.5 text-xs font-semibold text-bark">
                    {action}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Proof strip */}
      <section className="border-b border-stone bg-parchment py-8">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-6 md:grid-cols-3">
          {proofPoints.map((stat) => (
            <div key={stat.label} className="bg-cream p-5">
              <p className="text-3xl font-extrabold leading-none text-clay">{stat.title}</p>
              <p className="mt-2 text-xs font-semibold uppercase tracking-[0.08em] text-dusk">{stat.label}</p>
              <p className="mt-2 text-xs text-dusk leading-5">{stat.description}</p>
            </div>
          ))}
        </div>
        <p className="mx-auto mt-6 max-w-6xl px-6 text-[11px] text-dusk leading-5">
          {NEW_REGISTRATION_MONTHLY_AVG_CAVEAT}
        </p>
      </section>

      {/* The problem */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid gap-8 lg:grid-cols-[1fr_1fr] lg:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">The problem</p>
            <h2 className="mt-3 text-3xl font-extrabold leading-tight md:text-4xl">
              New providers are invisible until competitors win the relationship.
            </h2>
          </div>
          <div className="text-sm leading-7 text-dusk" style={{ fontFamily: "Lora" }}>
            <p>
              Most suppliers wait for Google results, directory referrals, or outdated CQC exports.
              By then, the newly registered provider may already have chosen their policy provider,
              compliance consultant, software vendor, recruiter, and marketing partner.
            </p>
            <p className="mt-4">
              CareGist surfaces registration movement early — filtered to your region, your service category,
              and your commercial window — so you reach providers while they are choosing suppliers.
            </p>
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="bg-charcoal py-12 text-cream">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-8">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber">From signal to workflow</p>
            <h2 className="mt-3 text-3xl font-extrabold leading-tight text-cream md:text-4xl">
              Filter, prioritise, export, and monitor.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone" style={{ fontFamily: "Lora" }}>
              Choose region, service type, confidence level, and registration window — then export the
              matched providers into your CRM, spreadsheet, or API workflow.
            </p>
          </div>

          <div className="grid gap-px bg-white/10 md:grid-cols-5">
            {workflowSteps.map(({ step, action }) => (
              <div key={step} className="bg-charcoal p-5">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber">{step}</p>
                <p className="mt-3 text-sm leading-6 text-stone">{action}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap gap-4">
            <TrackedLink
              href="/dashboard"
              eventType="homepage_cta_click"
              eventSource="homepage_workflow"
              meta={{ cta: "see_new_providers_in_my_region" }}
              className="inline-flex items-center justify-center rounded-lg bg-amber px-6 py-3 text-sm font-bold text-charcoal transition-colors hover:bg-cream"
            >
              See new providers in my region
            </TrackedLink>
            <TrackedLink
              href="/search"
              eventType="homepage_cta_click"
              eventSource="homepage_workflow"
              meta={{ cta: "open_lead_feed" }}
              className="inline-flex items-center justify-center rounded-lg border border-cream/35 px-6 py-3 text-sm font-bold text-cream transition-colors hover:bg-white/10"
            >
              Open New Provider Lead Feed
            </TrackedLink>
          </div>
        </div>
      </section>

      {/* Buyer use cases */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="mb-8">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">Who uses it</p>
          <h2 className="mt-3 text-3xl font-extrabold leading-tight md:text-4xl">
            Built for suppliers, consultants, recruiters, software vendors, and care-sector service providers.
          </h2>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {buyerUseCases.map((card, index) => (
            <div key={card.buyer} className="border border-stone bg-cream p-5">
              <p className="text-sm font-extrabold text-clay">0{index + 1}</p>
              <h3 className="mt-3 text-base font-bold text-bark">{card.buyer}</h3>
              <p className="mt-2 text-xs font-medium text-dusk">{card.pain}</p>
              <p className="mt-3 text-sm leading-6 text-bark">{card.promise}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing CTA */}
      <section className="border-y border-stone bg-parchment py-12">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">Get started</p>
          <h2 className="mt-3 text-3xl font-extrabold leading-tight">
            Start with the new-provider lead feed.
          </h2>
          <p className="mt-4 text-sm leading-7 text-dusk" style={{ fontFamily: "Lora" }}>
            Export newly registered CQC providers every week. Filter by region, service type, and
            registration window. Save recurring views and push records into CRM or API workflows.
          </p>
          <div className="mt-7 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <TrackedLink
              href="/dashboard"
              eventType="homepage_cta_click"
              eventSource="homepage_pricing_cta"
              meta={{ cta: "see_new_providers_in_my_region" }}
              className="inline-flex min-h-12 items-center justify-center rounded-lg bg-clay px-8 py-3 text-sm font-bold text-cream transition-colors hover:bg-bark"
            >
              See new providers in my region
            </TrackedLink>
            <TrackedLink
              href="/pricing"
              eventType="homepage_cta_click"
              eventSource="homepage_pricing_cta"
              meta={{ cta: "view_pricing" }}
              className="inline-flex min-h-12 items-center justify-center rounded-lg border border-stone px-8 py-3 text-sm font-bold text-bark transition-colors hover:bg-cream"
            >
              View pricing
            </TrackedLink>
          </div>
        </div>
      </section>

      {/* Directory (demoted) */}
      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr] lg:items-start">
          <div>
            <h2 className="text-2xl font-extrabold leading-tight">Explore the wider provider universe</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-dusk" style={{ fontFamily: "Lora" }}>
              Need a wider lookup beyond newly registered providers? Search the full CQC-registered
              dataset, then move into the new-provider lead feed, monitoring, exports, and API workflows
              when the task is recurring.
            </p>
          </div>
          <div className="border border-stone bg-parchment p-5">
            <SearchBar fetchServiceTypes={false} showAdvancedToggle={false} />
          </div>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { name: "Care Homes", slug: "care-homes" },
            { name: "Nursing Homes", slug: "nursing-homes" },
            { name: "Home Care", slug: "home-care" },
            { name: "GP Surgeries", slug: "gp-surgeries" },
            { name: "Dental Practices", slug: "dental" },
            { name: "Supported Living", slug: "supported-living" },
          ].map((type) => (
            <TrackedLink
              key={type.name}
              href={`/services/${type.slug}`}
              eventType="homepage_cta_click"
              eventSource="homepage_directory"
              meta={{ service_type: type.slug }}
              className="border border-stone bg-cream p-4 transition-colors hover:border-clay"
            >
              <div className="font-bold text-bark">{type.name}</div>
              <div className="mt-1 text-xs font-medium text-dusk">Browse current provider records</div>
            </TrackedLink>
          ))}
        </div>
      </section>

      {/* Regional entry points */}
      <section className="border-y border-stone bg-parchment py-10">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">Regional entry points</p>
              <h2 className="mt-2 text-2xl font-extrabold">Browse new-provider movement by region</h2>
            </div>
            <TrackedLink
              href="/api"
              eventType="homepage_cta_click"
              eventSource="homepage_api"
              meta={{ cta: "request_crm_integration" }}
              className="text-sm font-bold text-clay underline underline-offset-4 hover:text-bark"
            >
              Request CRM integration
            </TrackedLink>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-2 md:grid-cols-5">
            {[
              { name: "London", slug: "london" },
              { name: "South East", slug: "south-east" },
              { name: "North West", slug: "north-west" },
              { name: "East", slug: "east" },
              { name: "West Midlands", slug: "west-midlands" },
              { name: "South West", slug: "south-west" },
              { name: "Yorkshire", slug: "yorkshire-humberside" },
              { name: "East Midlands", slug: "east-midlands" },
              { name: "North East", slug: "north-east" },
            ].map((region) => (
              <TrackedLink
                key={region.slug}
                href={`/region/${region.slug}`}
                eventType="homepage_cta_click"
                eventSource="homepage_regions"
                meta={{ region: region.slug }}
                className="bg-cream px-3 py-3 text-center text-xs font-bold text-bark transition-colors hover:bg-white hover:text-clay"
              >
                {region.name}
              </TrackedLink>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12 pt-8">
        <EmailCaptureStrip
          source="homepage"
          heading="Get this week's CQC registration movement in your area — free."
          subheading="Weekly digest of newly registered providers, rating changes, and local market movement. Unsubscribe anytime."
        />
      </section>

      <section className="mx-auto max-w-5xl px-6 py-6 text-center text-xs text-dusk">
        <p>{NEW_REGISTRATION_SOURCE_LINE}</p>
        <p className="mt-2">{CQC_INDEPENDENCE_LINE}</p>
        <p className="mt-2">
          Built for suppliers, consultants, recruiters, software vendors, and care-sector service
          providers targeting the UK care market.
        </p>
      </section>

      <TrustSignal />
    </div>
  );
}
