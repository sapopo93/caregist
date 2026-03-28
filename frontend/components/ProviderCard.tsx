import RatingBadge from "./RatingBadge";
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
}

export default function ProviderCard({ provider }: { provider: Provider }) {
  const location = [provider.town, provider.county].filter(Boolean).join(", ");
  const services = provider.service_types?.split("|").slice(0, 2).join(", ") || "";

  return (
    <Link href={`/provider/${provider.slug}`}>
      <div className="bg-cream border border-stone rounded-lg p-5 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-semibold text-bark leading-tight">{provider.name}</h3>
          <RatingBadge rating={provider.overall_rating} />
        </div>
        <p className="text-dusk text-sm mb-1">{location} {provider.postcode}</p>
        {services && <p className="text-dusk text-sm mb-2">{services}</p>}
        <div className="flex gap-3 text-sm text-dusk">
          {provider.phone && <span>{provider.phone}</span>}
          {provider.number_of_beds > 0 && <span>{provider.number_of_beds} beds</span>}
          <span className="ml-auto text-xs bg-parchment px-2 py-0.5 rounded">{provider.quality_tier}</span>
        </div>
      </div>
    </Link>
  );
}
