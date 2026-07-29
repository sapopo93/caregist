import type { Metadata } from "next";
import Link from "next/link";

import LeadRequestForm from "@/components/directory/LeadRequestForm";
import { getDirectoryFilterOptions } from "@/lib/directory-db";
import { buildLeadListDefaults, buildLeadListExportHref } from "@/lib/lead-list-page";

export const metadata: Metadata = {
  title: "CQC Lead Lists | New Registrations & At-Risk Providers | CareGist",
  description:
    "Request CQC opportunity lead lists for newly registered providers, Inadequate services, Requires Improvement providers, and Not Yet Inspected services.",
};

const EXAMPLES = [
  "Newly registered homecare agencies in London",
  "Inadequate care homes for turnaround consulting outreach",
  "Care homes in the North West with Requires Improvement ratings",
  "Not Yet Inspected services for software, policy, equipment, or setup suppliers",
] as const;

const NEXT_STEPS = [
  {
    title: "Start with search",
    body:
      "Use the public directory to refine the segment you want before deciding whether a one-off lead list or a recurring plan is the right fit.",
    href: "/search?opportunity=new_90",
    cta: "Open opportunity lists",
  },
  {
    title: "Compare pricing",
    body:
      "If you need more than a one-off list, move into the subscription and dataset products that support recurring monitoring and larger exports.",
    href: "/pricing",
    cta: "See pricing",
  },
  {
    title: "Need workflow automation?",
    body:
      "If this segment needs to flow into CRM or internal operations, the API and webhook stack is the better long-term route than repeated CSV downloads.",
    href: "/api",
    cta: "Explore API",
  },
] as const;

export default async function LeadListPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const rawParams = await searchParams;
  const defaults = buildLeadListDefaults(rawParams);
  const options = await getDirectoryFilterOptions();
  const submitted = rawParams.submitted === "1";
  const token = typeof rawParams.token === "string" ? rawParams.token : "";
  const error = typeof rawParams.error === "string" ? rawParams.error : "";
  const exportHref = token ? buildLeadListExportHref(token, defaults) : "";
  const showExportDownload = submitted || Boolean(exportHref);

  return (
    <div className="bg-parchment px-6 py-14">
      <div className="mx-auto max-w-5xl">
        <section className="rounded-xl border border-stone bg-[linear-gradient(135deg,#2b2520_0%,#4f3b2d_55%,#6b4c35_100%)] px-6 py-8 text-cream shadow-xl sm:px-8 sm:py-10">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber">Lead lists</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-extrabold leading-tight md:text-5xl">
            Request the CQC opportunity list your sales team needs.
          </h1>
          <p className="mt-5 max-w-3xl text-base leading-7 text-stone">
            Choose a market movement signal: new registrations, Inadequate providers, Requires
            Improvement providers, Not Yet Inspected services, or a regional/service-type slice for CRM upload.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="#lead-request"
              className="rounded-full bg-amber px-5 py-3 text-sm font-semibold text-charcoal transition hover:bg-cream"
            >
              Build a lead request
            </a>
            <Link
              href="/pricing"
              className="rounded-full border border-cream/20 px-5 py-3 text-sm font-semibold text-cream transition hover:bg-white/10"
            >
              Compare plans
            </Link>
          </div>
        </section>

        <section className="mt-10 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            {showExportDownload ? (
              <div className="mb-6 rounded-xl border border-success/20 bg-success/10 p-5 text-sm text-bark">
                {submitted ? "Lead request created." : "Your filtered export is ready."}{" "}
                {exportHref ? (
                  <Link href={exportHref} className="font-semibold text-clay underline underline-offset-4">
                    Download this filtered CSV
                  </Link>
                ) : null}
              </div>
            ) : null}
            <LeadRequestForm options={options} defaults={defaults} error={error} />
          </div>

          <div className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">What to request</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">Examples of good lead-list briefs</h2>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-dusk">
              {EXAMPLES.map((example) => (
                <li key={example} className="rounded-xl border border-stone bg-parchment px-4 py-3">
                  {example}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Best fit</p>
            <h2 className="mt-3 text-3xl font-bold text-bark">When this product makes sense</h2>
            <p className="mt-4 text-sm leading-6 text-dusk">
              Choose a lead list when the job is immediate and scoped. If you need repeated monitoring,
              scheduled exports, or integrations, move up to the subscription or API products instead.
            </p>
          </div>
        </section>

        <section className="mt-10">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-clay">Next step options</p>
          <div className="mt-4 grid gap-6 md:grid-cols-3">
            {NEXT_STEPS.map((step) => (
              <div key={step.title} className="rounded-xl border border-stone bg-cream p-6 shadow-sm">
                <h3 className="text-2xl font-bold text-bark">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-dusk">{step.body}</p>
                <Link href={step.href} className="mt-5 inline-flex text-sm font-semibold text-clay hover:text-bark">
                  {step.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
