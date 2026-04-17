import RatingBadge from "./RatingBadge";
import VerifiedBadge from "./VerifiedBadge";
import CompareButton from "./CompareButton";
import Link from "next/link";
import { getProviderHref, getProviderPathKey } from "@/lib/provider-path";

interface Provider {
  id?: string | null;
  slug?: string | null;
  name: string;
  type: string;
  town: string;
  county: string;
  postcode: string;
  overall_rating: string;
  service_types: string;
  phone: string;
  number_of_beds: number | null;
  quality_score: number | null;
  quality_tier: string;
  last_inspection_date: string | null;
  is_claimed?: boolean;
  review_count?: number;
  avg_review_rating?: number | null;
}

const SERVICE_LABELS: Record<string, string> = {
  "Homecare Agencies": "Home Care",
  "Residential Homes": "Care Homes",
  "Nursing Homes": "Nursing Homes",
  "Doctors/Gps": "GP Surgery",
  "Dentist": "Dental",
  "Supported Living": "Supported Living",
  "Community Services - Healthcare": "Community Healthcare",
  "Hospitals - Mental Health/Capacity": "Mental Health Hospital",
};

export default function ProviderCard({ provider }: { provider: Provider }) {
  const location = [provider.town, provider.county].filter(Boolean).join(", ");
  const rawServices = provider.service_types?.split("|").slice(0, 2) || [];
  const services = rawServices.map((s) => SERVICE_LABELS[s.trim()] || s.trim()).join(", ");
  const providerKey = getProviderPathKey(provider);
  const providerHref = getProviderHref(provider);

  // Data confidence based on inspection age
  const confidence = (() => {
    if (!provider.last_inspection_date) return 10;
    const days = Math.floor((Date.now() - new Date(provider.last_inspection_date).getTime()) / 86400000);
    return Math.max(10, Math.round(100 - (days / 14)));
  })();
  const confColor = confidence >= 70 ? "#4A5E45" : confidence >= 40 ? "#D4943A" : "#C44444";

  return (
    <Link href={providerHref}>
      <div className="bg-cream border border-stone rounded-lg p-5 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-lg font-semibold text-bark leading-tight truncate">{provider.name}</h3>
            {provider.is_claimed && <VerifiedBadge />}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {providerKey && <CompareButton slug={providerKey} name={provider.name} />}
            <RatingBadge rating={provider.overall_rating} />
          </div>
        </div>
        <p className="text-dusk text-sm mb-1">{location} {provider.postcode}</p>
        {services && <p className="text-dusk text-sm mb-2">{services}</p>}
        <div className="flex gap-3 text-sm text-dusk items-center flex-wrap">
          {provider.phone && <span>{provider.phone}</span>}
          {(provider.number_of_beds ?? 0) > 0 && <span>{provider.number_of_beds} beds</span>}
          {(provider.review_count ?? 0) > 0 && provider.avg_review_rating && (
            <span className="text-clay">{provider.avg_review_rating} stars ({provider.review_count})</span>
          )}
          <span className="ml-auto flex items-center gap-2">
            {provider.quality_score && (
              <span className="text-xs font-mono font-bold" style={{ color: provider.quality_score >= 80 ? "#4A5E45" : provider.quality_score >= 60 ? "#D4943A" : "#C44444" }}>
                {provider.quality_score}/100
              </span>
            )}
            <span
              className="inline-block w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: confColor }}
              title={`Data confidence: ${confidence}% — based on inspection recency`}
            />
            <span className="text-xs bg-parchment px-2 py-0.5 rounded">{provider.quality_tier}</span>
          </span>
        </div>
      </div>
    </Link>
  );
}
