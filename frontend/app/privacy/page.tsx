import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Notice | CareGist",
  description: "How CareGist processes personal data for the Directory, Radar, Intelligence Feed, and Embedded services.",
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-bold">Privacy Notice</h1>
      <p className="mb-8 text-sm text-dusk">Version 2.0 · In force from 9 August 2026</p>

      <div className="prose prose-sm space-y-7 text-charcoal" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">1. Controller and contact</h2>
          <p>
            CareGist is operated by <strong>H-Kay Limited</strong>, registered in
            England and Wales under company number <strong>10417923</strong>, with
            registered office at C/O Bilberry Accountants Ltd, Castle Court, 41
            London Road, Reigate, England, RH2 9RJ. H-Kay Limited is the controller
            for personal data described in this notice. Contact{" "}
            <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>{" "}
            for privacy questions or rights requests.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">2. Data we process</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li><strong>Account and organisation data:</strong> name, work email, password hash, organisation, role, membership, and territory settings.</li>
            <li><strong>Subscription records:</strong> plan, entitlement, status, contractual acceptance, and Stripe identifiers. Full card data is handled by Stripe.</li>
            <li><strong>Workspace content:</strong> saved views, customer provider lists, event actions, optional outcomes, and support messages.</li>
            <li><strong>Delivery data:</strong> configured endpoint, delivery state, retry history, cursor, and signing-key identifier. Secret values are not displayed in delivery health.</li>
            <li><strong>Security and usage data:</strong> IP address or a derived security hash, browser information, session records, audit events, pages and features used, and error telemetry.</li>
            <li><strong>Claims and corrections:</strong> claimant identity, contact details, evidence supplied, and correction content.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">3. CQC source and report data</h2>
          <p>
            CareGist retrieves public CQC location, provider, registration, rating, and
            inspection-report information under the Open Government Licence v3.0. A
            public report can contain names or professional information. Public
            availability does not remove data-protection obligations, so CareGist limits
            processing to the defined signal and evidence purposes.
          </p>
          <p>
            Source reports may be stored privately as immutable evidence with their URL,
            retrieval time, and SHA-256 checksum. Evidence extraction records page,
            heading, and text-span references. Manager absence may be processed only if
            separately approved after privacy review; it is never labelled as a vacancy.
            Named-manager change processing is not part of the launched service.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">4. Purposes and lawful bases</h2>
          <div className="overflow-x-auto">
            <table className="w-full border border-stone text-sm">
              <thead><tr className="bg-parchment"><th className="border-b border-stone p-2 text-left">Purpose</th><th className="border-b border-stone p-2 text-left">Lawful basis</th></tr></thead>
              <tbody>
                <tr><td className="border-b border-stone p-2">Create accounts, workspaces, subscriptions, and deliver contracted features</td><td className="border-b border-stone p-2">Contract</td></tr>
                <tr><td className="border-b border-stone p-2">Secure the service, isolate tenants, prevent abuse, and maintain audit records</td><td className="border-b border-stone p-2">Legitimate interests and legal obligation where applicable</td></tr>
                <tr><td className="border-b border-stone p-2">Track saved, dismissed, exported, or reported outcomes to personalise deterministic ranking</td><td className="border-b border-stone p-2">Contract and legitimate interests</td></tr>
                <tr><td className="border-b border-stone p-2">Process CQC reports into traceable source facts and explanations</td><td className="border-b border-stone p-2">Legitimate interests in providing evidence-linked business intelligence</td></tr>
                <tr><td className="border-b border-stone p-2">Process payments, accounting records, and contractual acceptance</td><td className="border-b border-stone p-2">Contract and legal obligation</td></tr>
                <tr><td className="p-2">Respond to claims, corrections, support, and rights requests</td><td className="p-2">Contract, legitimate interests, and legal obligation as applicable</td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">5. Explanations, ranking and automated processing</h2>
          <p>
            Automated tools may extract report facts and draft a plain-language
            explanation. CareGist separates source facts from interpretation and
            suppresses a narrative that does not pass its evidence gate. Customer data
            is not included in report-narrative prompts.
          </p>
          <p>
            Initial ranking uses recency, contracted territory, service type, explicit
            provider lists, and the organisation&apos;s actions or optional outcomes. CareGist
            does not use this processing to make legal or similarly significant decisions
            about individuals, and predictive provider scores are not launched.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">6. Sharing and processors</h2>
          <p>
            CareGist uses contracted providers for infrastructure, database hosting,
            payment processing, email, support, monitoring, and—only when enabled—model
            processing. Current core providers include Vercel, Neon, and Stripe. We share
            only what is necessary for the service and use contractual safeguards for
            restricted transfers where required.
          </p>
          <p>
            We do not sell personal data. Organisation content is not disclosed to other
            CareGist customers. We may disclose data where required by law or to protect
            the rights, security, and integrity of the service.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">7. Retention</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>Account and organisation data: while the account is active and ordinarily 30 days after a valid deletion request, subject to legal holds.</li>
            <li>Subscription, invoice, acceptance, and accounting records: normally 6 years where required for UK records.</li>
            <li>Workspace actions and outcomes: while the organisation uses Radar and for up to 12 months after termination unless the contract or a deletion request requires less.</li>
            <li>Delivery attempts and operational logs: ordinarily 90 days; security and audit events may be retained longer where justified.</li>
            <li>Public CQC source snapshots and event evidence: retained for provenance, dispute handling, and reproducibility while the relevant service operates, then reviewed for deletion or archive.</li>
            <li>Claims and corrections: while needed to verify and maintain the listing, with verification evidence periodically reviewed.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">8. Security and tenant isolation</h2>
          <p>
            Measures include HTTPS, password hashing, least-privilege access, organisation
            ownership on workspace records, database tenant controls, explicit
            cross-tenant denial tests, audit logging, signing-key rotation, durable
            delivery queues, and restricted access to production systems. No system can
            provide absolute security.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">9. Your rights</h2>
          <p>
            Subject to applicable UK GDPR conditions, you may request access,
            rectification, erasure, restriction, portability, or object to processing
            based on legitimate interests. You may also raise concerns about automated
            processing and lodge a complaint with the Information Commissioner&apos;s Office.
            We normally respond to a valid rights request within one month.
          </p>
          <p>
            Contact{" "}<a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>{" "}
            or visit{" "}<a href="https://ico.org.uk/make-a-complaint/" className="text-clay underline" target="_blank" rel="noopener noreferrer">ico.org.uk</a>.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">10. Cookies and changes</h2>
          <p>
            Necessary cookies and local storage support authentication, security, and
            requested preferences. CareGist does not use advertising cookies. Details
            of the browser storage and first-party operational telemetry currently used
            are described in the{" "}
            <a href="/cookies" className="text-clay underline">Cookie Policy</a>. Material
            changes to this policy will be posted here and notified to registered
            customers where appropriate.
          </p>
        </section>
      </div>
    </main>
  );
}
