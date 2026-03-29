import SearchBar from "@/components/SearchBar";
import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-bark text-cream py-20 px-6 text-center">
        <h1 className="text-4xl md:text-5xl font-bold mb-4" style={{ fontFamily: "Playfair Display" }}>
          The gist of good care
        </h1>
        <p className="text-lg text-stone mb-8 max-w-2xl mx-auto" style={{ fontFamily: "Lora" }}>
          Search 55,818 CQC-rated care providers across England. Care homes, GP surgeries,
          dental practices, and home care agencies — all in one place.
        </p>
        <div className="flex justify-center">
          <SearchBar />
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { value: "55,818", label: "Active Providers" },
            { value: "22,617", label: "Rated Good" },
            { value: "10,309", label: "Care Homes" },
            { value: "9", label: "Regions" },
          ].map((stat) => (
            <div key={stat.label} className="bg-cream rounded-lg p-6 border border-stone">
              <div className="text-3xl font-bold text-clay">{stat.value}</div>
              <div className="text-sm text-dusk mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Browse by Service Type */}
      <section className="max-w-6xl mx-auto px-6 py-12">
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

      {/* CQC Attribution */}
      <section className="max-w-6xl mx-auto px-6 py-8 text-center text-sm text-dusk">
        <p>
          Provider data sourced from the Care Quality Commission (CQC).
          CareGist is not affiliated with or endorsed by CQC.
          For official inspection reports, visit{" "}
          <a href="https://www.cqc.org.uk" className="underline text-clay">cqc.org.uk</a>.
        </p>
      </section>
    </div>
  );
}
