import Link from "next/link";

/** Every answer restates something the site already says elsewhere (pricing, territory, Data Status, terms). */
const FAQ: Array<{ q: string; a: React.ReactNode }> = [
  {
    q: "Is the Brief a list of leads?",
    a: "No. It is a shortlist of organisations to investigate, each with a published fact, the reason it was included and the source evidence. Public CQC records do not establish vacancies, budgets, buying intent or a guaranteed commercial outcome.",
  },
  {
    q: "Can I pay online?",
    a: "No. Online ordering is not available, and neither route places an order or takes payment by itself. CareGist confirms scope and delivery dates in writing before any payment is requested.",
  },
  {
    q: "Is it a subscription?",
    a: "No. Both products are one-off purchases with no subscription and no automatic renewal.",
  },
  {
    q: "Is VAT added?",
    a: "CareGist is not currently VAT registered, so VAT is not currently charged.",
  },
  {
    q: "What is the difference between a location and a provider?",
    a: "The coverage check counts matching locations, and one provider can run several. The exact number of distinct provider organisations in the Brief is confirmed in writing before you pay.",
  },
  {
    q: "How current is the data?",
    a: (
      <>
        Every figure carries source and observation dates, and{" "}
        <Link href="/data-status" className="font-semibold text-clay underline underline-offset-4">Data Status</Link>{" "}
        shows when CQC published, when we retrieved and when we reconciled the source. CQC controls publication and can delay or correct it.
      </>
    ),
  },
  {
    q: "Is CareGist part of CQC?",
    a: "No. CareGist is independent of the Care Quality Commission and does not represent or endorse it. CQC information is reused under the Open Government Licence v3.0.",
  },
];

export default function PricingFaq() {
  return (
    <section aria-label="Questions buyers ask" className="mt-10">
      <h2 className="text-2xl font-bold text-bark">Questions buyers ask</h2>
      <div className="mt-4 divide-y divide-stone overflow-hidden rounded-xl border border-stone bg-cream">
        {FAQ.map((item) => (
          <details key={item.q} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-bark [&::-webkit-details-marker]:hidden">
              {item.q}
              <span aria-hidden className="text-xl leading-none text-clay transition group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-dusk">{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
