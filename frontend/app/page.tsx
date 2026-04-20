import type { Metadata } from "next";
import SearchBar from "@/components/SearchBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrackedLink from "@/components/TrackedLink";

export const metadata: Metadata = {
  title: "CareGist - UK Care-Provider Market Intelligence",
  description:
    "Daily CQC registration intelligence for CareTech sales, growth, RevOps, and market teams. Track new providers, filter by area, export records, and monitor market movement.",
};

const signalMetrics = [
  { label: "Registration window", value: "Last 7 days", note: "Example filter" },
  { label: "Confidence view", value: "High fit", note: "Matched location fields" },
  { label: "Market focus", value: "London", note: "Example region" },
  { label: "Service focus", value: "Home care", note: "Example service" },
];

const sampleFeed = [
  {
    provider: "Ashwell Community Care Ltd",
    region: "London",
    service: "Home care",
    registered: "Today",
    confidence: "High",
  },
  {
    provider: "Northpoint Supported Living",
    region: "North West",
    service: "Supported living",
    registered: "Yesterday",
    confidence: "High",
  },
  {
    provider: "Meadowbrook Nursing Services",
    region: "South East",
    service: "Nursing homes",
    registered: "2 days ago",
    confidence: "High",
  },
];

const useCases = [
  {
    title: "Prioritise fresh sales accounts",
    copy: "See new CQC locations while they are still early enough for outreach, onboarding, and territory planning.",
  },
  {
    title: "Monitor market movement",
    copy: "Track where new care capacity is appearing by region, local authority, provider type, and service category.",
  },
  {
    title: "Move records into workflows",
    copy: "Export filtered lists, save repeat views, or connect the feed to CRM, marketplace, and analytics systems.",
  },
];

const coverageStats = [
  { value: "National", label: "CQC location coverage" },
  { value: "Daily", label: "source refresh cadence" },
  { value: "Grouped", label: "care organisations normalised" },
  { value: "CSV + API", label: "workflow delivery options" },
];

