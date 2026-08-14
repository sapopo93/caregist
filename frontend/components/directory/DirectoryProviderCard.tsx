import type { DirectoryProviderSummary } from "@/lib/directory-db";
import CompareButton from "@/components/CompareButton";
import { getProviderHref } from "@/lib/provider-path";

function splitPipeValue(value: string | null): string[] {
  return (value ?? "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatLocation(provider: DirectoryProviderSummary) {
  return [provider.town, provider.county, provider.postcode].filter(Boolean).join(", ");
}

function formatInspectionDate(date: string | null) {
  if (!date) {
    return "Inspection date not published";
  }

  return new Date(date).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatRegistrationDate(date: string | null) {
  if (!date) {
    return "Registration date not published";
  }

  return new Date(date).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function DirectoryProviderCard({ provider }: { provider: DirectoryProviderSummary }) {
  const services = splitPipeValue(provider.service_types).slice(0, 3);
  const specialisms = splitPipeValue(provider.specialisms).slice(0, 3);
  const href = getProviderHref(provider);

  return (
    <article className="min-w-0 rounded-xl border border-stone bg-cream p-5 shadow-sm transition hover:border-clay sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">
            {provider.type ?? "Care provider"}
          </p>
          <h3 className="mt-2 break-words text-2xl font-bold leading-tight text-bark">
            <a href={href} className="hover:text-clay">
              {provider.name}
            </a>
          </h3>
          <p className="mt-2 break-words text-sm text-dusk">{formatLocation(provider)}</p>
        </div>

        <div className="flex max-w-full shrink-0 flex-wrap items-center justify-end gap-2">
          <CompareButton slug={provider.slug ?? provider.id} name={provider.name} />
          <div className="rounded-full border border-stone bg-white px-3 py-1 text-sm font-semibold text-bark">
            {provider.overall_rating ?? "Rating not published"}
          </div>
        </div>
      </div>

      {services.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {services.map((service) => (
            <span key={service} className="max-w-full break-words rounded-full bg-parchment px-3 py-1 text-xs font-medium text-bark">
              {service}
            </span>
          ))}
        </div>
      )}

      {specialisms.length > 0 && (
        <p className="mt-4 text-sm leading-6 text-dusk">
          <span className="font-semibold text-bark">Specialisms:</span> {specialisms.join(", ")}
        </p>
      )}

      <div className="mt-5 flex min-w-0 flex-wrap gap-4 text-sm text-dusk">
        {provider.phone && <span className="break-words">{provider.phone}</span>}
        {provider.number_of_beds ? <span>{provider.number_of_beds} beds</span> : null}
        <span>Registered: {formatRegistrationDate(provider.registration_date)}</span>
        <span>Last inspection: {formatInspectionDate(provider.last_inspection_date)}</span>
      </div>

      <div className="mt-5">
        <a href={href} className="text-sm font-semibold text-clay hover:text-bark">
          View provider details
        </a>
      </div>
    </article>
  );
}
