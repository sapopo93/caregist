import SearchBar from "@/components/SearchBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-bark text-cream py-14 md:py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-3" style={{ fontFamily: "Playfair Display" }}>
            The gist of good care
          </h1>
          <p className="text-amber text-sm font-medium tracking-wide uppercase mb-5">
            Independent quality intelligence for 55,818 CQC-registered care services
          </p>
          <p className="text-stone text-base mb-8 max-w-xl mx-auto" style={{ fontFamily: "Lora" }}>
            Find, compare, and monitor care providers across England — rated by CQC inspection data, not advertising.
          </p>
          <div className="flex justify-center mb-6">
            <SearchBar />
          </div>
          <div className="flex flex-wrap justify-center gap-4 text-stone/70 text-xs">
            <span>55,818 providers</span>
            <span>·</span>
            <span>Updated daily</span>
            <span>·</span>
            <span>Ranked by data, not by who pays</span>
          </div>
        </div>
      </section>

      {/* Value propositions */}
      <section className="bg-cream py-10 border-b border-stone">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-clay/15 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xl">&#128202;</span>
              </div>
              <div>
                <h3 className="font-bold text-bark mb-1 text-sm">Quality Scored</h3>
                <p className="text-xs text-dusk leading-relaxed">
                  Every provider gets a 0–100 quality score. See how they compare nationally and locally.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-clay/15 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xl">&#128337;</span>
              </div>
              <div>
                <h3 className="font-bold text-bark mb-1 text-sm">Data Confidence</h3>
                <p className="text-xs text-dusk leading-relaxed">
                  Know how fresh each rating is. Our confidence indicator shows whether data reflects recent performance.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-clay/15 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xl">&#128276;</span>
              </div>
              <div>
                <h3 className="font-bold text-bark mb-1 text-sm">Weekly Intelligence</h3>
                <p className="text-xs text-dusk leading-relaxed">
                  Get notified when providers in your area change CQC rating. Stay informed automatically.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-8">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid grid-cols-4 gap-4 text-center">
            {[
              { value: "55,818", label: "Providers" },
              { value: "22,617", label: "Rated Good" },
              { value: "4,876", label: "Groups" },
              { value: "Daily", label: "Refresh" },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl md:text-3xl font-bold text-clay">{stat.value}</div>
                <div className="text-xs text-dusk mt-0.5">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTAs — clean cards, no background images */}
      <section className="max-w-5xl mx-auto px-6 py-6">
        <div className="grid md:grid-cols-2 gap-4">
          <Link
            href="/find-care"
            className="block bg-bark text-cream rounded-xl p-6 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-lg font-bold mb-1" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              Find care near you
            </h2>
            <p className="text-stone text-sm">
              Enter your postcode to see rated providers within your chosen radius.
            </p>
          </Link>
          <Link
            href="/groups"
            className="block bg-bark text-cream rounded-xl p-6 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-lg font-bold mb-1" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              Compare care groups
            </h2>
            <p className="text-stone text-sm">
              Benchmark 4,876 UK care organisations by CQC ratings and quality scores.
            </p>
          </Link>
        </div>
      </section>

      {/* Email Capture */}
      <section className="max-w-5xl mx-auto px-6 py-4">
        <EmailCaptureStrip source="homepage" />
      </section>

      {/* Browse by Service Type */}
      <section className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-xl font-bold mb-4">Browse by service type</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { name: "Care Homes", count: "10,309", slug: "care-homes" },
            { name: "Nursing Homes", count: "4,386", slug: "nursing-homes" },
            { name: "Home Care", count: "14,240", slug: "home-care" },
            { name: "GP Surgeries", count: "9,367", slug: "gp-surgeries" },
            { name: "Dental Practices", count: "12,004", slug: "dental" },
            { name: "Supported Living", count: "4,727", slug: "supported-living" },
          ].map((type) => (
            <Link
              key={type.name}
              href={`/services/${type.slug}`}
              className="bg-cream border border-stone rounded-lg p-3 hover:border-clay transition-colors"
            >
              <div className="font-semibold text-bark text-sm">{type.name}</div>
              <div className="text-xs text-dusk">{type.count} providers</div>
            </Link>
          ))}
        </div>
      </section>

      {/* Browse by Region */}
      <section className="max-w-5xl mx-auto px-6 pb-8">
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
            <Link
              key={r.slug}
              href={`/region/${r.slug}`}
              className="bg-cream border border-stone rounded-lg p-2.5 text-center hover:border-clay transition-colors text-xs font-medium text-bark"
            >
              {r.name}
            </Link>
          ))}
        </div>
      </section>

      {/* Why CareGist */}
      <section className="bg-bark py-8">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
            Why families and professionals choose CareGist
          </h2>
          <div className="grid md:grid-cols-3 gap-6 text-stone text-xs mt-4">
            <div>
              <p className="text-cream font-semibold mb-1">Independent</p>
              <p>Rankings based on CQC data, not advertising. Providers cannot pay for higher placement.</p>
            </div>
            <div>
              <p className="text-cream font-semibold mb-1">Transparent</p>
              <p>Data Confidence scoring tells you how recent each rating is. No hidden assumptions.</p>
            </div>
            <div>
              <p className="text-cream font-semibold mb-1">Comprehensive</p>
              <p>55,818 providers with inspection summaries, quality scores, and group benchmarking.</p>
            </div>
          </div>
          <Link href="/why-caregist" className="inline-block mt-4 text-amber underline text-xs hover:text-cream">
            Learn more about CareGist
          </Link>
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
