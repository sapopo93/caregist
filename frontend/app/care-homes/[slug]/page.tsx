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
    title: `Care Homes in ${city} — CQC Rated | CareGist`,
    description: `Browse all CQC-rated care homes in ${city}. Inspection data, ratings, and provider details.`,
    alternates: { canonical: `https://caregist.co.uk/care-homes/${slug}` },
  };
}

export default async function AllCareHomesPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <CityRatingPage slug={slug} ratingFilter={null} ratingLabel="All" />;
}
