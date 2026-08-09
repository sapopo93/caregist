import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Business Terms of Service | CareGist",
  description: "Terms governing the CareGist Directory, Radar, Intelligence Feed Pilot, and Embedded Enterprise services.",
};

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-bold">Business Terms of Service</h1>
      <p className="mb-8 text-sm text-dusk">Version 2.0 · In force from 9 August 2026</p>

      <div className="prose prose-sm space-y-7 text-charcoal" style={{ fontFamily: "Lora" }}>
        <section>
          <p>
            These terms govern use of CareGist by a business, public body, charity, or
            professional customer. CareGist is operated by <strong>H-Kay Limited</strong>,
            registered in England and Wales under company number <strong>10417923</strong>,
            with registered office at C/O Bilberry Accountants Ltd, Castle Court, 41
            London Road, Reigate, England, RH2 9RJ (&quot;CareGist&quot;, &quot;we&quot;,
            &quot;us&quot;). If you accept these terms for an organisation, you confirm that
            you are authorised to bind it.
          </p>
          <p>
            The paid services are not offered for personal, family, or household use.
            A person seeking care should use the free directory and verify information
            directly with CQC and the provider.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">1. Products and scope</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li><strong>Free Directory:</strong> provider search, profiles, source dates, and free correction or claim requests when verification intake is available.</li>
            <li><strong>Radar Regional:</strong> one contracted England region, 2 users, 10 saved views, and 90 days of event export.</li>
            <li><strong>Radar National:</strong> all England, 5 users, 50 saved views or lists, 365 days of event export, and onboarding.</li>
            <li><strong>Intelligence Feed Pilot:</strong> a sales-assisted, contracted API and webhook pilot with a stated region, signal, and delivery scope.</li>
            <li><strong>Embedded Enterprise:</strong> a separately contracted white-label or regulated-use service.</li>
          </ul>
          <p className="mt-2">
            Radar does not include API or webhook access. Additional seats are not sold
            separately at launch. A written order form, pilot statement, or enterprise
            agreement prevails over these terms for its expressly stated scope.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">2. Source data and evidence</h2>
          <p>
            CareGist reuses CQC public information under the Open Government Licence
            v3.0. CareGist is independent of and is not endorsed by CQC. Source systems
            may delay, correct, remove, or republish information. CareGist records when
            it checked and observed a source; those timestamps are not a statement that
            the underlying change occurred at that time.
          </p>
          <p>
            A location-level signal must not be treated as a provider-group conclusion.
            Customers must check the linked official evidence before making a regulated,
            clinical, safeguarding, employment, credit, or other high-impact decision.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">3. Explanations and ranking</h2>
          <p>
            CareGist may attach a plain-language explanation to a verified event only
            after its factual claims pass the applicable evidence gate. If generation,
            extraction, or evaluation fails, the verified raw event may be delivered
            without a narrative. Source facts and CareGist interpretation are labelled
            separately.
          </p>
          <p>
            Initial ranking uses explainable factors such as recency, contracted
            territory, service type, explicit provider lists, and the organisation&apos;s
            recorded actions. CareGist does not sell predictive scores, vacancy claims,
            or guaranteed commercial opportunities.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">4. Accounts and organisations</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>Users must be at least 18 and provide accurate account information.</li>
            <li>Each organisation controls its members, saved views, provider lists, actions, outcomes, subscriptions, and deliveries.</li>
            <li>Credentials must not be shared outside the named organisation users.</li>
            <li>Owners and admins are responsible for member access and territory configuration.</li>
            <li>Customers must promptly report suspected unauthorised access.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">5. Customer data and outcomes</h2>
          <p>
            Customers may save provider lists, actions, and optional outcomes such as
            contacted, meeting booked, engagement won, or not relevant. The customer
            is responsible for having a lawful basis for personal data it submits and
            must not upload special-category data, patient data, care records, or other
            data that the product does not request.
          </p>
          <p>
            CareGist does not place customer data into report-narrative prompts. Any
            enterprise processing terms or customer-owned list integration must be
            agreed in the applicable contract or data-processing agreement.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">6. Fees, subscription and cancellation</h2>
          <p>
            Current prices and included limits are shown on the pricing page or in the
            signed order form. CareGist is not currently VAT registered, so VAT is not
            currently charged. Stripe processes self-serve payments; CareGist does not
            store full card details.
          </p>
          <p>
            Radar subscriptions renew for the displayed billing period until cancelled.
            Cancellation takes effect at the end of the current paid period unless law
            or an agreed order form requires otherwise. Customers can use billing
            management or contact support. Feed and Embedded terms, renewal, service
            levels, and termination are set out in the signed agreement.
          </p>
          <p>
            Historical one-off digital-content purchases remain governed by the terms
            and express immediate-supply consent captured at their checkout. This does
            not affect remedies that cannot lawfully be excluded. No new static dataset
            product is offered under this catalogue.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">7. Availability and delivery targets</h2>
          <p>
            Public statements labelled as a target are not a guaranteed service level.
            Any contracted service level applies only when written into the relevant
            Feed or Embedded agreement. Upstream CQC unavailability, delay, correction,
            and schema change can affect collection and delivery.
          </p>
          <p>
            CareGist may pause a collector, signal type, explanation, outbound delivery,
            or checkout to protect accuracy, security, or tenant isolation.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">8. Acceptable use</h2>
          <p>Customers must not:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>use the service unlawfully or to send unlawful unsolicited communications;</li>
            <li>attempt to access another organisation&apos;s data or bypass plan scope;</li>
            <li>misrepresent CareGist output as official CQC advice or a guaranteed prediction;</li>
            <li>use a signal as the sole basis for a high-impact decision about a person;</li>
            <li>interfere with, reverse engineer, or overload the service.</li>
          </ul>
          <p className="mt-2">The <a href="/acceptable-use" className="text-clay underline">Acceptable Use Policy</a> also applies.</p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">9. Intellectual property and licence</h2>
          <p>
            CQC data remains subject to its source rights and the Open Government
            Licence. CareGist owns or licenses its original software, event modelling,
            explanations, interface, and branding. During a paid term, the customer may
            use included outputs for its internal business purpose. White-label,
            redistribution, sublicensing, or embedding requires a written agreement.
          </p>
          <p>
            Exports must retain the supplied CQC/Open Government Licence attribution
            and CareGist source metadata.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">10. Disclaimers and liability</h2>
          <p>
            CQC information and third-party links are provided as published and may be
            incomplete, delayed, or corrected. CareGist does not guarantee a rating
            change, closure, expansion, engagement, or other commercial result.
          </p>
          <p>
            To the fullest extent permitted by law, neither party is liable for indirect
            or consequential loss. CareGist&apos;s aggregate liability under self-serve Radar
            is limited to fees paid for that service in the preceding 12 months. A signed
            enterprise agreement may set a different cap. Nothing excludes liability
            that cannot lawfully be limited, including fraud or death or personal injury
            caused by negligence.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">11. Suspension, termination and changes</h2>
          <p>
            CareGist may suspend access where reasonably necessary for security,
            non-payment, unlawful use, tenant protection, or material breach. Where
            practical, notice and an opportunity to remedy will be given. Material terms
            changes will be notified to registered customers and will not retrospectively
            alter a completed purchase.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">12. Governing law and contact</h2>
          <p>
            These terms are governed by the laws of England and Wales and the courts of
            England and Wales have exclusive jurisdiction, subject to any mandatory law.
            Questions may be sent to{" "}
            <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>{" "}
            or by post to H-Kay Limited at the registered office stated above.
          </p>
        </section>
      </div>
    </main>
  );
}
