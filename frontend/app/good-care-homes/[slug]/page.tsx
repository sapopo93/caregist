import { permanentRedirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function GoodCareHomesPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  permanentRedirect(`/search?q=${encodeURIComponent(slug.replace(/-/g, " "))}&service_type=residential-care-homes&rating=Good`);
}
