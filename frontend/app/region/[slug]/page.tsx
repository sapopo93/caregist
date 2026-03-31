import SearchBar from "@/components/SearchBar";
import ProviderCard from "@/components/ProviderCard";
import RatingDistributionBar from "@/components/RatingDistributionBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import { searchProviders, getRegionStats } from "@/lib/api";
import Link from "next/link";
import type { Metadata } from "next";

const REGION_MAP: Record<string, string> = {
  "south-east": "South East",
  "london": "London",
  "north-west": "North West",
  "east": "East",
  "west-midlands": "West Midlands",
  "south-west": "South West",
  "yorkshire-humberside": "Yorkshire & Humberside",
  "east-midlands": "East Midlands",
  "north-east": "North East",
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const isRegion = slug in REGION_MAP;
  const name = isRegion ? REGION_MAP[slug] : slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return {
    title: `${name} CQC Care Providers — Ratings & Inspection Data | CareGist`,
    description: `Browse CQC-rated care providers in ${name}. Rating distribution, top providers, and inspection data.`,
    alternates: { canonical: `https://caregist.co.uk/region/${slug}` },
  };
}

export default async function RegionPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { slug } = await params;
  const { page } = await searchParams;
  const isRegion = slug in REGION_MAP;

  // For the 9 known regions, use the search endpoint
  // For LA slugs, try the region_stats endpoint for rich data
  let stats: any = null;
  let results = { data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } };
  let error = false;
  let warmingUp = false;
  let displayName = isRegion ? REGION_MAP[slug] : slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  if (isRegion) {
    try {
      results = await searchProviders({ region: REGION_MAP[slug], page: page || "1" });
    } catch (e: any) {
      if (e?.message === "warming_up") warmingUp = true;
      error = true;
    }
  } else {
    // Try as local authority — fetch stats and providers independently
    // so a stats failure doesn't block provider results
    try {
      const statsRes = await getRegionStats(slug);
      stats = statsRes.data;
      displayName = stats.local_authority || displayName;
    } catch {
      // Stats unavailable — page still works without rich sections
    }

    const searchTerm = stats?.local_authority || displayName;
    try {
      results = await searchProviders({ q: searchTerm, page: page || "1" });
    } catch (e: any) {
      if (e?.message === "warming_up") warmingUp = true;
      error = true;
    }
  }

  const totalProviders = stats?.total_providers || results.meta.total;
  const pctGood = stats?.pct_good_or_outstanding;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* AEO Block */}
      <section className="bg-parchment border-b border-stone rounded-t-lg px-6 py-4 text-sm text-charcoal leading-relaxed mb-6">
        <p>
          There are {totalProviders.toLocaleString()} CQC-registered care providers in {displayName}.
          {pctGood !== undefined && <> {pctGood}% are rated Good or Outstanding.</>}
        </p>
      </section>

      <h1 className="text-3xl font-bold mb-2">CQC care providers in {displayName}</h1>
      <p className="text-dusk mb-6">{totalProviders.toLocaleString()} providers</p>

      {/* Rating Distribution */}
      {stats?.rating_distribution && Object.keys(stats.rating_distribution).length > 0 && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Rating Distribution</h2>
          <RatingDistributionBar distribution={stats.rating_distribution} />
        </div>
      )}

      {/* Top Providers */}
      {stats?.top_providers && stats.top_providers.length > 0 && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Top Providers</h2>
          <div className="space-y-3">
            {stats.top_providers.map((p: any) => (
              <Link
                key={p.slug}
                href={`/provider/${p.slug}`}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-parchment transition-colors"
              >
                <div>
                  <span className="font-semibold text-bark">{p.name}</span>
                  <span className="text-xs text-dusk ml-2">{p.type}</span>
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded ${
                  p.overall_rating === "Outstanding" ? "bg-moss/15 text-moss" :
                  p.overall_rating === "Good" ? "bg-amber/15 text-amber" :
                  "bg-stone text-dusk"
                }`}>
                  {p.overall_rating}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Type Breakdown */}
      {stats?.type_distribution && Object.keys(stats.type_distribution).length > 0 && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Provider Types</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(stats.type_distribution).map(([type, count]: [string, any]) => (
              <div key={type} className="text-center p-3 bg-parchment rounded-lg">
                <div className="text-lg font-bold text-clay">{count}</div>
                <div className="text-xs text-dusk">{type}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-6">
        <SearchBar />
      </div>

      {warmingUp && (
        <>
          <meta httpEquiv="refresh" content="30" />
          <div className="bg-cream border border-amber rounded-lg p-6 mb-6 text-center">
            <p className="text-bark font-semibold">The server is waking up</p>
            <p className="text-dusk text-sm mt-1">This takes about 30 seconds. Refreshing shortly...</p>
          </div>
        </>
      )}

      {error && !warmingUp && (
        <div className="bg-cream border border-alert rounded-lg p-6 mb-6 text-center">
          <p className="text-bark font-semibold">Search is temporarily unavailable</p>
        </div>
      )}

      <div className="grid gap-4">
        {results.data.map((provider: any) => (
          <ProviderCard key={provider.id} provider={provider} />
        ))}
      </div>

      {!error && results.data.length === 0 && (
        <p className="text-center text-dusk py-12">No providers found.</p>
      )}

      {/* Email Capture */}
      <div className="mt-8">
        <EmailCaptureStrip
          source={`region_${slug}`}
          heading={`Get weekly alerts for ${displayName}`}
          subheading="Rating changes and new inspections, delivered to your inbox."
        />
      </div>

      <div className="mt-4">
        <TrustSignal />
      </div>
    </div>
  );
}
