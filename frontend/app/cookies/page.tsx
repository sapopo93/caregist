import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cookie and Browser Storage Policy | CareGist",
  description: "How CareGist uses strictly necessary cookies, browser storage, and operational telemetry.",
};

export default function CookiePolicyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="mb-2 text-3xl font-bold">Cookie and Browser Storage Policy</h1>
      <p className="mb-8 text-sm text-dusk">Version 2.0 · In force from 9 August 2026</p>

      <div className="prose prose-sm space-y-7 text-charcoal" style={{ fontFamily: "Lora" }}>
        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">1. Current approach</h2>
          <p>
            CareGist uses strictly necessary cookies and local browser storage for sign-in,
            security, requested navigation, and user-selected preferences. CareGist does not
            use advertising, remarketing, social-media tracking, or cross-site tracking cookies.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">2. Storage used</h2>
          <div className="overflow-x-auto">
            <table className="w-full border border-stone text-sm">
              <thead>
                <tr className="bg-parchment">
                  <th className="border-b border-stone p-2 text-left">Item</th>
                  <th className="border-b border-stone p-2 text-left">Purpose</th>
                  <th className="border-b border-stone p-2 text-left">Typical duration</th>
                </tr>
              </thead>
              <tbody>
                <tr><td className="border-b border-stone p-2">Authentication session cookie</td><td className="border-b border-stone p-2">Keeps an authenticated session and protects gated routes.</td><td className="border-b border-stone p-2">Session or configured expiry.</td></tr>
                <tr><td className="border-b border-stone p-2">Signed-in user and displayed tier</td><td className="border-b border-stone p-2">Renders the current navigation and fail-closed entitlement state. No password, API key, or signing secret is intentionally stored.</td><td className="border-b border-stone p-2">Until logout or browser data is cleared.</td></tr>
                <tr><td className="border-b border-stone p-2">Provider comparison list</td><td className="border-b border-stone p-2">Remembers providers the user explicitly selected for comparison.</td><td className="border-b border-stone p-2">Until the list or browser data is cleared.</td></tr>
                <tr><td className="border-b border-stone p-2">Post-verification path</td><td className="border-b border-stone p-2">Returns a user to an approved CareGist route after email verification.</td><td className="border-b border-stone p-2">Removed after use or when browser data is cleared.</td></tr>
                <tr><td className="p-2">Storage-notice choice</td><td className="p-2">Prevents the informational storage notice from being shown repeatedly.</td><td className="p-2">Until browser data is cleared.</td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">3. Operational telemetry</h2>
          <p>
            CareGist records first-party request, security, feature-use, delivery, and error
            telemetry needed to operate and improve the service. This may include timestamps,
            requested routes, browser information, security identifiers, and account or
            organisation identifiers when signed in. CareGist does not use this telemetry for
            third-party advertising or cross-site profiling.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">4. Stripe-hosted checkout</h2>
          <p>
            When an approved paid checkout is enabled, Stripe may set cookies on its hosted
            checkout or billing-management pages. Stripe controls those cookies under its own{" "}
            <a href="https://stripe.com/gb/cookie-settings" className="text-clay underline" target="_blank" rel="noopener noreferrer">cookie policy</a>.
          </p>
        </section>

        <section>
          <h2 className="mb-3 mt-8 text-xl font-bold text-bark">5. Managing storage</h2>
          <p>
            Browser settings can remove or block cookies and local storage. Blocking strictly
            necessary storage may prevent sign-in, account management, comparison, or verified
            checkout from working. If CareGist introduces non-essential browser storage, this
            policy and the consent mechanism will be updated before it is used.
          </p>
          <p>
            Questions may be sent to{" "}
            <a href="mailto:privacy@caregist.co.uk" className="text-clay underline">privacy@caregist.co.uk</a>.
          </p>
        </section>
      </div>
    </main>
  );
}
