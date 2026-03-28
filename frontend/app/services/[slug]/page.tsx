import SearchBar from "@/components/SearchBar";
import ProviderCard from "@/components/ProviderCard";
import { searchProviders } from "@/lib/api";
import type { Metadata } from "next";

const SERVICE_MAP: Record<string, string> = {
  "care-homes": "Residential Homes",
  "nursing-homes": "Nursing Homes",
  "home-care": "Homecare Agencies",
  "gp-surgeries": "Doctors/Gps",
  "dental": "Dentist",
  "supported-living": "Supported Living",
};

const DISPLAY_NAMES: Record<string, string> = {
  "care-homes": "Care Homes",
  "nursing-homes": "Nursing Homes",
  "home-care": "Home Care Agencies",
  "gp-surgeries": "GP Surgeries",
  "dental": "Dental Practices",
  "supported-living": "Supported Living",
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const name = DISPLAY_NAMES[slug] || slug;
  return {
    title: `${name} in England | CareGist`,
    description: `Browse CQC-rated ${name.toLowerCase()} across England. Ratings, inspections, and contact details.`,
  };
}

export default async function ServiceTypePage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const { slug } = await params;
  const { page } = await searchParams;
  const serviceType = SERVICE_MAP[slug] || slug;
  const displayName = DISPLAY_NAMES[slug] || slug;

  let results = { data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } };
  try {
    results = await searchProviders({ service_type: serviceType, page: page || "1" });
  } catch (e) {
    console.error("Service type search failed:", e);
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">{displayName} in England</h1>
      <p className="text-dusk mb-6">{results.meta.total.toLocaleString()} providers</p>

      <div className="mb-6">
        <SearchBar />
      </div>

      <div className="grid gap-4">
        {results.data.map((provider: any) => (
          <ProviderCard key={provider.id} provider={provider} />
        ))}
      </div>

      {results.data.length === 0 && (
        <p className="text-center text-dusk py-12">No providers found for this service type.</p>
      )}
    </div>
  );
}
