import CityRatingPage from "@/components/CityRatingPage";
import { getTopCities } from "@/lib/api";
import type { Metadata } from "next";

export const revalidate = 86400;

export async function generateStaticParams() {
  try {
    const res = await getTopCities();
    return (res.data || []).slice(0, 500).map((c: any) => ({ slug: c.slug }));
  } catch {
    return [];
  }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const city = slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return {
    title: `Requires Improvement Care Homes in ${city} — CQC Rated | CareGist`,
    description: `Find care homes rated Requires Improvement in ${city}. CQC inspection data, ratings, and provider details.`,
    alternates: { canonical: `https://caregist.co.uk/requires-improvement-care-homes/${slug}` },
  };
}

export default async function RequiresImprovementCareHomesPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <CityRatingPage slug={slug} ratingFilter="Requires Improvement" ratingLabel="Requires Improvement" />;
}
