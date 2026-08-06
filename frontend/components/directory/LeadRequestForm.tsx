import {
  DEFAULT_RATING_OPTIONS,
  DEFAULT_REGION_OPTIONS,
  DEFAULT_SERVICE_TYPE_OPTIONS,
  DIRECTORY_OPPORTUNITY_OPTIONS,
  type DirectoryOpportunity,
} from "@/lib/directory-constants";
import type { DirectoryFilterOptions } from "@/lib/directory-db";

interface Props {
  options?: DirectoryFilterOptions | null;
  defaults?: {
    region?: string;
    serviceType?: string;
    rating?: string;
    opportunity?: DirectoryOpportunity | "";
  };
  error?: string;
}

export default function LeadRequestForm({ options, defaults, error }: Props) {
  const regions = options?.regions ?? DEFAULT_REGION_OPTIONS;
  const serviceTypes = options?.serviceTypes ?? DEFAULT_SERVICE_TYPE_OPTIONS;
  const ratings = options?.ratings ?? DEFAULT_RATING_OPTIONS;

  return (
    <form id="lead-request" action="/api/leads/request" method="post" className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
      <div className="max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Get a lead list</p>
        <h2 className="mt-2 text-3xl font-extrabold leading-tight text-bark">
          Request a filtered provider export
        </h2>
        <p className="mt-3 text-sm leading-6 text-dusk">
          Choose the segment you want, leave your email, and CareGist will create an export token for
          this filtered list.
        </p>
      </div>

      {error ? (
        <div className="mt-5 rounded-2xl border border-alert/20 bg-alert/10 px-4 py-3 text-sm text-alert">
          {error}
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="lead-opportunity" className="mb-1 block text-sm font-medium text-bark">
            Opportunity list
          </label>
          <select
            id="lead-opportunity"
            name="opportunity"
            defaultValue={defaults?.opportunity ?? ""}
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none transition focus:border-clay"
          >
            <option value="">All opportunities</option>
            {DIRECTORY_OPPORTUNITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.shortLabel}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="lead-region" className="mb-1 block text-sm font-medium text-bark">
            Region
          </label>
          <select
            id="lead-region"
            name="region"
            defaultValue={defaults?.region ?? ""}
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
          <label htmlFor="lead-service-type" className="mb-1 block text-sm font-medium text-bark">
            Service type
          </label>
          <select
            id="lead-service-type"
            name="service_type"
            defaultValue={defaults?.serviceType ?? ""}
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
          <label htmlFor="lead-rating" className="mb-1 block text-sm font-medium text-bark">
            Rating
          </label>
          <select
            id="lead-rating"
            name="rating"
            defaultValue={defaults?.rating ?? ""}
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

        <div>
          <label htmlFor="lead-email" className="mb-1 block text-sm font-medium text-bark">
            Email
          </label>
          <input
            id="lead-email"
            name="email"
            type="email"
            required
            placeholder="buyer@company.com"
            className="w-full rounded-xl border border-stone bg-white px-4 py-3 text-sm text-charcoal outline-none transition focus:border-clay"
          />
        </div>
      </div>

      <button
        type="submit"
        className="mt-6 rounded-xl bg-clay px-5 py-3 text-sm font-semibold text-white transition hover:bg-bark"
      >
        Create lead request
      </button>

      <p className="mt-3 text-xs leading-5 text-dusk">
        The export token only unlocks the filtered segment you requested and expires after seven days.
      </p>
    </form>
  );
}
