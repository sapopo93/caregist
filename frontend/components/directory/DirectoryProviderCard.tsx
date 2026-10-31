import type { DirectoryProviderSummary } from "@/lib/directory-db";
import CompareButton from "@/components/CompareButton";
import { getProviderHref, directoryReturnHref } from "@/lib/provider-path";
import { ratingSourceNote } from "@/lib/rating-source";
import { ratingToneClass } from "@/lib/rating-tone";

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
    return "Not published";
  }

  return new Date(date).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatRegistrationDate(date: string | null) {
  if (!date) {
    return "Not published";
  }

  return new Date(date).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function DirectoryProviderCard({ provider, returnTo }: { provider: DirectoryProviderSummary; returnTo?: string }) {
  const services = splitPipeValue(provider.service_types).slice(0, 2);
  const href = `${getProviderHref(provider)}${returnTo ? `?returnTo=${encodeURIComponent(directoryReturnHref(returnTo))}` : ""}`;

  return (
    <article className="group relative grid min-w-0 grid-cols-[0.375rem_1fr] overflow-hidden rounded-lg border border-stone bg-cream transition hover:border-clay hover:shadow-md">
      <span aria-hidden className={`${ratingToneClass(provider.overall_rating)}`} />
      <div className="grid min-w-0 gap-x-6 gap-y-2 p-4 md:grid-cols-[minmax(0,1fr)_11rem_9rem_auto] md:items-center">
        <div className="min-w-0">
          <h3 className="break-words text-lg font-bold leading-snug text-bark">
            <a href={href} className="after:absolute after:inset-0 hover:text-clay">
              {provider.name}
            </a>
          </h3>
          <p className="mt-0.5 break-words text-sm text-dusk">{formatLocation(provider)}</p>
          {services.length > 0 && (
            <p className="mt-1 break-words text-xs text-dusk">{services.join(" · ")}</p>
          )}
        </div>

        <dl className="text-xs leading-5 text-dusk">
          <div className="flex gap-1.5"><dt className="font-semibold text-bark">Registered</dt><dd>{formatRegistrationDate(provider.registration_date)}</dd></div>
          <div className="flex gap-1.5"><dt className="font-semibold text-bark">Inspected</dt><dd>{formatInspectionDate(provider.last_inspection_date)}</dd></div>
          {provider.number_of_beds ? <div className="flex gap-1.5"><dt className="font-semibold text-bark">Beds</dt><dd>{provider.number_of_beds}</dd></div> : null}
        </dl>

        <div className="md:text-right">
          <p className="text-sm font-semibold text-bark">
            {provider.overall_rating ?? "Rating not published"}
          </p>
          {ratingSourceNote(provider.rating_source, provider.rating_source_date) && (
            <p className="mt-0.5 text-xs text-dusk">{ratingSourceNote(provider.rating_source, provider.rating_source_date)}</p>
          )}
        </div>

        <div className="relative z-10 md:justify-self-end">
          <CompareButton slug={provider.slug ?? provider.id} name={provider.name} />
        </div>
      </div>
    </article>
  );
}
