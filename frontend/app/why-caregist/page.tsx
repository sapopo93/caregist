import type { Metadata } from "next";

import TrackedLink from "@/components/TrackedLink";

export const metadata: Metadata = {
  title: "Why CareGist — The Intelligence Layer for UK Care-Provider Data",
  description:
    "CareGist makes CQC care-provider data operationally usable with cleaned records, geospatial search, monitoring, dashboard workflows, exports, and API access.",
  alternates: { canonical: "https://caregist.co.uk/why-caregist" },
};

const STATS = [
  { value: "National", label: "CQC-registered provider coverage", source: "CQC Public Register" },
  { value: "Daily", label: "Data refresh from the CQC register", source: "CareGist pipeline" },
  { value: "Dashboard", label: "Search, export, and monitoring workflows", source: "CareGist product" },
  { value: "Grouped", label: "Care organisations normalised for benchmarking", source: "CareGist analysis" },
];

const CONTEXT_STATS = [
  { value: "4.8 weeks", label: "Average family search time before choosing care", source: "UK care-seeker research" },
  { value: "2.2 weeks", label: "Average time from decision to move-in", source: "UK care-seeker research" },
  { value: "44%", label: "Families who later regret their care choice", source: "UK care-seeker research" },
];

const VALUE_TABLE = [
  { challenge: "Raw regulatory data is hard to use in day-to-day work", context: "The public register is valuable, but most teams still need to clean, filter, export, and compare it manually.", howWeHelp: "CareGist packages the same underlying regulatory data into search, exports, monitoring, and API workflows." },
  { challenge: "Location-aware care market work is cumbersome", context: "Nearby search, coordinates, and local authority grouping matter for matching, analytics, and local market operations.", howWeHelp: "We normalise geospatial data and make nearby search part of the product instead of a separate data engineering task." },
  { challenge: "Static snapshots go stale quickly in operational teams", context: "Analysts and operators need to know what changed since yesterday, not just what existed in the last downloaded CSV.", howWeHelp: "Provider monitoring and change alerts turn the dataset into a continuous-use workflow." },
  { challenge: "Most buyers want packaged answers before raw API plumbing", context: "Teams often need to prove value in a dashboard or export before engineering resources are assigned.", howWeHelp: "CareGist leads with dashboard and export workflows while keeping API access available when integration is justified." },
];

