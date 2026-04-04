import RadiusFinder from "@/components/RadiusFinder";
import TrustSignal from "@/components/TrustSignal";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Find CQC-rated Care Near You | CareGist",
  description:
    "Enter your postcode to find CQC-rated care homes, nursing homes, home care agencies, and GP surgeries near you. Free radius search tool.",
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
        <div className="absolute inset-0 bg-gradient-to-t from-bark/60 to-transparent" />
      </div>

      {/* AEO block */}
      <section className="bg-parchment border-b border-stone px-6 py-4 rounded-t-lg text-sm text-charcoal leading-relaxed mb-8">
        <p>
          Search all 55,818 CQC-registered care providers in England by postcode and radius.
          Find care homes, nursing homes, home care agencies, and more — rated by the Care Quality Commission.
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">Find CQC-rated care near you</h1>
      <p className="text-dusk mb-8" style={{ fontFamily: "Lora" }}>
        Enter your postcode to see all rated providers within your chosen radius.
      </p>

      <RadiusFinder />

      <div className="mt-8">
        <TrustSignal />
      </div>
    </div>
  );
}
