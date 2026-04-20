import type { Metadata } from "next";
import SearchBar from "@/components/SearchBar";
import ProviderCard from "@/components/ProviderCard";
import FilterSidebar from "@/components/FilterSidebar";
import MapToggle from "@/components/MapToggle";
import ExportCSVButton from "@/components/ExportCSVButton";
import PrintButton from "@/components/PrintButton";
import InlineSortSelect from "@/components/InlineSortSelect";
import MobileFilterToggle from "@/components/MobileFilterToggle";
import WarmingUpBanner from "@/components/WarmingUpBanner";
import { searchProviders } from "@/lib/api";
import {
  NEW_REGISTRATION_MONTHLY_AVG,
  NEW_REGISTRATION_MONTHLY_AVG_CAVEAT,
} from "@/lib/caregist-config";
import { Suspense } from "react";
import Link from "next/link";

export const metadata: Metadata = {
  title: "CareGist New Provider Lead Feed",
  description: "Filter, export, and monitor newly registered CQC providers and UK care-market movement.",
};

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const query = params.q || "";
  const page = params.page || "1";
  const sort = params.sort || "relevance";

  let results = { data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } };
  let error = false;
  let warmingUp = false;

  try {
    results = await searchProviders({ ...params, page, sort });
  } catch (e: any) {
    console.error("Search failed:", e);
    if (e?.message === "warming_up") {
      warmingUp = true;
    }
    error = true;
  }

  // Build export URL
  const exportParams = new URLSearchParams();
  if (params.q) exportParams.set("q", params.q);
  if (params.region) exportParams.set("region", params.region);
  if (params.rating) exportParams.set("rating", params.rating);
  if (params.type) exportParams.set("type", params.type);
  if (params.service_type) exportParams.set("service_type", params.service_type);
  if (params.postcode) exportParams.set("postcode", params.postcode);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-clay">New Provider Lead Feed</p>
        <h1 className="mt-2 text-3xl font-extrabold text-bark md:text-4xl">
          New Provider Lead Feed
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-dusk" style={{ fontFamily: "Lora" }}>
          Find, filter, export, and monitor newly registered CQC providers and wider UK care-market
          movement. CareGist tracked an average of {NEW_REGISTRATION_MONTHLY_AVG} newly registered
          providers per month from January to March 2026.
        </p>
        <p className="mt-2 text-[11px] text-dusk/80 leading-5">
          {NEW_REGISTRATION_MONTHLY_AVG_CAVEAT}
        </p>
      </div>
      <div className="mb-8">
        <SearchBar
          defaultValue={query}
          defaultRegion={params.region || ""}
          defaultRating={params.rating || ""}
          defaultServiceType={params.service_type || ""}
          defaultPostcode={params.postcode || ""}
        />
      </div>

      <Suspense fallback={null}>
        <MobileFilterToggle />
      </Suspense>

      <div className="flex gap-8">
        {/* Filter Sidebar */}
        <div className="hidden md:block w-56 flex-shrink-0">
          <Suspense fallback={<div className="h-64 bg-cream rounded-lg animate-pulse" />}>
            <FilterSidebar />
          </Suspense>
        </div>

        {/* Results */}
        <div className="flex-1 min-w-0">
          {warmingUp && <WarmingUpBanner />}

          {error && !warmingUp && (
            <div className="bg-cream border border-alert rounded-lg p-6 mb-6 text-center">
              <p className="text-bark font-semibold">Search is temporarily unavailable</p>
              <p className="text-dusk text-sm mt-1">Please try again in a moment.</p>
            </div>
          )}

          {!error && results.meta.total > 0 && (
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <p className="text-sm text-dusk">
                {results.meta.total.toLocaleString()} provider{results.meta.total === 1 ? "" : "s"}
                {query ? <> matching &ldquo;{query}&rdquo;</> : " in the directory"}
                {" "} (page {results.meta.page} of {results.meta.pages})
              </p>
              <div className="flex gap-3 items-center print:hidden">
                <Suspense fallback={null}><InlineSortSelect /></Suspense>
                <ExportCSVButton exportUrl={`/api/v1/providers/export.csv?${exportParams.toString()}`} />
                <PrintButton />
              </div>
            </div>
          )}

          {results.data.length > 0 && <MapToggle providers={results.data} />}

          <div className="grid gap-4">
            {results.data.map((provider: any) => (
              <ProviderCard key={provider.id} provider={provider} />
            ))}
          </div>

          {!error && results.data.length === 0 && !warmingUp && (
            <div className="text-center py-12">
              <p className="text-lg text-bark font-semibold mb-3">No providers found</p>
              {query && (
                <p className="text-sm text-dusk mb-4">
                  Your search for &ldquo;{query}&rdquo; didn&apos;t match any providers.
                </p>
              )}
              <div className="bg-cream border border-stone rounded-lg p-6 max-w-md mx-auto text-left">
                <p className="text-sm font-medium text-bark mb-3">Try:</p>
                <ul className="space-y-2 text-sm text-dusk">
                  <li>Searching by <strong>town name</strong> (e.g. &ldquo;Birmingham&rdquo;)</li>
                  <li>Searching by <strong>postcode</strong> (e.g. &ldquo;BH1&rdquo;)</li>
                  <li>Searching by <strong>service type</strong> (e.g. &ldquo;nursing homes&rdquo;)</li>
                  <li>Removing filters in Advanced Search</li>
                </ul>
                <div className="flex gap-3 mt-4">
                  <Link href="/find-care" className="text-xs text-clay underline">
                    Use Radius Finder
                  </Link>
                  <Link href="/region/london" className="text-xs text-clay underline">
                    Browse by region
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Pagination */}
          {results.meta.pages > 1 && (
            <div className="flex justify-center gap-2 mt-8">
              {Array.from({ length: results.meta.pages }, (_, i) => i + 1)
                .filter((p) => {
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
                    (() => {
                      const cleanParams = Object.fromEntries(
                        Object.entries({ ...params, page: String(p) }).filter(([, v]) => v !== undefined && v !== "")
                      ) as Record<string, string>;
                      return (
                        <Link
                          key={p}
                          href={`/search?${new URLSearchParams(cleanParams).toString()}`}
                          className={`px-3 py-2 rounded ${
                            p === results.meta.page
                              ? "bg-clay text-white"
                              : "bg-cream border border-stone text-dusk hover:border-clay"
                          }`}
                        >
                          {p}
                        </Link>
                      );
                    })()
                  )
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
