import ProviderCard from "@/components/ProviderCard";
import { getClaimHref, getProviderHref, getProviderPathKey } from "@/lib/provider-path";
import ExportCSVButton from "@/components/ExportCSVButton";
import PrintButton from "@/components/PrintButton";
import RatingDistributionBar from "@/components/RatingDistributionBar";
import EmailCaptureStrip from "@/components/EmailCaptureStrip";
import TrustSignal from "@/components/TrustSignal";
import Link from "next/link";
import { getCityProviders } from "@/lib/api";

const RATING_LABELS: Record<string, string> = {
  Outstanding: "Outstanding",
  Good: "Good",
  "Requires Improvement": "Requires Improvement",
};

export default async function CityRatingPage({
  slug,
  ratingFilter,
  ratingLabel,
}: {
  slug: string;
  ratingFilter: string | null;
  ratingLabel: string;
}) {
  let results: any = { data: [], meta: { city: slug, total: 0, page: 1, pages: 0, rating_distribution: {} } };
  let error = false;

  try {
    results = await getCityProviders(slug, {
      rating: ratingFilter || undefined,
      page: "1",
    });
  } catch {
    error = true;
  }

  const city = results.meta?.city || slug.replace(/-/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
  const total = results.meta?.total || 0;
  const distribution = results.meta?.rating_distribution || {};

  const h1 = ratingFilter
    ? `${ratingLabel} care homes in ${city}`
    : `Care homes in ${city}`;

  const aeo = ratingFilter
    ? `There are ${total} ${ratingLabel.toLowerCase()}-rated care homes in ${city} according to CQC inspections.`
    : `There are ${total} CQC-registered care providers in ${city}.`;

  // Schema.org JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: h1,
    numberOfItems: total,
    itemListElement: results.data.slice(0, 10).map((p: any, i: number) => ({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "LocalBusiness",
        name: p.name,
        address: { "@type": "PostalAddress", addressLocality: p.town, postalCode: p.postcode, addressCountry: "GB" },
        ...(getProviderPathKey(p) && { url: `https://caregist.co.uk${getProviderHref(p)}` }),
      },
    })),
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* AEO Block */}
      <section className="bg-parchment border-b border-stone rounded-t-lg px-6 py-4 text-sm text-charcoal leading-relaxed mb-6">
        <p>{aeo}</p>
      </section>

      <h1 className="text-3xl font-bold mb-2">{h1}</h1>
      <div className="flex items-center justify-between mb-6">
        <p className="text-dusk">{total.toLocaleString()} providers</p>
        <div className="flex gap-3 items-center print:hidden">
          <ExportCSVButton exportUrl={`/api/v1/providers/export.csv?q=${encodeURIComponent(city)}${ratingFilter ? `&rating=${encodeURIComponent(ratingFilter)}` : ""}`} />
          <PrintButton />
        </div>
      </div>

      {/* Rating Distribution */}
      {Object.keys(distribution).length > 0 && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Rating Distribution in {city}</h2>
          <RatingDistributionBar distribution={distribution} />
        </div>
      )}

      {error && (
        <div className="bg-cream border border-alert rounded-lg p-6 mb-6 text-center">
          <p className="text-bark font-semibold">Data is temporarily unavailable</p>
        </div>
      )}

      {/* Provider List */}
      <div className="grid gap-4">
        {results.data.map((provider: any) => (
          <div key={provider.id}>
            <ProviderCard provider={provider} />
            {!provider.is_claimed && (
              <div className="text-right -mt-2 mb-2">
                <Link href={getClaimHref(provider)} className="text-xs text-dusk hover:text-clay underline">
                  Is this your home? Claim it
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>

      {!error && results.data.length === 0 && (
        <p className="text-center text-dusk py-12">No providers found.</p>
      )}

      {/* Email Capture */}
      <div className="mt-8">
        <EmailCaptureStrip
          source={`seo_${slug}`}
          heading={`Get alerts for care providers in ${city}`}
        />
      </div>

      <div className="mt-4">
        <TrustSignal />
      </div>
    </div>
  );
}
