import type { Metadata } from "next";
import Link from "next/link";

import TerritoryScopePicker from "@/components/TerritoryScopePicker";
import { CQC_INDEPENDENCE_LINE } from "@/lib/caregist-config";
import { TERRITORY_BRIEF_PRICE_GBP } from "@/lib/territory-scope";

export const metadata: Metadata = {
  title: "Confirm your territory | CareGist Territory Opportunity Brief",
  description:
    "Choose a region and buyer type, confirm the published CQC record supports it, then buy the Territory Opportunity Brief.",
};

export default function TerritoryScopePage() {
  const checkoutEnabled = process.env.TERRITORY_SELF_SERVE_CHECKOUT_ENABLED === "true";

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-clay">
        Territory Opportunity Brief · £{TERRITORY_BRIEF_PRICE_GBP}
      </p>
      <h1 className="mb-4 text-3xl font-bold text-bark">Confirm your territory, then buy</h1>
      <p className="mb-8 text-base leading-7 text-dusk" style={{ fontFamily: "Lora" }}>
        The brief is a buyer-specific shortlist of 25–50 care organisations with a
        stated reason for each, a CRM-ready dataset, and a 3–5 page brief on the
        territory. Instead of a scoping call, confirm the scope here: the system
        checks the published CQC record for your exact region and buyer type
        before you pay.
      </p>

      <TerritoryScopePicker checkoutEnabled={checkoutEnabled} />

      <section className="mt-10 rounded-xl border border-stone bg-parchment p-6">
        <h2 className="mb-2 text-lg font-bold text-bark">How the scope check works</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm leading-6 text-dusk">
          <li>You choose the region and the organisations you sell to.</li>
          <li>
            The system counts the matching organisations in CQC&apos;s published
            record and reports the most recent observation date.
          </li>
          <li>
            If the record supports the scope, you continue to payment. The pack is
            built from that same published record.
          </li>
        </ol>
        <p className="mt-4 text-xs text-dusk">
          Prefer to talk it through first?{" "}
          <Link href="/pricing" className="text-clay underline">
            See all products
          </Link>{" "}
          or email{" "}
          <a href="mailto:outreach@caregist.co.uk" className="text-clay underline">
            outreach@caregist.co.uk
          </a>
          .
        </p>
      </section>

      <footer className="mt-8 text-center text-xs text-dusk">
        <p>
          CQC information is reused under the Open Government Licence v3.0.{" "}
          {CQC_INDEPENDENCE_LINE}
        </p>
      </footer>
    </main>
  );
}
