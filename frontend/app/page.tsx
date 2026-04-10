import type { Metadata } from "next";
import SearchBar from "@/components/SearchBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import TrackedLink from "@/components/TrackedLink";

export const metadata: Metadata = {
  title: "CareGist — The Intelligence Layer for UK Care-Provider Data",
  description:
    "Daily-refreshed UK care-provider data for dashboard, exports, monitoring, and API workflows. Built for CareTech teams and care operators first.",
};

export default function HomePage() {
  const heroProof = [
    "55,818 providers cleaned and normalised",
    "Daily refresh cadence for regulatory changes",
    "Dashboard, exports, watchlists, and API access",
  ];

  return (
    <div>
      <TrackEventOnMount eventType="homepage_view" eventSource="homepage" />
      {/* Hero */}
      <section className="relative text-cream py-12 md:py-20 px-6 overflow-hidden">
        <div className="absolute inset-0" style={{
          backgroundImage: "url('https://images.unsplash.com/photo-1516549655169-df83a0774514?w=1200&q=60&auto=format')",
          backgroundSize: "cover", backgroundPosition: "center top"
        }} />
        <div className="absolute inset-0 bg-bark/75" />
        <div className="max-w-5xl mx-auto relative z-10">
          <p className="text-amber text-sm md:text-base font-medium tracking-wide uppercase mb-4">
            Daily-refreshed UK care-provider intelligence
          </p>
          <h1
            className="text-4xl md:text-6xl font-bold mb-4 max-w-4xl text-cream"
            style={{ fontFamily: "Playfair Display", color: "var(--color-cream)" }}
          >
            CQC data you can use in live care-market workflows
          </h1>
          <p className="text-stone text-base md:text-lg mb-8 max-w-3xl" style={{ fontFamily: "Lora" }}>
            CareGist gives care operators and CareTech teams cleaned provider records, geospatial search, watchlists, exports, and API access without forcing them to work from the raw register.
          </p>
          <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr] items-start">
            <div>
              <div className="flex flex-wrap gap-3 mb-5">
                <TrackedLink
                  href="/pricing"
                  eventType="homepage_cta_click"
                  eventSource="homepage_hero"
                  meta={{ cta: "see_pricing" }}
                  className="inline-flex items-center justify-center px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-amber transition-colors"
                >
                  See pricing
                </TrackedLink>
                <TrackedLink
                  href="/api"
                  eventType="homepage_cta_click"
                  eventSource="homepage_hero"
                  meta={{ cta: "view_api" }}
                  className="inline-flex items-center justify-center px-6 py-3 border border-cream/40 text-cream rounded-lg font-medium hover:bg-white/10 transition-colors"
                >
                  Explore API
                </TrackedLink>
              </div>
              <div className="grid gap-3 sm:grid-cols-3 max-w-3xl">
                {heroProof.map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-white/12 bg-black/10 px-4 py-4 text-sm text-cream/90 backdrop-blur-sm"
                  >
                    {item}
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap gap-4 text-cream/85 text-sm font-medium mt-6">
                <span>55,818 providers</span>
                <span className="text-amber">|</span>
                <span>Updated daily</span>
                <span className="text-amber">|</span>
                <span>Dashboard + exports + API</span>
              </div>
            </div>
            <div className="bg-charcoal/75 border border-white/10 rounded-3xl p-6 backdrop-blur-sm">
              <p className="text-xs uppercase tracking-[0.2em] text-amber mb-3">What you can do first</p>
              <div className="space-y-3 text-sm text-stone">
                <div className="rounded-2xl border border-white/10 p-4">
                  Search nearby providers and inspect cleaner records instead of raw regulatory tables.
                </div>
                <div className="rounded-2xl border border-white/10 p-4">
                  Track shortlist changes and export structured data into operating or product workflows.
                </div>
              </div>
              <TrackedLink
                href="/search"
                eventType="homepage_cta_click"
                eventSource="homepage_hero"
                meta={{ cta: "open_data_explorer" }}
                className="inline-flex items-center justify-center mt-4 text-amber font-medium underline underline-offset-4 hover:text-cream transition-colors"
              >
                Open the data explorer
              </TrackedLink>
            </div>
          </div>
        </div>
      </section>

      {/* Value propositions — cards with backgrounds */}
      <section className="bg-cream py-10 border-b border-stone">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-5">
            {[
              {
                icon: "\u{1F5FA}",
                title: "Geospatially useful",
                desc: "Radius search, coordinates, local authority fields, and location-aware exports for operational market work.",
              },
              {
                icon: "\u{1F4E6}",
                title: "Workflow-ready exports",
                desc: "Move from browser to CSV in one step. Starter proves value quickly; Pro and Business support heavier recurring workflows.",
              },
              {
                icon: "\u{1F514}",
                title: "Continuous monitoring",
                desc: "Watch provider shortlists and catch rating changes without checking the raw register manually.",
              },
            ].map((card) => (
              <div key={card.title} className="bg-parchment border border-stone rounded-xl p-5 flex gap-4">
                <div className="w-11 h-11 bg-clay/15 rounded-lg flex items-center justify-center shrink-0">
                  <span className="text-xl">{card.icon}</span>
                </div>
                <div>
                  <h3 className="font-bold text-bark mb-1 text-sm">{card.title}</h3>
                  <p className="text-xs text-dusk leading-relaxed">{card.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats + CTAs combined */}
      <section className="max-w-5xl mx-auto px-6 py-10">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 text-center mb-10">
          {[
            { value: "55,818", label: "Providers" },
            { value: "Daily", label: "Refresh cadence" },
            { value: "4,876", label: "Groups" },
            { value: "API", label: "Available on paid plans" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl md:text-4xl font-extrabold text-clay">{stat.value}</div>
              <div className="text-xs text-dusk mt-1 font-medium">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <div className="grid md:grid-cols-2 gap-5">
          <TrackedLink
            href="/api"
            eventType="homepage_cta_click"
            eventSource="homepage_midpage"
            meta={{ cta: "caretech_segment" }}
            className="block bg-bark text-cream rounded-xl p-7 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-xl font-bold mb-2" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              For CareTech teams
            </h2>
            <p className="text-stone text-sm">
              Start with a dashboard and export workflow, then plug CareGist data into matching, CRM, marketplace, or analytics products.
            </p>
          </TrackedLink>
          <TrackedLink
            href="/groups"
            eventType="homepage_cta_click"
            eventSource="homepage_midpage"
            meta={{ cta: "operator_segment" }}
            className="block bg-bark text-cream rounded-xl p-7 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-xl font-bold mb-2" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              For care operators
            </h2>
            <p className="text-stone text-sm">
              Monitor local markets, benchmark care groups, and export cleaner regulatory data into your operating workflows.
            </p>
          </TrackedLink>
        </div>
      </section>

      {/* Email Capture */}
      <section className="max-w-5xl mx-auto px-6 py-4">
        <EmailCaptureStrip source="homepage" />
      </section>

      {/* Browse by Service Type + Region combined */}
      <section className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-xl font-bold mb-4">Secondary directory entry points</h2>
        <p className="text-dusk mb-4" style={{ fontFamily: "Lora" }}>
          CareGist still supports search, directory SEO, and provider claiming. Those flows stay available, but the launch product leads with the intelligence layer above them.
        </p>
        <div className="bg-cream border border-stone rounded-2xl p-5 mb-8">
          <p className="text-sm font-semibold text-bark mb-3">Explore the directory when you need a lighter-weight lookup</p>
          <SearchBar fetchServiceTypes={false} showAdvancedToggle={false} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-10">
          {[
            { name: "Care Homes", count: "10,309", slug: "care-homes" },
            { name: "Nursing Homes", count: "4,386", slug: "nursing-homes" },
            { name: "Home Care", count: "14,240", slug: "home-care" },
            { name: "GP Surgeries", count: "9,367", slug: "gp-surgeries" },
            { name: "Dental Practices", count: "12,004", slug: "dental" },
            { name: "Supported Living", count: "4,727", slug: "supported-living" },
          ].map((type) => (
            <TrackedLink
              key={type.name}
              href={`/services/${type.slug}`}
              eventType="homepage_cta_click"
              eventSource="homepage_directory"
              meta={{ service_type: type.slug }}
              className="bg-cream border border-stone rounded-lg p-3 hover:border-clay transition-colors"
            >
              <div className="font-semibold text-bark text-sm">{type.name}</div>
              <div className="text-xs text-dusk">{type.count} providers</div>
            </TrackedLink>
          ))}
        </div>

        <h2 className="text-xl font-bold mb-4">Browse by region</h2>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
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
          ].map((r) => (
            <TrackedLink
              key={r.slug}
              href={`/region/${r.slug}`}
              eventType="homepage_cta_click"
              eventSource="homepage_regions"
              meta={{ region: r.slug }}
              className="bg-cream border border-stone rounded-lg p-2.5 text-center hover:border-clay transition-colors text-xs font-medium text-bark"
            >
              {r.name}
            </TrackedLink>
          ))}
        </div>
      </section>

      {/* Why CareGist */}
      <section className="bg-bark py-8">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
            Why operators and CareTech teams choose CareGist
          </h2>
          <div className="grid md:grid-cols-3 gap-6 text-stone text-xs mt-4">
            <div>
              <p className="text-cream font-semibold mb-1">Usable</p>
              <p>CQC provides the raw regulatory feed. CareGist makes it usable inside workflows.</p>
            </div>
            <div>
              <p className="text-cream font-semibold mb-1">Monitorable</p>
              <p>Daily-refreshed data with continuous monitoring and event-driven alerts.</p>
            </div>
            <div>
              <p className="text-cream font-semibold mb-1">Packaged for work</p>
              <p>Dashboard-first access for operators, exports for analysts, and API access for CareTech teams.</p>
            </div>
          </div>
          <TrackedLink href="/why-caregist" eventType="homepage_cta_click" eventSource="homepage_why" className="inline-block mt-4 text-amber underline text-xs hover:text-cream">
            Learn more about CareGist
          </TrackedLink>
        </div>
      </section>

      {/* CQC Attribution */}
      <section className="max-w-5xl mx-auto px-6 py-6 text-center text-xs text-dusk">
        <p>
          Provider data sourced from the Care Quality Commission (CQC).
          CareGist is not affiliated with or endorsed by CQC.
          For official inspection reports, visit{" "}
          <a href="https://www.cqc.org.uk" className="underline text-clay">cqc.org.uk</a>.
        </p>
      </section>

      <TrustSignal />
    </div>
  );
}
