import SearchBar from "@/components/SearchBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-bark text-cream py-16 md:py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-3" style={{ fontFamily: "Playfair Display" }}>
            The gist of good care
          </h1>
          <p className="text-sm text-amber font-medium tracking-wide uppercase mb-6">
            Independent quality intelligence for 55,818 CQC-registered care services
          </p>
          <p className="text-lg text-stone mb-8 max-w-2xl mx-auto" style={{ fontFamily: "Lora" }}>
            Find, compare, and monitor care homes, nursing homes, home care agencies, GP surgeries,
            and dental practices across England — rated by CQC inspection data, not advertising.
          </p>
          <div className="flex justify-center mb-8">
            <SearchBar />
          </div>
          {/* Trust bar */}
          <div className="flex flex-wrap justify-center gap-6 text-stone text-xs">
            <span>55,818 providers</span>
            <span className="text-stone/40">|</span>
            <span>Updated daily from CQC</span>
            <span className="text-stone/40">|</span>
            <span>Ranked by data, not by who pays</span>
            <span className="text-stone/40">|</span>
            <span>Free to use</span>
          </div>
        </div>
      </section>

      {/* What makes CareGist different */}
      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-clay/10 rounded-xl flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">&#128202;</span>
            </div>
            <h3 className="font-bold text-bark mb-2">Quality Scored</h3>
            <p className="text-sm text-dusk">
              Every provider gets a 0-100 quality score based on CQC data. See how they compare nationally and locally.
            </p>
          </div>
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-clay/10 rounded-xl flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">&#128337;</span>
            </div>
            <h3 className="font-bold text-bark mb-2">Data Confidence</h3>
            <p className="text-sm text-dusk">
              Know how fresh each rating is. Our confidence indicator shows whether the data reflects recent performance.
            </p>
          </div>
          <div className="text-center p-6">
            <div className="w-12 h-12 bg-clay/10 rounded-xl flex items-center justify-center mx-auto mb-3">
              <span className="text-2xl">&#128276;</span>
            </div>
            <h3 className="font-bold text-bark mb-2">Weekly Intelligence</h3>
            <p className="text-sm text-dusk">
              Get notified when providers in your area change CQC rating. Stay informed without manual checking.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-cream py-10">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {[
              { value: "55,818", label: "Active Providers" },
              { value: "22,617", label: "Rated Good" },
              { value: "4,876", label: "Care Groups Benchmarked" },
              { value: "Daily", label: "Data Refresh" },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl font-bold text-clay">{stat.value}</div>
                <div className="text-sm text-dusk mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Find Care CTA */}
      <section className="max-w-6xl mx-auto px-6 py-10">
        <div className="grid md:grid-cols-2 gap-4">
          <Link
            href="/find-care"
            className="block bg-bark text-cream rounded-xl p-6 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-xl font-bold mb-1" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              Find care near you
            </h2>
            <p className="text-stone text-sm">
              Enter your postcode to see all CQC-rated providers within your chosen radius.
            </p>
          </Link>
          <Link
            href="/groups"
            className="block bg-bark text-cream rounded-xl p-6 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-xl font-bold mb-1" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              Compare care groups
            </h2>
            <p className="text-stone text-sm">
              Benchmark 4,876 UK care organisations by CQC ratings, quality scores, and locations.
            </p>
          </Link>
        </div>
      </section>

      {/* Email Capture */}
      <section className="max-w-6xl mx-auto px-6 py-4">
        <EmailCaptureStrip source="homepage" />
      </section>

      {/* Browse by Service Type */}
      <section className="max-w-6xl mx-auto px-6 py-10">
        <h2 className="text-2xl font-bold mb-6">Browse by service type</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
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
              className="bg-cream border border-stone rounded-lg p-4 hover:border-clay transition-colors"
            >
              <div className="font-semibold text-bark">{type.name}</div>
              <div className="text-sm text-dusk">{type.count} providers</div>
            </Link>
          ))}
        </div>
      </section>

      {/* Browse by Region */}
      <section className="max-w-6xl mx-auto px-6 pb-10">
        <h2 className="text-2xl font-bold mb-6">Browse by region</h2>
        <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
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
              className="bg-cream border border-stone rounded-lg p-3 text-center hover:border-clay transition-colors text-sm font-medium text-bark"
            >
              {r.name}
            </Link>
          ))}
        </div>
      </section>

      {/* Why CareGist */}
      <section className="bg-bark py-10">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
            Why families and professionals choose CareGist
          </h2>
          <div className="grid md:grid-cols-3 gap-6 text-stone text-sm mt-6">
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
          <Link href="/why-caregist" className="inline-block mt-6 text-amber underline text-sm hover:text-cream">
            Learn more about CareGist
          </Link>
        </div>
      </section>

      {/* CQC Attribution */}
      <section className="max-w-6xl mx-auto px-6 py-8 text-center text-sm text-dusk">
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
