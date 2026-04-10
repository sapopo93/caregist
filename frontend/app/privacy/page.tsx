import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | CareGist",
  description: "How CareGist collects, uses, and protects your personal data under UK GDPR and the Data Protection Act 2018.",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-dusk text-sm mb-8">Last updated: 28 March 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Who we are</h2>
          <p>
            CareGist is a trading name of H-Kay Limited, registered in England and Wales
            (company number 10417923), with registered address at C/O Bilberry Accountants Ltd,
            Castle Court, 41 London Road, Reigate, England, RH2 9RJ.
          </p>
          <p>
            We are the data controller for the personal data described in this policy.
            You can contact us at <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>.
          </p>
          <p>
            H-Kay Limited is not required to appoint a Data Protection Officer (DPO) under
            Article 37 of the UK GDPR as our core activities do not involve large-scale processing
            of special category data or systematic monitoring of individuals.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. What data we collect</h2>
          <p>We collect and process the following personal data:</p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">2.1 Data you give us</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Account registration:</strong> name, email address, and password. Passwords are hashed using industry-standard salted hashing algorithms. We never store passwords in plain text.</li>
            <li><strong>Billing:</strong> processed by Stripe. We do not store card numbers, expiry dates, or CVV codes. Stripe&apos;s privacy policy applies to payment data.</li>
            <li><strong>Enquiry forms:</strong> name, email, phone number, message content, and care requirements you submit when contacting a care provider through our platform</li>
            <li><strong>Reviews:</strong> name, email, review text, star rating, and relationship to the care provider. Reviews you submit may be published publicly on our website together with the name you provide and your relationship to the care provider.</li>
            <li><strong>Provider claims:</strong> name, email, phone, role, and proof of association with the care provider</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">2.2 Data we collect automatically</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>API usage:</strong> API key, request timestamps, endpoints called, rate limit counters</li>
            <li><strong>Server logs:</strong> IP address, user agent, request path, response status code. These are collected for security monitoring and abuse prevention.</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">2.3 Care provider data</h3>
          <p>
            Our directory contains information about care providers sourced from the Care Quality Commission (CQC)
            public API. This includes provider names, addresses, phone numbers, CQC ratings, inspection dates,
            and service types. This data is published by CQC as a public authority under its statutory functions
            and is not personal data in most cases. Where it includes personal data (e.g., registered manager names
            in CQC reports), the lawful basis for our processing is legitimate interest (Article 6(1)(f) UK GDPR).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. How we use your data</h2>
          <table className="w-full text-sm border border-stone">
            <thead>
              <tr className="bg-parchment">
                <th className="text-left p-2 border-b border-stone">Purpose</th>
                <th className="text-left p-2 border-b border-stone">Lawful basis (UK GDPR)</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-2 border-b border-stone">Provide your account and API access</td><td className="p-2 border-b border-stone">Contract (Art. 6(1)(b))</td></tr>
              <tr><td className="p-2 border-b border-stone">Process payments via Stripe</td><td className="p-2 border-b border-stone">Contract (Art. 6(1)(b))</td></tr>
              <tr><td className="p-2 border-b border-stone">Send enquiries to care providers on your behalf</td><td className="p-2 border-b border-stone">Consent (Art. 6(1)(a)) — you choose to submit the form</td></tr>
              <tr><td className="p-2 border-b border-stone">Publish reviews you submit</td><td className="p-2 border-b border-stone">Consent (Art. 6(1)(a)) — reviews are published publicly with your name</td></tr>
              <tr><td className="p-2 border-b border-stone">Process provider claims</td><td className="p-2 border-b border-stone">Legitimate interest (Art. 6(1)(f)) — verifying provider identity</td></tr>
              <tr><td className="p-2 border-b border-stone">Monitor API usage and enforce rate limits</td><td className="p-2 border-b border-stone">Legitimate interest (Art. 6(1)(f)) — service security</td></tr>
              <tr><td className="p-2 border-b border-stone">Server logs, IP address logging, and security monitoring</td><td className="p-2 border-b border-stone">Legitimate interest (Art. 6(1)(f)) — preventing abuse and securing the service</td></tr>
              <tr><td className="p-2 border-b border-stone">Publish care provider directory data from CQC</td><td className="p-2 border-b border-stone">Legitimate interest (Art. 6(1)(f)) — public transparency</td></tr>
              <tr><td className="p-2 border-b border-stone">Comply with legal obligations</td><td className="p-2 border-b border-stone">Legal obligation (Art. 6(1)(c))</td></tr>
            </tbody>
          </table>
          <p className="mt-3 text-sm">
            Where we rely on legitimate interest as our lawful basis, we have carried out a Legitimate Interest
            Assessment (LIA) to ensure our processing is necessary and that your rights and interests do not
            override our legitimate interests. You may request a copy of our LIA by emailing{" "}
            <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Who we share data with</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.1 Data processors</h3>
          <table className="w-full text-sm border border-stone">
            <thead>
              <tr className="bg-parchment">
                <th className="text-left p-2 border-b border-stone">Processor</th>
                <th className="text-left p-2 border-b border-stone">Purpose</th>
                <th className="text-left p-2 border-b border-stone">Location</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-2 border-b border-stone">Stripe Inc.</td><td className="p-2 border-b border-stone">Payment processing</td><td className="p-2 border-b border-stone">US (SCCs in place)</td></tr>
              <tr><td className="p-2 border-b border-stone">Amazon Web Services</td><td className="p-2 border-b border-stone">Application and database infrastructure hosting</td><td className="p-2 border-b border-stone">UK/EU</td></tr>
              <tr><td className="p-2 border-b border-stone">Postcodes.io (ONS)</td><td className="p-2 border-b border-stone">Postcode geocoding (no personal data sent)</td><td className="p-2 border-b border-stone">UK</td></tr>
            </tbody>
          </table>
          <p className="mt-2">These providers act as data processors and process data on our behalf under data processing agreements.</p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.2 Other sharing</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Care providers</strong> — when you submit an enquiry form, we share your name, email, phone, and message with the care provider you are enquiring about. You consent to this sharing when you submit the form.</li>
          </ul>
          <p className="mt-2">We do not sell your personal data to third parties. We do not use your data for advertising or profiling.</p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. International transfers</h2>
          <p>
            Some of our data processors, including Stripe, may process data in the United States.
            These transfers are protected by Standard Contractual Clauses (SCCs) approved by the UK
            Information Commissioner&apos;s Office (ICO), or by the processor&apos;s participation in
            recognised data transfer frameworks.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. How long we keep data</h2>
          <table className="w-full text-sm border border-stone">
            <thead>
              <tr className="bg-parchment">
                <th className="text-left p-2 border-b border-stone">Data type</th>
                <th className="text-left p-2 border-b border-stone">Retention period</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-2 border-b border-stone">Account data</td><td className="p-2 border-b border-stone">Until you delete your account, then 30 days</td></tr>
              <tr><td className="p-2 border-b border-stone">API usage logs</td><td className="p-2 border-b border-stone">90 days</td></tr>
              <tr><td className="p-2 border-b border-stone">Server logs (IP addresses)</td><td className="p-2 border-b border-stone">90 days</td></tr>
              <tr><td className="p-2 border-b border-stone">Enquiry form data</td><td className="p-2 border-b border-stone">12 months, then anonymised</td></tr>
              <tr><td className="p-2 border-b border-stone">Reviews</td><td className="p-2 border-b border-stone">Published indefinitely; deleted on request</td></tr>
              <tr><td className="p-2 border-b border-stone">Provider claims</td><td className="p-2 border-b border-stone">Duration of the claim, then 12 months</td></tr>
              <tr><td className="p-2 border-b border-stone">Billing records</td><td className="p-2 border-b border-stone">7 years (HMRC requirement)</td></tr>
              <tr><td className="p-2 border-b border-stone">Care provider directory data</td><td className="p-2 border-b border-stone">Refreshed weekly from CQC; superseded data deleted</td></tr>
            </tbody>
          </table>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Your rights</h2>
          <p>Under the UK GDPR and the Data Protection Act 2018, you have the right to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Access</strong> — request a copy of the personal data we hold about you</li>
            <li><strong>Rectification</strong> — ask us to correct inaccurate data</li>
            <li><strong>Erasure</strong> — ask us to delete your data (&quot;right to be forgotten&quot;)</li>
            <li><strong>Restrict processing</strong> — ask us to limit how we use your data</li>
            <li><strong>Data portability</strong> — receive your data in a machine-readable format</li>
            <li><strong>Object</strong> — object to processing based on legitimate interest</li>
            <li><strong>Withdraw consent</strong> — where processing is based on consent, you can withdraw at any time</li>
          </ul>
          <p className="mt-2">
            To exercise any of these rights, email <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>.
            We will respond within 30 days (one calendar month) as required by law.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Security</h2>
          <p>We protect your data with:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Passwords hashed using industry-standard salted hashing algorithms (never stored in plain text)</li>
            <li>API keys generated using cryptographically secure random tokens</li>
            <li>HTTPS encryption for all data in transit</li>
            <li>PostgreSQL database with access restricted to application services only</li>
            <li>Payment data handled entirely by Stripe (PCI DSS Level 1 certified)</li>
            <li>Environment variables for all secrets (never committed to source code)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Cookies</h2>
          <p>
            CareGist does not use tracking cookies, advertising cookies, or third-party analytics cookies.
            We may use essential cookies strictly necessary for the functioning of the website (e.g., session
            management). These do not require consent under the Privacy and Electronic Communications
            Regulations 2003 (PECR).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Automated decision-making</h2>
          <p>
            CareGist does not make automated decisions that produce legal or similarly significant effects
            on individuals. Any scoring or ranking of care providers (such as our data completeness tiers)
            is informational only and does not constitute an assessment of care quality.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Children</h2>
          <p>
            CareGist is not directed at children under 18. We do not knowingly collect personal data from
            children. If you believe we have collected data from a child, please contact us and we will
            delete it promptly.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">12. Our role</h2>
          <p>
            CareGist provides a directory and data platform about care providers. We do not provide care
            services, medical advice, or healthcare services. We are not responsible for the care provided
            by any listed provider. Always verify information directly with the care provider and check the
            latest CQC inspection report at{" "}
            <a href="https://www.cqc.org.uk" className="text-clay underline" target="_blank" rel="noopener noreferrer">cqc.org.uk</a>{" "}
            before making care decisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">13. Changes to this policy</h2>
          <p>
            We may update this privacy policy from time to time. Material changes will be notified by email
            to registered users. The &quot;last updated&quot; date at the top of this page indicates when it was
            last revised.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">14. Complaints</h2>
          <p>
            If you are unhappy with how we handle your data, you have the right to lodge a complaint with
            the Information Commissioner&apos;s Office (ICO):
          </p>
          <ul className="list-disc pl-6 space-y-1 mt-2">
            <li>Website: <a href="https://ico.org.uk/make-a-complaint/" className="text-clay underline" target="_blank" rel="noopener noreferrer">ico.org.uk/make-a-complaint</a></li>
            <li>Phone: 0303 123 1113</li>
            <li>Post: Information Commissioner&apos;s Office, Wycliffe House, Water Lane, Wilmslow, Cheshire, SK9 5AF</li>
          </ul>
        </section>

      </div>
    </div>
  );
}
