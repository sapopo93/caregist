import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Status | CareGist",
  description: "Controlled pre-launch privacy status for CareGist.",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Privacy status</h1>
      <p className="text-dusk text-sm mb-6">Last updated: 30 July 2026</p>

      <div className="rounded-xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950 mb-8">
        <strong>Controlled pre-launch notice.</strong> The legal operator and data controller,
        processor register, transfer mechanisms, lawful-basis assessment and UK Country Pack
        still require Human Gate approval. Personal-data intake features remain disabled. This
        page records the implemented controls; it is not a claim of legal approval.
      </div>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Controller status</h2>
          <p>
            Existing project materials name H-Kay Limited (company number 10417923) and another
            possible operator. CareGist will not identify a contracting party or controller until
            authority, brand and intellectual-property rights are evidenced at Human Gate 1.
            Privacy questions and rights requests may be sent to{" "}
            <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Processing currently implemented</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Accounts:</strong> name, email address and a salted password hash; verification and security records.</li>
            <li><strong>Security and API operation:</strong> request timestamps, endpoints, rate-limit counters, IP address and user agent.</li>
            <li><strong>Browser storage:</strong> the signed-in user&apos;s id, name and email plus the displayed tier may be held in local storage; no password, API key or session secret is intentionally stored there.</li>
            <li><strong>CQC directory:</strong> organisation/location identifiers, names, business addresses, published phone numbers and websites, registration/rating/service fields and source timestamps.</li>
          </ul>
          <p>
            Enquiries, review submissions, provider claims, Lead-list requests, Export access
            tokens, checkout and export delivery are disabled by default pending approval. If a
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
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Purposes and legal review</h2>
          <p>
            Account operation and requested service access are intended to rely on contract;
            security, abuse prevention and business-directory operation are candidates for
            legitimate interests. Those conclusions are not approved until the controller is
            confirmed and the relevant legitimate-interests assessment and record of processing
            are signed. CareGist does not make solely automated decisions producing legal or
            similarly significant effects.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Recipients and transfers</h2>
          <p>
            The production processor inventory, data-processing agreements, hosting locations and
            any international-transfer mechanism must be verified before personal-data intake or
            billing is enabled. CareGist does not claim that a provider is a processor, that a DPA
            is signed, or that a transfer safeguard applies without documentary evidence.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Retention controls</h2>
          <table className="w-full text-sm border border-stone">
            <tbody>
              <tr><td className="p-2 border-b border-stone">Analytics and request metadata</td><td className="p-2 border-b border-stone">90 days</td></tr>
              <tr><td className="p-2 border-b border-stone">Audit records</td><td className="p-2 border-b border-stone">2 years by default, subject to approved legal requirements</td></tr>
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
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Before activation</h2>
          <p>
            The confirmed controller must approve the information asset register, lawful bases,
            CQC-field assessment, processor and transfer register, rights workflow, breach process,
            retention schedule and just-in-time notices. No outreach, publishing change, billing,
            export delivery, paid monitoring or provider-claim activation is authorised by this notice.
          </p>
        </section>
      </div>
    </div>
  );
}
