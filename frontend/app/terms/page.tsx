import type { Metadata } from "next";

import { TERRITORY_BRIEF_PRICE_GBP, WEEKLY_DIGEST_PILOT_PRICE_GBP } from "@/lib/territory-scope";

export const metadata: Metadata = {
  title: "Business Terms of Service | CareGist",
  description: "Terms governing the CareGist Free Directory, Territory Opportunity Brief and Weekly Digest pilot.",
};

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-bold">Business Terms of Service</h1>
      <p className="mb-8 text-sm text-dusk">Version 2.3 · In force from 19 October 2026</p>

      <div className="prose prose-sm space-y-7 text-charcoal" style={{ fontFamily: "Lora" }}>
        <section>
          <p>
            These terms govern use of CareGist by a business, public body, charity, or
            professional customer. <strong>H-Kay Limited</strong> provides the CareGist product,
            registered in England and Wales under company number <strong>10417923</strong>,
            with registered office at C/O Bilberry Accountants Ltd, Castle Court, 41
            London Road, Reigate, England, RH2 9RJ (&quot;H-Kay Limited&quot;, &quot;we&quot;,
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
            <li><strong>Free Directory:</strong> public search of CQC-registered locations, with source dates and links to the official CQC record.</li>
            <li><strong>Territory Opportunity Brief:</strong> a one-off research pack for an England territory agreed in writing. It contains a shortlist of 25 to 50 distinct provider organisations to investigate, a stated factual reason for each, a CSV dataset, a three to five page summary, and a source manifest with links and observation dates.</li>
            <li><strong>Weekly Digest pilot</strong> (available by enquiry only): four weekly digests for one agreed England region, reporting new registrations and newly published CQC ratings in that region, each linked to the CQC record and dated. It is not a subscription, dashboard, API or alert service.</li>
          </ul>
          <p className="mt-2">
            For a Territory Opportunity Brief, the written scope confirmation identifies
            the territory, buyer criteria and factual selection criteria. For a Weekly
            Digest pilot, the written confirmation of region, start date and delivery
            dates applies. Each is the order form for that purchase and prevails where it
            differs from a general statement on this site.
          </p>
          <p className="mt-2">
            CareGist does not currently offer any other paid service. Any future service
            will be offered on separate written terms.
          </p>
          <p className="mt-2">
            Outputs identify organisations to investigate. They are not leads, and they
            do not state or imply need, budget, vacancies, contract timing or intent to buy.
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
            A location-level fact must not be treated as a provider-group conclusion.
            Customers must check the linked official evidence before making a regulated,
            clinical, safeguarding, employment, credit, or other high-impact decision.
          </p>
          <p>
            <strong>Corrections and objections.</strong> A provider named in CareGist output,
            or a person whose details appear in it, may ask us to correct, update or stop
            using that information by emailing{" "}
            <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>.
            We aim to respond within 10 working days. Where the information is accurate and
            we have a lawful basis to continue, we will explain why. Requests about personal
            data are handled under our{" "}
            <a href="/privacy" className="text-clay underline">Privacy Notice</a>.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">3. Selection and ranking</h2>
          <p>
            A Territory Opportunity Brief selects and orders organisations using explainable,
            factual criteria agreed in the scope, such as recency of registration, service
            type and the published CQC record. Source facts and CareGist interpretation are
            labelled separately. CareGist does not sell predictive scores, vacancy claims,
            or guaranteed commercial opportunities.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">4. Accounts and organisations</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>Users must be at least 18 and provide accurate account information.</li>
            <li>Credentials must not be shared outside the named organisation users.</li>
            <li>Customers must promptly report suspected unauthorised access.</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">5. Customer data, personal data and outreach</h2>
          <p>
            The customer is responsible for having a lawful basis for any personal data it
            gives us and must not send special-category data, patient data, care records, or
            other data that the product does not request.
          </p>
          <p>
            <strong>Personal data in outputs.</strong> Some providers are registered with CQC
            as individuals or partnerships, so outputs may contain personal data. Each
            customer is an independent controller of any personal data it receives from
            CareGist. The customer must: (a) have its own lawful basis for any use; (b) comply
            with the UK GDPR, the Data Protection Act 2018 and the Privacy and Electronic
            Communications (EC Directive) Regulations 2003, including screening calls against
            the Telephone Preference Service and Corporate Telephone Preference Service, and
            not sending unsolicited electronic marketing to individual subscribers (including
            sole traders and partnerships) without the consent the law requires; (c) honour
            objections and opt-outs promptly; and (d) not use outputs to profile, or take
            decisions about, an individual&apos;s suitability, creditworthiness or employment.
          </p>
          <p>
            <strong>The customer&apos;s own communications.</strong> The customer is solely
            responsible for the content, lawfulness and targeting of any communication it
            sends to a provider. Outputs must not be presented to a provider as coming from
            or endorsed by CQC.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">6. Fees, payment and cancellation</h2>
          <p>
            <strong>Formation.</strong> A contract for a paid product forms when CareGist
            confirms the agreed scope in writing and the customer pays the payment link or
            invoice that refers to these terms.
          </p>
          <p>
            <strong>Prices.</strong> Prices are as stated in the written scope or invoice.
            H-Kay Limited is not currently VAT registered. No VAT is added. Payment is due in
            full before work begins. Card payments are processed by Stripe; H-Kay Limited does
            not store full card details. Unpaid invoices accrue statutory interest under the
            Late Payment of Commercial Debts (Interest) Act 1998.
          </p>
          <p>
            <strong>Territory Opportunity Brief.</strong> The Brief costs <strong>£{TERRITORY_BRIEF_PRICE_GBP}</strong>.
            CareGist confirms the scope and the relevant source path before it sends a payment
            link or accepts payment. The buyer may cancel by email before work begins and
            receive a full refund. Once work has begun on the agreed bespoke Brief, the fee is
            non-refundable except where CareGist fails to deliver the agreed scope or a remedy
            cannot lawfully be excluded. If a source issue after payment prevents delivery of
            the agreed scope, CareGist will offer a revised delivery date or an alternative
            scope, or a full refund if neither is agreed.
          </p>
          <p>
            <strong>Weekly Digest pilot.</strong> Available by enquiry only. Where agreed, the
            pilot costs £{WEEKLY_DIGEST_PILOT_PRICE_GBP} for four weekly digests. CareGist
            confirms the region, the start date and the source path before it sends an invoice
            or payment link. The buyer may cancel by email before the first digest is sent and
            receive a full refund. After the first digest is sent, the fee for digests already
            delivered is non-refundable, except where CareGist fails to deliver an agreed
            digest. If CareGist does not deliver an agreed digest within the agreed week, it
            will deliver it late or refund one quarter of the pilot fee for that digest, at the
            buyer&apos;s choice. The pilot does not renew automatically and ends after the
            fourth digest.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">7. Availability and delivery targets</h2>
          <p>
            Public statements labelled as a target are not a guaranteed service level.
            Upstream CQC unavailability, delay, correction, and schema change can affect
            collection and delivery.
          </p>
          <p>
            The delivery target for a Territory Opportunity Brief is three working days
            after both the written scope confirmation and source-path check are complete.
            A working day is Monday to Friday, excluding public holidays in England. If a
            material source issue affects the agreed scope, CareGist will notify the buyer
            and apply the remedy in section 6.
          </p>
          <p>
            The delivery target for each Weekly Digest is the agreed weekday of each of four
            consecutive weeks from the agreed start date. A digest reflects the most recent CQC
            register edition CareGist has reconciled, which may be earlier than the delivery
            date. A digest is not a live feed.
          </p>
          <p>
            CareGist may pause collection, delivery or any free feature to protect accuracy
            or security.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">8. Acceptable use</h2>
          <p>Customers must not:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>use the service unlawfully or to send unlawful unsolicited communications;</li>
            <li>attempt to access another organisation&apos;s data or bypass the agreed scope;</li>
            <li>misrepresent CareGist output as official CQC advice or a guaranteed prediction;</li>
            <li>use CareGist output as the sole basis for a high-impact decision about a person;</li>
            <li>interfere with, reverse engineer, or overload the service.</li>
          </ul>
          <p className="mt-2">The <a href="/acceptable-use" className="text-clay underline">Acceptable Use Policy</a> also applies.</p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">9. Intellectual property and licence</h2>
          <p>
            CQC data remains subject to its source rights and the Open Government Licence.
            CareGist owns or licenses its original software, selection method, summaries,
            interface, and branding. For a one-off product, the customer receives a
            non-exclusive, non-transferable, perpetual licence to use the outputs for its
            internal business purposes. Resale, publication, redistribution, sublicensing or
            bulk sharing of outputs requires CareGist&apos;s written agreement.
          </p>
          <p>
            Outputs must keep the supplied CQC and Open Government Licence attribution and
            CareGist source metadata.
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
            Nothing in these terms limits liability for death or personal injury caused by
            negligence, for fraud or fraudulent misrepresentation, or for any other liability
            that cannot lawfully be limited.
          </p>
          <p>
            Subject to that, neither party is liable for loss of profit, revenue, business,
            contracts or anticipated savings, loss or corruption of data, loss of goodwill, or
            any indirect or consequential loss. CareGist&apos;s total liability arising from a
            product is limited to the fee paid for that product: £{TERRITORY_BRIEF_PRICE_GBP} for
            a Territory Opportunity Brief and £{WEEKLY_DIGEST_PILOT_PRICE_GBP} for a Weekly Digest
            pilot. A signed agreement may set a different limit.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">11. Suspension, termination and changes</h2>
          <p>
            CareGist may suspend access where reasonably necessary for security,
            non-payment, unlawful use, or material breach. Where practical, notice and an
            opportunity to remedy will be given. Material terms changes will be notified to
            registered customers and will not retrospectively alter a completed purchase.
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
