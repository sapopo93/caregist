import Link from "next/link";
import RatingBadge from "@/components/RatingBadge";
import PrintButton from "@/components/PrintButton";
import { getServerApiBase, getServerApiKey } from "@/lib/server-api-config";
import { getProviderHref } from "@/lib/provider-path";
import type { Metadata } from "next";

async function fetchGroup(slug: string) {
  const API_BASE = getServerApiBase();
  const API_KEY = getServerApiKey();
  const res = await fetch(`${API_BASE}/api/v1/groups/${slug}`, {
    headers: { "X-API-Key": API_KEY },
    next: { revalidate: 3600 },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.data;
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const group = await fetchGroup(slug);
  const name = group?.group_name || slug;
  return {
    title: `${name} — CQC Ratings & Benchmarking | CareGist`,
    description: `${name} operates ${group?.location_count || 0} care locations. ${group?.pct_good_or_outstanding || 0}% rated Good or Outstanding. Average quality score: ${group?.avg_quality_score || "N/A"}/100.`,
  };
}

export default async function GroupDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const group = await fetchGroup(slug);

  if (!group) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-16 text-center">
        <h1 className="text-2xl font-bold mb-4">Group not found</h1>
        <Link href="/groups" className="text-clay underline">Browse all groups</Link>
      </div>
    );
  }

  const benchmark = group.benchmark || {};
  const locations = group.locations || [];

  const ratingCounts = [
    { label: "Outstanding", count: group.outstanding_count, color: "bg-moss" },
    { label: "Good", count: group.good_count, color: "bg-amber" },
    { label: "Requires Improvement", count: group.ri_count, color: "bg-alert/70" },
    { label: "Inadequate", count: group.inadequate_count, color: "bg-alert" },
    { label: "Not Inspected", count: group.not_inspected_count, color: "bg-stone" },
  ];
  const inspected = group.location_count - group.not_inspected_count;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-2">
        <Link href="/groups" className="text-sm text-clay underline">All groups</Link>
        <PrintButton />
      </div>

      <h1 className="text-3xl font-bold mb-2">{group.group_name}</h1>
      <p className="text-dusk mb-8">
        {group.location_count} locations across {(group.regions || []).join(", ")}
        {group.total_beds ? ` · ${group.total_beds.toLocaleString()} total beds` : ""}
      </p>

      {/* Benchmark comparison */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <div className="bg-cream border border-stone rounded-lg p-5 text-center">
          <p className="text-sm text-dusk mb-1">Average Quality Score</p>
          <p className="text-3xl font-bold text-clay">{group.avg_quality_score || "—"}<span className="text-sm text-dusk">/100</span></p>
          {benchmark.national_avg_quality && (
            <p className="text-xs text-dusk mt-1">
              National avg: {benchmark.national_avg_quality}/100
              {group.avg_quality_score > benchmark.national_avg_quality
                ? <span className="text-moss ml-1">Above average</span>
                : <span className="text-alert ml-1">Below average</span>
              }
            </p>
          )}
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5 text-center">
          <p className="text-sm text-dusk mb-1">% Good or Outstanding</p>
          <p className="text-3xl font-bold text-clay">{group.pct_good_or_outstanding || "—"}<span className="text-sm text-dusk">%</span></p>
          {benchmark.national_pct_good && (
            <p className="text-xs text-dusk mt-1">
              National avg: {benchmark.national_pct_good}%
              {group.pct_good_or_outstanding > benchmark.national_pct_good
                ? <span className="text-moss ml-1">Above average</span>
                : <span className="text-alert ml-1">Below average</span>
              }
            </p>
          )}
        </div>
        <div className="bg-cream border border-stone rounded-lg p-5 text-center">
          <p className="text-sm text-dusk mb-1">Locations</p>
          <p className="text-3xl font-bold text-clay">{group.location_count}</p>
          <p className="text-xs text-dusk mt-1">{inspected} inspected · {group.not_inspected_count} pending</p>
        </div>
      </div>

      {/* Rating distribution bar */}
      <div className="bg-cream border border-stone rounded-lg p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Rating Distribution</h2>
        <div className="flex rounded-lg overflow-hidden h-8 mb-4">
          {ratingCounts.filter(r => r.count > 0).map((r) => (
            <div
              key={r.label}
              className={`${r.color} flex items-center justify-center text-white text-xs font-bold`}
              style={{ width: `${(r.count / group.location_count) * 100}%` }}
              title={`${r.label}: ${r.count}`}
            >
              {r.count > 0 && r.count}
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          {ratingCounts.map((r) => (
            <div key={r.label} className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${r.color}`} />
              <span className="text-dusk">{r.label}: {r.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* All locations */}
      <h2 className="text-xl font-bold mb-4">All {group.location_count} Locations</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-stone text-left text-dusk">
              <th className="py-3 pr-4 font-medium">Name</th>
              <th className="py-3 pr-4 font-medium">Location</th>
              <th className="py-3 pr-4 font-medium text-center">Rating</th>
              <th className="py-3 pr-4 font-medium text-center">Quality</th>
              <th className="py-3 pr-4 font-medium text-center">Beds</th>
              <th className="py-3 font-medium">Last Inspected</th>
            </tr>
          </thead>
          <tbody>
            {locations.map((loc: any) => (
              <tr key={loc.id} className="border-b border-stone/50 hover:bg-cream/50">
                <td className="py-3 pr-4">
                  <Link href={getProviderHref(loc)} className="text-bark hover:text-clay font-medium">
                    {loc.name}
                  </Link>
                </td>
                <td className="py-3 pr-4 text-dusk">{loc.town}{loc.postcode ? `, ${loc.postcode}` : ""}</td>
                <td className="py-3 pr-4 text-center"><RatingBadge rating={loc.overall_rating} /></td>
                <td className="py-3 pr-4 text-center font-mono">{loc.quality_score || "—"}</td>
                <td className="py-3 pr-4 text-center font-mono">{loc.number_of_beds || "—"}</td>
                <td className="py-3 text-dusk">
                  {loc.last_inspection_date
                    ? new Date(loc.last_inspection_date).toLocaleDateString("en-GB")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