export default function WhyCareGistPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <div className="rounded-xl overflow-hidden mb-8 h-48 relative">
        <img
          src="https://images.unsplash.com/photo-1516549655169-df83a0774514?w=900&q=40&auto=format"
          alt="Care operations and data workflow"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-parchment/40 to-transparent" />
      </div>

      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Why CareGist</h1>
        <p className="text-dusk text-lg max-w-2xl mx-auto" style={{ fontFamily: "Lora" }}>
          The Care Quality Commission does vital work publishing the raw regulatory register. CareGist builds the operational layer above it.
        </p>
      </div>

      <div className="bg-bark rounded-xl p-8 mb-10">
        <p className="text-amber font-mono text-xs uppercase tracking-wider mb-6">What CareGist provides</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-bold text-cream">{s.value}</p>
              <p className="text-stone text-xs mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-parchment border-b border-stone rounded-t-lg px-6 py-4 text-sm text-charcoal leading-relaxed mb-8">
        <p>
          CareGist is not a replacement for the regulator. It is the operational layer above it. CQC provides the raw regulatory feed. CareGist cleans, normalises, geocodes, packages, and monitors that data so product teams, operators, and analysts can use it in recurring workflows.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-10">
        {CONTEXT_STATS.map((s) => (
          <div key={s.label} className="bg-cream border border-stone rounded-lg p-5 text-center">
            <p className="text-2xl font-bold text-clay">{s.value}</p>
            <p className="text-xs text-charcoal mt-1">{s.label}</p>
            <p className="text-[10px] text-dusk mt-1 italic">{s.source}</p>
          </div>
        ))}
      </div>

      <h2 className="text-2xl font-bold mb-6">How CareGist adds value</h2>
      <div className="space-y-3 mb-10">
        {VALUE_TABLE.map((row) => (
          <div key={row.challenge} className="bg-cream border border-stone rounded-lg p-5">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <p className="text-xs font-bold text-bark uppercase mb-1">Challenge</p>
                <p className="text-sm text-charcoal">{row.challenge}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-dusk uppercase mb-1">Context</p>
                <p className="text-sm text-charcoal">{row.context}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-moss uppercase mb-1">How we help</p>
                <p className="text-sm text-charcoal">{row.howWeHelp}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-moss/10 border border-moss/20 rounded-xl p-8 mb-10 text-center">
        <h2 className="text-2xl font-bold text-bark mb-3">Our commitment to accuracy</h2>
        <p className="text-sm text-charcoal max-w-xl mx-auto mb-4">
          We are careful about what we claim. We do not describe CareGist as live occupancy, live pricing, or real-time source data. We state what the implementation supports today: daily refresh, monitoring, exports, and workflow-ready access to cleaned regulatory data.
        </p>
        <p className="text-xs text-dusk">
          CareGist is built on CQC data published under the Open Government Licence v3.0. Crown copyright and database right. CareGist is not affiliated with or endorsed by the Care Quality Commission.
        </p>
      </div>

      <div className="bg-cream border border-stone rounded-xl p-6 mb-10">
        <h2 className="text-2xl font-bold text-bark mb-3">Where CareGist fits</h2>
        <p className="text-sm text-charcoal">
          CareGist is built for operational, continuous-use workflows on top of the CQC register: recurring search, monitoring, exports, and API access for teams that need a working data layer rather than another static snapshot.
        </p>
      </div>

      <h2 className="text-2xl font-bold mb-6">Who CareGist launches for</h2>
      <div className="grid md:grid-cols-2 gap-4 mb-10">
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">CareTech teams and product builders</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Daily-refreshed provider data through dashboard, exports, and API</li>
            <li>Stable access layer over the public register</li>
            <li>Geospatial search, coordinates, local authority, and quality fields</li>
            <li>Faster path to usable care data without rebuilding a cleaning pipeline</li>
            <li>Low-friction self-serve starting point</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Care groups and operators</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Monitor local markets and rating changes continuously</li>
            <li>Benchmark group portfolios using the same cleaned dataset</li>
            <li>Export shortlists and regional views into operating workflows</li>
            <li>Use dashboard-first access without needing internal engineering support</li>
            <li>Claim and enrich listings as a secondary workflow</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Commissioners and local authorities</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Group benchmarking across normalised care organisations</li>
            <li>Regional quality trends and rating distribution</li>
            <li>Monitoring and exports for market visibility</li>
            <li>Enriched CSV exports with quality scores and CQC report links</li>
            <li>Enterprise contact path for procurement-heavy rollouts</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Families and provider claiming</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Directory pages and provider profiles remain available</li>
            <li>Claimed providers can still add richer profile information</li>
            <li>Search and browse flows preserve existing directory utility</li>
            <li>These are valuable secondary motions, not the launch message</li>
            <li>Operational workflows stay at the centre of the product story</li>
          </ul>
        </div>
      </div>

      <div className="text-center">
        <p className="text-bark font-semibold mb-4 text-lg">Use the register as a workflow, not just a directory</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <TrackedLink href="/pricing" eventType="homepage_cta_click" eventSource="why_caregist" className="px-8 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors">
            See pricing
          </TrackedLink>
          <TrackedLink href="/api" eventType="homepage_cta_click" eventSource="why_caregist" className="px-8 py-3 border border-clay text-clay rounded-lg font-medium hover:bg-clay hover:text-white transition-colors">
            Explore API
          </TrackedLink>
          <TrackedLink href="/search" eventType="homepage_cta_click" eventSource="why_caregist" className="px-8 py-3 border border-stone text-dusk rounded-lg font-medium hover:border-clay hover:text-clay transition-colors">
            Open New Provider Lead Feed
          </TrackedLink>
        </div>
      </div>
    </div>
  );
}
