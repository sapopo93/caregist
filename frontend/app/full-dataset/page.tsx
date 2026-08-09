import type { Metadata } from "next";

import FullDatasetCheckout from "@/components/FullDatasetCheckout";
import { CQC_SOURCE_ATTRIBUTION } from "@/lib/directory-export";

export const metadata: Metadata = {
  title: "Full CQC Dataset | CareGist",
  description: "Buy a current, CRM-ready export of active CQC care locations in England.",
};

export default async function FullDatasetPage({
  searchParams,
}: {
  searchParams: Promise<{ session_id?: string; cancelled?: string }>;
}) {
  const query = await searchParams;
  const enabled = process.env.FULL_DATASET_CHECKOUT_ENABLED === "true";

  return (
    <main className="mx-auto max-w-5xl px-6 py-16">
      {query.session_id && (
        <div className="mb-8 rounded-lg border border-moss/40 bg-moss/10 p-4 text-bark" role="status">
          Payment received. Your private download link is being sent to the email used at checkout.
        </div>
      )}
      {query.cancelled && (
        <div className="mb-8 rounded-lg border border-stone bg-parchment p-4 text-bark" role="status">
          Checkout was cancelled. No payment was taken.
        </div>
      )}
      <div className="grid gap-10 md:grid-cols-[1fr_24rem] md:items-start">
        <section>
          <p className="font-mono text-xs uppercase tracking-widest text-clay">One-time dataset pack</p>
          <h1 className="mt-3 text-4xl font-extrabold text-bark">The full active CQC location dataset</h1>
          <p className="mt-5 text-lg leading-8 text-dusk" style={{ fontFamily: "Lora" }}>
            A current CSV for research, territory planning, recruitment, supplier prospecting, and CRM import—without manually copying thousands of directory records.
          </p>
          <ul className="mt-7 space-y-3 text-charcoal">
            <li>✓ Every active location in the current CareGist snapshot</li>
            <li>✓ Stable CQC location ID and parent provider ID for matching and deduplication</li>
            <li>✓ Contact, address, service, specialism, rating, and inspection fields</li>
            <li>✓ Immutable checksum and source watermark tied to your purchase</li>
            <li>✓ Private link delivered automatically after confirmed Stripe payment</li>
          </ul>
          <p className="mt-8 text-xs leading-5 text-dusk">
            {CQC_SOURCE_ATTRIBUTION}. CareGist is independent of and not endorsed by the CQC.
          </p>
        </section>
        <aside>
          <div className="mb-4">
            <span className="text-4xl font-extrabold text-bark">£199</span>
            <span className="ml-2 text-sm text-dusk">one-off</span>
          </div>
          <FullDatasetCheckout enabled={enabled} />
        </aside>
      </div>
    </main>
  );
}
