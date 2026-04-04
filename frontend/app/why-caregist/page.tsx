import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Why CareGist — Clearer Care Intelligence for Better Decisions",
  description:
    "CareGist builds on official CQC data to provide quality scoring, data confidence indicators, and weekly intelligence — helping families, providers, and commissioners make better-informed decisions.",
  alternates: { canonical: "https://caregist.co.uk/why-caregist" },
};

const STATS = [
  { value: "55,818", label: "CQC-registered providers in our database", source: "CQC Public Register" },
  { value: "Daily", label: "Data refresh from the CQC register", source: "CareGist pipeline" },
  { value: "0–100", label: "Quality score for every rated provider", source: "CareGist methodology" },
  { value: "4,876", label: "Care groups benchmarked nationally", source: "CareGist analysis" },
];

const CONTEXT_STATS = [
  { value: "3.7 yrs", label: "Average age of a CQC rating as of mid-2024", source: "Dash Review, commissioned by DHSC" },
  { value: "19%", label: "Of CQC-regulated locations have never received a rating", source: "DHSC Analysis, 2024" },
];

const VALUE_TABLE = [
  { challenge: "Some CQC ratings are several years old", context: "Inspection volumes have not returned to pre-2020 levels, meaning ratings may not reflect recent improvements", howWeHelp: "Our Data Confidence indicator shows how recently each provider was inspected, so you can judge the freshness of every rating" },
  { challenge: "Focused inspections may not cover all five CQC domains", context: "A provider's overall rating can include domain scores from different inspection cycles", howWeHelp: "We clearly flag which domains were assessed and which were not, so you always know the full picture" },
  { challenge: "Providers who have improved may still show an older rating", context: "Many providers invest significantly in improvement but must wait for CQC to schedule a reinspection", howWeHelp: "Claimed providers can publish what they have done since their last inspection — free of charge" },
  { challenge: "Comparing providers across different areas is difficult", context: "CQC publishes individual ratings but does not provide comparative tools or quality scoring", howWeHelp: "Our quality score (0–100), local ranking, and group benchmarking let you compare objectively" },
  { challenge: "Keeping track of rating changes across a region is manual work", context: "Commissioners and care professionals need to monitor many providers simultaneously", howWeHelp: "Weekly intelligence digest, group dashboards, and rating change alerts delivered automatically" },
];

export default function WhyCareGistPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Why CareGist</h1>
        <p className="text-dusk text-lg max-w-2xl mx-auto" style={{ fontFamily: "Lora" }}>
          The Care Quality Commission does vital work inspecting and rating care services across England.
          CareGist builds on that foundation to make CQC data easier to understand, compare, and act on.
        </p>
      </div>

      {/* What CareGist provides */}
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

      {/* The context */}
      <div className="bg-parchment border-b border-stone rounded-t-lg px-6 py-4 text-sm text-charcoal leading-relaxed mb-8">
        <p>
          The CQC is undertaking a significant transformation of its regulatory approach, including the introduction
          of the Single Assessment Framework and a new digital platform. Independent reviews commissioned by the
          Department of Health and Social Care have acknowledged that this transition has created temporary challenges
          around inspection capacity and data currency. CareGist exists to help bridge that gap — providing additional
          context, analysis, and transparency on top of official CQC data while the regulator continues its important
          modernisation work.
        </p>
      </div>

      {/* Key context numbers */}
      <div className="grid grid-cols-2 gap-4 mb-10">
        {CONTEXT_STATS.map((s) => (
          <div key={s.label} className="bg-cream border border-stone rounded-lg p-5 text-center">
            <p className="text-2xl font-bold text-clay">{s.value}</p>
            <p className="text-xs text-charcoal mt-1">{s.label}</p>
            <p className="text-[10px] text-dusk mt-1 italic">{s.source}</p>
          </div>
        ))}
      </div>

      {/* How CareGist helps */}
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

      {/* Our commitment */}
      <div className="bg-moss/10 border border-moss/20 rounded-xl p-8 mb-10 text-center">
        <h2 className="text-2xl font-bold text-bark mb-3">Our commitment to transparency</h2>
        <p className="text-sm text-charcoal max-w-xl mx-auto mb-4">
          CareGist quality scores and rankings are derived entirely from official CQC inspection data.
          Providers cannot pay for higher scores, better rankings, or removal of factual information.
          We believe good care deserves to be visible — and families deserve honest, accessible information
          to make confident decisions.
        </p>
        <p className="text-xs text-dusk">
          CareGist is built on CQC data published under the Open Government Licence v3.0. Crown copyright and database right.
          CareGist is not affiliated with or endorsed by the Care Quality Commission.
        </p>
      </div>

      {/* Who we serve */}
      <h2 className="text-2xl font-bold mb-6">Who CareGist is for</h2>
      <div className="grid md:grid-cols-2 gap-4 mb-10">
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Families and individuals</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Data Confidence scoring — understand how recent each rating is</li>
            <li>Quality score (0–100) with national and local comparison</li>
            <li>Plain-English inspection summaries for every provider</li>
            <li>Personalised questions to ask when visiting a care service</li>
            <li>Weekly alerts when providers in your area change rating</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Care providers</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Share what you have done since your last inspection — free</li>
            <li>See how your service compares with others in your area</li>
            <li>Claim your listing to add photos and a description</li>
            <li>Understand your quality score and what drives it</li>
            <li>Track rating changes among nearby services</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Commissioners and local authorities</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Group benchmarking across 4,876 care organisations</li>
            <li>Regional quality trends and rating distribution</li>
            <li>Weekly intelligence on rating changes in your area</li>
            <li>Enriched CSV exports with quality scores and CQC report links</li>
            <li>Stable API for integration with existing systems</li>
          </ul>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5">
          <h3 className="font-bold text-bark mb-2">Developers and data teams</h3>
          <ul className="space-y-2 text-sm text-charcoal">
            <li>Full REST API covering all 55,818 providers</li>
            <li>Daily data refresh — cleaned, normalised, and enriched</li>
            <li>Quality scores, ratings, coordinates, and contact details</li>
            <li>Consistent, well-documented schema</li>
            <li>Built for reliability — no upstream instability passed through</li>
          </ul>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center">
        <p className="text-bark font-semibold mb-4 text-lg">Make better-informed care decisions</p>
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
