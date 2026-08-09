import { getProvider } from "@/lib/api";
import { getProviderHref } from "@/lib/provider-path";
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
          href={getProviderHref(provider)}
          className="inline-block px-6 py-3 bg-clay text-white rounded-lg font-medium hover:bg-bark transition-colors"
        >
          View provider
        </a>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12">
      <div className="rounded-xl border border-stone bg-white p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Controlled hold</p>
        <h1 className="mt-2 text-2xl font-bold text-bark">Claims are not currently accepting submissions</h1>
        <p className="mt-4 text-dusk">
          The listing for <strong>{provider.name}</strong> is available to view, but CareGist has not yet activated its provider identity and authority verification process.
        </p>
        <p className="mt-3 text-sm text-dusk">
          No claim, fast-track review, payment, or profile-control right is created from this page.
        </p>
        <a href={getProviderHref(provider)} className="mt-6 inline-block rounded-lg bg-clay px-6 py-3 font-medium text-white hover:bg-bark">
          View provider record
        </a>
      </div>
    </div>
  );
}
