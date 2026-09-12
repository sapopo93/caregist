import type { Metadata } from "next";
import Link from "next/link";

import TerritoryScopePicker from "@/components/TerritoryScopePicker";
import { CQC_INDEPENDENCE_LINE } from "@/lib/caregist-config";
import { TERRITORY_BRIEF_PRICE_GBP } from "@/lib/territory-scope";

export const metadata: Metadata = {
  title: "Confirm your territory | CareGist Territory Opportunity Brief",
  description:
    "Check coverage for your territory and review the next steps for a Territory Opportunity Brief.",
};

export default function TerritoryScopePage() {

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <Link href="/pricing" className="mb-6 inline-block text-sm text-clay underline">← Back to pricing</Link>
      <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-clay">
        Territory Opportunity Brief · £{TERRITORY_BRIEF_PRICE_GBP}
      </p>
      <h1 className="mb-4 text-3xl font-bold text-bark">Check coverage for your territory</h1>
      <p className="mb-8 text-base leading-7 text-dusk" style={{ fontFamily: "Lora" }}>
        £{TERRITORY_BRIEF_PRICE_GBP} for a one-off Territory Opportunity Brief.
        The intended pack includes a shortlist of 25–50 care organisations,
        a CRM-ready dataset and a 3–5 page territory brief. Start by checking
        how many organisations match your selections.
      </p>

      <aside className="mb-8 rounded-lg border border-stone bg-parchment p-4 text-sm leading-6 text-bark">
        <strong>Online ordering is not available.</strong> You can check coverage
        and email your scope for review. Coverage counts do not confirm pack
        availability or delivery. No payment is taken on this page.
      </aside>
      <TerritoryScopePicker />

      <section className="mt-10 rounded-xl border border-stone bg-parchment p-6">
        <h2 className="mb-2 text-lg font-bold text-bark">3. What happens next</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm leading-6 text-dusk">
          <li>Review the matching count and the date shown above. A smaller count means a shorter potential shortlist.</li>
          <li>Email your selections if you want us to review availability. You must send the email from your email app.</li>
          <li>Before any payment, the scope, final price and delivery arrangements must be confirmed. This page does not create an order.</li>
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
