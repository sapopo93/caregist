import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | CareGist",
  description: "Terms governing your use of the CareGist Directory. Includes eligibility, payments, intellectual property, acceptable use, and liability.",
};

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
      <p className="text-dusk text-sm mb-6">Last updated: 9 August 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <p>
            These Terms of Service (&quot;Terms&quot;) govern your use of the CareGist Directory
            website (the &quot;Service&quot;), operated by Henry Mlalazi trading as CareGist
            (&quot;CareGist&quot;, &quot;we&quot;, &quot;us&quot;, &quot;our&quot;).
          </p>
          <p>
            By accessing or using the Service, you agree to be bound by these Terms. If you do not
            agree, do not use the Service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. About the Service</h2>
          <p>
            CareGist Directory is a searchable directory of CQC-registered care providers in England.
            It provides:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Search and browse functionality for care providers by location, service type, and rating</li>
            <li>Provider detail pages with CQC data, ratings, and contact information</li>
            <li>Lead enquiry services connecting care sector buyers with registered providers</li>
            <li>Paid access to exported lead data and contact information</li>
          </ul>
          <p className="mt-2">
            The Service uses public sector information from the <strong>Care Quality Commission
            (CQC)</strong>, licensed under the Open Government Licence v3.0. CareGist is{" "}
            <strong>not affiliated with, endorsed by, or connected to the CQC</strong>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Eligibility</h2>
          <p>
            You must be at least 18 years old to use the Service. By using the Service, you represent
            that you are 18 or older.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Accounts</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>You are responsible for maintaining the confidentiality of your account credentials</li>
            <li>You are responsible for all activity under your account</li>
            <li>You must provide accurate, complete information when creating an account</li>
            <li>We reserve the right to suspend or terminate accounts that violate these Terms</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Payments and Lead Purchases</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.1 Payment Processing</h3>
          <p>
            Payments are processed by <strong>Stripe</strong>, a third-party payment processor. By
            making a purchase, you agree to Stripe&apos;s terms of service. We do not store full
            payment card details.
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.2 Lead Data</h3>
          <p>
            Lead data provided through the Service includes information from CQC public records and,
            where applicable, lead enquiry submissions. We do not guarantee:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>That a provider is currently accepting new clients</li>
            <li>The accuracy of any provider&apos;s contact details (sourced from CQC and displayed as published)</li>
            <li>That any provider will respond to your enquiry</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.3 Digital content, cancellation and refunds</h3>
          <p>
            A purchased dataset is digital content. At checkout, you may expressly request that we
            supply it immediately, before the end of the 14-day cancellation period, and acknowledge
            that you lose the statutory right to cancel once download access is provided. We will not
            begin immediate supply unless you give both confirmations using the required checkout box.
          </p>
          <p className="mt-2">
            This cancellation waiver does not affect your statutory remedies if digital content is
            faulty, misdescribed, or not supplied with reasonable care and skill. If the dataset is
            materially inaccurate or unusable, contact us within 14 days so we can investigate and
            provide an appropriate remedy, which may include repair, replacement, or refund. Contact{" "}
            <a href="mailto:henry.mlalazi@gmail.com" className="text-clay underline">
              henry.mlalazi@gmail.com
            </a>
            .
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.4 Pricing</h3>
          <p>
            Pricing is displayed on the Service and may change. Changes do not affect purchases
            already made. CareGist is not currently VAT registered, so VAT is not currently charged.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Intellectual Property</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">5.1 Our Content</h3>
          <p>
            The CareGist Directory website design, search functionality, lead system, branding, and
            original content are owned by or licensed to CareGist. All rights reserved.
          </p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">5.2 CQC Data</h3>
          <p>
            CQC data displayed on the Service is:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>&copy; Care Quality Commission, used under the Open Government Licence v3.0</li>
            <li>Not owned by CareGist</li>
            <li>Provided for informational purposes</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">5.3 User Content</h3>
          <p>
            By submitting lead enquiries or other content through the Service, you grant CareGist a
            non-exclusive, royalty-free licence to use that content to provide the Service (including
            sharing with the provider you are enquiring about).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Acceptable Use</h2>
          <p>You agree not to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Use the Service for any unlawful purpose</li>
            <li>Scrape, harvest, or bulk-download data from the Service without permission</li>
            <li>Submit false or misleading lead enquiries</li>
            <li>Impersonate any person or entity</li>
            <li>Interfere with the operation of the Service</li>
            <li>Use the Service to send unsolicited communications (spam)</li>
            <li>Reverse engineer or attempt to extract the source code</li>
          </ul>
          <p className="mt-2">
            See our{" "}
            <a href="/acceptable-use" className="text-clay underline">
              Acceptable Use Policy
            </a>{" "}
            for full details.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Third-Party Links and Data</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">7.1 CQC Data</h3>
          <p>
            Care provider information displayed on the Service is sourced from the{" "}
            <strong>Care Quality Commission</strong> and is provided <strong>&quot;as is&quot;</strong>.
            CareGist:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Does not verify, endorse, or guarantee the accuracy of CQC data</li>
            <li>Displays data as published by CQC</li>
            <li>
              Encourages users to verify information with CQC directly at{" "}
              <a href="https://www.cqc.org.uk" className="text-clay underline" target="_blank" rel="noopener noreferrer">
                www.cqc.org.uk
              </a>{" "}
              for critical decisions
            </li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">7.2 External Links</h3>
          <p>
            The Service contains links to third-party websites (e.g., provider websites, CQC
            inspection reports). We are not responsible for the content or practices of these sites.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Disclaimers</h2>
          <p>
            THE SERVICE IS PROVIDED ON AN &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; BASIS,
            WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Accuracy, completeness, or timeliness of CQC data</li>
            <li>Availability of the Service (we aim for high availability but do not guarantee uninterrupted service)</li>
            <li>Fitness for a particular purpose</li>
            <li>Non-infringement</li>
          </ul>
          <p className="mt-2">
            Care provider information is sourced from CQC public data.{" "}
            <strong>
              Always verify critical information directly with CQC or the provider before making care
              decisions.
            </strong>
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Limitation of Liability</h2>
          <p>To the fullest extent permitted by applicable law:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>
              CareGist shall not be liable for any indirect, incidental, special, consequential, or
              punitive damages
            </li>
            <li>
              CareGist&apos;s total liability for any claim relating to the Service shall not exceed
              the amount paid by you to CareGist in the 12 months preceding the claim, or &pound;100
              if no payment was made
            </li>
            <li>
              Nothing in these Terms limits liability for death or personal injury caused by
              negligence, fraud, or any liability that cannot be excluded by law
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Indemnification</h2>
          <p>
            You agree to indemnify and hold harmless CareGist and its operators from any claims,
            damages, or expenses arising from:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Your use of the Service</li>
            <li>Your violation of these Terms</li>
            <li>Your violation of any third-party rights</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Termination</h2>
          <p>
            We may suspend or terminate your access to the Service at any time, with or without cause,
            without prior notice. Upon termination:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Your right to use the Service ceases immediately</li>
            <li>Data retention follows our{" "}
              <a href="/privacy" className="text-clay underline">Privacy Policy</a>
            </li>
            <li>Any outstanding payment obligations survive termination</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">12. Changes to Terms</h2>
          <p>
            We reserve the right to modify these Terms at any time. Changes will be posted on this
            page with an updated &quot;Last updated&quot; date. Material changes will be notified to
            registered users. Continued use after changes constitutes acceptance.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">13. Governing Law</h2>
          <p>
            These Terms are governed by the laws of <strong>England and Wales</strong>. Any disputes
            shall be subject to the exclusive jurisdiction of the English courts.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">14. Contact</h2>
          <p>
            For questions about these Terms:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>
              <strong>Email:</strong>{" "}
              <a href="mailto:henry.mlalazi@gmail.com" className="text-clay underline">
                henry.mlalazi@gmail.com
              </a>
            </li>
          </ul>
        </section>

        <p className="italic text-dusk mt-8 pt-4 border-t border-stone">
          These Terms of Service are effective from 8 August 2026.
        </p>

      </div>
    </div>
  );
}
