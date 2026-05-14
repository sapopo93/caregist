/**
 * /app/cookie-settings/page.tsx
 *
 * Standalone cookie-settings page that renders the full preference panel.
 * Accessible directly via /cookie-settings and linked from the footer.
 * Also reachable by the legacy /cookies URL via Next.js rewrites.
 */

import type { Metadata } from "next";
import CookieSettingsClient from "./CookieSettingsClient";

export const metadata: Metadata = {
  title: "Cookie Settings | CareGist",
  description:
    "Manage your cookie preferences for CareGist. Choose which types of cookies you allow us to use.",
  robots: "noindex", // Consent UI pages should not be indexed
};

export default function CookieSettingsPage() {
  return (
    <main className="max-w-2xl mx-auto px-4 py-12 sm:px-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Cookie settings</h1>
      <p className="text-sm text-gray-600 mb-8">
        Under UK PECR (SI 2003/2426) and ICO guidance, we need your informed
        consent before setting any non-essential cookies. Update your preferences
        below at any time. See our{" "}
        <a href="/privacy" className="underline text-blue-600 hover:text-blue-800">
          privacy policy
        </a>{" "}
        and{" "}
        <a href="/cookies" className="underline text-blue-600 hover:text-blue-800">
          cookie policy
        </a>{" "}
        for details.
      </p>
      <CookieSettingsClient />
    </main>
  );
}
