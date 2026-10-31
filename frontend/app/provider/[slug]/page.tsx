import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import RatingScale from "@/components/RatingScale";
import { getDirectoryProvider } from "@/lib/directory-db";
import { normalizeExternalHttpUrl, cqcEvidenceUrl } from "@/lib/external-url";
import { getProviderHref, directoryReturnHref } from "@/lib/provider-path";
import { ratingToneClass } from "@/lib/rating-tone";
import { ratingSourceNote } from "@/lib/rating-source";
import { getSiteUrl } from "@/lib/site";

const ratingDimensions = [
  { key: "rating_safe", label: "Safe" },
  { key: "rating_effective", label: "Effective" },
  { key: "rating_caring", label: "Caring" },
  { key: "rating_responsive", label: "Responsive" },
  { key: "rating_well_led", label: "Well-led" },
] as const;

export const dynamic = "force-dynamic";

function splitPipeValue(value: string | null): string[] {
  return (value ?? "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatDate(date: string | null) {
  if (!date) {
    return "Not published";
  }

  return new Date(date).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  let provider = null;

  try {
    provider = await getDirectoryProvider(slug);
  } catch {
    provider = null;
  }

  if (!provider) {
    notFound();
  }

  return {
    title: provider.meta_title || `${provider.name} | CareGist`,
    description:
      provider.meta_description ||
      `${provider.name} is a CQC-registered ${provider.type?.toLowerCase() ?? "care provider"} in ${
        provider.town ?? "England"
      }.`,
    alternates: { canonical: `${getSiteUrl()}${getProviderHref(provider)}` },
  };
}

export default async function ProviderPage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const returnTo = directoryReturnHref((await searchParams).returnTo);
  const { slug } = await params;
  let provider = null;

  try {
    provider = await getDirectoryProvider(slug);
  } catch {
    provider = null;
  }

  if (!provider) {
    notFound();
  }

  const serviceTypes = splitPipeValue(provider.service_types);
  const specialisms = splitPipeValue(provider.specialisms);
  const location = [provider.address_line1, provider.address_line2, provider.town, provider.county, provider.postcode]
    .filter(Boolean)
    .join(", ");
  const providerWebsite = normalizeExternalHttpUrl(provider.website);
  const inspectionReportUrl = cqcEvidenceUrl(provider.inspection_report_url, provider.id);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <Link href={returnTo} className="text-sm font-medium text-clay hover:text-bark">
        Back to search
      </Link>

      <div className="relative mt-4 overflow-hidden rounded-3xl border border-stone bg-cream p-8 pt-10 shadow-sm">
        <span aria-hidden className={`absolute inset-x-0 top-0 h-2 ${ratingToneClass(provider.overall_rating)}`} />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">
              {provider.type ?? "Care provider"}
            </p>
            <h1 className="mt-2 text-4xl font-extrabold leading-tight text-bark">{provider.name}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-dusk">{location}</p>
          </div>

          <div className="flex flex-col items-end gap-1">
            <div className="rounded-full border border-stone bg-white px-4 py-2 text-sm font-semibold text-bark">
              {provider.overall_rating ?? "Rating not published"}
            </div>
            {ratingSourceNote(provider.rating_source, provider.rating_source_date) && (
              <p className="max-w-xs text-right text-xs text-dusk">{ratingSourceNote(provider.rating_source, provider.rating_source_date)}</p>
            )}
          </div>
        </div>

        <dl className="mt-6 grid divide-y divide-stone rounded-2xl border border-stone bg-white md:grid-cols-3 md:divide-x md:divide-y-0">
          <div className="p-4">
            <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">Last inspection</dt>
            <dd className="mt-1 text-sm font-semibold text-bark">{formatDate(provider.last_inspection_date)}</dd>
          </div>
          <div className="p-4">
            <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">Phone</dt>
            <dd className="mt-1 text-sm font-semibold text-bark">{provider.phone ?? "Not published"}</dd>
          </div>
          <div className="p-4">
            <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">Beds</dt>
            <dd className="mt-1 text-sm font-semibold text-bark">
              {provider.number_of_beds ? `${provider.number_of_beds} beds` : "Not published"}
            </dd>
          </div>
        </dl>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <div className="space-y-6">
            <section className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <h2 className="text-2xl font-bold text-bark">CQC ratings</h2>
              <div className="mt-5 space-y-4">
                <RatingScale label="Overall" rating={provider.overall_rating} />
                <div className="border-t border-stone" />
                {ratingDimensions.map((dimension) => (
                  <RatingScale key={dimension.key} label={dimension.label} rating={provider[dimension.key]} />
                ))}
              </div>
              <p className="mt-5 text-xs leading-5 text-dusk">
                Published on CQC&apos;s four-step scale. An empty track means CQC has not published that rating.
              </p>
            </section>

            <section className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <h2 className="text-2xl font-bold text-bark">Service profile</h2>

              {serviceTypes.length > 0 ? (
                <>
                  <p className="mt-4 text-sm font-semibold text-bark">Service types</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {serviceTypes.map((value) => (
                      <span key={value} className="rounded-full bg-parchment px-3 py-1 text-xs font-medium text-bark">
                        {value}
                      </span>
                    ))}
                  </div>
                </>
              ) : null}

              {specialisms.length > 0 ? (
                <>
                  <p className="mt-5 text-sm font-semibold text-bark">Specialisms</p>
                  <ul className="mt-3 grid gap-2 text-sm text-dusk sm:grid-cols-2">
                    {specialisms.map((value) => (
                      <li key={value} className="rounded-2xl border border-stone bg-white px-4 py-3">
                        {value}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </section>
          </div>

          <div className="space-y-6">
            <section className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <h2 className="text-2xl font-bold text-bark">Contact</h2>
              <div className="mt-4 space-y-3 text-sm text-dusk">
                <p>
                  <span className="font-semibold text-bark">Region:</span> {provider.region ?? "Not published"}
                </p>
                <p>
                  <span className="font-semibold text-bark">Local authority:</span>{" "}
                  {provider.local_authority ?? "Not published"}
                </p>
                {provider.phone ? (
                  <p>
                    <span className="font-semibold text-bark">Phone:</span>{" "}
                    <a href={`tel:${provider.phone}`} className="text-clay underline">
                      {provider.phone}
                    </a>
                  </p>
                ) : null}
                {provider.website ? (
                  <p>
                    <span className="font-semibold text-bark">Website:</span>{" "}
                    {providerWebsite ? (
                      <a
                        href={providerWebsite}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="break-all text-clay underline"
                      >
                        {provider.website}
                      </a>
                    ) : (
                      <span className="break-all">{provider.website}</span>
                    )}
                  </p>
                ) : null}
                {inspectionReportUrl ? (
                  <p>
                    <span className="font-semibold text-bark">CQC report:</span>{" "}
                    <a
                      href={inspectionReportUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-clay underline"
                    >
                      View CQC record and reports
                    </a>
                  </p>
                ) : null}
              </div>
            </section>

            <section className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Source discipline</p>
              <h2 className="mt-2 text-2xl font-bold text-bark">Use the official evidence</h2>
              <p className="mt-3 text-sm leading-6 text-dusk">
                This free profile is a discovery aid. Confirm material decisions against
                the current CQC record. CareGist customers receive verified new-registration
                and rating-change events with source evidence and observation times.
              </p>
              <Link
                href="/pricing"
                className="mt-5 block rounded-full bg-clay px-4 py-2 text-center text-sm font-semibold text-white hover:bg-bark"
              >
                See the two products
              </Link>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
