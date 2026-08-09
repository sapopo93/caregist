import {
  DEFAULT_RATING_OPTIONS,
  DEFAULT_REGION_OPTIONS,
  DEFAULT_SERVICE_TYPE_OPTIONS,
  DIRECTORY_OPPORTUNITY_OPTIONS,
  type DirectoryOpportunity,
} from "@/lib/directory-constants";
import type { DirectoryFilterOptions } from "@/lib/directory-db";

interface Props {
  action?: string;
  title?: string;
  titleHeading?: "h1" | "h2";
  description?: string;
  query?: string;
  region?: string;
  serviceType?: string;
  rating?: string;
  opportunity?: DirectoryOpportunity | "";
  submitLabel?: string;
  options?: DirectoryFilterOptions | null;
}

export default function DirectorySearchForm({
  action = "/search",
  title = "Search 55,818 active CQC providers",
  titleHeading = "h2",
  description = "Search by provider name or town, then narrow by region, service type, and rating.",
  query = "",
  region = "",
  serviceType = "",
  rating = "",
  opportunity = "",
  submitLabel = "Search directory",
  options,
}: Props) {
  const regions = options?.regions ?? DEFAULT_REGION_OPTIONS;
  const serviceTypes = options?.serviceTypes ?? DEFAULT_SERVICE_TYPE_OPTIONS;
  const ratings = options?.ratings ?? DEFAULT_RATING_OPTIONS;
  const TitleHeading = titleHeading;

  return (
    <section className="min-w-0 rounded-xl border border-stone bg-cream p-5 shadow-sm sm:p-6">
      <div className="max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-clay">CQC directory</p>
        <TitleHeading className="mt-2 text-3xl font-extrabold leading-tight text-bark">
          {title}
        </TitleHeading>
        <p className="mt-3 text-sm leading-6 text-dusk">{description}</p>
      </div>

      <form action={action} method="get" className="mt-6 grid min-w-0 gap-4 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1fr_auto]">
        <div>
          <label htmlFor="directory-q" className="mb-1 block text-sm font-medium text-bark">
            Name or town
          </label>
          <input
            id="directory-q"
            name="q"
            defaultValue={query}
            placeholder="London, Ipswich, Henley House..."
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none ring-0 transition focus:border-clay"
          />
        </div>

        <div>
          <label htmlFor="directory-opportunity" className="mb-1 block text-sm font-medium text-bark">
            Factual segment
          </label>
          <select
            id="directory-opportunity"
            name="opportunity"
            defaultValue={opportunity}
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none transition focus:border-clay"
          >
            <option value="">All provider records</option>
            {DIRECTORY_OPPORTUNITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.shortLabel}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="directory-region" className="mb-1 block text-sm font-medium text-bark">
            Region
          </label>
          <select
            id="directory-region"
            name="region"
            defaultValue={region}
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none transition focus:border-clay"
          >
            <option value="">All regions</option>
            {regions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="directory-service-type" className="mb-1 block text-sm font-medium text-bark">
            Service type
          </label>
          <select
            id="directory-service-type"
            name="service_type"
            defaultValue={serviceType}
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none transition focus:border-clay"
          >
            <option value="">All service types</option>
            {serviceTypes.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="directory-rating" className="mb-1 block text-sm font-medium text-bark">
            Rating
          </label>
          <select
            id="directory-rating"
            name="rating"
            defaultValue={rating}
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none transition focus:border-clay"
          >
            <option value="">All ratings</option>
            {ratings.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            className="w-full rounded-xl bg-clay px-5 py-3 text-sm font-semibold text-white transition hover:bg-bark lg:w-auto"
          >
            {submitLabel}
          </button>
        </div>
      </form>
    </section>
  );
}
