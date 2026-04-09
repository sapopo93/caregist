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
            in England, accessible via website and API. CareGist is operated by H-Kay Limited,
            registered in England and Wales (company number 10417923).
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
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Eligibility</h2>
          <p>
            You must be at least 18 years old to create an account and use CareGist. By registering,
            you confirm that you meet this age requirement. If you are using CareGist on behalf of an
            organisation, you confirm that you have authority to bind that organisation to these terms.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Accounts and API keys</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>You must provide accurate information when registering.</li>
            <li>You are responsible for keeping your API key confidential. Do not share it or embed it in client-side code.</li>
            <li>Free and Starter are single-user tiers. Pro includes 3 named users, Business includes 10, and larger arrangements run through Enterprise.</li>
            <li>You may delete your account at any time by emailing <a href="mailto:support@caregist.co.uk" className="text-clay underline">support@caregist.co.uk</a>.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Acceptable use</h2>
          <p>
            You agree to comply with our <a href="/acceptable-use" className="text-clay underline">Acceptable Use Policy</a>,
            which forms part of these terms. In summary, you agree not to:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Scrape, bulk-download, or systematically copy the database beyond the limits of your tier</li>
            <li>Redistribute CareGist data as a competing directory or data product without our written consent</li>
            <li>Use the service to harass, defame, or harm care providers, their staff, or residents</li>
            <li>Submit false reviews, fraudulent claims, or misleading enquiries</li>
            <li>Attempt to circumvent rate limits, authentication, or tier restrictions</li>
            <li>Use automated tools to create multiple free accounts to avoid paying</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Subscriptions and billing</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Paid plans are billed monthly via Stripe. Prices are in GBP and exclude VAT where applicable.</li>
            <li>You can upgrade, downgrade, or cancel at any time. Subscription changes are processed through Stripe and reflected in your CareGist entitlements.</li>
            <li>Cancellation reverts your account to the Free tier. No refunds are provided for partial months.</li>
            <li>We may change pricing with 30 days&apos; written notice. Existing subscriptions continue at the old price until renewal.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Service availability</h2>
          <p>
            We aim to keep CareGist available at all times but do not guarantee uninterrupted service.
            The service may be unavailable due to scheduled maintenance, technical issues, or factors
            outside our control. We will endeavour to provide advance notice of planned maintenance
            where practicable.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. No warranty</h2>
          <p>
            CareGist is provided on an &quot;as is&quot; and &quot;as available&quot; basis. We make no warranties,
            express or implied, including but not limited to accuracy, completeness, fitness for a
            particular purpose, and non-infringement.
          </p>
          <p className="mt-2">
            Care provider data is sourced from the CQC public API and refreshed regularly, but may not reflect
            the most recent inspections or changes. CQC ratings, registration status, and contact details can
            change at any time.
          </p>
          <p className="mt-2">
            To the maximum extent permitted by law, we exclude liability for:
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
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Intellectual property</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>The CareGist brand, logo, website design, and software are our intellectual property.</li>
            <li>Care provider data is sourced from CQC and is subject to CQC&apos;s terms of use.</li>
            <li>User-submitted content (reviews, claims) remains your intellectual property, but you grant us a perpetual, non-exclusive licence to display, moderate, and use it on CareGist.</li>
            <li>API output may be used in your applications subject to your tier limits and these terms. You must include CQC attribution when displaying provider data.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Data usage restrictions</h2>
          <p>
            You may use CareGist data in your internal business operations or applications, but you may not:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Resell, sublicense, or redistribute CareGist data as a standalone dataset</li>
            <li>Create a competing directory, database, or data service using CareGist data</li>
            <li>Republish large portions of the CareGist database</li>
            <li>Cache or store bulk data beyond reasonable operational use</li>
            <li>Remove or obscure CQC attribution when displaying provider data</li>
          </ul>
          <p className="mt-2">
            We reserve the right to monitor API usage and may throttle, suspend, or terminate accounts
            that use excessive bandwidth, attempt to download large portions of the database, or
            otherwise use the API in a way that harms the service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Reviews and user content</h2>
          <p>
            Users are solely responsible for the content they submit, including reviews and enquiries.
            CareGist does not endorse user content and is not responsible for its accuracy.
          </p>
          <ul className="list-disc pl-6 space-y-1 mt-2">
            <li>Reviews are moderated before publication according to our <a href="/review-policy" className="text-clay underline">Review Policy</a>.</li>
            <li>We reserve the right to reject or remove reviews that are defamatory, abusive, off-topic, or appear to be fake.</li>
            <li>We do not verify reviewer identity or their relationship to the care provider.</li>
            <li>Care providers may respond to reviews through their claimed listing.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">12. Termination</h2>
          <p>
            We may suspend or terminate your account and access to CareGist at any time if you violate
            these terms, misuse the service, attempt to circumvent pricing or rate limits, or use the
            service in a way that could harm CareGist, care providers, or other users.
          </p>
          <p className="mt-2">
            We may also discontinue the service at any time. Where possible, we will provide 30 days&apos;
            notice to paid subscribers. On termination:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Your API key will be deactivated immediately</li>
            <li>Active subscriptions will be cancelled (pro-rata refund at our discretion for service discontinuation only)</li>
            <li>Your account data will be retained for 30 days, then deleted</li>
            <li>Published reviews will remain unless you request removal</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">13. Indemnity</h2>
          <p>
            You agree to indemnify and hold harmless H-Kay Limited, its directors, officers, and employees
            from any claims, damages, losses, liabilities, and expenses (including reasonable legal fees)
            arising from:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Your use of CareGist</li>
            <li>Your use of CareGist data in your own applications</li>
            <li>Reviews, content, or enquiries you submit</li>
            <li>Your breach of these terms</li>
            <li>Any third-party claim arising from your use of the service</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">14. Force majeure</h2>
          <p>
            We are not liable for any failure or delay in performance caused by events outside our
            reasonable control, including but not limited to: internet outages, cloud provider failures,
            CQC API unavailability, strikes, fire, flood, pandemic, government action, or regulatory changes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">15. Changes to these terms</h2>
          <p>
            We may update these terms from time to time. If we make material changes, we will notify
            registered users by email or through a prominent notice on the website at least 14 days
            before the changes take effect. Continued use of CareGist after the changes take effect
            constitutes acceptance of the updated terms. If you do not agree to the changes, you
            should stop using the service and cancel your subscription.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">16. Governing law</h2>
          <p>
            These terms are governed by the laws of England and Wales. Any disputes will be subject to the
            exclusive jurisdiction of the courts of England and Wales.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">17. Contact</h2>
          <p>
            For questions about these terms, email <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>.
          </p>
        </section>

      </div>
    </div>
  );
}
