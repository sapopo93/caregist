import { getProvider } from "@/lib/api";
import ClaimStepper from "@/components/ClaimStepper";
import TrackEventOnMount from "@/components/TrackEventOnMount";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const res = await getProvider(slug);
    return {
      title: `Claim ${res.data.name} | CareGist`,
      description: `Claim and verify your listing for ${res.data.name} on CareGist.`,
    };
  } catch {
    return { title: "Claim Provider | CareGist" };
  }
}

export default async function ClaimPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let provider: any;
  try {
    const res = await getProvider(slug);
    provider = res.data;
  } catch (e: any) {
    if (e?.status === 404) notFound();
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-bark mb-4">Something went wrong</h1>
        <p className="text-dusk">We couldn&apos;t load this provider. Please try again later.</p>
      </div>
    );
  }

  if (!provider) notFound();

  if (provider.is_claimed) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <h1 className="text-2xl font-bold text-bark mb-4">Already claimed</h1>
        <p className="text-dusk mb-6">
          {provider.name} has already been claimed and verified.
        </p>
        <a
          href={`/provider/${slug}`}
          className="inline-block px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
        >
          View provider
        </a>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <TrackEventOnMount eventType="provider_claim_start" eventSource="claim_page" meta={{ slug }} />
      <ClaimStepper
        slug={slug}
        providerName={provider.name}
        providerId={provider.id}
      />
    </div>
  );
}
