import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | CareGist",
  description: "Terms and conditions for using the CareGist care provider directory and API.",
};

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
      <p className="text-dusk text-sm mb-8">Last updated: 28 March 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. About CareGist</h2>
          <p>
            CareGist provides a directory of care providers registered with the Care Quality Commission (CQC)
            in England, accessible via website and API. CareGist is operated by [Your Company Name],
            registered in England and Wales (company number [XXXXXXXX]).
          </p>
          <p>
            By using CareGist, you agree to these terms. If you do not agree, do not use the service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. What CareGist is not</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>CareGist is <strong>not</strong> an official CQC service and is not affiliated with, endorsed by, or operated by the Care Quality Commission.</li>
            <li>CareGist does <strong>not</strong> provide care, inspect providers, or make recommendations about care providers.</li>
            <li>CareGist does <strong>not</strong> verify the accuracy of user-submitted reviews or provider claims beyond basic moderation.</li>
            <li>CareGist does <strong>not</strong> provide medical, legal, or financial advice.</li>
          </ul>
          <p className="mt-2">
            Always verify information directly with the care provider and check the latest CQC inspection report
            at <a href="https://www.cqc.org.uk" className="text-clay underline" target="_blank" rel="noopener noreferrer">cqc.org.uk</a> before
            making care decisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Accounts and API keys</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>You must provide accurate information when registering.</li>
            <li>You are responsible for keeping your API key confidential. Do not share it or embed it in client-side code.</li>
            <li>We may suspend or terminate accounts that violate these terms, abuse rate limits, or use the service for unlawful purposes.</li>
            <li>You may delete your account at any time by emailing <a href="mailto:support@caregist.co.uk" className="text-clay underline">support@caregist.co.uk</a>.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Acceptable use</h2>
          <p>You agree not to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Scrape, bulk-download, or systematically copy the entire database beyond the limits of your tier</li>
            <li>Redistribute CareGist data as a competing directory or data product without our written consent</li>
            <li>Use the service to harass, defame, or harm care providers, their staff, or residents</li>
            <li>Submit false reviews, fraudulent claims, or misleading enquiries</li>
            <li>Attempt to circumvent rate limits, authentication, or tier restrictions</li>
            <li>Use automated tools to create multiple free accounts to avoid paying</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Subscriptions and billing</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Paid plans are billed monthly via Stripe. Prices are in GBP and exclude VAT where applicable.</li>
            <li>You can upgrade, downgrade, or cancel at any time. Changes take effect at the next billing cycle.</li>
            <li>Cancellation reverts your account to the Free tier. No refunds are provided for partial months.</li>
            <li>We may change pricing with 30 days&apos; written notice. Existing subscriptions continue at the old price until renewal.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Data accuracy and liability</h2>
          <p>
            Care provider data is sourced from the CQC public API and refreshed regularly, but may not reflect
            the most recent inspections or changes. CQC ratings, registration status, and contact details can
            change at any time.
          </p>
          <p className="mt-2">
            <strong>CareGist is provided &quot;as is&quot; without warranty of any kind.</strong> To the maximum extent
            permitted by law, we exclude liability for:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Inaccurate, incomplete, or outdated provider data</li>
            <li>Decisions made based on information found on CareGist</li>
            <li>Loss of revenue, data, or business arising from use of the service</li>
            <li>Service downtime or API unavailability</li>
          </ul>
          <p className="mt-2">
            Nothing in these terms excludes liability for death or personal injury caused by our negligence,
            fraud, or any other liability that cannot be excluded by law.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Intellectual property</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>The CareGist brand, logo, website design, and software are our intellectual property.</li>
            <li>Care provider data is sourced from CQC and is subject to CQC&apos;s terms of use.</li>
            <li>User-submitted content (reviews, claims) remains your intellectual property, but you grant us a perpetual, non-exclusive licence to display, moderate, and use it on CareGist.</li>
            <li>API output may be used in your applications subject to your tier limits and these terms. You must include CQC attribution when displaying provider data.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Reviews and user content</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Reviews are moderated before publication. We reserve the right to reject or remove reviews that are defamatory, abusive, off-topic, or appear to be fake.</li>
            <li>We do not verify reviewer identity or their relationship to the care provider.</li>
            <li>Care providers may respond to reviews through their claimed listing.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Governing law</h2>
          <p>
            These terms are governed by the laws of England and Wales. Any disputes will be subject to the
            exclusive jurisdiction of the courts of England and Wales.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Contact</h2>
          <p>
            For questions about these terms, email <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>.
          </p>
        </section>

      </div>
    </div>
  );
}