export default function HomePage() {
  return (
    <div className="bg-cream">
      <TrackEventOnMount eventType="homepage_view" eventSource="homepage" />

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
              Care-provider market intelligence
            </p>
            <h1
              className="max-w-3xl text-[2.35rem] font-extrabold leading-[1.04] text-cream md:text-6xl"
              style={{ color: "var(--color-cream)" }}
            >
              Find newly registered care providers before your competitors do.
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-stone md:text-lg" style={{ fontFamily: "Lora" }}>
              CareGist turns CQC registration changes into a daily decision feed for sales, growth,
              RevOps, and market teams: filter fresh providers, size local movement, export records,
              and monitor the accounts that matter.
            </p>

            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <TrackedLink
                href="/search"
                eventType="homepage_cta_click"
                eventSource="homepage_hero"
                meta={{ cta: "view_live_feed" }}
                className="inline-flex min-h-12 items-center justify-center rounded-lg bg-amber px-6 py-3 text-sm font-bold text-charcoal transition-colors hover:bg-cream"
              >
                View live feed
              </TrackedLink>
              <TrackedLink
                href="/pricing"
                eventType="homepage_cta_click"
                eventSource="homepage_hero"
                meta={{ cta: "see_plans" }}
                className="inline-flex min-h-12 items-center justify-center rounded-lg border border-cream/35 px-6 py-3 text-sm font-bold text-cream transition-colors hover:bg-white/10"
              >
                See plans
              </TrackedLink>
            </div>

            <div className="mt-7 grid grid-cols-3 gap-3 max-w-xl">
              {["Daily CQC refresh", "Export-ready records", "Saved monitoring"].map((proof) => (
                <div key={proof} className="border-l border-amber/50 pl-3 text-xs font-medium leading-5 text-stone">
                  {proof}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-white/15 bg-cream text-charcoal shadow-2xl">
            <div className="flex items-center justify-between border-b border-stone px-4 py-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-clay">Example signal preview</p>
                <p className="mt-1 text-xs text-dusk">Illustrative workflow</p>
              </div>
              <span className="rounded-full bg-moss px-3 py-1 text-xs font-bold text-cream">Sample</span>
            </div>

            <div className="grid grid-cols-2 border-b border-stone">
              {signalMetrics.map((metric) => (
                <div key={metric.label} className="border-stone p-4 odd:border-r [&:nth-child(-n+2)]:border-b">
                  <p className="text-xs font-medium text-dusk">{metric.label}</p>
                  <p className="mt-2 text-2xl font-extrabold leading-none text-charcoal">{metric.value}</p>
                  <p className="mt-2 text-xs font-medium text-moss">{metric.note}</p>
                </div>
              ))}
            </div>

            <div className="p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-bold text-bark">Example provider feed</p>
                <p className="text-xs text-dusk">Sample filter</p>
              </div>
              <div className="overflow-hidden rounded-lg border border-stone bg-white">
                <div className="grid grid-cols-[1.35fr_0.75fr_0.9fr_0.65fr] bg-parchment px-3 py-2 text-[11px] font-bold uppercase tracking-[0.08em] text-dusk">
                  <span>Provider</span>
                  <span>Region</span>
                  <span>Service</span>
                  <span className="text-right">Fit</span>
                </div>
                {sampleFeed.map((row) => (
                  <div
                    key={row.provider}
                    className="grid grid-cols-[1.35fr_0.75fr_0.9fr_0.65fr] items-center border-t border-stone px-3 py-3 text-xs"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-bold text-charcoal">{row.provider}</p>
                      <p className="mt-1 text-[11px] text-dusk">{row.registered}</p>
                    </div>
                    <span className="text-dusk">{row.region}</span>
                    <span className="text-dusk">{row.service}</span>
                    <span className="text-right font-bold text-moss">{row.confidence}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {["Export CSV", "Save filter", "Send to CRM"].map((action) => (
                  <span key={action} className="rounded-full border border-stone px-3 py-1.5 text-xs font-semibold text-bark">
                    {action}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-stone bg-parchment py-8">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-4 px-6 md:grid-cols-4">
          {coverageStats.map((stat) => (
            <div key={stat.label} className="bg-cream p-5">
              <p className="text-3xl font-extrabold leading-none text-clay">{stat.value}</p>
              <p className="mt-2 text-xs font-semibold uppercase tracking-[0.08em] text-dusk">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-b border-stone bg-cream py-6">
        <div className="mx-auto grid max-w-6xl gap-4 px-6 md:grid-cols-[0.75fr_1.25fr] md:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">Data freshness</p>
            <h2 className="mt-2 text-2xl font-extrabold leading-tight">Daily refresh, not real-time source data.</h2>
          </div>
          <p className="text-sm leading-6 text-dusk" style={{ fontFamily: "Lora" }}>
            CareGist refreshes against the CQC public register on a daily cadence, then normalises
            registration, location, rating, and provider fields for workflow use. We avoid presenting
            sample metrics as live totals unless they are backed by the product feed.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">Manager use cases</p>
            <h2 className="mt-3 text-3xl font-extrabold leading-tight md:text-4xl">
              The page should answer, "What changed, where, and what should we do?"
            </h2>
            <p className="mt-4 text-sm leading-6 text-dusk" style={{ fontFamily: "Lora" }}>
              CareGist is positioned around fast commercial decisions, not passive directory browsing.
              The interface surfaces new market activity first, then gives teams paths to act.
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {useCases.map((card, index) => (
              <div key={card.title} className="border border-stone bg-cream p-5">
                <p className="text-sm font-extrabold text-clay">0{index + 1}</p>
                <h3 className="mt-3 text-base font-bold text-bark" style={{ fontFamily: "DM Sans" }}>
                  {card.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{card.copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-charcoal py-12 text-cream">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 lg:grid-cols-[1fr_0.9fr] lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber">From signal to workflow</p>
            <h2 className="mt-3 text-3xl font-extrabold leading-tight text-cream md:text-4xl" style={{ color: "var(--color-cream)" }}>
              Filter a market in seconds, then push the result into the next system.
            </h2>
            <div className="mt-6 grid gap-3 text-sm text-stone md:grid-cols-3">
              {[
                "Select region, service type, authority, and registration window.",
                "Review confidence, source date, and matched location fields.",
                "Save the view, export the list, or use API access on paid plans.",
              ].map((step) => (
                <div key={step} className="border-t border-amber/50 pt-3 leading-6">
                  {step}
                </div>
              ))}
            </div>
          </div>
          <div className="border border-white/15 bg-bark/40 p-5">
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Region", "North West"],
                ["Service", "Home care"],
                ["Window", "Last 30 days"],
                ["Result", "Filtered providers"],
              ].map(([label, value]) => (
                <div key={label} className="bg-charcoal/70 p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-amber">{label}</p>
                  <p className="mt-2 font-bold text-cream">{value}</p>
                </div>
              ))}
            </div>
            <TrackedLink
              href="/search"
              eventType="homepage_cta_click"
              eventSource="homepage_workflow"
              meta={{ cta: "open_data_explorer" }}
              className="mt-4 inline-flex w-full items-center justify-center rounded-lg bg-cream px-5 py-3 text-sm font-bold text-charcoal transition-colors hover:bg-amber"
            >
              Open the data explorer
            </TrackedLink>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr] lg:items-start">
          <div>
            <h2 className="text-3xl font-extrabold leading-tight">Explore the underlying provider dataset</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-dusk" style={{ fontFamily: "Lora" }}>
              Need a lighter lookup? Search the provider directory, then move into richer feed,
              monitoring, export, and API workflows when the task needs repeatability.
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
              <div className="mt-1 text-xs font-medium text-dusk">Browse providers</div>
            </TrackedLink>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 pb-12">
        <EmailCaptureStrip source="homepage" />
      </section>

      <section className="border-y border-stone bg-parchment py-10">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">Regional entry points</p>
              <h2 className="mt-2 text-2xl font-extrabold">Browse market activity by region</h2>
            </div>
            <TrackedLink
              href="/api"
              eventType="homepage_cta_click"
              eventSource="homepage_api"
              meta={{ cta: "explore_api" }}
              className="text-sm font-bold text-clay underline underline-offset-4 hover:text-bark"
            >
              Explore API access
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

      <section className="mx-auto max-w-5xl px-6 py-6 text-center text-xs text-dusk">
        <p>
          Provider data sourced from the Care Quality Commission (CQC). CareGist is not affiliated
          with or endorsed by CQC. For official inspection reports, visit{" "}
          <a href="https://www.cqc.org.uk" className="underline text-clay">
            cqc.org.uk
          </a>.
        </p>
      </section>

      <TrustSignal />
    </div>
  );
}
