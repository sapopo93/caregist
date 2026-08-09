import type { Metadata } from "next";
import Link from "next/link";
import { DM_Sans, Playfair_Display } from "next/font/google";
import { connection } from "next/server";

import "./globals.css";

import AuthNav from "@/components/AuthNav";
import CompareBar from "@/components/CompareBar";
import CookieConsent from "@/components/CookieConsent";
import SupportWidgetMount from "@/components/SupportWidgetMount";

import { getServerApiBase } from "@/lib/server-api-config";

const SITE_URL = "https://caregist.co.uk";

async function getDataRefreshDate(): Promise<string | null> {
  try {
    const apiBase = getServerApiBase();
    const response = await fetch(`${apiBase}/api/v1/health/freshness`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return null;
    const data = await response.json();
    const retrievedAt = data?.source?.sourceRetrievedAt;
    if (!retrievedAt) return null;
    return new Date(retrievedAt).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return null;
  }
}

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-dm-sans",
  display: "swap",
});

const playfairDisplay = Playfair_Display({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--font-playfair-display",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "CareGist | Search UK CQC Care Providers",
  description:
    "Track CQC market movement, new registrations, Inadequate providers, Requires Improvement providers, and care-sector opportunity lists.",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    title: "CareGist | Search UK CQC Care Providers",
    description:
      "Track CQC market movement, new registrations, Inadequate providers, Requires Improvement providers, and care-sector opportunity lists.",
    siteName: "CareGist",
    type: "website",
    locale: "en_GB",
    images: [{ url: "/opengraph-image" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CareGist | Search UK CQC Care Providers",
    description:
      "Track CQC market movement, new registrations, Inadequate providers, Requires Improvement providers, and care-sector opportunity lists.",
    images: ["/twitter-image"],
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  await connection();
  const dataRefreshDate = await getDataRefreshDate();

  return (
    <html lang="en" className={`${dmSans.variable} ${playfairDisplay.variable}`}>
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </head>
      <body className="flex min-h-screen flex-col">
        <header className="relative border-b border-stone bg-bark px-6 py-4 text-cream">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <Link href="/" className="flex items-center">
              <img src="/logo-lockup-reverse.svg" alt="CareGist" className="h-12 w-auto md:h-14" />
            </Link>

            <div className="flex items-center justify-end gap-3">
              <Link
                href="/search?opportunity=new_90"
                className="rounded-full bg-amber px-4 py-2 text-sm font-semibold text-charcoal transition hover:bg-cream md:hidden"
              >
                Lists
              </Link>
              <nav className="hidden items-center gap-5 text-sm font-medium md:flex">
                <Link href="/search?opportunity=new_90" className="hover:text-amber">
                  Opportunity lists
                </Link>
                <Link href="/lead-list" className="hover:text-amber">
                  Lead lists
                </Link>
                <Link href="/pricing" className="hover:text-amber">
                  Pricing
                </Link>
                <Link href="/api" className="hover:text-amber">
                  API
                </Link>
                <Link href="/why-caregist" className="hover:text-amber">
                  About
                </Link>
                <Link
                  href="/lead-list?opportunity=new_90"
                  className="rounded-full bg-amber px-4 py-2 text-sm font-semibold text-charcoal transition hover:bg-cream"
                >
                  Get intelligence
                </Link>
              </nav>
              <AuthNav />
            </div>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <CompareBar />
        <CookieConsent />
        <SupportWidgetMount />

        <footer className="bg-charcoal px-6 py-8 text-sm text-stone">
          <div className="mx-auto max-w-6xl">
            <p className="mb-2">
              Contains public sector information licensed under the{" "}
              <a
                href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
                className="underline hover:text-cream"
                target="_blank"
                rel="noopener noreferrer"
              >
                Open Government Licence v3.0
              </a>
              .
            </p>
            {dataRefreshDate && (
              <p className="mb-2 text-dusk">
                CQC data last updated: {dataRefreshDate}.
              </p>
            )}
            <p className="mb-2 text-dusk">
              CareGist is not an official CQC service.
            </p>
            <p className="text-dusk">
              If you have concerns about care quality, contact CQC directly at{" "}
              <a href="https://www.cqc.org.uk/contact-us" className="underline hover:text-cream">
                cqc.org.uk/contact-us
              </a>{" "}
              or call 03000 616161.
            </p>
            <div className="mt-4 flex flex-wrap gap-4 text-dusk">
              <Link href="/privacy" className="underline hover:text-cream">
                Privacy Policy
              </Link>
              <Link href="/terms" className="underline hover:text-cream">
                Terms of Service
              </Link>
              <Link href="/acceptable-use" className="underline hover:text-cream">
                Acceptable Use
              </Link>
              <Link href="/review-policy" className="underline hover:text-cream">
                Review Policy
              </Link>
              <Link href="/cookies" className="underline hover:text-cream">
                Cookies
              </Link>
              <Link href="/data-status" className="underline hover:text-cream">
                Data Status
              </Link>
              <Link href="/search" className="underline hover:text-cream">
                Opportunity lists
              </Link>
              <Link href="/find-care" className="underline hover:text-cream">
                Find Care
              </Link>
              <Link href="/groups" className="underline hover:text-cream">
                Care Groups
              </Link>
              <Link href="/pricing" className="underline hover:text-cream">
                Pricing
              </Link>
              <Link href="/api" className="underline hover:text-cream">
                API
              </Link>
              <Link href="/why-caregist" className="underline hover:text-cream">
                Why CareGist
              </Link>
              <Link href="/lead-list" className="underline hover:text-cream">
                Get intelligence
              </Link>
              <a href="mailto:hello@caregist.co.uk" className="underline hover:text-cream">
                Contact
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
