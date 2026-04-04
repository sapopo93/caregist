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
          <h1 className="text-4xl md:text-6xl font-bold mb-4" style={{ fontFamily: "Playfair Display" }}>
            The gist of good care
          </h1>
          <p className="text-amber text-sm md:text-base font-medium tracking-wide uppercase mb-5">
            Independent quality intelligence for 55,818 CQC-registered care services
          </p>
          <p className="text-stone text-base md:text-lg mb-8 max-w-xl mx-auto" style={{ fontFamily: "Lora" }}>
            Find, compare, and monitor care providers across England — rated by CQC inspection data, not advertising.
          </p>
          <div className="flex justify-center mb-8">
            <SearchBar />
          </div>
          <div className="flex flex-wrap justify-center gap-4 text-cream/80 text-sm font-medium">
            <span>55,818 providers</span>
            <span className="text-amber">|</span>
            <span>Updated daily</span>
            <span className="text-amber">|</span>
            <span>Ranked by data, not by who pays</span>
          </div>
        </div>
      </section>

      {/* Value propositions — cards with backgrounds */}
      <section className="bg-cream py-10 border-b border-stone">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-5">
            {[
              {
                icon: "\u{1F4CA}",
                title: "Quality Scored",
                desc: "Every provider gets a 0\u2013100 quality score. See how they compare nationally and locally.",
              },
              {
                icon: "\u{1F551}",
                title: "Data Confidence",
                desc: "Know how fresh each rating is. Our confidence indicator shows whether data reflects recent performance.",
              },
              {
                icon: "\u{1F514}",
                title: "Weekly Intelligence",
                desc: "Get notified when providers in your area change CQC rating. Stay informed automatically.",
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
            { value: "22,617", label: "Rated Good" },
            { value: "4,876", label: "Groups" },
            { value: "Daily", label: "Refresh" },
          ].map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl md:text-4xl font-extrabold text-clay">{stat.value}</div>
              <div className="text-xs text-dusk mt-1 font-medium">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <div className="grid md:grid-cols-2 gap-5">
          <Link
            href="/find-care"
            className="block bg-bark text-cream rounded-xl p-7 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-xl font-bold mb-2" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
              Find care near you
            </h2>
            <p className="text-stone text-sm">
              Enter your postcode to see rated providers within your chosen radius.
            </p>
          </Link>
          <Link
            href="/groups"
            className="block bg-bark text-cream rounded-xl p-7 hover:bg-charcoal transition-colors"
          >
            <h2 className="text-xl font-bold mb-2" style={{ fontFamily: "Playfair Display", color: "var(--color-amber)" }}>
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

      {/* Browse by Service Type + Region combined */}
      <section className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-xl font-bold mb-4">Browse by service type</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-10">
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
