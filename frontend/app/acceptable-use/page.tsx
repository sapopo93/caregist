import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Acceptable Use Policy | CareGist",
  description: "Rules for using the CareGist Directory, Radar, Intelligence Feed, and Embedded services.",
};

export default function AcceptableUsePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-bold">Acceptable Use Policy</h1>
      <p className="mb-8 text-sm text-dusk">Version 2.0 · In force from 9 August 2026</p>

      <div className="prose prose-sm space-y-7 text-charcoal" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">1. Scope</h2>
          <p>
            This policy governs the CareGist Directory, Radar, Intelligence Feed Pilot,
            Embedded Enterprise services, exports, APIs, and webhooks operated by
            H-Kay Limited (company number 10417923). It supplements the{" "}
            <a href="/terms" className="text-clay underline">Business Terms of Service</a>.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">2. Permitted use</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>Search and verify public CQC location information through the free Directory.</li>
            <li>Use Radar events, saved views, provider lists, actions, outcomes, and included exports within the organisation and territory stated by the customer&apos;s plan.</li>
            <li>Use Feed APIs and signed webhooks only within the region, signal, volume, retention, and integration scope stated in the pilot agreement.</li>
            <li>Use CareGist output in internal analysis and client work while retaining the supplied source attribution and evidence links.</li>
            <li>Submit genuine provider correction or claim requests when authorised to represent the provider.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">3. Evidence and high-impact decisions</h2>
          <p>
            CareGist is independent of CQC. A signal is not regulatory advice, a vacancy,
            a prediction, or a guaranteed commercial opportunity. You must review the
            linked official evidence before relying on an event in a regulated, clinical,
            safeguarding, employment, credit, or other high-impact decision.
          </p>
          <p>
            You must not present a location-level event as a provider-group conclusion,
            remove the distinction between source fact and CareGist interpretation, or
            represent CareGist output as official CQC guidance.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">4. Data protection and outreach</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>Do not upload patient records, care records, special-category data, or other information the product does not request.</li>
            <li>Do not use CareGist to send unlawful unsolicited communications or to harass a provider, employee, resident, or service user.</li>
            <li>Maintain your own lawful basis and transparency information for customer data, provider lists, outcomes, and outreach activity.</li>
            <li>Do not infer a named individual&apos;s vacancy, performance, health, or employment status from a CareGist event.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">5. Security and access</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>Keep account credentials and Feed signing secrets confidential and rotate them if compromise is suspected.</li>
            <li>Do not share access outside the contracted organisation or attempt to access another organisation&apos;s workspace.</li>
            <li>Do not bypass authentication, tenant controls, territory restrictions, export windows, rate limits, cursors, or delivery controls.</li>
            <li>Do not introduce malicious code, interfere with service availability, or conduct load testing or security scanning without written permission.</li>
            <li>Do not place credentials or signing secrets in browser code, public repositories, public URLs, or unprotected logs.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">6. Reuse and redistribution</h2>
          <p>
            CQC source information remains available under its applicable source rights,
            including the Open Government Licence v3.0. CareGist does not restrict rights
            granted directly by that licence. CareGist&apos;s original event model, interface,
            delivery system, explanations, and customer workspace content remain subject
            to the Business Terms and the contracted scope.
          </p>
          <p>
            You may not remove supplied CQC/OGL attribution, resell CareGist outputs as a
            competing signal service, redistribute customer-specific intelligence, or use
            the service to systematically replicate CareGist&apos;s event ledger. White-label,
            sublicensing, and embedded redistribution require an Embedded Enterprise agreement.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">7. Enforcement and contact</h2>
          <p>
            CareGist may warn, throttle, suspend, or terminate access where reasonably
            necessary to protect evidence integrity, tenant isolation, security, lawful
            operation, or other customers. Where practical, CareGist will give notice and
            an opportunity to remedy the issue.
          </p>
          <p>
            Report suspected abuse to{" "}
            <a href="mailto:abuse@caregist.co.uk" className="text-clay underline">abuse@caregist.co.uk</a>{" "}
            and policy questions to{" "}
            <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>.
          </p>
        </section>
      </div>
    </main>
  );
}
