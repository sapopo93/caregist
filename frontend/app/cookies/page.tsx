import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cookie Policy | CareGist",
  description: "How CareGist uses cookies and similar technologies.",
};

export default function CookiePolicyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-2">Cookie Policy</h1>
      <p className="text-dusk text-sm mb-8">Last updated: 28 March 2026</p>

      <div className="prose prose-sm text-charcoal space-y-6" style={{ fontFamily: "Lora" }}>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">1. What are cookies</h2>
          <p>
            Cookies are small text files stored on your device when you visit a website. They are widely
            used to make websites work, remember your preferences, and provide information to the site owner.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">2. How CareGist uses cookies</h2>
          <p>
            CareGist uses a minimal approach to cookies. We do not use advertising cookies, tracking cookies,
            or third-party analytics cookies.
          </p>

          <table className="w-full text-sm border border-stone mt-4">
            <thead>
              <tr className="bg-parchment">
                <th className="text-left p-2 border-b border-stone">Cookie type</th>
                <th className="text-left p-2 border-b border-stone">Purpose</th>
                <th className="text-left p-2 border-b border-stone">Duration</th>
                <th className="text-left p-2 border-b border-stone">Consent required</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="p-2 border-b border-stone">Essential / strictly necessary</td>
                <td className="p-2 border-b border-stone">Session management, security tokens, CSRF protection</td>
                <td className="p-2 border-b border-stone">Session (deleted when you close browser)</td>
                <td className="p-2 border-b border-stone">No (exempt under PECR)</td>
              </tr>
              <tr>
                <td className="p-2 border-b border-stone">Local storage</td>
                <td className="p-2 border-b border-stone">Store your API key and tier for the dashboard, compare list</td>
                <td className="p-2 border-b border-stone">Until you clear browser data or log out</td>
                <td className="p-2 border-b border-stone">No (strictly necessary for functionality)</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">3. What we do not use</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Google Analytics or any third-party analytics service</li>
            <li>Advertising or remarketing cookies</li>
            <li>Social media tracking pixels</li>
            <li>Cross-site tracking cookies</li>
            <li>Fingerprinting or device identification technologies</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">4. Third-party cookies</h2>
          <p>
            When you make a payment through Stripe Checkout, Stripe may set its own cookies on the
            Stripe-hosted checkout page. These are governed by{" "}
            <a href="https://stripe.com/gb/cookie-settings" className="text-clay underline" target="_blank" rel="noopener noreferrer">
              Stripe&apos;s cookie policy
            </a>.
            CareGist does not control these cookies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">5. Managing cookies</h2>
          <p>
            You can control and delete cookies through your browser settings. Most browsers allow you to:
          </p>
          <ul className="list-disc pl-6 space-y-1">
            <li>See what cookies are stored and delete them individually</li>
            <li>Block third-party cookies</li>
            <li>Block all cookies</li>
            <li>Clear all cookies when you close the browser</li>
          </ul>
          <p className="mt-2">
            Note: blocking essential cookies may prevent CareGist from functioning correctly
            (e.g., your dashboard may not load).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">6. Legal basis</h2>
          <p>
            Our use of essential cookies is permitted under Regulation 6 of the Privacy and Electronic
            Communications Regulations 2003 (PECR), which exempts cookies that are strictly necessary
            for providing a service requested by the user. No consent banner is required for these cookies.
          </p>
          <p className="mt-2">
            If we introduce non-essential cookies in the future (such as analytics), we will update this
            policy and implement a consent mechanism before setting those cookies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-bark mt-8 mb-3">7. Contact</h2>
          <p>
            Questions about cookies: <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>
          </p>
        </section>

      </div>
    </div>
  );
}
