import RatingBadge from "./RatingBadge";
import VerifiedBadge from "./VerifiedBadge";
import CompareButton from "./CompareButton";
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
  data_completeness_score: number | null;
  data_completeness_tier: string;
  last_inspection_date: string | null;
  is_claimed?: boolean;
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

  return (
    <div className="bg-cream border border-stone rounded-lg p-5 hover:shadow-md transition-shadow">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-lg font-semibold text-bark leading-tight truncate">
              <a href={providerHref} className="hover:text-clay">{provider.name}</a>
            </h3>
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
          <span className="ml-auto flex items-center gap-2">
            {provider.data_completeness_score && (
              <span className="text-xs font-mono font-bold" style={{ color: provider.data_completeness_score >= 80 ? "#4A5E45" : provider.data_completeness_score >= 60 ? "#D4943A" : "#C44444" }}>
                Data {provider.data_completeness_score}/100
              </span>
            )}
            <span className="text-xs bg-parchment px-2 py-0.5 rounded" title="Public-record field completeness, not care quality">{provider.data_completeness_tier}</span>
          </span>
        </div>
        <a href={providerHref} className="mt-4 inline-flex text-sm font-semibold text-clay hover:text-bark">
          View provider details
        </a>
    </div>
  );
}
