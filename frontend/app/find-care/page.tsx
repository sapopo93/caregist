import { Suspense } from "react";
import RadiusFinder from "@/components/RadiusFinder";
import TrustSignal from "@/components/TrustSignal";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Find Care Near You | CareGist Directory",
  description:
    "Search CQC-registered care providers by postcode and radius, then verify material details with CQC and the provider.",
};

export default function FindCarePage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="rounded-xl mb-8 h-40 bg-gradient-to-br from-moss/25 via-parchment to-clay/20" aria-hidden="true">
      </div>

      {/* AEO block */}
      <section className="bg-parchment border-b border-stone px-6 py-4 rounded-t-lg text-sm text-charcoal leading-relaxed mb-8">
        <p>
          Search CQC-registered care providers in England by postcode and radius.
          Find care homes, nursing homes, home care agencies, and other services using
          published CQC information. CareGist is a discovery aid, not a care-placement,
          medical, safeguarding, or regulatory service.
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">Find CQC-rated care near you</h1>
      <p className="text-dusk mb-8">
        Enter your postcode to browse local providers. Always confirm availability,
        services, fees, suitability, and the current regulatory record directly with the
        provider and CQC before making a care decision.
      </p>

      <div className="bg-cream border border-stone rounded-lg p-4 mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-dusk mb-1">Free directory</p>
          <p className="text-sm text-bark">
            Search factual provider records freely. Compliance and quality-improvement
            teams can compare evidence-linked Radar plans separately.
          </p>
        </div>
        <div className="flex gap-3 text-sm">
          <a href="/search" className="text-clay underline">Open provider search</a>
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
