import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Why CareGist — Care Intelligence Beyond Raw CQC Data",
  description:
    "CQC inspections dropped 57%. Average ratings are 3.7 years old. CareGist adds data confidence scoring, quality analysis, and weekly intelligence to help you make safer decisions.",
  alternates: { canonical: "https://caregist.co.uk/why-caregist" },
};

const STATS = [
  { value: "57%", label: "Drop in CQC inspections since 2019", source: "DHSC Analysis, 2024" },
  { value: "3.7 yrs", label: "Average age of a CQC rating", source: "Dash Review, 2024" },
  { value: "19%", label: "Of providers have never been rated", source: "DHSC Analysis, 2024" },
  { value: "£145M", label: "Cost of CQC IT transformation (vs £28M planned)", source: "Gill IT Review, 2025" },
];

const FRICTION_TABLE = [
  { problem: "Ratings can be 3-4 years old", effect: "Families make decisions based on historical data", solution: "Data Confidence Index shows how fresh each rating is" },
  { problem: "Domain ratings mask different inspection dates", effect: "Safe might be from 2024, Caring from 2019", solution: "We flag unassessed dimensions and show inspection recency" },
  { problem: "No link between CQC rating and real experience", effect: "A 'Good' rated home may have declined since", solution: "User reviews + quality scoring + weekly change alerts" },
  { problem: "CQC API is unstable (15,000+ IT incidents)", effect: "Third-party apps break, data feeds fail", solution: "Stable API with daily refresh and cached data" },
  { problem: "Providers stuck in 'Rating Limbo'", effect: "Improved homes broadcast outdated bad ratings", solution: "Providers can document improvements for free" },
  { problem: "Commissioners lack predictive intelligence", effect: "Reactive crisis management, not proactive oversight", solution: "Group benchmarking, weekly movers, quality trends" },
];

export default function WhyCareGistPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Why CareGist exists</h1>
        <p className="text-dusk text-lg" style={{ fontFamily: "Lora" }}>
          The UK care market needs clearer, more usable intelligence than raw regulatory systems currently provide.
        </p>
      </div>

      {/* The Problem */}
      <div className="bg-bark rounded-xl p-8 mb-10">
        <p className="text-amber font-mono text-xs uppercase tracking-wider mb-6">The CQC data problem</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-bold text-cream">{s.value}</p>
              <p className="text-stone text-xs mt-1">{s.label}</p>
              <p className="text-dusk text-[10px] mt-1 italic">{s.source}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Context */}
      <div className="bg-parchment border-b border-stone rounded-t-lg px-6 py-4 text-sm text-charcoal leading-relaxed mb-8">
        <p>
          In 2023, the CQC launched a major regulatory transformation, including a new IT platform and Single Assessment Framework.
          Independent government reviews in 2024 found the transformation caused systemic operational collapse: inspection volumes
          dropped, ratings became stale, the Provider Portal failed, and the IT budget escalated from £28M to £145M.
          These are not CareGist opinions — they are findings from the Dash Review, Richards Review, and Gill IT Review,
          all commissioned by the Department of Health and Social Care.
        </p>
      </div>

      {/* What this means */}
      <h2 className="text-2xl font-bold mb-6">What this means for you</h2>

      <div className="space-y-3 mb-10">
        {FRICTION_TABLE.map((row) => (
          <div key={row.problem} className="bg-cream border border-stone rounded-lg p-5">
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <p className="text-xs font-bold text-alert uppercase mb-1">Problem</p>
                <p className="text-sm text-charcoal">{row.problem}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-dusk uppercase mb-1">Effect</p>
                <p className="text-sm text-charcoal">{row.effect}</p>
              </div>
              <div>
                <p className="text-xs font-bold text-moss uppercase mb-1">CareGist</p>
                <p className="text-sm text-charcoal">{row.solution}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Trust statement */}
      <div className="bg-moss/10 border border-moss/20 rounded-xl p-8 mb-10 text-center">
        <h2 className="text-2xl font-bold text-bark mb-3">We rank by data, not by who pays us</h2>
        <p className="text-sm text-charcoal max-w-xl mx-auto mb-4">
          CareGist quality scores and rankings are derived entirely from CQC inspection data.
          Providers cannot pay for higher scores, better rankings, or removal of negative information.
          Our assessments are independent.
        </p>
        <p className="text-xs text-dusk">
          Contains CQC data published under the Open Government Licence v3.0. Crown copyright and database right.
        </p>
      </div>

      {/* What CareGist does differently */}
      <h2 className="text-2xl font-bold mb-6">What CareGist does differently</h2>
      <div className="grid md:grid-cols-2 gap-4 mb-10">
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">For families</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Data Confidence scoring — know how fresh each rating really is</li>
            <li>Quality score (0-100) with national and local comparison</li>
            <li>Plain-English inspection summaries on 55,818 providers</li>
            <li>Personalised visit questions based on inspection findings</li>
            <li>Weekly rating change alerts for your area</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">For providers</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Document improvements since your last inspection — free</li>
            <li>Escape Rating Limbo with public improvement evidence</li>
            <li>See how you rank against nearby competitors</li>
            <li>Enhanced profiles with photos and virtual tours</li>
            <li>Monitor competitor rating changes</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">For commissioners</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Group benchmarking across 4,876 care groups</li>
            <li>Regional quality trends and rating distribution</li>
            <li>Weekly movers digest — know what changed</li>
            <li>Enriched CSV exports with quality scores</li>
            <li>Stable API — no CQC infrastructure dependency</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">For developers</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Full REST API with 55,818 providers</li>
            <li>Daily refresh from CQC — cached and stable</li>
            <li>Quality scores, ratings, coordinates, and more</li>
            <li>No CQC API key required — use ours</li>
            <li>Consistent schema — no SAF sparsity surprises</li>
          </ul>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center">
        <p className="text-bark font-semibold mb-4 text-lg">Start making safer decisions</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/search" className="px-8 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors">
            Search providers
          </Link>
          <Link href="/find-care" className="px-8 py-3 border border-clay text-clay rounded-lg font-medium hover:bg-clay hover:text-white transition-colors">
            Find care near you
          </Link>
          <Link href="/sample-report" className="px-8 py-3 border border-stone text-dusk rounded-lg font-medium hover:border-clay hover:text-clay transition-colors">
            See a sample assessment
          </Link>
        </div>
      </div>
    </div>
  );
}
