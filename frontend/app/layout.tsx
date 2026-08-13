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

const SITE_URL = "https://www.caregist.co.uk";

async function getDataCurrentAsOf(): Promise<string | null> {
  try {
    const apiBase = getServerApiBase();
    const response = await fetch(`${apiBase}/api/v1/health/freshness`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return null;
    const data = await response.json();
    if (data?.status !== "fresh") return null;
    const retrievedAt = data?.sourceRetrievedAt;
    if (!retrievedAt) return null;
    const retrieved = new Date(retrievedAt);
    if (Number.isNaN(retrieved.getTime())) return null;
    return retrieved.toLocaleString("en-GB", {
      dateStyle: "long",
      timeStyle: "short",
      timeZone: "UTC",
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
  title: "CareGist | CQC Signal Intelligence",
  description:
    "Search CQC-registered services for free and turn verified new registrations and rating changes into evidence-linked team workflows.",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    title: "CareGist | CQC Signal Intelligence",
    description:
      "Verified CQC new registrations and rating changes with traceable source evidence.",
    siteName: "CareGist",
    type: "website",
    locale: "en_GB",
    images: [{ url: "/opengraph-image" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CareGist | CQC Signal Intelligence",
    description:
      "Verified CQC new registrations and rating changes with traceable source evidence.",
    images: ["/twitter-image"],
  },
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  await connection();
  const dataCurrentAsOf = await getDataCurrentAsOf();

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
                href="/pricing"
                className="rounded-full bg-amber px-4 py-2 text-sm font-semibold text-charcoal transition hover:bg-cream md:hidden"
              >
                Radar
              </Link>
              <nav aria-label="Primary" className="hidden items-center gap-5 text-sm font-medium md:flex">
                <Link href="/search" className="hover:text-amber">
                  Directory
                </Link>
                <Link href="/pricing" className="hover:text-amber">
                  Radar
                </Link>
                <Link href="/intelligence-feed" className="hover:text-amber">
                  Intelligence Feed
                </Link>
                <Link href="/why-caregist" className="hover:text-amber">
                  About
                </Link>
                <Link
                  href="/pricing"
                  className="rounded-full bg-amber px-4 py-2 text-sm font-semibold text-charcoal transition hover:bg-cream"
                >
                  Compare plans
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
            {dataCurrentAsOf && (
              <p className="mb-2 text-stone">
                Data current as of {dataCurrentAsOf} UTC.
              </p>
            )}
            <p className="mb-2 text-stone">
              CareGist is not an official CQC service.
            </p>
            <p className="text-stone">
              If you have concerns about care quality, contact CQC directly at{" "}
              <a href="https://www.cqc.org.uk/contact-us" className="underline hover:text-cream">
                cqc.org.uk/contact-us
              </a>{" "}
              or call 03000 616161.
            </p>
            <div className="mt-4 flex flex-wrap gap-4 text-stone">
              <Link href="/privacy" className="underline hover:text-cream">
                Privacy Policy
              </Link>
              <Link href="/terms" className="underline hover:text-cream">
                Terms of Service
              </Link>
              <Link href="/acceptable-use" className="underline hover:text-cream">
                Acceptable Use
              </Link>
              <Link href="/cookies" className="underline hover:text-cream">
                Cookies
              </Link>
              <Link href="/data-status" className="underline hover:text-cream">
                Data Status
              </Link>
              <Link href="/search" className="underline hover:text-cream">
                Directory
              </Link>
              <Link href="/find-care" className="underline hover:text-cream">
                Find Care
              </Link>
              <Link href="/pricing" className="underline hover:text-cream">
                Pricing
              </Link>
              <Link href="/intelligence-feed" className="underline hover:text-cream">
                Intelligence Feed
              </Link>
              <Link href="/why-caregist" className="underline hover:text-cream">
                Why CareGist
              </Link>
              <a href="mailto:support@caregist.co.uk" className="underline hover:text-cream">
                Contact
              </a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
