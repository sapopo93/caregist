import CareGistAssessment from "@/components/CareGistAssessment";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sample CareGist Assessment Report | CareGist",
  description:
    "See what a CareGist provider assessment looks like. CQC ratings, inspection recency, data completeness, and visit questions — all free.",
  alternates: { canonical: "https://caregist.co.uk/sample-report" },
};

// Realistic sample data for demonstration
const sampleProvider = {
  id: "sample",
  name: "Rosewood Manor Care Home",
  slug: "rosewood-manor-care-home-bournemouth",
  type: "Care Home",
  town: "Bournemouth",
  postcode: "BH1 3QJ",
  region: "South West",
  overall_rating: "Good",
  data_completeness_score: 82,
  data_completeness_tier: "GOOD",
  number_of_beds: 42,
  rating_safe: "Good",
  rating_effective: "Good",
  rating_caring: "Outstanding",
  rating_responsive: "Good",
  rating_well_led: "Requires Improvement",
  last_inspection_date: "2024-11-15",
  service_types: "Residential Homes|Nursing Homes",
  specialisms: "Dementia|Caring For Adults Over 65 Yrs|Physical Disabilities",
  phone: "01202 555 123",
  inspection_report_url: "https://www.cqc.org.uk/location/example",
  inspection_summary: "Rosewood Manor Care Home is a residential care home with 42 beds in Bournemouth (BH1 3QJ). CQC inspectors rated this service Good overall. Breakdown: Safe — Good, Effective — Good, Caring — Outstanding, Responsive — Good, Well-led — Requires Improvement. Last inspected 15 November 2024. Specialises in: dementia, caring for adults over 65 yrs, physical disabilities.",
  latitude: 50.7192,
  longitude: -1.8808,
  is_claimed: false,
};

export default function SampleReportPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <div className="rounded-xl mb-8 h-44 bg-gradient-to-br from-clay/20 via-parchment to-moss/20" aria-hidden="true">
      </div>

      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">The CareGist Assessment</h1>
        <p className="text-dusk text-lg mb-2" style={{ fontFamily: "Lora" }}>
          Every provider page includes a free, independent assessment.
        </p>
        <p className="text-dusk text-sm">
          CQC rating context, inspection recency, data completeness, and personalised visit questions — built from official CQC data, not advertising.
        </p>
      </div>

      {/* What makes it different */}
      <div className="grid md:grid-cols-3 gap-4 mb-12">
        <div className="bg-cream border border-stone rounded-lg p-5 text-center">
          <div className="text-3xl mb-2">&#128202;</div>
          <h3 className="font-bold text-bark text-sm mb-1">Data Completeness</h3>
          <p className="text-xs text-dusk">Shows which expected CQC directory fields are present. It is not a care-quality judgement.</p>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5 text-center">
          <div className="text-3xl mb-2">&#128205;</div>
          <h3 className="font-bold text-bark text-sm mb-1">Inspection Context</h3>
          <p className="text-xs text-dusk">See the published CQC rating and inspection date without a CareGist-generated quality rank.</p>
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5 text-center">
          <div className="text-3xl mb-2">&#9745;</div>
          <h3 className="font-bold text-bark text-sm mb-1">Visit Questions</h3>
          <p className="text-xs text-dusk">Personalised questions to ask on your visit, based on each provider's specific inspection findings.</p>
        </div>
      </div>

      {/* Not pay to rank badge */}
      <div className="bg-bark rounded-lg p-4 mb-8 text-center">
        <p className="text-cream text-sm font-semibold">
          CareGist ranks by CQC inspection data, not by who pays us.
        </p>
        <p className="text-stone text-xs mt-1">
          Our assessments are independent. Providers cannot pay for higher scores or rankings.
        </p>
      </div>

      {/* Sample report */}
      <div className="mb-8">
        <p className="text-sm text-dusk mb-4 text-center">
          Below is a sample assessment for a fictional care home. Every real provider on CareGist has one.
        </p>
        <div className="border-2 border-dashed border-stone/50 rounded-xl p-2">
          <CareGistAssessment provider={sampleProvider} />
        </div>
      </div>

      {/* CTA */}
      <div className="text-center">
        <p className="text-bark font-semibold mb-4 text-lg">Find your provider's assessment</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/search"
            className="px-8 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
          >
            Search providers
          </Link>
          <Link
            href="/find-care"
            className="px-8 py-3 border border-clay text-clay rounded-lg font-medium hover:bg-clay hover:text-white transition-colors"
          >
            Search by postcode
          </Link>
        </div>
      </div>

      {/* Trust signals */}
      <div className="mt-12 grid grid-cols-3 gap-6 text-center">
        <div>
          <p className="text-2xl font-bold text-clay">National</p>
          <p className="text-xs text-dusk">Provider assessments</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-clay">Daily</p>
          <p className="text-xs text-dusk">Data refresh from CQC</p>
        </div>
        <div>
          <p className="text-2xl font-bold text-clay">Free</p>
          <p className="text-xs text-dusk">Always, for everyone</p>
        </div>
      </div>
    </div>
  );
}
