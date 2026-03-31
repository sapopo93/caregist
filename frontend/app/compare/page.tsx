import { getCompareProviders, getComparisonByToken } from "@/lib/api";
import RatingBadge from "@/components/RatingBadge";
import VerifiedBadge from "@/components/VerifiedBadge";
import ComparisonActions from "@/components/ComparisonActions";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Compare Providers | CareGist",
  description: "Compare CQC-rated care providers side by side.",
};

const ratingDimensions = [
  { key: "rating_safe", label: "Safe" },
  { key: "rating_effective", label: "Effective" },
  { key: "rating_caring", label: "Caring" },
  { key: "rating_responsive", label: "Responsive" },
  { key: "rating_well_led", label: "Well-led" },
];

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ providers?: string; token?: string }>;
}) {
  const params = await searchParams;

  let slugs = params.providers?.split(",").filter(Boolean).slice(0, 3) || [];

  // Support shared comparison links via token
  if (!slugs.length && params.token) {
    try {
      const tokenRes = await getComparisonByToken(params.token);
      slugs = tokenRes.data?.slug_list || [];
    } catch {
      // fall through to the "select providers" prompt
    }
  }

  if (slugs.length < 2) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-bark mb-4">Compare Providers</h1>
        <p className="text-dusk mb-6">
          Select 2 or 3 providers to compare side by side. Use the &quot;+ Compare&quot; button on any provider card.
        </p>
        <Link href="/search" className="px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors">
          Search Providers
        </Link>
      </div>
    );
  }

  let providers: any[] = [];
  try {
    const res = await getCompareProviders(slugs);
    providers = res.data || [];
  } catch {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-bark mb-4">Comparison unavailable</h1>
        <p className="text-dusk">We couldn&apos;t load the providers. Please try again.</p>
      </div>
    );
  }

  if (providers.length < 2) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-bark mb-4">Providers not found</h1>
        <p className="text-dusk">Some of the selected providers could not be found.</p>
      </div>
    );
  }

  // Sort providers to match the slug order requested
  const ordered = slugs
    .map((s) => providers.find((p: any) => p.slug === s))
    .filter(Boolean);

  const colClass = ordered.length === 2 ? "grid-cols-2" : "grid-cols-3";

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Compare Providers</h1>
        <ComparisonActions slugs={slugs} />
      </div>

      {/* Provider names header */}
      <div className={`grid ${colClass} gap-4 mb-6`}>
        {ordered.map((p: any) => (
          <div key={p.slug} className="bg-cream border border-stone rounded-lg p-4 text-center">
            <Link href={`/provider/${p.slug}`} className="text-lg font-semibold text-bark hover:text-clay transition-colors">
              {p.name}
            </Link>
            <div className="flex items-center justify-center gap-2 mt-2">
              <RatingBadge rating={p.overall_rating} />
              {p.is_claimed && <VerifiedBadge />}
            </div>
            <p className="text-sm text-dusk mt-1">{p.type}</p>
          </div>
        ))}
      </div>

      {/* Comparison table */}
      <div className="border border-stone rounded-lg overflow-hidden">
        <CompareRow label="Location" cols={ordered.map((p: any) => [p.town, p.county, p.postcode].filter(Boolean).join(", "))} />
        <CompareRow label="Phone" cols={ordered.map((p: any) => p.phone || "-")} highlight />
        <CompareRow label="Beds" cols={ordered.map((p: any) => (p.number_of_beds > 0 ? String(p.number_of_beds) : "-"))} />
        <CompareRow label="Ownership" cols={ordered.map((p: any) => p.ownership_type || "-")} highlight />
        <CompareRow label="Quality Score" cols={ordered.map((p: any) => p.quality_score ? `${p.quality_score}/100` : "-")} />
        <CompareRow label="Last Inspection" cols={ordered.map((p: any) => p.last_inspection_date || "-")} highlight />

        {/* Overall rating row */}
        <div className={`grid ${colClass} gap-0 border-t border-stone`}>
          <div className="col-span-full bg-parchment px-4 py-2 font-semibold text-sm text-bark border-b border-stone">
            CQC Ratings
          </div>
        </div>
        <CompareRow label="Overall" cols={ordered.map((p: any) => p.overall_rating || "-")} isRating />
        {ratingDimensions.map((d, i) => (
          <CompareRow key={d.key} label={d.label} cols={ordered.map((p: any) => p[d.key] || "-")} isRating highlight={i % 2 === 1} />
        ))}

        {/* Services */}
        <div className={`grid ${colClass} gap-0 border-t border-stone`}>
          <div className="col-span-full bg-parchment px-4 py-2 font-semibold text-sm text-bark border-b border-stone">
            Services
          </div>
        </div>
        <div className={`grid ${colClass} gap-0 border-t border-stone`}>
          {ordered.map((p: any) => (
            <div key={p.slug} className="px-4 py-3 text-sm border-r last:border-r-0 border-stone">
              {p.service_types
                ? p.service_types.split("|").filter(Boolean).map((s: string) => (
                    <span key={s} className="inline-block bg-parchment border border-stone px-2 py-0.5 rounded-full text-xs mr-1 mb-1">{s}</span>
                  ))
                : <span className="text-dusk">-</span>}
            </div>
          ))}
        </div>

        {/* Community reviews */}
        <CompareRow label="Community Reviews" cols={ordered.map((p: any) =>
          p.review_count > 0 && p.avg_review_rating
            ? `${p.avg_review_rating} stars (${p.review_count})`
            : "No reviews yet"
        )} highlight />
      </div>

      {/* Enquiry CTAs */}
      <div className={`grid ${colClass} gap-4 mt-6`}>
        {ordered.map((p: any) => (
          <Link
            key={p.slug}
            href={`/provider/${p.slug}#enquiry`}
            className="block text-center px-4 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
          >
            Enquire about {p.name.length > 20 ? p.name.slice(0, 20) + "..." : p.name}
          </Link>
        ))}
      </div>
    </div>
  );
}

function CompareRow({
  label,
  cols,
  highlight = false,
  isRating = false,
}: {
  label: string;
  cols: string[];
  highlight?: boolean;
  isRating?: boolean;
}) {
  const colClass = cols.length === 2 ? "grid-cols-[140px_1fr_1fr]" : "grid-cols-[140px_1fr_1fr_1fr]";
  return (
    <div className={`grid ${colClass} gap-0 border-t border-stone ${highlight ? "bg-parchment/50" : ""}`}>
      <div className="px-4 py-2.5 text-sm font-medium text-bark border-r border-stone">{label}</div>
      {cols.map((val, i) => (
        <div key={i} className="px-4 py-2.5 text-sm border-r last:border-r-0 border-stone">
          {isRating ? <RatingBadge rating={val} /> : val}
        </div>
      ))}
    </div>
  );
}
