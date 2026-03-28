import SearchBar from "@/components/SearchBar";
import ProviderCard from "@/components/ProviderCard";
import { searchProviders } from "@/lib/api";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; region?: string; rating?: string; type?: string; service_type?: string; page?: string }>;
}) {
  const params = await searchParams;
  const query = params.q || "";
  const page = params.page || "1";

  let results = { data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } };

  if (query || params.region || params.rating || params.service_type) {
    try {
      results = await searchProviders({ ...params, page });
    } catch (e) {
      console.error("Search failed:", e);
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <SearchBar defaultValue={query} />
      </div>

      {results.meta.total > 0 && (
        <p className="text-sm text-dusk mb-4">
          {results.meta.total.toLocaleString()} providers found
          {query && <> for &ldquo;{query}&rdquo;</>}
        </p>
      )}

      <div className="grid gap-4">
        {results.data.map((provider: any) => (
          <ProviderCard key={provider.id} provider={provider} />
        ))}
      </div>

      {results.data.length === 0 && (query || params.service_type) && (
        <div className="text-center py-12 text-dusk">
          <p className="text-lg">No providers found.</p>
          <p className="text-sm mt-2">Try a different search term or broaden your filters.</p>
        </div>
      )}

      {/* Pagination */}
      {results.meta.pages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {Array.from({ length: Math.min(results.meta.pages, 10) }, (_, i) => i + 1).map((p) => (
            <a
              key={p}
              href={`/search?q=${encodeURIComponent(query)}&page=${p}`}
              className={`px-3 py-2 rounded ${
                p === results.meta.page
                  ? "bg-clay text-white"
                  : "bg-cream border border-stone text-dusk hover:border-clay"
              }`}
            >
              {p}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
