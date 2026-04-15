import { Suspense } from "react";
import RadiusFinder from "@/components/RadiusFinder";
import TrustSignal from "@/components/TrustSignal";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Find Care Near You | CareGist Directory",
  description:
    "Search CQC-rated care providers by postcode and radius. CareGist keeps directory and claiming flows available while the launch product centres on care-provider data intelligence.",
  alternates: { canonical: "https://caregist.co.uk/find-care" },
};

export default function FindCarePage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      {/* Hero image */}
      <div className="rounded-xl overflow-hidden mb-8 h-40 relative">
        <img
          src="https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?w=800&q=40&auto=format"
          alt="Care home garden"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-bark/30 to-transparent" />
      </div>

      {/* AEO block */}
      <section className="bg-parchment border-b border-stone px-6 py-4 rounded-t-lg text-sm text-charcoal leading-relaxed mb-8">
        <p>
          Search all 55,818 CQC-registered care providers in England by postcode and radius.
          Find care homes, nursing homes, home care agencies, and more — rated by the Care Quality Commission. This directory remains available as a secondary entry point alongside CareGist&apos;s dashboard, exports, and API workflows.
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">Find CQC-rated care near you</h1>
      <p className="text-dusk mb-8" style={{ fontFamily: "Lora" }}>
        Enter your postcode to browse local providers. If you need operational monitoring, exports, or benchmarking, CareGist&apos;s pricing and data explorer are the stronger starting point.
      </p>

      <div className="bg-cream border border-stone rounded-lg p-4 mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-dusk mb-1">Operational workflows</p>
          <p className="text-sm text-bark">
            Teams using CareGist for recurring search, exports, and monitoring should start with the data product.
          </p>
        </div>
        <div className="flex gap-3 text-sm">
          <a href="/search" className="text-clay underline">Open data explorer</a>
          <a href="/pricing" className="text-clay underline">See pricing</a>
        </div>
      </div>

      <Suspense>
        <RadiusFinder />
      </Suspense>

      <div className="mt-8">
        <TrustSignal />
      </div>
    </div>
  );
}
