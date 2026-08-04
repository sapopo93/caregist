import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Business Terms | CareGist",
  description: "Draft business terms for CareGist, operated by H-Kay Limited.",
};

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Business Terms</h1>
      <p className="text-dusk text-sm mb-3">Draft version 1.1 &middot; Updated 2 August 2026</p>
      <div className="rounded-xl border border-stone bg-mist p-4 text-sm text-charcoal mb-8">
        These terms are awaiting solicitor approval. Paid self-service checkout is unavailable and
        this draft is not presented as an operative paid contract.
      </div>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Who we are</h2>
          <p>
            CareGist is operated by <strong>H-Kay Limited</strong>, a company registered in England
            and Wales under company number <strong>10417923</strong>, whose registered office is
            C/O Bilberry Accountants Ltd, Castle Court, 41 London Road, Reigate, England, RH2 9RJ
            (&quot;we&quot;, &quot;us&quot;, &quot;CareGist&quot;). These terms form the contract
            between us and the business or organisation subscribing (&quot;you&quot;).
          </p>
          <p>
            Paid plans are offered only for business use. Consumer self-service purchasing is not
            supported. Before any paid Checkout Session can be created, an authenticated user must
            separately confirm that they are acting for a business and are authorised to bind it to
            the exact approved version of these terms.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. What the service is</h2>
          <p>
            CareGist provides search, monitoring, alerting, export and API access over information
            about CQC-registered health and social care services in England, together with our own
            presentation, structuring and enrichment of that information.
          </p>
          <p>
            We are <strong>not</strong> the Care Quality Commission. We are not affiliated with,
            endorsed by, or acting for CQC. We do not provide care, and nothing we publish is
            professional, legal, medical or financial advice. Source information may be incomplete,
            superseded or inaccurate. Verify anything material directly with the provider and the
            current CQC record before relying on it.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Accounts and API keys</h2>
          <p>
            You are responsible for the accuracy of your account details, for keeping credentials
            and API keys confidential, and for all activity under them. Tell us promptly at
            security@caregist.co.uk if you believe a key is compromised, and we will rotate it.
          </p>
          <p>
            API keys are issued per seat. Your plan sets the number of seats; keys created beyond
            that allowance will not authenticate until you add seats or upgrade.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Plans, fees and VAT</h2>
          <p>
            Paid plans are Alerts Pro (&pound;49/month), Data Starter (&pound;99/month), Data Pro
            (&pound;199/month), Data Business (&pound;499/month) and Enterprise (priced by
            agreement). H-Kay Limited is not currently VAT registered, so the displayed prices are
            the total customer prices and no VAT is charged. If that status changes, CareGist will
            update its pricing and invoice treatment from the applicable effective date and give
            existing subscribers any notice required by these terms.
          </p>
          <p>
            Each plan carries limits on request rate, daily and monthly volume, result fields,
            exports, monitors, saved filters and seats. Current limits are shown on the pricing
            page and are enforced by the service. Exceeding a limit results in throttling or a
            refused request, not an automatic charge.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Payment, renewal and cancellation</h2>
          <p>
            Subscriptions are billed monthly in advance by card through Stripe, our payment
            processor. We do not receive or store your full card details. Your subscription renews
            automatically each month until cancelled.
          </p>
          <p>
            You may cancel at any time from your account or by emailing billing@caregist.co.uk.
            Cancellation takes effect at the end of the paid period; access continues until then
            and the subscription does not renew. We do not pro-rate part-months.
          </p>
          <p>
            We may change prices or plan limits on 30 days&apos; notice by email. If a change is to
            your material disadvantage you may cancel before it takes effect and we will refund any
            period paid for and not used.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Acceptable use</h2>
          <p>
            You may use the service for your own business purposes, including internal analysis and
            client work. You may not resell, redistribute or republish bulk extracts as a competing
            directory or dataset; circumvent rate limits, seat limits or field restrictions; scrape
            outside the documented API; or use the service to send unlawful marketing.
          </p>
          <p>
            Our <a href="/acceptable-use" className="underline">Acceptable Use Policy</a> forms part
            of these terms.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Source rights and intellectual property</h2>
          <p>
            CQC source information is made available under the Open Government Licence v3.0. This
            service contains public sector information licensed under the Open Government Licence
            v3.0. The OGL expressly excludes personal data, and nothing in these terms narrows
            rights the OGL grants you directly.
          </p>
          <p>
            Our software, interfaces, original presentation, structuring and enrichment remain our
            property. We grant you a non-exclusive, non-transferable right to use them for the term
            of your subscription.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Data protection</h2>
          <p>
            H-Kay Limited is the controller for personal data we process about you and your users.
            How we handle it is set out in our <a href="/privacy" className="underline">Privacy
            Notice</a>. Where you use the service to process personal data for your own purposes,
            you are the controller for that processing and are responsible for your own lawful
            basis and transparency obligations.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Availability and support</h2>
          <p>
            We aim to keep the service available and current, but we do not guarantee uninterrupted
            availability, and we may suspend access for maintenance, security or provider incidents.
            Data freshness depends on CQC publication, which we do not control. Support is by email
            at hello@caregist.co.uk during UK business hours. We do not offer a contractual uptime
            service level unless one is agreed in writing on an Enterprise plan.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Liability</h2>
          <p>
            Nothing in these terms limits liability for death or personal injury caused by
            negligence, for fraud, or for anything else that cannot lawfully be limited.
          </p>
          <p>
            Subject to that, we are not liable for loss of profit, revenue, contracts, goodwill,
            anticipated savings, or for indirect or consequential loss; and our total liability
            arising from the service in any 12-month period is limited to the fees you paid in that
            period. We provide the service &quot;as is&quot; to the fullest extent the law allows,
            and give no warranty that source information is accurate, current or complete.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Suspension and termination</h2>
          <p>
            We may suspend or terminate access if you materially breach these terms or the
            Acceptable Use Policy, if payment fails and is not resolved within 14 days of notice, or
            if we are required to by law. Where practical we will give notice and an opportunity to
            fix the problem first. On termination your right to use the service ends; provisions on
            intellectual property, liability and governing law survive.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">12. Complaints, law and jurisdiction</h2>
          <p>
            Please raise any complaint with hello@caregist.co.uk and we will respond within 14 days.
            These business terms are governed by the law of England and Wales. Any jurisdiction
            clause in the operative version remains subject to solicitor approval.
          </p>
          <p>
            You can contact us at H-Kay Limited, C/O Bilberry Accountants Ltd, Castle Court, 41
            London Road, Reigate, England, RH2 9RJ, or by email at legal@caregist.co.uk.
          </p>
        </section>
      </div>
    </div>
  );
}
