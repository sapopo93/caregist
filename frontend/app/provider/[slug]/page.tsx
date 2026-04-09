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
import TrackProfileView from "@/components/TrackProfileView";
import CareGistAssessment from "@/components/CareGistAssessment";
import MapView from "@/components/MapView";
import ServiceBreakdown from "@/components/ServiceBreakdown";
import ProfileNav from "@/components/ProfileNav";
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

function parseProfilePhotos(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string" && item.length > 0);
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed)
        ? parsed.filter((item): item is string => typeof item === "string" && item.length > 0)
        : [];
    } catch {
      return [];
    }
  }
  return [];
}

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

  const profilePhotos = parseProfilePhotos(provider.profile_photos);

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

  // service_types and specialisms are used by ServiceBreakdown component

  const daysSinceInspection = provider.last_inspection_date
    ? Math.floor((Date.now() - new Date(provider.last_inspection_date).getTime()) / 86400000)
    : null;

  return (
    <div>
      <TrackProfileView slug={slug} />
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
          This service was last inspected over {Math.floor(daysSinceInspection / 365)} years ago. The rating shown is the most recent available from CQC. Consider contacting the provider directly for the latest information.
        </div>
      )}

      {/* Header */}
      <div className="mb-8" id="overview">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-center gap-3 flex-wrap">
            {provider.logo_url && (
              <img src={provider.logo_url} alt={`${provider.name} logo`} className="h-12 w-12 rounded-lg object-contain bg-white border border-stone" />
            )}
            <h1 className="text-3xl font-bold">{provider.name}</h1>
            {provider.is_claimed && <VerifiedBadge size="md" />}
            {provider.is_claimed && (
              <a href={`/provider-dashboard/${slug}`} className="text-xs text-clay underline ml-2">Manage listing</a>
            )}
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

      {/* Quick Actions */}
      <div className="flex gap-3 mb-6 print:hidden">
        <a href="#enquiry" className="px-5 py-2 bg-clay text-white rounded-lg text-sm font-medium hover:bg-bark transition-colors">
          Contact this provider
        </a>
        {!provider.is_claimed && (
          <a href={`/claim/${slug}`} className="px-5 py-2 border border-clay text-clay rounded-lg text-sm font-medium hover:bg-clay hover:text-white transition-colors">
            Claim this listing
          </a>
        )}
      </div>

      {/* Sticky section nav */}
      <ProfileNav />

      {/* Enhanced Profile — paid content from claimed providers */}
      {provider.profile_description && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          {profilePhotos.length > 0 && (
            <div className="flex gap-3 overflow-x-auto mb-4 pb-2">
              {profilePhotos.map((url: string, i: number) => (
                <img key={i} src={url} alt={`${provider.name} photo ${i + 1}`} className="h-48 rounded-lg object-cover flex-shrink-0" />
              ))}
            </div>
          )}
          <h2 className="text-xl font-bold mb-3">About {provider.name}</h2>
          <p className="text-sm text-charcoal leading-relaxed">{provider.profile_description}</p>
          {provider.virtual_tour_url && (
            <a
              href={provider.virtual_tour_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-3 px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors"
            >
              Take a virtual tour
            </a>
          )}
        </div>
      )}

      {provider.inspection_response && (
        <div className="bg-moss/5 border border-moss/20 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-3 text-moss">Provider Response to Inspection</h2>
          <p className="text-xs font-semibold text-dusk mb-2">The provider states:</p>
          <p className="text-sm text-charcoal leading-relaxed">{provider.inspection_response}</p>
          <p className="text-xs text-dusk mt-3">This response was submitted by the care provider. CareGist does not verify provider statements.</p>
        </div>
      )}

      {/* CTA for unclaimed providers */}
      {!provider.is_claimed && (
        <div className="bg-amber/5 border border-amber/20 rounded-lg p-4 mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-bark">Is this your care service?</p>
            <p className="text-xs text-dusk">Claim this listing to add photos, respond to inspections, and track analytics.</p>
          </div>
          <a href={`/claim/${slug}`} className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors shrink-0">
            Claim listing
          </a>
        </div>
      )}

      {/* Inspection Summary */}
      {provider.inspection_summary && (
        <div className="bg-parchment border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-3">Inspection Summary</h2>
          <p className="text-sm text-charcoal leading-relaxed">{provider.inspection_summary}</p>
          {provider.inspection_report_url && (
            <a
              href={provider.inspection_report_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-3 text-sm text-clay underline hover:text-bark"
            >
              Read full CQC inspection report
            </a>
          )}
          <p className="text-xs text-dusk mt-2">
            Contains CQC data. Crown copyright and database right.
          </p>
        </div>
      )}

      {/* CareGist Assessment */}
      <CareGistAssessment provider={provider} />

      {/* Key Question Ratings — always show all 5, flag unassessed */}
      {provider.overall_rating && provider.overall_rating !== "Not Yet Inspected" && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6" id="ratings">
          <h2 className="text-xl font-bold mb-4">CQC Inspection Ratings</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {ratingDimensions.map((d) => (
              <div key={d.key} className="text-center">
                <div className="text-sm text-dusk mb-1">{d.label}</div>
                {provider[d.key] ? (
                  <RatingBadge rating={provider[d.key]} />
                ) : (
                  <span className="inline-block px-3 py-1 bg-stone/20 text-dusk text-xs rounded-full">
                    Not assessed
                  </span>
                )}
              </div>
            ))}
          </div>
          {ratingDimensions.some((d) => !provider[d.key]) && (
            <p className="text-xs text-dusk mt-4">
              Dimensions marked &ldquo;Not assessed&rdquo; were not evaluated in the most recent CQC inspection.
              This may indicate a focused inspection rather than a comprehensive assessment.
            </p>
          )}
        </div>
      )}

      {/* Rating History */}
      <RatingTimeline slug={slug} />

      {/* Details Grid */}
      <div className="grid md:grid-cols-2 gap-6 mb-6" id="contact-details">
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

      {/* Map */}
      {provider.latitude && provider.longitude && (
        <div className="bg-cream border border-stone rounded-lg p-4 mb-6">
          <h2 className="text-xl font-bold mb-3">Location</h2>
          <MapView providers={[{
            slug: slug,
            name: provider.name,
            town: provider.town || "",
            overall_rating: provider.overall_rating || "",
            latitude: provider.latitude,
            longitude: provider.longitude,
            type: provider.type || "",
          }]} />
        </div>
      )}

      {/* Care Provided — categorised services, specialisms, regulated activities */}
      <ServiceBreakdown
        serviceTypes={provider.service_types}
        specialisms={provider.specialisms}
        regulatedActivities={provider.regulated_activities}
      />

      {/* Funding & Fees — provider-entered when claimed */}
      {((provider.funding_types && provider.funding_types.length > 0) || provider.fee_guidance) && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6" id="funding">
          <h2 className="text-xl font-bold mb-4">Funding & Fees</h2>
          {provider.fee_guidance && (
            <p className="text-charcoal mb-3">{provider.fee_guidance}</p>
          )}
          {provider.funding_types && (
            <div>
              <p className="text-sm text-dusk mb-2 font-semibold">Funding types accepted:</p>
              <div className="flex flex-wrap gap-2">
                {provider.funding_types.map((f: string) => (
                  <span key={f} className="bg-parchment border border-stone px-3 py-1.5 rounded-lg text-sm text-charcoal">
                    {f.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Practical Details — provider-entered when claimed */}
      {(provider.min_visit_duration || (provider.contract_types && provider.contract_types.length > 0) || (provider.age_ranges && provider.age_ranges.length > 0)) && (
        <div className="bg-cream border border-stone rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Practical Details</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {provider.min_visit_duration && (
              <div className="bg-parchment rounded-lg p-4">
                <p className="text-sm text-dusk font-semibold mb-1">Minimum visit</p>
                <p className="text-charcoal">{provider.min_visit_duration}</p>
              </div>
            )}
            {provider.contract_types && (
              <div className="bg-parchment rounded-lg p-4">
                <p className="text-sm text-dusk font-semibold mb-1">Contract types</p>
                <ul className="space-y-1">
                  {provider.contract_types.map((c: string) => (
                    <li key={c} className="text-sm text-charcoal">
                      <span className="text-moss mr-1">&#10003;</span>
                      {c.replace(/_/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase())}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {provider.age_ranges && (
              <div className="bg-parchment rounded-lg p-4">
                <p className="text-sm text-dusk font-semibold mb-1">Age groups</p>
                <ul className="space-y-1">
                  {provider.age_ranges.map((a: string) => (
                    <li key={a} className="text-sm text-charcoal">
                      <span className="text-moss mr-1">&#10003;</span>
                      {a.replace(/_/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase())}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Enquiry Form — the money section */}
      <div id="enquiry">
        <EnquiryForm slug={slug} providerName={provider.name} />
      </div>

      {/* Reviews */}
      <div id="reviews">
        <ReviewsSection slug={slug} reviews={reviews} summary={reviewSummary} providerName={provider.name} />
      </div>

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
