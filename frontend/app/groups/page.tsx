import Link from "next/link";
import ExportCSVButton from "@/components/ExportCSVButton";
import PrintButton from "@/components/PrintButton";
import { searchProviders } from "@/lib/api";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Care Home Groups — UK Provider Group Benchmarking | CareGist",
  description:
    "Compare UK care home groups by CQC ratings, quality scores, and inspection outcomes. Benchmark Barchester, Care UK, HC-One, and thousands more.",
  alternates: { canonical: "https://caregist.co.uk/groups" },
};

async function fetchGroups(q?: string, page?: string) {
  const API_BASE = process.env.API_URL || "http://localhost:8000";
  const API_KEY = process.env.API_KEY || "dev_key_change_me";
  const params = new URLSearchParams({ per_page: "25", page: page || "1", min_locations: "3" });
  if (q) params.set("q", q);

  const res = await fetch(`${API_BASE}/api/v1/groups?${params}`, {
    headers: { "X-API-Key": API_KEY },
    next: { revalidate: 3600 },
  });
  if (!res.ok) return { data: [], meta: { total: 0, page: 1, pages: 0 } };
  return res.json();
}

export default async function GroupsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>;
}) {
  const params = await searchParams;
  const results = await fetchGroups(params.q, params.page);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold mb-2">Care Home Groups in the UK</h1>
      <div className="flex items-center justify-between mb-6">
        <p className="text-dusk">{results.meta.total.toLocaleString()} groups with 3+ locations</p>
        <div className="flex gap-3 items-center print:hidden">
          <PrintButton />
        </div>
      </div>

      {/* Search */}
      <form method="get" className="mb-8">
        <div className="flex gap-3">
          <input
            name="q"
            type="text"
            defaultValue={params.q || ""}
            placeholder="Search by group name..."
            className="flex-1 px-4 py-3 rounded-lg border border-stone bg-cream text-sm"
          />
          <button
            type="submit"
            className="px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
          >
            Search
          </button>
        </div>
      </form>

      {/* Results table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-stone text-left text-dusk">
              <th className="py-3 pr-4 font-medium">Group</th>
              <th className="py-3 pr-4 font-medium text-center">Locations</th>
              <th className="py-3 pr-4 font-medium text-center">Avg Quality</th>
              <th className="py-3 pr-4 font-medium text-center">% Good+</th>
              <th className="py-3 pr-4 font-medium text-center">Outstanding</th>
              <th className="py-3 pr-4 font-medium text-center">Good</th>
              <th className="py-3 pr-4 font-medium text-center">RI</th>
              <th className="py-3 pr-4 font-medium text-center">Inadequate</th>
              <th className="py-3 font-medium text-center">Beds</th>
            </tr>
          </thead>
          <tbody>
            {results.data.map((g: any) => (
              <tr key={g.provider_id} className="border-b border-stone/50 hover:bg-cream/50">
                <td className="py-3 pr-4">
                  <Link href={`/groups/${g.slug}`} className="font-semibold text-bark hover:text-clay">
                    {g.group_name}
                  </Link>
                  <p className="text-xs text-dusk">{(g.regions || []).slice(0, 3).join(", ")}</p>
                </td>
                <td className="py-3 pr-4 text-center font-mono">{g.location_count}</td>
                <td className="py-3 pr-4 text-center">
                  <span className="font-mono font-bold">{g.avg_quality_score || "—"}</span>
                  <span className="text-xs text-dusk">/100</span>
                </td>
                <td className="py-3 pr-4 text-center font-mono">{g.pct_good_or_outstanding ? `${g.pct_good_or_outstanding}%` : "—"}</td>
                <td className="py-3 pr-4 text-center font-mono text-moss">{g.outstanding_count}</td>
                <td className="py-3 pr-4 text-center font-mono text-amber">{g.good_count}</td>
                <td className="py-3 pr-4 text-center font-mono text-alert">{g.ri_count}</td>
                <td className="py-3 pr-4 text-center font-mono text-alert font-bold">{g.inadequate_count}</td>
                <td className="py-3 text-center font-mono">{g.total_beds || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {results.data.length === 0 && (
        <p className="text-center text-dusk py-12">No groups found.</p>
      )}

      {/* Pagination */}
      {results.meta.pages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {Array.from({ length: Math.min(results.meta.pages, 10) }, (_, i) => i + 1).map((p) => {
            const qp = new URLSearchParams();
            if (params.q) qp.set("q", params.q);
            qp.set("page", String(p));
            return (
              <Link
                key={p}
                href={`/groups?${qp}`}
                className={`px-3 py-2 rounded ${
                  p === results.meta.page
                    ? "bg-clay text-white"
                    : "bg-cream border border-stone text-dusk hover:border-clay"
                }`}
              >
                {p}
              </Link>
            );
          })}
          {results.meta.pages > 10 && <span className="px-2 py-2 text-dusk">...</span>}
        </div>
      )}
    </div>
  );
}
