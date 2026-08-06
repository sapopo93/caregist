import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Status | CareGist",
  description: "Controlled pre-launch privacy status for CareGist.",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Privacy Notice</h1>
      <p className="text-dusk text-sm mb-6">Last updated: 2 August 2026</p>

      <div className="rounded-xl border border-stone bg-mist p-4 text-sm text-charcoal mb-8">
        Paid checkout, provider claims, reviews, enquiries, exports, outreach and monitoring
        activation remain fail-closed. External processor and transfer approvals are release gates.
      </div>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Who controls your data</h2>
          <p>
            CareGist is operated by <strong>H-Kay Limited</strong>, registered in England and Wales
            under company number <strong>10417923</strong>, registered office C/O Bilberry
            Accountants Ltd, Castle Court, 41 London Road, Reigate, England, RH2 9RJ. H-Kay Limited
            is the data controller for personal data processed through CareGist.
          </p>
          <p>
            Privacy questions and rights requests may be sent to{" "}
            <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>.
            You may also complain to the UK Information Commissioner&apos;s Office at ico.org.uk.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Processing currently implemented</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Accounts:</strong> name, email address and a salted password hash; verification and security records.</li>
            <li><strong>Security and API operation:</strong> request timestamps, endpoints, rate-limit counters, minimised IP evidence and user agent.</li>
            <li><strong>Browser storage:</strong> the signed-in user&apos;s id, name and email plus the displayed tier may be held in local storage; no password, API key or session secret is intentionally stored there.</li>
            <li><strong>CQC directory:</strong> organisation/location identifiers, names, business addresses, published phone numbers and websites, registration/rating/service fields and source timestamps.</li>
          </ul>
          <p>
            Enquiries, review submissions, provider claims, lead-list requests, export access
            tokens, paid checkout, monitoring activation and export delivery are disabled by default pending approval. If a
            gate is later approved, this notice and the processing record must be updated before
            collection begins.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. CQC source and reuse boundary</h2>
          <p>
            CQC makes its data available under the Open Government Licence v3.0. CareGist must
            attribute CQC, must not imply CQC endorsement, and must independently comply with data
            protection law because the OGL does not license personal-data rights. The public
            directory excludes known registered-manager names and does not infer individual care
            quality. Source publication time and CareGist ingestion time are reported separately.
          </p>
          <p>
            Contains public sector information licensed under the Open Government Licence v3.0.
            CareGist is not an official CQC service and is not endorsed by CQC.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Purposes and lawful bases</h2>
          <p>
            Account operation, subscription and requested service access rely on performance of a
            contract with you. Security, abuse prevention and operation of the business directory
            rely on our legitimate interests in running a secure and accurate service; the
            legitimate-interests assessment and record of processing are maintained by the
            controller. CareGist does not make solely automated decisions producing legal or
            similarly significant effects.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Recipients and transfers</h2>
          <p>
            CareGist currently uses or is configured to use the following suppliers. This list
            describes the technical role; it does not mark the processor agreement, hosting
            location, transfer assessment or safeguard as approved.
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Neon:</strong> PostgreSQL hosting for accounts, operational records, audit evidence and CQC-derived data.</li>
            <li><strong>Vercel:</strong> application hosting, request routing, deployment logs and service diagnostics.</li>
            <li><strong>Stripe:</strong> payment customers, Checkout Sessions, subscriptions, invoices and webhook events; new checkout remains disabled.</li>
            <li><strong>Resend:</strong> transactional email delivery and delivery-failure handling where an approved email path is active.</li>
            <li><strong>Sentry:</strong> application error diagnostics when a DSN is configured, subject to data-minimisation controls.</li>
            <li><strong>Redis:</strong> shared rate-limit and short-lived operational state when configured; it is not the system of record.</li>
          </ul>
          <p>
            The controlled processor register must record each supplier&apos;s contract, sub-processors,
            retention, hosting regions and UK transfer mechanism. Paid checkout and new personal-data
            intake cannot be enabled until the relevant entries and transfer assessment are approved.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Retention controls</h2>
          <table className="w-full text-sm border border-stone">
            <tbody>
              <tr><td className="p-2 border-b border-stone">Analytics and request metadata</td><td className="p-2 border-b border-stone">90 days</td></tr>
              <tr><td className="p-2 border-b border-stone">Audit records</td><td className="p-2 border-b border-stone">2 years by default, subject to approved legal requirements</td></tr>
              <tr><td className="p-2 border-b border-stone">B2B contract acceptance evidence</td><td className="p-2 border-b border-stone">For the contract term and the approved limitation/accounting period; the final schedule is a legal gate</td></tr>
              <tr><td className="p-2 border-b border-stone">Stripe subscription and invoice records</td><td className="p-2 border-b border-stone">According to the approved accounting and statutory retention schedule</td></tr>
              <tr><td className="p-2 border-b border-stone">Sent email queue rows</td><td className="p-2 border-b border-stone">30 days; failed rows remain in the controlled dead-letter process</td></tr>
              <tr><td className="p-2 border-b border-stone">Enquiries and rejected review identity</td><td className="p-2 border-b border-stone">Anonymised after 12 months if those features are approved</td></tr>
              <tr><td className="p-2 border-b border-stone">Closed provider claims</td><td className="p-2 border-b border-stone">Identity and evidence fingerprint anonymised after 12 months</td></tr>
              <tr><td className="p-2 border-b border-stone">Lead-list requests</td><td className="p-2 border-b border-stone">Deleted after 12 months</td></tr>
              <tr><td className="p-2 border-b border-stone">Export access tokens</td><td className="p-2 border-b border-stone">90 days after expiry</td></tr>
              <tr><td className="p-2 border-b border-stone">VAT records</td><td className="p-2 border-b border-stone">At least 6 years if the confirmed operator is VAT-registered; specialist schemes may differ</td></tr>
            </tbody>
          </table>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Your rights and complaints</h2>
          <p>
            Depending on the processing and lawful basis, UK data-protection rights can include
            access, correction, erasure, restriction, portability, objection and withdrawal of
            consent. Direct-marketing objections are absolute. Requests should be sent to the
            privacy address above. You may also complain to the UK Information Commissioner&apos;s Office.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Features not yet active</h2>
          <p>
            Provider claims, reviews and enquiries collect personal data and remain switched off at
            the route boundary until their moderation, safeguarding and lawful-basis controls are
            approved. Outbound marketing is not authorised by this notice: no direct-marketing
            outreach is carried out on the basis described here.
          </p>
        </section>
      </div>
    </div>
  );
}
