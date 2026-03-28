import RatingBadge from "./RatingBadge";
import VerifiedBadge from "./VerifiedBadge";
import CompareButton from "./CompareButton";
import Link from "next/link";

interface Provider {
  slug: string;
  name: string;
  type: string;
  town: string;
  county: string;
  postcode: string;
  overall_rating: string;
  service_types: string;
  phone: string;
  number_of_beds: number | null;
  quality_tier: string;
  is_claimed?: boolean;
  review_count?: number;
  avg_review_rating?: number | null;
}

export default function ProviderCard({ provider }: { provider: Provider }) {
  const location = [provider.town, provider.county].filter(Boolean).join(", ");
  const services = provider.service_types?.split("|").slice(0, 2).join(", ") || "";

  return (
    <Link href={`/provider/${provider.slug}`}>
      <div className="bg-cream border border-stone rounded-lg p-5 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-lg font-semibold text-bark leading-tight truncate">{provider.name}</h3>
            {provider.is_claimed && <VerifiedBadge />}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <CompareButton slug={provider.slug} name={provider.name} />
            <RatingBadge rating={provider.overall_rating} />
          </div>
        </div>
        <p className="text-dusk text-sm mb-1">{location} {provider.postcode}</p>
        {services && <p className="text-dusk text-sm mb-2">{services}</p>}
        <div className="flex gap-3 text-sm text-dusk items-center">
          {provider.phone && <span>{provider.phone}</span>}
          {(provider.number_of_beds ?? 0) > 0 && <span>{provider.number_of_beds} beds</span>}
          {(provider.review_count ?? 0) > 0 && provider.avg_review_rating && (
            <span className="text-clay">{provider.avg_review_rating} stars ({provider.review_count})</span>
          )}
          <span className="ml-auto text-xs bg-parchment px-2 py-0.5 rounded">{provider.quality_tier}</span>
        </div>
      </div>
    </Link>
  );
}
