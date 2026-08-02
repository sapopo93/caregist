import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import EnquiryForm from "@/components/EnquiryForm";
import ReviewsSection from "@/components/ReviewsSection";
import { getProviderReviews } from "@/lib/api";
import { getDirectoryProvider } from "@/lib/directory-db";
import { getProviderHref } from "@/lib/provider-path";
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

export default async function ProviderPage({ params }: { params: Promise<{ slug: string }> }) {
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

  const providerSlug = provider.slug ?? provider.id;
  let reviews: any[] = [];
  let reviewSummary: { count: number; avg_rating: number | null } = { count: 0, avg_rating: null };
  try {
    const reviewData = await getProviderReviews(providerSlug);
    reviews = Array.isArray(reviewData?.data) ? reviewData.data : [];
    reviewSummary = reviewData?.summary ?? reviewSummary;
  } catch {
    // Reviews are supplementary; keep the provider page useful during an API cold start.
  }
  const serviceTypes = splitPipeValue(provider.service_types);
  const specialisms = splitPipeValue(provider.specialisms);
  const location = [provider.address_line1, provider.address_line2, provider.town, provider.county, provider.postcode]
    .filter(Boolean)
    .join(", ");
  const leadParams = new URLSearchParams();
  if (provider.region) leadParams.set("region", provider.region);
  if (serviceTypes[0]) leadParams.set("service_type", serviceTypes[0]);
  if (provider.overall_rating) leadParams.set("rating", provider.overall_rating);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <Link href="/search" className="text-sm font-medium text-clay hover:text-bark">
        Back to search
      </Link>

      <div className="mt-4 rounded-3xl border border-stone bg-cream p-8 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">
              {provider.type ?? "Care provider"}
            </p>
            <h1 className="mt-2 text-4xl font-extrabold leading-tight text-bark">{provider.name}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-dusk">{location}</p>
          </div>

          <div className="rounded-full border border-stone bg-white px-4 py-2 text-sm font-semibold text-bark">
            {provider.overall_rating ?? "Rating not published"}
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-stone bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">Inspection</p>
            <p className="mt-2 text-sm text-dusk">Last inspection: {formatDate(provider.last_inspection_date)}</p>
          </div>
          <div className="rounded-2xl border border-stone bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">Phone</p>
            <p className="mt-2 text-sm text-dusk">{provider.phone ?? "Not published"}</p>
          </div>
          <div className="rounded-2xl border border-stone bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">Beds</p>
            <p className="mt-2 text-sm text-dusk">
              {provider.number_of_beds ? `${provider.number_of_beds} beds` : "Not published"}
            </p>
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <div className="space-y-6">
            <section className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <h2 className="text-2xl font-bold text-bark">CQC ratings</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {ratingDimensions.map((dimension) => (
                  <div key={dimension.key} className="rounded-2xl border border-stone bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-clay">
                      {dimension.label}
                    </p>
                    <p className="mt-2 text-sm text-dusk">
                      {provider[dimension.key] ?? "Not published"}
                    </p>
                  </div>
                ))}
              </div>
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
                    <a
                      href={provider.website}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="break-all text-clay underline"
                    >
                      {provider.website}
                    </a>
                  </p>
                ) : null}
                {provider.inspection_report_url ? (
                  <p>
                    <span className="font-semibold text-bark">CQC report:</span>{" "}
                    <a
                      href={provider.inspection_report_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-clay underline"
                    >
                      View report
                    </a>
                  </p>
                ) : null}
              </div>
              <Link
                href={`/claim/${encodeURIComponent(providerSlug)}`}
                className="mt-5 block rounded-full border border-clay px-4 py-2 text-center text-sm font-semibold text-clay hover:bg-parchment"
              >
                Claim or manage this profile
              </Link>
            </section>

            <section className="rounded-3xl border border-stone bg-cream p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Monetisation</p>
              <h2 className="mt-2 text-2xl font-bold text-bark">Want this segment as a CSV?</h2>
              <p className="mt-3 text-sm leading-6 text-dusk">
                Request a filtered opportunity list for this provider&apos;s region and service type, or ask for
                wider market access when the buyer needs more than one segment.
              </p>
              <div className="mt-5 flex flex-col gap-3">
                <Link
                  href={leadParams.toString() ? `/lead-list?${leadParams.toString()}` : "/lead-list"}
                  className="rounded-full bg-clay px-4 py-2 text-center text-sm font-semibold text-white hover:bg-bark"
                >
                  Get a lead list
                </Link>
                <a
                  href="/lead-list"
                  className="rounded-full border border-clay px-4 py-2 text-center text-sm font-semibold text-clay hover:bg-parchment"
                >
                  Request wider access
                </a>
              </div>
            </section>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <ReviewsSection
          slug={providerSlug}
          reviews={reviews}
          summary={reviewSummary}
          providerName={provider.name}
        />
        <EnquiryForm slug={providerSlug} providerName={provider.name} />
      </div>
    </div>
  );
}
