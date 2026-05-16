import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | CareGist",
  description:
    "How CareGist collects, uses, and protects your personal data under UK GDPR and the Data Protection Act 2018.",
};

export default function PrivacyPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-12 text-gray-800">
      <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-sm text-gray-500 mb-8">Last updated: 2026-05-14</p>

      {/* 1. Who we are */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">1. Who we are</h2>
        <p className="mb-3">
          CareGist is operated by <strong>H-Kay Limited</strong>, registered in England and Wales
          (company number <span className="font-mono">10417923</span>), with registered
          address at <span className="font-mono">[Company registered address — registered in Reigate; owner to fill exact street address from Companies House public record]</span>.
        </p>
        <p className="mb-3">
          We are the <strong>data controller</strong> for the personal data described in this
          policy. You can contact us at{" "}
          <a href="mailto:privacy@caregist.co.uk" className="text-blue-600 hover:underline">
            privacy@caregist.co.uk
          </a>
          .
        </p>
        <p className="mb-3">
          We are registered with the Information Commissioner&rsquo;s Office (ICO) under
          registration number{" "}
          <span className="font-mono">[ICO reg number — owner fills post-registration]</span>.
        </p>
        <p>
          H-Kay Limited is not required to appoint a Data Protection Officer (DPO) under Article 37
          of the UK GDPR, as our core activities do not involve large-scale processing of special
          category data or systematic monitoring of individuals at scale.
        </p>
      </section>

      {/* 2. What data we collect */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">2. What data we collect</h2>
        <p className="mb-3">We collect and process the following categories of personal data:</p>

        <h3 className="font-semibold mb-2">2.1 Account data</h3>
        <ul className="list-disc list-inside mb-4 space-y-1">
          <li>Name and email address provided on registration.</li>
          <li>
            Password — stored only as a salted hash; we never hold your password in plain text.
          </li>
        </ul>

        <h3 className="font-semibold mb-2">2.2 Reviews and ratings</h3>
        <ul className="list-disc list-inside mb-4 space-y-1">
          <li>
            Review content, star rating, and relationship to the care provider that you submit.
          </li>
          <li>
            Reviews are published publicly together with the name you provide, unless and until your
            account is deleted (see section 10).
          </li>
        </ul>

        <h3 className="font-semibold mb-2">2.3 Claims (provider verification)</h3>
        <ul className="list-disc list-inside mb-4 space-y-1">
          <li>
            Name, email, phone number, job role, and proof of association submitted when claiming a
            CQC provider profile.
          </li>
        </ul>

        <h3 className="font-semibold mb-2">2.4 Payment metadata</h3>
        <ul className="list-disc list-inside mb-4 space-y-1">
          <li>
            Stripe customer ID and subscription tier. We do <strong>not</strong> store card numbers,
            expiry dates, or CVV codes. All card processing is handled by Stripe Inc. under their
            own PCI-DSS certification.
          </li>
        </ul>

        <h3 className="font-semibold mb-2">2.5 Session and IP logs</h3>
        <ul className="list-disc list-inside mb-4 space-y-1">
          <li>IP address, browser user-agent, request path, and response status code.</li>
          <li>Session tokens stored in HttpOnly cookies.</li>
          <li>These logs are retained for 90 days (sessions) and 30 days (pipeline/API logs).</li>
        </ul>

        <h3 className="font-semibold mb-2">2.6 Care provider directory data (CQC)</h3>
        <p>
          Our directory contains provider names, addresses, phone numbers, CQC ratings, and service
          types sourced from the CQC public API. Where this data includes personal data (e.g.,
          registered manager names), our lawful basis is legitimate interest (Article 6(1)(f)).
        </p>
      </section>

      {/* 3. Lawful bases */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">3. Lawful bases for processing</h2>
        <p className="mb-3">
          We rely on three lawful bases under UK GDPR Article 6:
        </p>
        <ul className="list-disc list-inside space-y-2">
          <li>
            <strong>Article 6(1)(b) — Contract performance:</strong> processing your account data,
            enabling API access, and processing subscriptions is necessary to perform our contract
            with you.
          </li>
          <li>
            <strong>Article 6(1)(f) — Legitimate interests:</strong> aggregating and publishing CQC
            public data, operating security logging, and verifying provider claims. We have carried
            out Legitimate Interest Assessments (LIAs) for each; copies are available on request at{" "}
            <a href="mailto:privacy@caregist.co.uk" className="text-blue-600 hover:underline">
              privacy@caregist.co.uk
            </a>
            .
          </li>
          <li>
            <strong>Article 6(1)(a) — Consent:</strong> sending marketing emails. Consent is
            collected separately at sign-up, is granular and unbundled from service terms, and may
            be withdrawn at any time (see section 12).
          </li>
        </ul>
      </section>

      {/* 4. How we use your data */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">4. How we use your data</h2>
        <ul className="list-disc list-inside space-y-2">
          <li>Creating and managing your account.</li>
          <li>Processing subscription payments via Stripe.</li>
          <li>Sending transactional emails (account confirmation, password reset) via Resend.</li>
          <li>Publishing care-provider reviews you submit.</li>
          <li>Verifying care-provider claims.</li>
          <li>Aggregating and displaying CQC public data.</li>
          <li>Monitoring service health, enforcing rate limits, and preventing abuse.</li>
          <li>Sending marketing updates — only where you have given separate consent.</li>
          <li>Complying with legal and regulatory obligations.</li>
        </ul>
      </section>

      {/* 5. Sub-processors */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">5. Sub-processors</h2>
        <p className="mb-4">
          We engage the following third-party data processors under written data processing
          agreements (DPAs):
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 px-3 py-2 text-left">Processor</th>
                <th className="border border-gray-300 px-3 py-2 text-left">Purpose</th>
                <th className="border border-gray-300 px-3 py-2 text-left">Location</th>
                <th className="border border-gray-300 px-3 py-2 text-left">DPA / Privacy link</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-3 py-2">Stripe Inc.</td>
                <td className="border border-gray-300 px-3 py-2">Payment processing &amp; billing</td>
                <td className="border border-gray-300 px-3 py-2">US / EU (SCC)</td>
                <td className="border border-gray-300 px-3 py-2">
                  <a
                    href="https://stripe.com/en-gb/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    stripe.com/privacy
                  </a>
                </td>
              </tr>
              <tr className="bg-gray-50">
                <td className="border border-gray-300 px-3 py-2">Resend</td>
                <td className="border border-gray-300 px-3 py-2">Transactional email delivery</td>
                <td className="border border-gray-300 px-3 py-2">US (SCC)</td>
                <td className="border border-gray-300 px-3 py-2">
                  <a
                    href="https://resend.com/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    resend.com/privacy
                  </a>
                </td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-3 py-2">Sentry (Functional Software Inc.)</td>
                <td className="border border-gray-300 px-3 py-2">Error monitoring &amp; performance</td>
                <td className="border border-gray-300 px-3 py-2">US (SCC)</td>
                <td className="border border-gray-300 px-3 py-2">
                  <a
                    href="https://sentry.io/privacy/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    sentry.io/privacy
                  </a>
                </td>
              </tr>
              <tr className="bg-gray-50">
                <td className="border border-gray-300 px-3 py-2">Amazon Web Services (AWS)</td>
                <td className="border border-gray-300 px-3 py-2">Cloud hosting (primary region: eu-west-2, London)</td>
                <td className="border border-gray-300 px-3 py-2">UK (EU-West-2)</td>
                <td className="border border-gray-300 px-3 py-2">
                  <a
                    href="https://aws.amazon.com/privacy/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    aws.amazon.com/privacy
                  </a>
                </td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-3 py-2">Neon (Neon Inc.)</td>
                <td className="border border-gray-300 px-3 py-2">Serverless PostgreSQL database</td>
                <td className="border border-gray-300 px-3 py-2">EU (AWS eu-west-1)</td>
                <td className="border border-gray-300 px-3 py-2">
                  <a
                    href="https://neon.tech/privacy-policy"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    neon.tech/privacy-policy
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 6. International transfers */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">6. International transfers</h2>
        <p className="mb-3">
          Our primary hosting is on AWS eu-west-2 (London), within the UK. However, some
          sub-processors may transfer data internationally:
        </p>
        <ul className="list-disc list-inside space-y-2">
          <li>
            <strong>Stripe:</strong> data may be processed in the United States, protected by
            Standard Contractual Clauses (SCCs) approved under UK GDPR.
          </li>
          <li>
            <strong>Resend:</strong> email delivery infrastructure is US-based, protected by SCCs.
          </li>
          <li>
            <strong>Sentry:</strong> error data may transit to US servers, protected by SCCs.
          </li>
        </ul>
        <p className="mt-3">
          In each case we have satisfied ourselves that appropriate safeguards exist under Article
          46 UK GDPR before any transfer takes place.
        </p>
      </section>

      {/* 7. Retention */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">7. Retention periods</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 px-3 py-2 text-left">Data type</th>
                <th className="border border-gray-300 px-3 py-2 text-left">Retention period</th>
                <th className="border border-gray-300 px-3 py-2 text-left">Legal basis for retention</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 px-3 py-2">Account data (name, email, password hash)</td>
                <td className="border border-gray-300 px-3 py-2">7 years after account deletion</td>
                <td className="border border-gray-300 px-3 py-2">UK tax law (HMRC record-keeping obligations)</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="border border-gray-300 px-3 py-2">Reviews authored by you</td>
                <td className="border border-gray-300 px-3 py-2">Indefinite — your name is redacted to &ldquo;Former user&rdquo; upon account deletion</td>
                <td className="border border-gray-300 px-3 py-2">Legitimate interest (public-interest information about care providers)</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-3 py-2">Session tokens &amp; IP logs</td>
                <td className="border border-gray-300 px-3 py-2">90 days</td>
                <td className="border border-gray-300 px-3 py-2">Legitimate interest (security monitoring)</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="border border-gray-300 px-3 py-2">API / pipeline logs</td>
                <td className="border border-gray-300 px-3 py-2">30 days</td>
                <td className="border border-gray-300 px-3 py-2">Legitimate interest (operational monitoring)</td>
              </tr>
              <tr>
                <td className="border border-gray-300 px-3 py-2">Payment metadata (Stripe customer ID)</td>
                <td className="border border-gray-300 px-3 py-2">7 years after last transaction</td>
                <td className="border border-gray-300 px-3 py-2">UK tax law</td>
              </tr>
              <tr className="bg-gray-50">
                <td className="border border-gray-300 px-3 py-2">Claims data</td>
                <td className="border border-gray-300 px-3 py-2">Duration of claim + 3 years for dispute resolution</td>
                <td className="border border-gray-300 px-3 py-2">Legitimate interest</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 8. Your rights */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">8. Your rights</h2>
        <p className="mb-3">Under UK GDPR you have the following rights:</p>
        <ul className="list-disc list-inside space-y-2">
          <li>
            <strong>Right of access (Article 15):</strong> request a copy of the personal data we
            hold about you.
          </li>
          <li>
            <strong>Right to rectification (Article 16):</strong> ask us to correct inaccurate or
            incomplete data.
          </li>
          <li>
            <strong>Right to erasure (Article 17):</strong> ask us to delete your data, subject to
            our legal retention obligations.
          </li>
          <li>
            <strong>Right to restriction of processing (Article 18):</strong> ask us to pause
            processing while a dispute is resolved.
          </li>
          <li>
            <strong>Right to data portability (Article 20):</strong> receive your data in a
            machine-readable format where processing is based on consent or contract.
          </li>
          <li>
            <strong>Right to object (Article 21):</strong> object to processing based on legitimate
            interest; we will cease unless we can demonstrate compelling legitimate grounds.
          </li>
          <li>
            <strong>Right to withdraw consent (Article 7(3)):</strong> withdraw marketing consent
            at any time without affecting the lawfulness of prior processing.
          </li>
          <li>
            <strong>Right to complain to the ICO:</strong> you may lodge a complaint with the
            Information Commissioner&rsquo;s Office at any time (see section 9).
          </li>
        </ul>
      </section>

      {/* 9. How to exercise rights */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">9. How to exercise your rights</h2>
        <p className="mb-3">
          Email us at{" "}
          <a href="mailto:privacy@caregist.co.uk" className="text-blue-600 hover:underline">
            privacy@caregist.co.uk
          </a>
          . We will respond within <strong>30 days</strong> of receipt. We may ask you to verify
          your identity before processing your request.
        </p>
        <p>
          You also have the right to complain to the Information Commissioner&rsquo;s Office (ICO)
          at{" "}
          <a
            href="https://ico.org.uk/concerns"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            https://ico.org.uk/concerns
          </a>{" "}
          or by calling 0303 123 1113.
        </p>
      </section>

      {/* 10. What we retain after account deletion */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">10. What we retain after account deletion</h2>
        <p className="mb-3">
          When you delete your account, your profile, name, and email address are removed from our
          active systems. However:
        </p>
        <ul className="list-disc list-inside space-y-2 mb-3">
          <li>
            Reviews you authored are retained with your name redacted to &ldquo;Former user&rdquo;.
            Other readers rely on review history; we believe this balance protects your privacy
            while preserving public-interest information about care providers.
          </li>
          <li>
            Payment records (Stripe customer ID and transaction history) are retained for 7 years
            to comply with HMRC tax obligations.
          </li>
          <li>Anonymised aggregate statistics derived from your usage may be retained indefinitely.</li>
        </ul>
        <p>
          Backup media containing your data will be overwritten or deleted within 90 days of account
          deletion in accordance with our backup rotation schedule.
        </p>
      </section>

      {/* 11. Cookies */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">11. Cookies</h2>
        <p className="mb-3">
          We use strictly necessary cookies for authentication (HttpOnly, Secure, SameSite=Lax
          session cookies) and, with your consent, analytics and functional cookies.
        </p>
        <p>
          You can manage your cookie preferences at any time via our{" "}
          <a href="/cookie-settings" className="text-blue-600 hover:underline">
            cookie settings page
          </a>
          . Refusing non-essential cookies does not affect your ability to use the core service.
        </p>
      </section>

      {/* 12. Marketing communications */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">12. Marketing communications</h2>
        <p className="mb-3">
          We send marketing emails only where you have given <strong>separate, granular consent</strong>{" "}
          at the point of sign-up. This consent is collected independently of the service terms and
          is not a condition of using CareGist.
        </p>
        <p>
          Every marketing email contains an unsubscribe link. You may also withdraw consent at any
          time by emailing{" "}
          <a href="mailto:privacy@caregist.co.uk" className="text-blue-600 hover:underline">
            privacy@caregist.co.uk
          </a>{" "}
          or updating your preferences in the account dashboard. Withdrawal of consent does not
          affect the lawfulness of marketing sent before withdrawal.
        </p>
      </section>

      {/* 13. Security */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">13. Security</h2>
        <ul className="list-disc list-inside space-y-2">
          <li>All data in transit is encrypted using TLS 1.2 or higher.</li>
          <li>Database backups are encrypted at rest using KMS-managed customer master keys (CMK).</li>
          <li>
            Session cookies are set with <code>HttpOnly</code>, <code>Secure</code>, and{" "}
            <code>SameSite=Lax</code> flags to mitigate XSS and CSRF risks.
          </li>
          <li>Admin actions are logged in a tamper-evident audit log.</li>
          <li>
            We apply the principle of least privilege to all internal system access and conduct
            periodic access reviews.
          </li>
        </ul>
        <p className="mt-3">
          If you discover a security vulnerability, please report it responsibly to{" "}
          <a href="mailto:privacy@caregist.co.uk" className="text-blue-600 hover:underline">
            privacy@caregist.co.uk
          </a>
          .
        </p>
      </section>

      {/* 14. Changes to this policy */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">14. Changes to this policy</h2>
        <p>
          We may update this policy from time to time. For material changes (for example, a new
          category of data or a new lawful basis), we will notify you by email before the change
          takes effect. Minor clarifications will be published here with an updated &ldquo;Last
          updated&rdquo; date. Continued use of CareGist after a notified material change
          constitutes acceptance of the revised policy.
        </p>
      </section>

      {/* 15. Contact */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-3">15. Contact</h2>
        <p className="mb-3">
          <strong>Data controller:</strong> H-Kay Limited,{" "}
          <span className="font-mono">[Company registered address — registered in Reigate; owner to fill exact street address from Companies House public record]</span>
        </p>
        <p className="mb-3">
          <strong>Privacy enquiries:</strong>{" "}
          <a href="mailto:privacy@caregist.co.uk" className="text-blue-600 hover:underline">
            privacy@caregist.co.uk
          </a>
        </p>
        <p>
          <strong>Information Commissioner&rsquo;s Office (ICO):</strong>{" "}
          <a
            href="https://ico.org.uk"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            ico.org.uk
          </a>{" "}
          &mdash; Wycliffe House, Water Lane, Wilmslow, Cheshire SK9 5AF &mdash; 0303 123 1113
        </p>
      </section>
    </main>
  );
}
