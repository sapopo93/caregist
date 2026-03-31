import { getProvider, getProviderReviews } from "@/lib/api";
import RatingBadge from "@/components/RatingBadge";
import VerifiedBadge from "@/components/VerifiedBadge";
import ReviewsSection from "@/components/ReviewsSection";
import EnquiryForm from "@/components/EnquiryForm";
import CompareButton from "@/components/CompareButton";
import AeoBlock from "@/components/AeoBlock";
import ProviderJsonLd from "@/components/ProviderJsonLd";
import MonitorButton from "@/components/MonitorButton";
import RatingTimeline from "@/components/RatingTimeline";
import TrustSignal from "@/components/TrustSignal";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

const ratingDimensions = [
  { key: "rating_safe", label: "Safe" },
  { key: "rating_effective", label: "Effective" },
  { key: "rating_caring", label: "Caring" },
  { key: "rating_responsive", label: "Responsive" },
  { key: "rating_well_led", label: "Well-led" },
];

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const res = await getProvider(slug);
    const p = res.data;
    const aeoText = `${p.name} is a CQC-registered ${(p.type || "care provider").toLowerCase()} based in ${p.town || "England"}. Their current rating is ${p.overall_rating || "Not Yet Inspected"}.`;
    return {
      title: `${p.name} — CQC Rating & Inspection | CareGist`,
      description: p.meta_description || aeoText,
      alternates: { canonical: `https://caregist.co.uk/provider/${slug}` },
    };
  } catch {
    return { title: "Provider Not Found | CareGist" };
  }
}

