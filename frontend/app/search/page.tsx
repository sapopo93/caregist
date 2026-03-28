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
  let error = false;

  if (query || params.region || params.rating || params.service_type) {
    try {
      results = await searchProviders({ ...params, page });
    } catch (e) {
      console.error("Search failed:", e);
      error = true;
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <SearchBar defaultValue={query} />
      </div>

      {error && (
        <div className="bg-cream border border-alert rounded-lg p-6 mb-6 text-center">
          <p className="text-bark font-semibold">Search is temporarily unavailable</p>
          <p className="text-dusk text-sm mt-1">Please try again in a moment.</p>
        </div>
      )}

      {!error && results.meta.total > 0 && (
        <p className="text-sm text-dusk mb-4">
          {results.meta.total.toLocaleString()} providers found
          {query && <> for &ldquo;{query}&rdquo;</>}
          {" "} (page {results.meta.page} of {results.meta.pages})
        </p>
      )}

      <div className="grid gap-4">
        {results.data.map((provider: any) => (
          <ProviderCard key={provider.id} provider={provider} />
        ))}
      </div>

      {!error && results.data.length === 0 && (query || params.service_type) && (
        <div className="text-center py-12 text-dusk">
          <p className="text-lg">No providers found.</p>
          <p className="text-sm mt-2">Try a different search term or broaden your filters.</p>
        </div>
      )}

      {/* Pagination — only show valid pages */}
      {results.meta.pages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {Array.from({ length: results.meta.pages }, (_, i) => i + 1)
            .filter((p) => {
              // Show first 3, last 3, and 2 around current page
              const current = results.meta.page;
              return p <= 3 || p > results.meta.pages - 3 || Math.abs(p - current) <= 2;
            })
            .reduce<(number | "...")[]>((acc, p, i, arr) => {
              if (i > 0 && p - (arr[i - 1] as number) > 1) acc.push("...");
              acc.push(p);
              return acc;
            }, [])
            .map((p, i) =>
              p === "..." ? (
                <span key={`gap-${i}`} className="px-2 py-2 text-dusk">...</span>
              ) : (
                <a
                  key={p}
                  href={`/search?${new URLSearchParams({ ...params, page: String(p) }).toString()}`}
                  className={`px-3 py-2 rounded ${
                    p === results.meta.page
                      ? "bg-clay text-white"
                      : "bg-cream border border-stone text-dusk hover:border-clay"
                  }`}
                >
                  {p}
                </a>
              )
            )}
        </div>
      )}
    </div>
  );
}
