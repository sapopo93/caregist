import type { Metadata } from "next";
import Link from "next/link";

import DirectoryPagination from "@/components/directory/DirectoryPagination";
import DirectoryProviderCard from "@/components/directory/DirectoryProviderCard";
import DirectorySearchForm from "@/components/directory/DirectorySearchForm";
import { getDirectoryOpportunity } from "@/lib/directory-constants";
import { getDirectoryFilterOptions, searchDirectoryProviders } from "@/lib/directory-db";
import { parseDirectorySearchParams } from "@/lib/directory-filters";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Search CQC-registered Care Services | CareGist",
  description:
    "Search factual CQC location records by name, region, service type, rating, and registration recency.",
};

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const rawParams = await searchParams;
  const filters = parseDirectorySearchParams(rawParams);
  const opportunity = getDirectoryOpportunity(filters.opportunity);
  const [optionsResult, resultsResult] = await Promise.allSettled([
    getDirectoryFilterOptions(),
    searchDirectoryProviders(filters),
  ]);

  const options = optionsResult.status === "fulfilled" ? optionsResult.value : null;
  const results = resultsResult.status === "fulfilled" ? resultsResult.value : null;
  const error = resultsResult.status === "rejected";

  return (
    <div className="mx-auto max-w-6xl overflow-x-hidden px-4 py-8 sm:px-6 sm:py-10">
      <DirectorySearchForm
        action="/search"
        options={options}
        query={filters.query}
        region={filters.region}
        serviceType={filters.serviceType}
        rating={filters.rating}
        opportunity={filters.opportunity}
        titleHeading="h1"
        title={opportunity ? opportunity.label : "Search CQC-registered care services"}
        description="Filter factual CQC location records. Segment labels describe published registration or rating state and are not predictions or recommendations."
        submitLabel="Update search"
      />

      <div className="mt-8 grid min-w-0 gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="min-w-0">
          {error ? (
            <div className="rounded-3xl border border-alert/20 bg-alert/10 p-6">
              <p className="text-lg font-semibold text-bark">Search is temporarily unavailable.</p>
              <p className="mt-2 text-sm text-dusk">
                Check the database connection and try again. The page itself is up, but the directory query failed.
              </p>
            </div>
          ) : null}

          {!error && results ? (
            <>
              <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">
                    {opportunity ? "Factual segment" : "Provider directory"}
                  </p>
                  <h2 className="mt-2 text-3xl font-extrabold text-bark">
                    {results.total.toLocaleString()} provider{results.total === 1 ? "" : "s"}
                  </h2>
                  <p className="mt-2 text-sm text-dusk">
                    {opportunity
                      ? `${opportunity.shortLabel}, based on the published registration or rating fields.`
                      : filters.query
                      ? `Matching "${filters.query}" with your selected filters.`
                      : "Filtered across the full active provider directory."}
                  </p>
                </div>
                <p className="text-sm text-dusk">
                  Page {filters.page} of {Math.max(results.totalPages, 1)}
                </p>
              </div>

              {results.providers.length > 0 ? (
                <div className="grid gap-4">
                  {results.providers.map((provider) => (
                    <DirectoryProviderCard key={provider.id} provider={provider} />
                  ))}
                </div>
              ) : (
                <div className="rounded-3xl border border-stone bg-cream p-8 text-center shadow-sm">
                  <p className="text-lg font-semibold text-bark">No providers matched this search.</p>
                  <p className="mt-2 text-sm text-dusk">
                    Try removing one filter or using a broader town or provider name.
                  </p>
                </div>
              )}

              <DirectoryPagination
                basePath="/search"
                currentPage={filters.page}
                totalPages={results.totalPages}
                params={{
                  q: filters.query,
                  region: filters.region,
                  service_type: filters.serviceType,
                  rating: filters.rating,
                  opportunity: filters.opportunity,
                }}
              />
            </>
          ) : null}
        </section>

        <aside className="min-w-0 space-y-4">
          <div className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Radar</p>
            <h2 className="mt-2 text-2xl font-bold text-bark">Need to know what changes next?</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              Radar records new registrations and rating changes as evidence-linked events, with team views and bounded event history.
            </p>
            <Link
              href="/pricing"
              className="mt-5 inline-flex rounded-full bg-clay px-4 py-2 text-sm font-semibold text-white hover:bg-bark"
            >
              Compare Radar plans
            </Link>
          </div>

          <div className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Source discipline</p>
            <h2 className="mt-2 text-2xl font-bold text-bark">Verify before acting</h2>
            <p className="mt-3 text-sm leading-6 text-dusk">
              Directory records can lag or change. Follow the official CQC source link on a provider
              profile before making a care, compliance, or commercial decision.
            </p>
            <a
              href="https://www.cqc.org.uk/care-services"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-5 inline-flex rounded-full border border-clay px-4 py-2 text-sm font-semibold text-clay hover:bg-parchment"
            >
              Open CQC search
            </a>
          </div>
        </aside>
      </div>
    </div>
  );
}
