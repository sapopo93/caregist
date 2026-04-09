import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Acceptable Use Policy | CareGist",
  description: "Rules for using the CareGist API and directory. Covers permitted use, prohibited activities, rate limits, and enforcement.",
};

export default function AcceptableUsePage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Acceptable Use Policy</h1>
      <p className="text-dusk text-sm mb-8">Last updated: 28 March 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. Purpose</h2>
          <p>
            This Acceptable Use Policy (&quot;AUP&quot;) governs your use of the CareGist website, API,
            and related services operated by H-Kay Limited (company number 10417923). This AUP
            supplements our <a href="/terms" className="text-clay underline">Terms of Service</a> and{" "}
            <a href="/privacy" className="text-clay underline">Privacy Policy</a>.
          </p>
          <p>
            By using CareGist, you agree to comply with this policy. We may update it from time to time
            and will notify registered users of material changes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. Permitted use</h2>
          <p>You may use CareGist to:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Search for and view information about CQC-registered care providers</li>
            <li>Integrate provider data into your own applications, products, or reports via the API, subject to your subscription tier limits</li>
            <li>Submit genuine reviews based on real experiences with care providers</li>
            <li>Submit enquiries to care providers through our contact forms</li>
            <li>Claim a provider listing if you are authorised to represent that provider</li>
            <li>Export data within the limits of your subscription tier</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. Prohibited activities</h2>
          <p>You must not:</p>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.1 Data misuse</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Scrape, crawl, or bulk-download data beyond the limits of your subscription tier</li>
            <li>Redistribute, resell, or sublicense CareGist data as a competing directory or data product without our prior written consent</li>
            <li>Remove or obscure CQC attribution when displaying provider data sourced from CareGist</li>
            <li>Present CareGist data as your own original data or claim affiliation with the Care Quality Commission</li>
            <li>Use data obtained from CareGist to send unsolicited marketing communications to care providers (spam)</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.2 API abuse</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Attempt to circumvent rate limits, authentication, or tier restrictions</li>
            <li>Create multiple free accounts to avoid purchasing a paid subscription</li>
            <li>Share API keys with third parties or embed them in publicly accessible client-side code</li>
            <li>Use the API to conduct denial-of-service attacks, load testing, or vulnerability scanning without our written permission</li>
            <li>Reverse-engineer, decompile, or attempt to extract source code from the API</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.3 Harmful content</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Submit false, misleading, or defamatory reviews about care providers</li>
            <li>Submit fraudulent provider claims or impersonate a provider representative</li>
            <li>Use the platform to harass, threaten, or intimidate care providers, their staff, or residents</li>
            <li>Submit enquiries that are abusive, fraudulent, or intended to waste a provider&apos;s time</li>
            <li>Post content that is illegal, discriminatory, or violates the rights of others</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">3.4 Technical abuse</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Introduce malware, viruses, or malicious code through the API or website</li>
            <li>Attempt to gain unauthorised access to our systems, databases, or other users&apos; accounts</li>
            <li>Interfere with the availability or performance of the service for other users</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. API usage rules</h2>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.1 Rate limits</h3>
          <p>Each subscription tier has defined burst, daily, 7-day, and monthly limits. These are enforced automatically. When you exceed a limit:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>The API returns HTTP 429 (Too Many Requests)</li>
            <li>Response headers indicate your remaining quota and reset time</li>
            <li>You should implement backoff logic in your application</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.2 API key security</h3>
          <ul className="list-disc pl-6 space-y-1">
            <li>Store API keys securely (environment variables, secrets managers) — never in source code, client-side JavaScript, or public repositories</li>
            <li>Rotate your API key immediately if you suspect it has been compromised (use the /api/v1/auth/rotate-key endpoint)</li>
            <li>Each API key is for use by a single organisation. Pro includes 3 named users, Business includes 10, and larger arrangements run through Enterprise.</li>
          </ul>

          <h3 className="text-lg font-semibold text-bark mt-4 mb-2">4.3 Attribution</h3>
          <p>
            When displaying CareGist data in your application, you must include the following attribution
            in a visible location:
          </p>
          <p className="bg-parchment border border-stone rounded p-3 text-sm mt-2">
            Data source: Care Quality Commission (CQC) via CareGist. CareGist is not an official CQC service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Data storage and caching</h2>
          <p>
            You may store CareGist data only as reasonably necessary for your application&apos;s
            operation (e.g., caching search results for display). You must not:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Build or maintain a separate database containing a substantial portion of the CareGist dataset</li>
            <li>Create local copies or mirrors of the CareGist database</li>
            <li>Store bulk data for offline use beyond your current operational needs</li>
            <li>Retain cached data for longer than 7 days without refreshing from the API</li>
          </ul>
          <p className="mt-2">
            Long-term storage, bulk caching, or systematic replication of the database is prohibited
            without a commercial data licence. Bulk datasets and commercial redistribution licences
            are available under separate agreements — contact{" "}
            <a href="mailto:sales@caregist.co.uk" className="text-clay underline">sales@caregist.co.uk</a>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Competing services</h2>
          <p>
            You may not use CareGist data or the CareGist API to build, operate, or improve a competing
            directory, database, or data product that substantially replicates the CareGist service.
            This includes using CareGist data to seed, train, or populate an alternative care provider
            directory.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Automated data collection</h2>
          <p>
            Automated access to CareGist, including scraping, crawling, or systematic downloading of
            data, is only permitted through the official API and within your subscription tier limits.
            Any automated access that bypasses the API (e.g., scraping web pages) is prohibited
            regardless of the method used.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">8. Fair use</h2>
          <p>
            Even within published rate limits, you must not use the service in a way that places
            excessive load on our systems or attempts to download a substantial portion of the database.
            We reserve the right to limit or suspend accounts that we reasonably believe are attempting
            to replicate the CareGist dataset, even if individual requests are within tier limits.
          </p>
          <p className="mt-2">
            Examples of usage patterns that may trigger fair use review:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Systematically paginating through the entire dataset</li>
            <li>Requesting every provider by ID or slug in sequence</li>
            <li>Running the same broad query repeatedly with different pagination offsets</li>
            <li>Sustained usage at maximum rate limits for extended periods</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">9. Monitoring and enforcement</h2>
          <p>We monitor API usage patterns to detect abuse. If we identify a violation of this policy, we may:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li><strong>Warn</strong> — notify you of the violation and request corrective action</li>
            <li><strong>Throttle</strong> — temporarily reduce your rate limits</li>
            <li><strong>Suspend</strong> — temporarily disable your API key pending investigation</li>
            <li><strong>Terminate</strong> — permanently revoke your account and API access</li>
          </ul>
          <p className="mt-2">
            We will provide reasonable notice before taking enforcement action, except where immediate
            action is necessary to prevent harm to our service, other users, or care providers.
          </p>
          <p className="mt-2">
            Unauthorised use of CareGist data may cause irreparable harm to our business. We reserve
            the right to seek injunctive relief and damages where necessary to protect our data,
            service, and users.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">10. Reporting violations</h2>
          <p>
            If you believe another user is violating this policy, or if you have concerns about content
            on our platform, please report it to{" "}
            <a href="mailto:abuse@caregist.co.uk" className="text-clay underline">abuse@caregist.co.uk</a>.
            We investigate all reports and respond within 5 working days.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">11. Contact</h2>
          <p>
            Questions about this policy: <a href="mailto:legal@caregist.co.uk" className="text-clay underline">legal@caregist.co.uk</a>
          </p>
        </section>

      </div>
    </div>
  );
}
