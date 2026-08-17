import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Provider Claims Unavailable | CareGist",
  description: "CareGist provider claims are not currently available.",
  robots: { index: false, follow: true },
};

export default async function ClaimUnavailablePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const providerName = slug.replace(/-/g, " ");

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-clay">Fail closed</p>
      <h1 className="mt-3 text-4xl font-extrabold text-bark">Provider claims are unavailable</h1>
      <p className="mt-5 max-w-2xl text-base leading-7 text-dusk">
        CareGist is not accepting or verifying provider profile claims. No ownership or
        authority can be established through this page.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href={`/search?q=${encodeURIComponent(providerName)}`}
          className="rounded-lg bg-clay px-5 py-3 text-sm font-semibold text-white hover:bg-bark"
        >
          Find the provider in CareGist
        </Link>
        <a
          href="https://www.cqc.org.uk/care-services/find-care-service"
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-lg border border-clay px-5 py-3 text-sm font-semibold text-clay hover:bg-cream"
        >
          Search the official CQC directory
        </a>
      </div>
    </main>
  );
}
