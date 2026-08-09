import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | CareGist",
  description: "How CareGist collects, uses, and safeguards your personal data. UK GDPR and Data Protection Act 2018 compliant.",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-dusk text-sm mb-6">Last updated: 8 August 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Who We Are</h2>
          <p>
            CareGist is a trading name of Henry Mlalazi, a sole trader operating in England and Wales.
            For the purposes of UK data protection law, we are the <strong>data controller</strong> of
            personal data processed through the Service.
          </p>
          <p>
            <strong>Contact:</strong>{" "}
            <a href="mailto:henry.mlalazi@gmail.com" className="text-clay underline">
              henry.mlalazi@gmail.com
            </a>
            <br />
            <strong>ICO registration:</strong> pending (Tier 1, micro organisation)
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Information We Collect</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">2.1 Information You Provide</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Account data:</strong> Name, email address, and password when you create an account</li>
            <li><strong>Lead purchase data:</strong> Payment information (processed by Stripe; we do not store full card details), transaction records</li>
            <li><strong>Lead enquiries:</strong> When you submit a lead enquiry form, we collect your name, contact details, and enquiry message</li>
            <li><strong>Lead-list requests:</strong> Email address and the directory segment you request</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">2.2 Information Collected Automatically</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Usage data:</strong> Pages visited, search queries, features used (anonymised where possible)</li>
            <li><strong>Technical data:</strong> IP address, browser type, device information, referring URL</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">2.3 Information From Third Parties</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>
              <strong>CQC public data:</strong> Provider names, addresses, phone numbers, CQC ratings,
              and service types — obtained from the Care Quality Commission under the Open Government
              Licence v3.0. This is organisational data, not personal data.
            </li>
            <li><strong>Stripe:</strong> Transaction confirmation and payment status</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. How We Use Your Information</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-stone">
              <thead>
                <tr className="bg-parchment">
                  <th className="text-left p-2 border-b border-stone">Purpose</th>
                  <th className="text-left p-2 border-b border-stone">Data used</th>
                  <th className="text-left p-2 border-b border-stone">Lawful basis</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 border-b border-stone">Provide and maintain the Service</td>
                  <td className="p-2 border-b border-stone">Account data, usage data</td>
                  <td className="p-2 border-b border-stone">Contract (necessary for service)</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Process payments and deliver leads</td>
                  <td className="p-2 border-b border-stone">Payment data, account data</td>
                  <td className="p-2 border-b border-stone">Contract + legal obligation (financial records)</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Respond to enquiries and support</td>
                  <td className="p-2 border-b border-stone">Contact data, enquiry content</td>
                  <td className="p-2 border-b border-stone">Legitimate interest</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Improve and analyse the Service</td>
                  <td className="p-2 border-b border-stone">Anonymised usage data</td>
                  <td className="p-2 border-b border-stone">Legitimate interest</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Communicate service updates</td>
                  <td className="p-2 border-b border-stone">Email address</td>
                  <td className="p-2 border-b border-stone">Legitimate interest (existing customers)</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Comply with legal obligations</td>
                  <td className="p-2 border-b border-stone">All relevant data</td>
                  <td className="p-2 border-b border-stone">Legal obligation</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2">
            We do <strong>not</strong> use personal data for automated decision-making or profiling.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Who We Share Your Data With</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.1 Service Providers (Data Processors)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-stone">
              <thead>
                <tr className="bg-parchment">
                  <th className="text-left p-2 border-b border-stone">Provider</th>
                  <th className="text-left p-2 border-b border-stone">Purpose</th>
                  <th className="text-left p-2 border-b border-stone">Location</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 border-b border-stone"><strong>Vercel Inc.</strong></td>
                  <td className="p-2 border-b border-stone">Website hosting and infrastructure</td>
                  <td className="p-2 border-b border-stone">United States (EU/US Data Privacy Framework)</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone"><strong>Stripe</strong></td>
                  <td className="p-2 border-b border-stone">Payment processing</td>
                  <td className="p-2 border-b border-stone">United States/Global (PCI DSS Level 1, DPF)</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone"><strong>Vercel Postgres (Neon)</strong></td>
                  <td className="p-2 border-b border-stone">Database hosting</td>
                  <td className="p-2 border-b border-stone">United States (DPF)</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.2 Lead Data Sharing</h3>
          <p>
            When you submit a lead enquiry about a specific care provider, your enquiry details
            (name, contact information, message) are shared with <strong>that specific care provider</strong>{" "}
            so they can respond to your enquiry. By submitting the form, you consent to this sharing.
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.3 Legal Disclosure</h3>
          <p>
            We may disclose information where required by law, court order, or governmental regulation.
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.4 We Do NOT Sell Personal Data</h3>
          <p>
            We do not sell, rent, or trade personal data to third parties for their marketing purposes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Data Retention</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-stone">
              <thead>
                <tr className="bg-parchment">
                  <th className="text-left p-2 border-b border-stone">Data type</th>
                  <th className="text-left p-2 border-b border-stone">Retention period</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 border-b border-stone">Account data</td>
                  <td className="p-2 border-b border-stone">Duration of account + 30 days after deletion request</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Lead enquiries</td>
                  <td className="p-2 border-b border-stone">24 months from submission</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Payment/transaction records</td>
                  <td className="p-2 border-b border-stone">6 years (UK financial record-keeping requirements)</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Export access tokens</td>
                  <td className="p-2 border-b border-stone">90 days after expiry, then deleted or irreversibly anonymised</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">Anonymised usage data</td>
                  <td className="p-2 border-b border-stone">26 months</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-stone">CQC public data</td>
                  <td className="p-2 border-b border-stone">Retained while Service operates (non-personal)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Your Rights Under UK GDPR</h2>
          <p>You have the following rights regarding your personal data:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Right to be informed</strong> — This Privacy Policy fulfils this right</li>
            <li><strong>Right of access</strong> — Request a copy of your personal data (Subject Access Request)</li>
            <li><strong>Right to rectification</strong> — Correct inaccurate or incomplete data</li>
            <li><strong>Right to erasure</strong> — Request deletion of your data (&quot;right to be forgotten&quot;)</li>
            <li><strong>Right to restrict processing</strong> — Limit how we use your data</li>
            <li><strong>Right to data portability</strong> — Receive your data in a machine-readable format</li>
            <li><strong>Right to object</strong> — Object to processing based on legitimate interest</li>
            <li><strong>Rights relating to automated decision-making</strong> — Not applicable (we do not use ADM)</li>
          </ul>
          <p className="mt-2">
            To exercise any of these rights, contact us at{" "}
            <a href="mailto:henry.mlalazi@gmail.com" className="text-clay underline">
              henry.mlalazi@gmail.com
            </a>
            . We will respond within <strong>one calendar month</strong>.
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">Complaints</h3>
          <p>
            If you are dissatisfied with our response, you have the right to lodge a complaint with
            the <strong>Information Commissioner&apos;s Office (ICO)</strong>:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>
              Website:{" "}
              <a href="https://ico.org.uk/make-a-complaint/" className="text-clay underline" target="_blank" rel="noopener noreferrer">
                ico.org.uk/make-a-complaint
              </a>
            </li>
            <li>Helpline: 0303 123 1113</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Cookies</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">Strictly Necessary Cookies</h3>
          <p>
            These are essential for the Service to function and cannot be switched off:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Session cookies (authentication, security)</li>
            <li>Stripe payment cookies (payment processing)</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">Analytics Cookies</h3>
          <p>
            We may use anonymised analytics to understand how visitors use the Service. These do not
            identify you personally. You can opt out via our cookie banner.
          </p>
          <p className="mt-2">
            We do <strong>not</strong> use:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Advertising/targeting cookies</li>
            <li>Third-party tracking cookies</li>
            <li>Social media pixels</li>
          </ul>
          <p className="mt-2">
            See our{" "}
            <a href="/cookies" className="text-clay underline">
              Cookie Policy
            </a>{" "}
            for full details.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Data Security</h2>
          <p>
            We implement appropriate technical and organisational measures to protect your personal data:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>HTTPS encryption for all data in transit</li>
            <li>Database encryption at rest</li>
            <li>Password hashing (bcrypt/argon2)</li>
            <li>Access controls for lead and payment data</li>
            <li>Regular security review</li>
          </ul>
          <p className="mt-2">
            However, no method of transmission or storage is 100% secure. We cannot guarantee absolute security.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. International Transfers</h2>
          <p>
            Where data is transferred outside the UK (e.g., to US-based processors Vercel, Stripe,
            and Neon), we rely on:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>UK Adequacy Regulations</strong> recognising countries with adequate data protection</li>
            <li><strong>EU/US Data Privacy Framework (DPF)</strong> certification for US-based processors</li>
            <li><strong>Standard Contractual Clauses</strong> where applicable</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Children&apos;s Privacy</h2>
          <p>
            Our Service is not directed to individuals under the age of 18. We do not knowingly
            collect personal data from children.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Changes to This Privacy Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. Changes will be posted on this page
            with an updated &quot;Last updated&quot; date. Material changes will be notified to
            registered users via email.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">12. Contact Us</h2>
          <p>
            For questions about this Privacy Policy or to exercise your data rights:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>
              <strong>Email:</strong>{" "}
              <a href="mailto:henry.mlalazi@gmail.com" className="text-clay underline">
                henry.mlalazi@gmail.com
              </a>
            </li>
            <li>
              <strong>Post:</strong> C/O Bilberry Accountants Ltd, Castle Court, 41 London Road,
              Reigate, England, RH2 9RJ
            </li>
          </ul>
        </section>

        <p className="italic text-dusk mt-8 pt-4 border-t border-stone">
          This Privacy Policy is effective from 8 August 2026.
        </p>

      </div>
    </div>
  );
}
