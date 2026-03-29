import SearchBar from "@/components/SearchBar";
import ProviderCard from "@/components/ProviderCard";
import { searchProviders } from "@/lib/api";
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
  const region = REGION_MAP[slug] || slug;
  return {
    title: `Care Providers in ${region} | CareGist`,
    description: `Browse CQC-rated care homes, GP surgeries, dental practices, and home care agencies in ${region}.`,
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
  const region = REGION_MAP[slug] || slug;

  let results = { data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } };
  let error = false;
  let warmingUp = false;

  try {
    results = await searchProviders({ region, page: page || "1" });
  } catch (e: any) {
    console.error("Region search failed:", e);
    if (e?.message === "warming_up") warmingUp = true;
    error = true;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">Care Providers in {region}</h1>
      <p className="text-dusk mb-6">{results.meta.total.toLocaleString()} providers</p>

      <div className="mb-6">
        <SearchBar />
      </div>

      {warmingUp && (
        <>
          <meta httpEquiv="refresh" content="30" />
          <div className="bg-cream border border-amber rounded-lg p-6 mb-6 text-center">
            <p className="text-bark font-semibold">The server is waking up</p>
            <p className="text-dusk text-sm mt-1">
              This takes about 30 seconds on first load. Refreshing the page in a moment...
            </p>
          </div>
        </>
      )}

      {error && !warmingUp && (
        <div className="bg-cream border border-alert rounded-lg p-6 mb-6 text-center">
          <p className="text-bark font-semibold">Search is temporarily unavailable</p>
          <p className="text-dusk text-sm mt-1">Please try again in a moment.</p>
        </div>
      )}

      <div className="grid gap-4">
        {results.data.map((provider: any) => (
          <ProviderCard key={provider.id} provider={provider} />
        ))}
      </div>

      {!error && results.data.length === 0 && (
        <p className="text-center text-dusk py-12">No providers found in this region.</p>
      )}
    </div>
  );
}