export default async function ProviderPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let provider: any;
  try {
    const res = await getProvider(slug);
    provider = res.data;
  } catch (e: any) {
    if (e?.status === 404) notFound();
    return (
      <div className="max-w-4xl mx-auto px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-bark mb-4">Something went wrong</h1>
        <p className="text-dusk">We couldn&apos;t load this provider. Please try again later.</p>
      </div>
    );
  }

  if (!provider) notFound();

  // Fetch reviews (non-blocking — page still renders if this fails)
  let reviews: any[] = [];
  let reviewSummary = { count: 0, avg_rating: null as number | null };
  try {
    const reviewRes = await getProviderReviews(slug);
    reviews = reviewRes.data || [];
    reviewSummary = reviewRes.summary || reviewSummary;
  } catch {
    // Reviews failing shouldn't break the page
  }

  const location = [provider.address_line1, provider.address_line2, provider.town, provider.county, provider.postcode]
    .filter(Boolean)
    .join(", ");

  const services = provider.service_types?.split("|").filter(Boolean) || [];
  const specs = provider.specialisms?.split("|").filter(Boolean) || [];

  const daysSinceInspection = provider.last_inspection_date
    ? Math.floor((Date.now() - new Date(provider.last_inspection_date).getTime()) / 86400000)
    : null;

  return (
    <div>
      <ProviderJsonLd
        name={provider.name}
        type={provider.type}
        address={provider.address_line1}
        town={provider.town}
        postcode={provider.postcode}
        region={provider.region}
        phone={provider.phone}
        website={provider.website}
        rating={provider.overall_rating}
        latitude={provider.latitude}
        longitude={provider.longitude}
        slug={slug}
      />
      <AeoBlock
        name={provider.name}
        type={provider.type}
        town={provider.town}
        rating={provider.overall_rating}
        inspectionDate={provider.last_inspection_date}
      />
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Freshness warning */}
      {daysSinceInspection !== null && daysSinceInspection > 730 && (
        <div className="bg-amber/10 border border-amber rounded-lg p-4 mb-6 text-sm text-charcoal">
          This provider has not been inspected in over {Math.floor(daysSinceInspection / 365)} years. The rating shown may not reflect current performance.
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-3xl font-bold">{provider.name}</h1>
            {provider.is_claimed && <VerifiedBadge size="md" />}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <MonitorButton slug={slug} />
            <CompareButton slug={slug} name={provider.name} />
            <RatingBadge rating={provider.overall_rating} />
          </div>
        </div>
        <p className="text-dusk">{provider.type}</p>
        <p className="text-dusk">{location}</p>
        {provider.last_inspection_date && (
          <p className="text-sm text-dusk mt-1">
            Last inspected: {new Date(provider.last_inspection_date).toLocaleDateString("en-GB")}
            {daysSinceInspection !== null && <> ({daysSinceInspection} days ago)</>}
          </p>
        )}
        {provider.review_count > 0 && provider.avg_review_rating && (
          <p className="text-sm text-clay mt-1">
            {provider.avg_review_rating} stars from {provider.review_count} review{provider.review_count !== 1 ? "s" : ""}
          </p>
        )}
      </div>

      {/* Key Question Ratings */}
      {ratingDimensions.some((d) => provider[d.key]) && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">CQC Inspection Ratings</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {ratingDimensions.map((d) => (
              <div key={d.key} className="text-center">
                <div className="text-sm text-dusk mb-1">{d.label}</div>
                <RatingBadge rating={provider[d.key] || "N/A"} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rating History */}
      <RatingTimeline slug={slug} />

      {/* Details Grid */}
      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Contact */}
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Contact</h2>
          {provider.phone && (
            <p className="mb-1">
              <span className="text-dusk">Phone:</span>{" "}
              <a href={`tel:${provider.phone}`} className="text-clay underline">{provider.phone}</a>
            </p>
          )}
          {provider.website && (
            <p className="mb-1">
              <span className="text-dusk">Website:</span>{" "}
              <a href={provider.website} target="_blank" rel="noopener noreferrer" className="text-clay underline truncate inline-block max-w-xs">
                {provider.website.replace(/^https?:\/\//, "").slice(0, 40)}
              </a>
            </p>
          )}
          {provider.email && <p className="mb-1"><span className="text-dusk">Email:</span> {provider.email}</p>}
          {provider.latitude && provider.longitude && (
            <p className="mt-3">
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${provider.latitude},${provider.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-clay underline text-sm"
              >
                View on Google Maps
              </a>
            </p>
          )}
        </div>

        {/* Key Info */}
        <div className="bg-cream border border-stone rounded-lg p-6">
          <h2 className="text-xl font-bold mb-3">Details</h2>
          {provider.number_of_beds > 0 && <p className="mb-1"><span className="text-dusk">Beds:</span> {provider.number_of_beds}</p>}
          {provider.region && <p className="mb-1"><span className="text-dusk">Region:</span> {provider.region}</p>}
          {provider.local_authority && <p className="mb-1"><span className="text-dusk">Local Authority:</span> {provider.local_authority}</p>}
          {provider.registration_date && <p className="mb-1"><span className="text-dusk">Registered:</span> {provider.registration_date}</p>}
          {provider.last_inspection_date && <p className="mb-1"><span className="text-dusk">Last Inspection:</span> {provider.last_inspection_date}</p>}
          {provider.ownership_type && <p className="mb-1"><span className="text-dusk">Ownership:</span> {provider.ownership_type}</p>}
        </div>
      </div>

      {/* Services & Specialisms */}
      {(services.length > 0 || specs.length > 0) && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-3">Services & Specialisms</h2>
          {services.length > 0 && (
            <div className="mb-3">
              <span className="text-dusk text-sm">Services:</span>
              <div className="flex flex-wrap gap-2 mt-1">
                {services.map((s: string) => (
                  <span key={s} className="bg-parchment border border-stone px-3 py-1 rounded-full text-sm">{s}</span>
                ))}
              </div>
            </div>
          )}
          {specs.length > 0 && (
            <div>
              <span className="text-dusk text-sm">Specialisms:</span>
              <div className="flex flex-wrap gap-2 mt-1">
                {specs.map((s: string) => (
                  <span key={s} className="bg-parchment border border-stone px-3 py-1 rounded-full text-sm">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Enquiry Form — the money section */}
      <EnquiryForm slug={slug} providerName={provider.name} />

      {/* Reviews */}
      <ReviewsSection slug={slug} reviews={reviews} summary={reviewSummary} providerName={provider.name} />

      {/* CQC Link */}
      {provider.inspection_report_url && (
        <div className="text-center py-6">
          <a
            href={provider.inspection_report_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-6 py-3 bg-moss text-white rounded-lg font-medium hover:bg-bark transition-colors"
          >
            View full CQC inspection report
          </a>
        </div>
      )}

      {/* Claim listing */}
      {!provider.is_claimed && (
        <div className="text-center py-4">
          <Link href={`/claim/${slug}`} className="text-sm text-dusk hover:text-clay underline">
            Are you the provider? Claim this listing
          </Link>
        </div>
      )}

      {/* Attribution & Trust */}
      <div className="text-center text-sm text-dusk py-4 border-t border-stone mt-6">
        <p>{provider.data_attribution}</p>
        <p className="mt-1">Data completeness: {provider.quality_tier} ({provider.quality_score}/100)</p>
        <TrustSignal />
      </div>
    </div>
    </div>
  );
}
